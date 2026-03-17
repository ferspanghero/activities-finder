"""Shared CLI utilities for date validation and output path generation."""

import logging
import sys
from datetime import date

logger = logging.getLogger(__name__)

MAX_RANGE_DAYS = 14


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
