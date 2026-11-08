"""Parser for ShowHub weekly listings (HTML)."""

import re
from datetime import date

from bs4 import BeautifulSoup, Tag

from src.cities import city_from_text
from src.models import Event
from src.parsers.dates import infer_year

# Month abbreviation to number
_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# Pattern: "Saturday, Mar 7 at 9:00 PM"
_SINGLE_DATE_RE = re.compile(
    r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+"
    r"([A-Za-z]+)\s+(\d+)\s+at\s+(.+)",
    re.IGNORECASE,
)

# Pattern: "Friday, Mar 6 – Sunday, Mar 8"
_DATE_RANGE_RE = re.compile(
    r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+"
    r"([A-Za-z]+)\s+(\d+)\s*[–-]\s*"
    r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+"
    r"([A-Za-z]+)\s+(\d+)",
    re.IGNORECASE,
)


def _month_num(abbr: str) -> int | None:
    return _MONTHS.get(abbr.lower().rstrip("."))


def _matches_date_range(dt_text: str, from_date: date, to_date: date) -> tuple[bool, date | None, str | None]:
    """Check if a date/time string falls within the query date range.

    Returns (matches, event_date, time_str or None).
    """
    # Try date range first: "Friday, Mar 6 – Sunday, Mar 8"
    m = _DATE_RANGE_RE.search(dt_text)
    if m:
        start_month = _month_num(m.group(1))
        start_day = int(m.group(2))
        end_month = _month_num(m.group(3))
        end_day = int(m.group(4))
        if start_month and end_month:
            start = infer_year(start_month, start_day, from_date)
            end = infer_year(end_month, end_day, from_date)
            if start and end and start <= to_date and end >= from_date:
                return True, max(start, from_date), None

    # Try single date: "Saturday, Mar 7 at 9:00 PM"
    m = _SINGLE_DATE_RE.search(dt_text)
    if m:
        month = _month_num(m.group(1))
        day = int(m.group(2))
        time_str = m.group(3).strip()
        if month:
            evt_date = infer_year(month, day, from_date)
            if evt_date and from_date <= evt_date <= to_date:
                return True, evt_date, time_str

    return False, None, None


def _listed_dates(dt_text: str, ref: date) -> list[date]:
    found = []
    m = _DATE_RANGE_RE.search(dt_text)
    pairs = [(m.group(1), m.group(2)), (m.group(3), m.group(4))] if m else []
    if not m and (single := _SINGLE_DATE_RE.search(dt_text)):
        pairs = [(single.group(1), single.group(2))]
    for month_abbr, day in pairs:
        month = _month_num(month_abbr)
        if month and (d := infer_year(month, int(day), ref)):
            found.append(d)
    return found


def _date_text(li: Tag) -> str:
    """Date/time text that follows the <br> in a listing item."""
    br = li.find("br")
    if not br or not br.next_sibling:
        return ""
    sibling = br.next_sibling
    return sibling.strip() if isinstance(sibling, str) else sibling.get_text(strip=True)


def listed_through(html: str, ref: date) -> date | None:
    """Last day the weekly page lists, to detect queries that run past the published week."""
    soup = BeautifulSoup(html, "html.parser")
    days = [
        d
        for ul in soup.select("ul.show-list")
        for li in ul.find_all("li", recursive=False)
        for d in _listed_dates(_date_text(li), ref)
    ]
    return max(days, default=None)


def parse_showhub(html: str, source_url: str, from_date: date, to_date: date) -> list[Event]:
    """Parse ShowHub HTML into Event objects, filtered to the date range."""
    soup = BeautifulSoup(html, "html.parser")
    events = []

    for ul in soup.select("ul.show-list"):
        for li in ul.find_all("li", recursive=False):
            link = li.find("a")
            if not link:
                continue

            dt_text = _date_text(li)
            matches, evt_date, time_str = _matches_date_range(dt_text, from_date, to_date)
            if not matches or evt_date is None:
                continue

            # Parse "Artist at Venue": rsplit so "at" in event names doesn't split wrong
            link_text = link.get_text(strip=True)
            if " at " in link_text:
                name, venue = link_text.rsplit(" at ", 1)
            else:
                name = link_text
                venue = None

            venue_name = venue.strip() if venue else None
            events.append(Event(
                name=name.strip(),
                city=city_from_text(venue_name),
                address=None,
                time=time_str,
                event_date=evt_date,
                source_name="ShowHub",
                source_url=str(link.get("href") or source_url),
                venue=venue_name,
                category="music",
            ))

    return events
