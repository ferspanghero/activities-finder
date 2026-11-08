"""Parser for Daily Hive event listings (Next.js embedded JSON)."""

import json
from datetime import date, datetime

from bs4 import BeautifulSoup

from src.categories import map_source_category
from src.models import Event
from src.parsers.common import format_price
from src.timeparse import format_clock

BASE_URL = "https://dailyhive.com/vancouver/listed/events"


def _parse_datetime(dt_str: str) -> datetime:
    """Parse ISO datetime like '2026-03-06T10:00:00.000Z'.

    Daily Hive stamps local wall-clock times with a 'Z' suffix (an evening play
    reads 19:00Z), so the value is used as local time, not converted from UTC.
    """
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))  # Python 3.10 rejects a "Z" suffix


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


def _start_time(item: dict, event_date: date) -> str | None:
    """Clock time when the event starts on `event_date`; None for earlier starts or all-day."""
    try:
        start = _parse_datetime(item["start_datetime"])
    except (KeyError, ValueError):
        return None

    if start.date() != event_date or (start.hour, start.minute) == (0, 0):
        return None

    return format_clock(start.hour, start.minute)


def _page_props(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")

    if not script or not script.string:
        return {}

    try:
        return json.loads(script.string).get("props", {}).get("pageProps", {})
    except json.JSONDecodeError:
        return {}


def page_count(html: str) -> int:
    """Total result pages reported by the listing (1 when absent)."""
    pagination = _page_props(html).get("pagination") or {}

    return int(pagination.get("total_pages") or 1)


def parse_dailyhive(html: str, source_url: str, from_date: date, to_date: date) -> list[Event]:
    """Parse Daily Hive HTML (Next.js __NEXT_DATA__) into Event objects."""
    events = []

    for item in _page_props(html).get("upcomingEvents", []):
        overlaps, event_date = _event_overlaps_range(item, from_date, to_date)
        if not overlaps:
            continue

        venue = item.get("venue_details") or {}
        slug = item.get("slug", "")
        event_url = item.get("ticket_url") or f"{BASE_URL}/{slug}"
        category = next(
            (c for c in map(map_source_category, item.get("categories") or []) if c), None,
        )

        events.append(Event(
            name=item.get("title", "").strip(),
            city=venue.get("city"),
            address=venue.get("address"),
            time=_start_time(item, event_date),
            event_date=event_date,
            source_name="Daily Hive",
            source_url=event_url,
            venue=venue.get("name"),
            category=category,
            price=format_price(item.get("price_from"), item.get("price_to")),
        ))

    return events
