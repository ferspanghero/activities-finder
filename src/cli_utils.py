"""Shared CLI utilities: date validation, output paths, and the filter/sort/dedup flow."""

import argparse
import logging
import sys
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path

from src.categories import CATEGORY_LABELS, filter_by_types, parse_types
from src.cities import filter_by_cities, resolve_allowed_cities
from src.dedup import DedupResult, dedupe
from src.models import Event, SourceStatus
from src.timeparse import sort_minutes

logger = logging.getLogger(__name__)

MAX_RANGE_DAYS = 14
VENUE_CACHE = Path(__file__).resolve().parent.parent / "data" / "venues.json"


def parse_and_validate_dates(from_str: str, to_str: str) -> tuple[date, date]:
    """Parse and validate date range strings. Exits on invalid input."""
    try:
        from_date = date.fromisoformat(from_str)
    except ValueError:
        logger.error("Invalid start date format '%s'. Use YYYY-MM-DD.", from_str)
        sys.exit(1)

    try:
        to_date = date.fromisoformat(to_str)
    except ValueError:
        logger.error("Invalid end date format '%s'. Use YYYY-MM-DD.", to_str)
        sys.exit(1)

    if from_date > to_date:
        logger.error("Start date %s is after end date %s.", from_date, to_date)
        sys.exit(1)

    range_days = (to_date - from_date).days + 1
    if range_days > MAX_RANGE_DAYS:
        logger.error("Date range of %d days exceeds maximum of %d days.", range_days, MAX_RANGE_DAYS)
        sys.exit(1)

    return from_date, to_date


def build_output_path(from_date: date, to_date: date, fmt: str, explicit_output: str | None) -> str:
    """Build the output file path from dates and format."""
    if explicit_output:
        return explicit_output

    ext = "md" if fmt == "markdown" else "html"
    if from_date == to_date:
        return f"events-{from_date.isoformat()}.{ext}"
    return f"events-{from_date.isoformat()}_to_{to_date.isoformat()}.{ext}"


@dataclass(frozen=True)
class FilterOptions:
    """Raw CLI filter flags: `cities` replaces the default list, `add_cities` extends it."""

    cities: str | None = None
    add_cities: str | None = None
    types: str | None = None


def add_filter_arguments(parser: argparse.ArgumentParser) -> None:
    """Register the --cities / --add-cities / --types flags shared by both CLIs."""
    cities = parser.add_mutually_exclusive_group()
    cities.add_argument("--cities", help="Only these comma-separated cities (drops events with unknown city)")
    cities.add_argument("--add-cities", help="Comma-separated cities to add to the default city list")
    parser.add_argument("--types", help=f"Comma-separated activity types: {', '.join(CATEGORY_LABELS)}")


def validate_filter_options(options: FilterOptions) -> None:
    """Raise ValueError for conflicting city flags or unknown activity types."""
    resolve_allowed_cities(options.cities, options.add_cities)

    if options.types:
        parse_types(options.types)


def recount_sources(events: list[Event], statuses: list[SourceStatus]) -> list[SourceStatus]:
    """Statuses with counts recomputed from the final event list (after filters and dedup)."""
    counts: dict[str, int] = {}

    for e in events:
        counts[e.source_name] = counts.get(e.source_name, 0) + 1

    return [replace(s, count=counts.get(s.name, 0)) for s in statuses]


def finalize_events(events: list[Event], options: FilterOptions) -> DedupResult:
    """Filter by city and type, sort by date then start time, and merge duplicates.

    Raises ValueError for conflicting city flags or unknown activity types.
    """
    allowed, keep_unknown = resolve_allowed_cities(options.cities, options.add_cities)
    selected = filter_by_cities(events, allowed, keep_unknown)

    if options.types:
        selected = filter_by_types(selected, parse_types(options.types))

    selected = sorted(selected, key=lambda e: (e.event_date, sort_minutes(e.time)))
    logger.info("Filters kept %d of %d events", len(selected), len(events))

    return dedupe(selected)
