"""Parser for BC Ale Trail event listings (HTML with embedded JSON)."""

import json
from dataclasses import replace
from datetime import date, datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.categories import categorize
from src.models import Event


def _format_time(iso_str: str) -> str | None:
    """Format ISO datetime string to human-readable time like '4:00 PM'."""
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%I:%M %p").lstrip("0")
    except (ValueError, TypeError):
        return None


def _starts_in_range(upcoming_times: list[dict], from_date: date, to_date: date) -> list[tuple[date, str]]:
    """First start (date, ISO string) of each distinct day within the query range."""
    starts: dict[date, str] = {}

    for t in upcoming_times:
        start_str = t.get("start", "")
        try:
            start_date = datetime.fromisoformat(start_str).date()
        except (ValueError, TypeError):
            continue

        if from_date <= start_date <= to_date:
            starts.setdefault(start_date, start_str)

    return sorted(starts.items())


def parse_bcaletrail(html: str, source_url: str, from_date: date, to_date: date) -> list[Event]:
    """Parse BC Ale Trail HTML into one Event per occurrence date within the range."""
    soup = BeautifulSoup(html, "html.parser")
    events: list[Event] = []

    for card in soup.find_all("div", class_="event-item"):
        data_str = str(card.get("data-event-times") or "")
        if not data_str:
            continue

        try:
            records = json.loads(data_str)
        except json.JSONDecodeError:
            continue

        if not records:
            continue
        record = records[0]

        starts = _starts_in_range(record.get("upcoming_times", []), from_date, to_date)
        if not starts:
            continue

        title_el = card.find("h2")
        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            continue

        locations = record.get("locations", [])
        loc = locations[0] if locations else {}
        city = (loc.get("city") or "").strip() or None
        address = (loc.get("street_address") or "").strip() or None
        venue = (loc.get("name") or "").strip() or None

        event_link = card.find("a", class_="event-thumbnail")
        href = str(event_link.get("href") or "") if event_link else ""
        event_url = urljoin(source_url, href) if href else source_url

        template = Event(
            name=title, city=city, address=address, time=None, event_date=from_date,
            source_name="BC Ale Trail", source_url=event_url, venue=venue,
        )
        # Brewery listings without a more specific keyword count as food & drink.
        template = replace(template, category=categorize(template) or "food")

        events.extend(
            replace(template, event_date=evt_date, time=_format_time(start_str))
            for evt_date, start_str in starts
        )

    return events
