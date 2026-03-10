"""Parser for Daily Hive event listings (Next.js embedded JSON)."""

import json
from datetime import date, datetime

from bs4 import BeautifulSoup

from src.models import Event

BASE_URL = "https://dailyhive.com/vancouver/listed/events"


def _parse_datetime(dt_str: str) -> datetime:
    """Parse ISO datetime like '2026-03-06T10:00:00.000Z'."""
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))


def _event_overlaps_range(item: dict, from_date: date, to_date: date) -> tuple[bool, date]:
    """Check if a multi-day event overlaps the query date range.

    Returns (overlaps, event_date) where event_date is the first day
    of the event within the queried range.
    """
    try:
        start = _parse_datetime(item["start_datetime"]).date()
        end = _parse_datetime(item["end_datetime"]).date()
        if start <= to_date and end >= from_date:
            return True, max(start, from_date)
        return False, from_date
    except (KeyError, ValueError):
        return True, from_date  # If we can't parse dates, include it


def parse_dailyhive(html: str, source_url: str, from_date: date, to_date: date) -> list[Event]:
    """Parse Daily Hive HTML (Next.js __NEXT_DATA__) into Event objects."""
    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")
    if not script or not script.string:
        return []

    try:
        data = json.loads(script.string)
    except json.JSONDecodeError:
        return []

    items = (
        data.get("props", {})
        .get("pageProps", {})
        .get("upcomingEvents", [])
    )

    events = []
    for item in items:
        overlaps, event_date = _event_overlaps_range(item, from_date, to_date)
        if not overlaps:
            continue

        venue = item.get("venue_details") or {}
        slug = item.get("slug", "")
        event_url = item.get("ticket_url") or f"{BASE_URL}/{slug}"

        events.append(Event(
            name=item.get("title", ""),
            city=venue.get("city"),
            address=venue.get("address"),
            time=None,  # Daily Hive doesn't provide human-readable time reliably
            event_date=event_date,
            source_name="Daily Hive",
            source_url=event_url,
        ))

    return events
