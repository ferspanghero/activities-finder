"""Shared formatting utilities for renderers."""

from datetime import date


def format_short_date(d: date) -> str:
    """Format a date as 'Sat, Mar 7' for table cells."""
    return f"{d.strftime('%a, %b')} {d.day}"
