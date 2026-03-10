"""Parser for BC Ale Trail event listings (HTML with embedded JSON)."""

import json
from datetime import date, datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.models import Event


def _format_time(iso_str: str) -> str | None:
    """Format ISO datetime string to human-readable time like '4:00 PM'."""
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%I:%M %p").lstrip("0")
    except (ValueError, TypeError):
        return None


def _matches_date_range(upcoming_times: list[dict], from_date: date, to_date: date) -> tuple[bool, str | None, date | None]:
    """Check if any upcoming time falls within the query date range.

    Returns (matches, iso_start_str or None, event_date or None).
    """
    for t in upcoming_times:
        start_str = t.get("start", "")
        try:
            start_dt = datetime.fromisoformat(start_str)
            if from_date <= start_dt.date() <= to_date:
                return True, start_str, start_dt.date()
        except (ValueError, TypeError):
            continue
    return False, None, None


def parse_bcaletrail(html: str, source_url: str, from_date: date, to_date: date) -> list[Event]:
    """Parse BC Ale Trail HTML into Event objects, filtered to the date range."""
    soup = BeautifulSoup(html, "html.parser")
    events: list[Event] = []

    for card in soup.find_all("div", class_="event-item"):
        data_str = card.get("data-event-times", "")
        if not data_str:
            continue

        try:
            records = json.loads(data_str)
        except json.JSONDecodeError:
            continue

        if not records:
            continue
        record = records[0]

        matches, start_str, evt_date = _matches_date_range(
            record.get("upcoming_times", []), from_date, to_date
        )
        if not matches:
            continue

        title_el = card.find("h2")
        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            continue

        locations = record.get("locations", [])
        city = None
        address = None
        if locations:
            loc = locations[0]
            city = (loc.get("city") or "").strip() or None
            address = (loc.get("street_address") or "").strip() or None

        time_str = _format_time(start_str) if start_str else None

        event_link = card.find("a", class_="event-thumbnail")
        href = event_link.get("href", "") if event_link else ""
        event_url = urljoin(source_url, href) if href else source_url

        events.append(Event(
            name=title,
            city=city,
            address=address,
            time=time_str,
            event_date=evt_date,
            source_name="BC Ale Trail",
            source_url=event_url,
        ))

    return events
