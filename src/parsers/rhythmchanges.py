"""Parser for Rhythm Changes gig listings (HTML)."""

import re
from datetime import date

from bs4 import BeautifulSoup

from src.models import Event

# Month name to number
_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}

# Pattern for gig line: "TIME - VENUE, EVENT (PRICE)"
_GIG_RE = re.compile(r"^(\d{1,2}:\d{2}\s*[AP]M)\s*-\s*(.+?),\s*(.+?)(?:\(.*\))?\s*$", re.IGNORECASE)


def _parse_day_header(h4_text: str, year: int) -> date | None:
    """Parse 'Saturday, March 7' into a date object."""
    # Remove day name prefix
    m = re.match(r"(?:Sun|Mon|Tue|Wed|Thu|Fri|Sat)\w*,\s+(\w+)\s+(\d+)", h4_text)
    if not m:
        return None
    month_name = m.group(1).lower()
    day = int(m.group(2))
    month = _MONTHS.get(month_name)
    if not month:
        return None
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _parse_gig_line(text: str) -> tuple[str | None, str | None, str | None]:
    """Parse a gig line into (time, venue, event_name).

    Format: "8:00 PM - Jazz Club, Mike Smith Trio ($10)"
    """
    m = _GIG_RE.match(text.strip())
    if m:
        return m.group(1).strip(), m.group(2).strip(), m.group(3).strip()

    # Fallback: try splitting on " - " and then ","
    parts = text.strip().split(" - ", 1)
    if len(parts) != 2:
        return None, None, text.strip()

    time_str = parts[0].strip()
    rest = parts[1].strip()

    # Split venue from event name on first comma
    comma_parts = rest.split(",", 1)
    if len(comma_parts) == 2:
        venue = comma_parts[0].strip()
        event_name = re.sub(r"\(.*?\)\s*$", "", comma_parts[1]).strip()
        return time_str, venue, event_name

    return time_str, None, rest


def parse_rhythmchanges(html: str, source_url: str, target_date: date) -> list[Event]:
    """Parse Rhythm Changes HTML into Event objects for the target date."""
    soup = BeautifulSoup(html, "html.parser")
    events = []

    for h4 in soup.find_all("h4"):
        day_date = _parse_day_header(h4.get_text(strip=True), target_date.year)
        if day_date != target_date:
            continue

        # Get the <ul> following this h4
        ul = h4.find_next_sibling("ul")
        if not ul:
            continue

        for li in ul.find_all("li", recursive=False):
            # Rhythm Changes uses <s> (strikethrough) to mark cancelled/past gigs
            if li.find("s"):
                continue

            text = li.get_text(strip=True)
            if not text:
                continue

            time_str, venue, event_name = _parse_gig_line(text)

            events.append(Event(
                name=event_name or text,
                city=None,  # Rhythm Changes doesn't list cities
                address=venue,
                time=time_str,
                source_name="Rhythm Changes",
                source_url=source_url,
            ))

    return events
