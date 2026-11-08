"""Parser for Do604 day pages (Svelte-rendered event cards, 20 per page)."""

import re
from datetime import date
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from src.categories import map_source_category
from src.cities import city_from_text
from src.models import Event
from src.timeparse import parse_time_to_minutes

CARD_SELECTOR = 'div.standard-card[data-card-kind="event"]'
# Do604 marks an all-day event as running midnight to 11:59 pm.
_ALL_DAY_RE = re.compile(r"12(?::00)?\s*am\s*[-–]\s*11:59\s*pm", re.IGNORECASE)
# A date range ("Oct 22 - Nov 27") marks a long-running listing. Its time, when before 6 AM, is a
# placeholder series start ("4 am"), not this day's; a real run keeps its show time ("7 pm").
_DATE_RANGE_RE = re.compile(r"[-–]")
_EARLIEST_REAL_START = 6 * 60

# Do604 neighbourhood labels that do not name their city.
_NEIGHBOURHOOD_CITY: dict[str, str] = {
    "Gastown": "Vancouver",
    "Granville Entertainment District": "Vancouver",
    "Granville Island": "Vancouver",
    "Commercial Drive / The Drive": "Vancouver",
    "Hastings-Sunrise / PNE Grounds": "Vancouver",
    "Kitsilano / West Broadway": "Vancouver",
    "Main Street / Mount Pleasant": "Vancouver",
    "Stadium District": "Vancouver",
    "Strathcona / Railtown": "Vancouver",
    "Chinatown": "Vancouver",
    "Davie Village": "Vancouver",
    "Olympic Village": "Vancouver",
    "Coal Harbour": "Vancouver",
    "Yaletown": "Vancouver",
    "West End / Denman": "Vancouver",
    "Downtown": "Vancouver",
    "Central City / Guildford": "Surrey",
    "Metrotown / Brentwood": "Burnaby",
}


def has_events(html: str) -> bool:
    """True when the page contains at least one event card (pagination stop signal)."""
    return 'data-card-kind="event"' in html


def _resolve_city(enrichment_parts: list[str], venue: str | None) -> str | None:
    for part in enrichment_parts[1:]:
        if part in _NEIGHBOURHOOD_CITY:
            return _NEIGHBOURHOOD_CITY[part]

        if city := city_from_text(part):
            return city

    return city_from_text(venue)


def _parse_card(card: Tag, page_url: str, day: date) -> Event | None:
    title_el = card.find("h3")
    title = title_el.get_text(strip=True) if title_el else ""

    if not title:
        return None

    date_el = card.select_one("p.date")
    time = None

    if date_el and "|" in (date_text := date_el.get_text(" ", strip=True)):
        dates, _, time = (part.strip() for part in date_text.rpartition("|"))

        if _ALL_DAY_RE.fullmatch(time):
            time = "all day"
        elif _DATE_RANGE_RE.search(dates) and parse_time_to_minutes(time) < _EARLIEST_REAL_START:
            time = None

        time = time or None

    venue = None

    if date_el:
        venue_el = date_el.find_next_sibling("p", class_=lambda c: not c or "enrichment" not in c)
        venue = venue_el.get_text(strip=True) if venue_el else None

    enrichment_el = card.select_one("p.enrichment")
    parts = [p.strip() for p in enrichment_el.get_text().split("•")] if enrichment_el else []
    link = card.select_one("a.card-link")
    href = link.get("href") if link else None

    return Event(
        name=title,
        city=_resolve_city(parts, venue),
        address=None,
        time=time,
        event_date=day,
        source_name="Do604",
        source_url=urljoin(page_url, href) if isinstance(href, str) else page_url,
        venue=venue,
        category=map_source_category(parts[0]) if parts else None,
    )


def parse_do604(html: str, source_url: str, from_date: date, to_date: date) -> list[Event]:
    """Parse one Do604 day page; every card is dated `from_date` (pages are fetched per day)."""
    soup = BeautifulSoup(html, "html.parser")
    events = (_parse_card(card, source_url, from_date) for card in soup.select(CARD_SELECTOR))

    return [e for e in events if e is not None]
