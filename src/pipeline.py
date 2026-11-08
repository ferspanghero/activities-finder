"""Pipeline orchestrator: fetch -> parse -> health checks -> venue enrichment -> categorize."""

import logging
from dataclasses import dataclass, field, replace
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from src.categories import categorize
from src.cities import canonical_city
from src.fetch_sources import fetch_raw_sources
from src.geocode import lookup_from_pages, lookup_venues
from src.models import Event, FetchResult, SourceStatus
from src.sources import SOURCES, source_host
from src.venues import VenueBook

logger = logging.getLogger(__name__)

_ZERO_EVENTS_WARNING = "0 events parsed from a successful fetch; page layout may have changed"


@dataclass(slots=True)
class PipelineResult:
    """Enriched events from every source plus one status per source."""

    events: list[Event] = field(default_factory=list)
    source_statuses: list[SourceStatus] = field(default_factory=list)


def _dispatch_parser(fetch_result: FetchResult) -> list[Event]:
    """Route a FetchResult to its source's parser (unknown sources yield no events)."""
    spec = SOURCES.get(fetch_result.source_id)

    if spec is None:
        return []

    return spec.parser(fetch_result.content, fetch_result.url, fetch_result.from_date, fetch_result.to_date)


def _coverage_warning(fetch_result: FetchResult) -> str | None:
    """Warn when a fixed-window page (this week/month) ends before the requested range does."""
    spec = SOURCES.get(fetch_result.source_id)

    if not (spec and spec.listed_through and isinstance(fetch_result.content, str)):
        return None

    last = spec.listed_through(fetch_result.content, fetch_result.from_date)

    if last is not None and last < fetch_result.to_date:
        return f"lists events only through {last.isoformat()}"

    return None


def _merge_statuses(statuses: list[SourceStatus]) -> list[SourceStatus]:
    """Merge per-request statuses into one per source.

    A source errors only when every request failed; partial failures keep the
    count and become a warning. Distinct warnings are joined in order.
    """
    grouped: dict[str, list[SourceStatus]] = {}

    for s in statuses:
        grouped.setdefault(s.name, []).append(s)

    merged = []

    for name, group in grouped.items():
        errors = [s.error for s in group if s.error]
        warnings = list(dict.fromkeys(s.warning for s in group if s.warning))

        if errors and len(errors) < len(group):
            warnings.insert(0, f"{len(errors)} of {len(group)} requests failed: {errors[0]}")

        merged.append(SourceStatus(
            name=name,
            count=sum(s.count for s in group),
            error=errors[0] if len(errors) == len(group) else None,
            warning="; ".join(warnings) or None,
        ))

    return merged


def _source_id_by_name(fetch_results: list[FetchResult]) -> dict[str, str]:
    return {fr.source_name: fr.source_id for fr in fetch_results}


def _flag_zero_counts(statuses: list[SourceStatus], ids: dict[str, str]) -> list[SourceStatus]:
    flagged = []

    for s in statuses:
        spec = SOURCES.get(ids.get(s.name, ""))

        if spec and spec.expect_events and s.count == 0 and not s.error and not s.warning:
            s = replace(s, warning=_ZERO_EVENTS_WARNING)

        flagged.append(s)

    return flagged


_PAGES_PER_VENUE = 2


def _venue_pages(events: list[Event], names: list[str]) -> dict[str, list[str]]:
    """For each venue name, up to two event pages on the source's own site (https only).

    Links that leave the source's domain (promoter or ticketing sites) are never fetched.
    """
    hosts = {spec.name: source_host(spec) for spec in SOURCES.values() if spec.venue_pages}
    wanted = set(names)
    pages: dict[str, list[str]] = {}

    for e in events:
        url = urlparse(e.source_url)

        if e.venue not in wanted or url.scheme != "https" or url.netloc != hosts.get(e.source_name):
            continue

        urls = pages.setdefault(e.venue, [])

        if e.source_url not in urls and len(urls) < _PAGES_PER_VENUE:
            urls.append(e.source_url)

    return pages


async def _look_up(book: VenueBook, events: list[Event], names: list[str], today: date) -> None:
    """Resolve venues from their event pages, then OpenStreetMap; record results and misses.

    Venues whose pages failed to load are searched last and keep only a hit, never a miss,
    so their pages are retried next run.
    """
    pages = _venue_pages(events, names)
    from_pages = await lookup_from_pages(pages) if pages else {}

    for name, info in from_pages.items():
        if info:
            book.record(name, info, today)

    page_failed = [n for n in names if n in pages and n not in from_pages]
    remaining = [n for n in names if n not in page_failed and not from_pages.get(n)] + page_failed

    if remaining:
        for name, info in (await lookup_venues(remaining)).items():
            if info or name not in page_failed:
                book.record(name, info, today)


async def _enrich(events: list[Event], venue_cache: Path | None, today: date) -> list[Event]:
    """Fill city/address from the venue book, canonicalize city, categorize.

    With a venue file path, venues still lacking a city are looked up online first and the
    book is saved back, so each venue is searched once.
    """
    book = VenueBook.load(venue_cache) if venue_cache else VenueBook()
    untrusted = {spec.name for spec in SOURCES.values() if not spec.trusted_venues}
    book.learn([e for e in events if e.source_name not in untrusted])

    if venue_cache:
        unknown = book.needs_lookup(book.fill(events), today)

        if unknown:
            logger.info("Looking up %d venues without a city", len(unknown))
            await _look_up(book, events, unknown, today)

        book.save(venue_cache)

    events = book.fill(events)

    return [
        replace(e, city=canonical_city(e.city) if e.city else None, category=e.category or categorize(e))
        for e in events
    ]


async def run_pipeline(from_date: date, to_date: date, venue_cache: Path | None = None) -> PipelineResult:
    """Fetch all sources, parse, check source health, and enrich events."""
    fetch_results = await fetch_raw_sources(from_date, to_date)

    all_events: list[Event] = []
    statuses: list[SourceStatus] = []

    for fr in fetch_results:
        if fr.error:
            statuses.append(SourceStatus(name=fr.source_name, count=0, error=fr.error))
            continue

        try:
            events = _dispatch_parser(fr)
        except Exception as e:  # noqa: BLE001 - one broken parser must not sink the run
            logger.error("Parser error for %s: %s", fr.source_name, e)
            # Exception text can quote scraped content, so the status names only the type.
            statuses.append(SourceStatus(name=fr.source_name, count=0, error=f"parser error: {type(e).__name__}"))
            continue

        logger.debug("Parsed %s (%s): %d events", fr.source_name, fr.url, len(events))
        all_events.extend(events)
        warnings = [w for w in (fr.warning, _coverage_warning(fr)) if w]
        statuses.append(SourceStatus(
            name=fr.source_name, count=len(events), error=None, warning="; ".join(warnings) or None,
        ))

    statuses = _flag_zero_counts(_merge_statuses(statuses), _source_id_by_name(fetch_results))

    for s in statuses:
        logger.info("Source %s", s.label())

    all_events = await _enrich(all_events, venue_cache, date.today())
    logger.info("Pipeline complete: %d total events from %d sources", len(all_events), len(statuses))

    return PipelineResult(events=all_events, source_statuses=statuses)
