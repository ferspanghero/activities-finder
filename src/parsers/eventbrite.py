"""Parser for Eventbrite city search pages (window.__SERVER_DATA__ JSON embedded in HTML)."""

import json
import re
from datetime import date

from src.categories import map_source_category
from src.models import Event
from src.timeparse import format_clock

_SERVER_DATA_RE = re.compile(r"window\.__SERVER_DATA__\s*=\s*")


def _search_events(html: str) -> dict:
    m = _SERVER_DATA_RE.search(html)

    if not m:
        return {}

    try:
        data, _ = json.JSONDecoder().raw_decode(html, m.end())
    except json.JSONDecodeError:
        return {}

    return (data.get("search_data") or {}).get("events") or {}


def page_count(html: str) -> int:
    """Total result pages reported by the search (1 when absent)."""
    return int((_search_events(html).get("pagination") or {}).get("page_count") or 1)


def _clock(hhmm: str | None) -> str | None:
    if not hhmm or not re.fullmatch(r"\d{1,2}:\d{2}", hhmm):
        return None

    hour, minute = map(int, hhmm.split(":"))

    return format_clock(hour, minute)


def _category(tags: list[dict]) -> str | None:
    labels = (t.get("display_name") for t in tags if t.get("prefix") == "EventbriteCategory")

    return next((c for c in map(map_source_category, labels) if c), None)


def parse_eventbrite(html: str, source_url: str, from_date: date, to_date: date) -> list[Event]:
    """Parse in-person, non-cancelled events overlapping the range.

    A run that began before the range is dated `from_date` with no time.
    """
    events = []

    for item in _search_events(html).get("results") or []:
        if item.get("is_online_event") or item.get("is_cancelled"):
            continue

        try:
            start = date.fromisoformat(item["start_date"])
            end = date.fromisoformat(item.get("end_date") or item["start_date"])
        except (KeyError, ValueError):
            continue

        if start > to_date or end < from_date:
            continue

        event_date = max(start, from_date)
        venue = item.get("primary_venue") or {}
        address = venue.get("address") or {}

        events.append(Event(
            name=(item.get("name") or "").strip(),
            city=address.get("city") or None,
            address=address.get("address_1") or None,
            time=_clock(item.get("start_time")) if event_date == start else None,
            event_date=event_date,
            source_name="Eventbrite",
            source_url=item.get("url") or source_url,
            venue=venue.get("name") or None,
            category=_category(item.get("tags") or []),
        ))

    return events
