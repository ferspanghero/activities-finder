"""Parser for ShowHub weekly listings (HTML)."""

import re
from datetime import date

from bs4 import BeautifulSoup

from src.models import Event

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
            try:
                start = date(from_date.year, start_month, start_day)
                end = date(from_date.year, end_month, end_day)
                if start <= to_date and end >= from_date:
                    return True, max(start, from_date), None
            except ValueError:
                pass

    # Try single date: "Saturday, Mar 7 at 9:00 PM"
    m = _SINGLE_DATE_RE.search(dt_text)
    if m:
        month = _month_num(m.group(1))
        day = int(m.group(2))
        time_str = m.group(3).strip()
        if month:
            try:
                evt_date = date(from_date.year, month, day)
                if from_date <= evt_date <= to_date:
                    return True, evt_date, time_str
            except ValueError:
                pass

    return False, None, None


def parse_showhub(html: str, source_url: str, from_date: date, to_date: date) -> list[Event]:
    """Parse ShowHub HTML into Event objects, filtered to the date range."""
    soup = BeautifulSoup(html, "html.parser")
    events = []

    for ul in soup.select("ul.show-list"):
        for li in ul.find_all("li", recursive=False):
            link = li.find("a")
            if not link:
                continue

            # Get date/time text after <br>
            br = li.find("br")
            dt_text = ""
            if br and br.next_sibling:
                dt_text = (
                    br.next_sibling.strip()
                    if isinstance(br.next_sibling, str)
                    else br.next_sibling.get_text(strip=True)
                )

            matches, evt_date, time_str = _matches_date_range(dt_text, from_date, to_date)
            if not matches:
                continue

            # Parse "Artist at Venue" — rsplit so "at" in event names doesn't split wrong
            link_text = link.get_text(strip=True)
            if " at " in link_text:
                name, venue = link_text.rsplit(" at ", 1)
            else:
                name = link_text
                venue = None

            events.append(Event(
                name=name.strip(),
                city=None,  # ShowHub doesn't include city in listings
                address=venue.strip() if venue else None,
                time=time_str,
                event_date=evt_date,
                source_name="ShowHub",
                source_url=link.get("href", source_url),
            ))

    return events
