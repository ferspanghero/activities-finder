"""Parser for Kids Out and About Vancouver day lists (Drupal Views HTML)."""

import re
from datetime import date, datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from src.cities import city_from_text
from src.models import Event

_SKIP_LOCATION_RE = re.compile(r"\bonline\b|united states", re.IGNORECASE)
_TRAILING_RE = re.compile(r"^(bc|british columbia|canada)\b", re.IGNORECASE)


def split_location(location: str) -> tuple[str | None, str | None, str | None]:
    """Split 'Venue, 1 Street, City, BC, Canada' into (venue, street address, city).

    A leading part that starts with a digit is a street address, not a venue.
    """
    parts = [p.strip() for p in location.split(",") if p.strip()]
    city = city_from_text(location)
    city_idx = next(
        (i for i, p in enumerate(parts) if city and p.lower() == city.lower()),
        len(parts),
    )
    head = [p for p in parts[:city_idx] if not _TRAILING_RE.match(p)]

    if not head:
        return None, None, city

    if head[0][0].isdigit():
        return None, ", ".join(head), city

    return head[0], ", ".join(head[1:]) or None, city


def _dates(row: Tag) -> list[date]:
    found = []

    for span in row.select("span.date-display-single"):
        try:
            found.append(datetime.strptime(span.get_text(strip=True), "%m/%d/%Y").date())
        except ValueError:
            continue

    return found


def _parse_row(row: Tag, page_url: str, day: date) -> Event | None:
    link = row.select_one(".group-activity-details h2 a")
    title = link.get_text(strip=True) if link else ""

    if not link or not title:
        return None

    # Organizer-submitted rows carry a contact block instead of a places field; both name the location.
    loc_field = row.select_one(".field-name-field-venue-places-api, .field-name-field-contact-info")

    if not loc_field or _SKIP_LOCATION_RE.search(loc_field.get_text(" ", strip=True)):
        return None

    loc_el = loc_field.select_one(".field-item > div")

    listed = _dates(row)

    if listed and day not in listed:
        return None

    if loc_el:
        venue, address, city = split_location(loc_el.get_text(" ", strip=True))
    else:
        venue, address, city = None, None, city_from_text(loc_field.get_text(" ", strip=True))

    time_el = row.select_one(".field-name-field-time .field-item")
    time = time_el.get_text("\n", strip=True).splitlines()[0] if time_el and time_el.get_text(strip=True) else None
    href = link.get("href")

    return Event(
        name=title,
        city=city,
        address=address,
        time=time,
        event_date=day,
        source_name="Kids Out and About",
        source_url=urljoin(page_url, href) if isinstance(href, str) else page_url,
        venue=venue,
        category="family",
    )


def parse_kidsoutandabout(html: str, source_url: str, from_date: date, to_date: date) -> list[Event]:
    """Parse one day page; rows not listed on `from_date`, online, or US-based are skipped."""
    soup = BeautifulSoup(html, "html.parser")
    events = (_parse_row(row, source_url, from_date) for row in soup.select("div.views-row"))

    return [e for e in events if e is not None]
