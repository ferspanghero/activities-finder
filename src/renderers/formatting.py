"""Shared formatting utilities for renderers."""

import re
from datetime import date
from urllib.parse import urlparse

from src.categories import CATEGORY_LABELS
from src.models import Event, SourceStatus


def format_short_date(d: date) -> str:
    """Format a date as 'Sat, Mar 7' for table cells."""
    return f"{d.strftime('%a, %b')} {d.day}"


def safe_url(url: str | None) -> str | None:
    """Scraped link made safe to render: http(s) only, with spaces and parentheses encoded.

    Returns None for other schemes (javascript:, data:) so they are shown as plain text.
    """
    url = re.sub(r"[\x00-\x1f\x7f<>]", "", url or "")

    if not url or urlparse(url).scheme.lower() not in ("http", "https"):
        return None

    return url.replace(" ", "%20").replace("(", "%28").replace(")", "%29")


def location_text(event: Event) -> str | None:
    """Venue and street address joined for display ('Frankie's, 755 Beatty St'), or None."""
    parts = [p for p in (event.venue, event.address) if p]

    if len(parts) == 2 and parts[1].lower().startswith(parts[0].lower()):
        parts = parts[1:]

    return ", ".join(parts) or None


def maps_query(event: Event) -> str | None:
    """Google Maps search text: the location plus city; None when there is no venue or address."""
    location = location_text(event)

    if not location:
        return None

    return f"{location}, {event.city}" if event.city and event.city.lower() not in location.lower() else location


def category_label(key: str | None) -> str | None:
    """Display label for an activity-type key."""
    return CATEGORY_LABELS.get(key) if key else None


def sources_footer(statuses: list[SourceStatus]) -> str:
    """'Sources checked: Do604 (12), ShowHub (ERROR: ...)' line."""
    return "Sources checked: " + ", ".join(s.label() for s in statuses)


def summary_line(events: list[Event], statuses: list[SourceStatus]) -> str:
    """'Found X events across Y cities from Z/N sources' header."""
    cities = {e.city for e in events if e.city}
    reporting = sum(1 for s in statuses if s.count > 0)

    return f"Found {len(events)} events across {len(cities)} cities from {reporting}/{len(statuses)} sources"
