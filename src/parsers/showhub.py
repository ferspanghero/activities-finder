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


def _matches_target_date(dt_text: str, target: date) -> tuple[bool, str | None]:
    """Check if a date/time string matches the target date.

    Returns (matches, time_str or None).
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
                start = date(target.year, start_month, start_day)
                end = date(target.year, end_month, end_day)
                return start <= target <= end, None
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
                event_date = date(target.year, month, day)
                return event_date == target, time_str
            except ValueError:
                pass

    return False, None


def parse_showhub(html: str, source_url: str, target_date: date) -> list[Event]:
    """Parse ShowHub HTML into Event objects, filtered to target_date."""
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

            matches, time_str = _matches_target_date(dt_text, target_date)
            if not matches:
                continue

            # Parse "Artist at Venue" from link text
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
                source_name="ShowHub",
                source_url=link.get("href", source_url),
            ))

    return events
