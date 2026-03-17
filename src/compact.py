"""Two-step CLI for fetch-then-render with LLM deduplication in between.

Usage:
    # Step 1: Fetch events and print compact list
    python3 -m src.compact fetch --from 2026-03-17 --to 2026-03-22

    # Step 2: Render from cache, excluding duplicate indexes
    python3 -m src.compact render .events-cache.json --exclude 1,15,27 --format html --output events.html
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import date

from src.models import Event, SourceStatus
from src.pipeline import run_pipeline
from src.renderers.html_renderer import render_html, parse_time_to_minutes
from src.renderers.markdown_renderer import render_markdown

logger = logging.getLogger(__name__)

CACHE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".events-cache.json")


def _print_compact(events: list[Event], source_statuses: list[SourceStatus]) -> None:
    """Print a compact numbered event list to stdout."""
    print("# | Name | City | Address | Date | Time | Source")
    for i, e in enumerate(events, 1):
        city = e.city or "\u2014"
        address = e.address or "\u2014"
        time = e.time or "\u2014"
        print(f"{i} | {e.name} | {city} | {address} | {e.event_date} | {time} | {e.source_name}")

    parts = []
    for s in source_statuses:
        if s.error:
            parts.append(f"{s.name} (ERROR: {s.error})")
        else:
            parts.append(f"{s.name} ({s.count})")
    print(f"\nSources: {', '.join(parts)}")


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
    """Fetch events, print compact list, and save cache."""
    from src.cli_utils import parse_and_validate_dates

    from_date, to_date = parse_and_validate_dates(args.from_date, args.to_date)

    range_days = (to_date - from_date).days + 1
    logger.info("Fetching events for %s to %s (%d days)", from_date, to_date, range_days)
    result = asyncio.run(run_pipeline(from_date, to_date))

    if args.cities:
        allowed = {c.strip() for c in args.cities.split(",")}
        result.events = [e for e in result.events if e.city and e.city in allowed]

    result.events.sort(key=lambda e: (e.event_date, parse_time_to_minutes(e.time)))

    _print_compact(result.events, result.source_statuses)
    _save_cache(result.events, result.source_statuses, from_date, to_date)


def _recalculate_source_counts(events: list[Event], source_statuses: list[SourceStatus]) -> list[SourceStatus]:
    """Recalculate source counts from the actual event list."""
    counts: dict[str, int] = {}
    for e in events:
        counts[e.source_name] = counts.get(e.source_name, 0) + 1

    return [
        SourceStatus(name=s.name, count=counts.get(s.name, 0), error=s.error)
        for s in source_statuses
    ]


def cmd_render(args: argparse.Namespace) -> None:
    """Load cache, exclude duplicates, render to file."""
    from src.cli_utils import build_output_path

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

    source_statuses = _recalculate_source_counts(events, source_statuses)

    if args.format == "markdown":
        content = render_markdown(events, source_statuses, from_date, to_date)
    else:
        content = render_html(events, source_statuses, from_date, to_date)

    output_path = build_output_path(from_date, to_date, args.format, args.output)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info("Exported %d events to %s", len(events), output_path)

    os.remove(args.cache_file)
    logger.info("Removed cache file %s", args.cache_file)


def main() -> None:
    parser = argparse.ArgumentParser(description="Two-step event pipeline with LLM deduplication")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch", help="Fetch events and print compact list")
    fetch_parser.add_argument("--from", dest="from_date", required=True, help="Start date YYYY-MM-DD")
    fetch_parser.add_argument("--to", dest="to_date", required=True, help="End date YYYY-MM-DD")
    fetch_parser.add_argument("--cities", help="Comma-separated list of cities to filter by")

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

    if args.command == "fetch":
        cmd_fetch(args)
    elif args.command == "render":
        cmd_render(args)


if __name__ == "__main__":
    main()
