"""Two-step CLI: fetch (with automatic dedup), review uncertain pairs, then render.

Usage:
    # Step 1: Fetch, filter, and merge duplicates; print the summary and possible duplicates
    python3 -m src.compact fetch --from 2026-03-17 --to 2026-03-22

    # Step 2: Render from cache, excluding reviewed duplicate indexes
    python3 -m src.compact render .events-cache.json --exclude 15,27 --format html --output events.html
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import date

from src.cli_utils import (
    VENUE_CACHE,
    FilterOptions,
    add_filter_arguments,
    build_output_path,
    finalize_events,
    parse_and_validate_dates,
    recount_sources,
    validate_filter_options,
)
from src.dedup import DedupResult
from src.models import Event, SourceStatus
from src.pipeline import run_pipeline
from src.renderers.formatting import location_text, sources_footer
from src.renderers.html_renderer import render_html
from src.renderers.markdown_renderer import render_markdown

logger = logging.getLogger(__name__)

CACHE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".events-cache.json")


_REVIEW_FIELD_MAX = 120


def _review_field(value: str | None) -> str:
    """Scraped text made safe for the review list: one line, no column separators, capped."""
    if not value:
        return "—"

    return " ".join(value.split()).replace("|", "/")[:_REVIEW_FIELD_MAX]


def _row(index: int, e: Event) -> str:
    fields = (e.name, e.city, location_text(e), str(e.event_date), e.time, e.source_name)

    return f"{index} | " + " | ".join(_review_field(f) for f in fields)


def _print_review(result: DedupResult, source_statuses: list[SourceStatus]) -> None:
    """Print the run summary and each possible-duplicate pair (1-based indexes) for review."""
    print(f"Events: {len(result.events)} (merged {result.removed} duplicates automatically)")
    print(f"Possible duplicates to review: {len(result.candidates)} pairs")

    if result.candidates:
        print("# | Name | City | Location | Date | Time | Source")

    for i, j in result.candidates:
        print(_row(i, result.events[i - 1]))
        print(_row(j, result.events[j - 1]))
        print()

    print(sources_footer(source_statuses).replace("Sources checked:", "Sources:"))


def _save_cache(
    events: list[Event],
    source_statuses: list[SourceStatus],
    from_date: date,
    to_date: date,
) -> None:
    """Save pipeline results to a JSON cache file."""
    cache = {
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "events": [e.to_dict() for e in events],
        "source_statuses": [s.to_dict() for s in source_statuses],
    }
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f)
    logger.info("Cached %d events to %s", len(events), CACHE_PATH)


def _load_cache(cache_path: str) -> dict:
    """Load pipeline results from a JSON cache file."""
    with open(cache_path, encoding="utf-8") as f:
        return json.load(f)


def cmd_fetch(args: argparse.Namespace) -> None:
    """Fetch, filter, and dedupe events; print review pairs and save the cache."""
    from_date, to_date = parse_and_validate_dates(args.from_date, args.to_date)
    options = FilterOptions(cities=args.cities, add_cities=args.add_cities, types=args.types)

    try:
        validate_filter_options(options)
    except ValueError as e:
        logger.error("%s", e)
        sys.exit(2)

    range_days = (to_date - from_date).days + 1
    logger.info("Fetching events for %s to %s (%d days)", from_date, to_date, range_days)
    result = asyncio.run(run_pipeline(from_date, to_date, venue_cache=VENUE_CACHE))
    deduped = finalize_events(result.events, options)
    statuses = recount_sources(deduped.events, result.source_statuses)

    _print_review(deduped, statuses)
    _save_cache(deduped.events, statuses, from_date, to_date)


def cmd_render(args: argparse.Namespace) -> None:
    """Load cache, exclude duplicates, render to file."""
    try:
        cache = _load_cache(args.cache_file)
    except FileNotFoundError:
        logger.error("Cache file '%s' not found. Run 'fetch' first.", args.cache_file)
        sys.exit(1)
    except json.JSONDecodeError:
        logger.error("Cache file '%s' is corrupted.", args.cache_file)
        sys.exit(1)

    events = [Event.from_dict(d) for d in cache["events"]]
    source_statuses = [SourceStatus.from_dict(d) for d in cache["source_statuses"]]
    from_date = date.fromisoformat(cache["from_date"])
    to_date = date.fromisoformat(cache["to_date"])

    if args.exclude:
        try:
            exclude_indexes = {int(x.strip()) for x in args.exclude.split(",")}
        except ValueError:
            logger.error("--exclude must be comma-separated integers, got '%s'", args.exclude)
            sys.exit(1)

        valid_range = set(range(1, len(events) + 1))
        out_of_range = exclude_indexes - valid_range
        if out_of_range:
            logger.warning("Exclude indexes out of range (max %d): %s", len(events), sorted(out_of_range))

        before = len(events)
        events = [e for i, e in enumerate(events, 1) if i not in exclude_indexes]
        logger.info("Excluded %d duplicates: %d → %d events", before - len(events), before, len(events))

    source_statuses = recount_sources(events, source_statuses)

    if args.format == "markdown":
        content = render_markdown(events, source_statuses, from_date, to_date)
    else:
        content = render_html(events, source_statuses, from_date, to_date)

    output_path = build_output_path(from_date, to_date, args.format, args.output)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info("Exported %d events to %s", len(events), output_path)

    # Only ever delete the fetch cache, never an arbitrary path passed on the command line.
    if os.path.basename(args.cache_file) == os.path.basename(CACHE_PATH):
        os.remove(args.cache_file)
        logger.info("Removed cache file %s", args.cache_file)


def main() -> None:
    parser = argparse.ArgumentParser(description="Two-step event pipeline with duplicate review")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch", help="Fetch events and print possible duplicates")
    fetch_parser.add_argument("--from", dest="from_date", required=True, help="Start date YYYY-MM-DD")
    fetch_parser.add_argument("--to", dest="to_date", required=True, help="End date YYYY-MM-DD")
    add_filter_arguments(fetch_parser)

    render_parser = subparsers.add_parser("render", help="Render events from cache to file")
    render_parser.add_argument("cache_file", help="Path to the JSON cache file")
    render_parser.add_argument("--exclude", help="Comma-separated 1-based indexes to exclude")
    render_parser.add_argument("--format", choices=["markdown", "html"], default="html")
    render_parser.add_argument("--output", help="Output file path")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )
    logging.getLogger("aiohttp").setLevel(logging.WARNING)

    if args.command == "fetch":
        cmd_fetch(args)
    elif args.command == "render":
        cmd_render(args)


if __name__ == "__main__":
    main()
