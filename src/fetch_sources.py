"""Fetches event sources in parallel (paginated, rate-limited, retried) and returns raw HTML/JSON."""

import asyncio
import json
import logging
from dataclasses import dataclass, replace
from datetime import date, timedelta

import aiohttp

from src.models import FetchResult
from src.sources import SOURCES, SourceSpec

logger = logging.getLogger(__name__)

# Browser-like UA required: Daily Hive returns 0 events for bot-like User-Agents.
BROWSER_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
_TIMEOUT = aiohttp.ClientTimeout(total=30)
_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
_MAX_BACKOFF_SECONDS = 15.0
# Pages requested together while probing an "until_empty" source for its last page.
_UNTIL_EMPTY_BATCH = 4


def build_source_url(source_id: str, from_date: date, to_date: date) -> str:
    """First-page URL for a source and date window."""
    return SOURCES[source_id].url_template.format(
        YYYY=f"{from_date.year:04d}",
        MM=f"{from_date.month:02d}",
        DD=f"{from_date.day:02d}",
        M=str(from_date.month),
        D=str(from_date.day),
        from_date=from_date.isoformat(),
        to_date=to_date.isoformat(),
    )


def page_url(url: str, page: int) -> str:
    """URL for result page `page` (page 1 is the bare URL)."""
    if page <= 1:
        return url

    return f"{url}{'&' if '?' in url else '?'}page={page}"


def calculate_week_number(target_date: date) -> int:
    """Calculate which Sun-Sat week of the month a date falls in.

    Week 1 starts on the 1st regardless of day-of-week and runs until
    the first Saturday. Subsequent weeks run Sunday through Saturday.

    Example for March 2026 (starts on Sunday):
      Week 1: Mar 1-7 (Sun-Sat)
      Week 2: Mar 8-14, Week 3: Mar 15-21, etc.

    Example for a month starting on Wednesday:
      Week 1: 1st-4th (Wed-Sat), Week 2: 5th-11th (Sun-Sat), etc.
    """
    first_of_month = target_date.replace(day=1)
    first_day_weekday = first_of_month.weekday()  # Mon=0..Sun=6

    # Last day (inclusive) of week 1 = first Saturday of the month
    if first_day_weekday == 6:  # Month starts on Sunday
        last_day_of_week1 = 7   # Full Sun-Sat week
    else:
        last_day_of_week1 = 6 - first_day_weekday  # Days until Saturday

    if target_date.day <= last_day_of_week1:
        return 1

    days_past_week1 = target_date.day - last_day_of_week1 - 1
    return 2 + days_past_week1 // 7


def backoff_seconds(retry_after: str | None, attempt: int, base: float) -> float:
    """Delay before retry `attempt` (1-based): the server's numeric Retry-After, else base * 2^attempt.

    Capped so one slow source cannot stall the whole run.
    """
    try:
        delay = float(retry_after) if retry_after is not None else base * 2 ** attempt
    except ValueError:
        delay = base * 2 ** attempt

    return min(delay, _MAX_BACKOFF_SECONDS)


@dataclass(frozen=True)
class _Client:
    session: aiohttp.ClientSession
    semaphore: asyncio.Semaphore
    retries: int
    retry_delay: float

    async def get_text(self, url: str, source_limit: asyncio.Semaphore) -> str:
        """GET under the global and per-source limits; retries transient failures (5xx, 429, network)."""
        attempt = 0

        while True:
            retry_after = None

            try:
                async with source_limit, self.semaphore, self.session.get(url, timeout=_TIMEOUT) as resp:
                    resp.raise_for_status()
                    return await resp.text()
            except aiohttp.ClientResponseError as e:
                if e.status not in _RETRYABLE_STATUS or attempt >= self.retries:
                    raise
                retry_after = e.headers.get("Retry-After") if e.headers else None
            except (asyncio.TimeoutError, aiohttp.ClientError):
                if attempt >= self.retries:
                    raise

            attempt += 1
            logger.warning("Retrying %s (attempt %d)", url, attempt + 1)
            await asyncio.sleep(backoff_seconds(retry_after, attempt, self.retry_delay))


async def _fetch_page(
    client: _Client,
    source_id: str,
    spec: SourceSpec,
    url: str,
    from_date: date,
    to_date: date,
    source_limit: asyncio.Semaphore,
) -> FetchResult:
    def result(content: str | dict | None, error: str | None) -> FetchResult:
        return FetchResult(source_id, spec.name, url, content, error, from_date, to_date)

    try:
        raw = await client.get_text(url, source_limit)
    except (asyncio.TimeoutError, aiohttp.ClientError) as e:
        logger.warning("Fetch failed for %s: %s", spec.name, e)
        return result(None, str(e) or type(e).__name__)

    if not spec.json:
        return result(raw, None)

    try:
        return result(json.loads(raw), None)
    except json.JSONDecodeError as e:
        logger.warning("Invalid JSON from %s: %s", spec.name, e)
        return result(None, f"Invalid JSON from {spec.name}: {e}")


async def _fetch_window(
    client: _Client,
    source_id: str,
    spec: SourceSpec,
    from_date: date,
    to_date: date,
    source_limit: asyncio.Semaphore,
) -> list[FetchResult]:
    """Fetch every result page for one source and date window."""
    base = build_source_url(source_id, from_date, to_date)
    first = await _fetch_page(client, source_id, spec, base, from_date, to_date, source_limit)

    if first.error or spec.pagination == "none" or spec.max_pages <= 1:
        return [first]

    def fetch(page: int):
        return _fetch_page(client, source_id, spec, page_url(base, page), from_date, to_date, source_limit)

    if spec.pagination == "count" and spec.page_count:
        try:
            reported = int(spec.page_count(first.content))
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            return [replace(first, warning=f"pagination unreadable: {type(e).__name__}")]

        last = min(reported, spec.max_pages)
        rest = await asyncio.gather(*(fetch(p) for p in range(2, last + 1)))

        if reported > last:
            first = replace(first, warning=f"showing first {last} of {reported} result pages")

        return [first, *rest]

    def has_events(fr: FetchResult) -> bool:
        return bool(spec.has_events and isinstance(fr.content, str) and spec.has_events(fr.content))

    try:
        if not has_events(first):
            return [first]
    except (AttributeError, KeyError, TypeError, ValueError) as e:
        return [replace(first, warning=f"pagination unreadable: {type(e).__name__}")]

    results = [first]

    for batch_start in range(2, spec.max_pages + 1, _UNTIL_EMPTY_BATCH):
        batch_end = min(batch_start + _UNTIL_EMPTY_BATCH, spec.max_pages + 1)
        batch = await asyncio.gather(*(fetch(p) for p in range(batch_start, batch_end)))

        for fr in batch:
            if fr.error:
                return [*results, fr]

            if not has_events(fr):
                return results

            results.append(fr)

    results[0] = replace(results[0], warning=f"stopped at the {spec.max_pages}-page limit")

    return results


def _windows(spec: SourceSpec, from_date: date, to_date: date) -> list[tuple[date, date]]:
    if not spec.per_day:
        return [(from_date, to_date)]

    return [(from_date + timedelta(days=i),) * 2 for i in range((to_date - from_date).days + 1)]


async def fetch_raw_sources(
    from_date: date,
    to_date: date,
    *,
    sources: dict[str, SourceSpec] | None = None,
    concurrency: int = 8,
    retries: int = 2,
    retry_delay: float = 1.0,
) -> list[FetchResult]:
    """Fetch all pages of all sources for the range, one FetchResult per page request."""
    sources = SOURCES if sources is None else sources
    logger.info("Fetching %d sources for %s to %s", len(sources), from_date, to_date)

    async with aiohttp.ClientSession(headers=BROWSER_HEADERS) as session:
        client = _Client(session, asyncio.Semaphore(concurrency), retries, retry_delay)
        limits = {sid: asyncio.Semaphore(spec.concurrency or concurrency) for sid, spec in sources.items()}
        windows = await asyncio.gather(*(
            _fetch_window(client, source_id, spec, f, t, limits[source_id])
            for source_id, spec in sources.items()
            for f, t in _windows(spec, from_date, to_date)
        ))

    results = [fr for window in windows for fr in window]
    succeeded = sum(1 for r in results if r.error is None)
    logger.info("Fetched %d/%d pages successfully", succeeded, len(results))

    return results
