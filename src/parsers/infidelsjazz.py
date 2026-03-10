"""Parser for Infidels Jazz WordPress REST API (JSON)."""

import html
from datetime import date, datetime

from src.models import Event


def _format_time(start_date_str: str) -> str:
    """Convert '2026-03-07 23:00:00' to '11:00 PM'."""
    dt = datetime.strptime(start_date_str, "%Y-%m-%d %H:%M:%S")
    return dt.strftime("%I:%M %p").lstrip("0")


def parse_infidelsjazz(data: dict, source_url: str, from_date: date, to_date: date) -> list[Event]:
    """Parse Infidels Jazz API JSON into Event objects."""
    events = []
    for item in data.get("events", []):
        venue = item.get("venue") or {}
        title = html.unescape(item.get("title", ""))

        time = None
        event_date = from_date
        if item.get("start_date"):
            time = _format_time(item["start_date"])
            event_date = datetime.strptime(item["start_date"], "%Y-%m-%d %H:%M:%S").date()

        events.append(Event(
            name=title,
            city=venue.get("city"),
            address=venue.get("address"),
            time=time,
            event_date=event_date,
            source_name="Infidels Jazz",
            source_url=item.get("url", source_url),
        ))
    return events
