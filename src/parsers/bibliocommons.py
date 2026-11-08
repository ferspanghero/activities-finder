"""Parser for BiblioCommons public-library event search JSON (Vancouver and Richmond libraries)."""

import re
from datetime import date, datetime

from src.categories import map_source_category
from src.models import Event
from src.timeparse import format_clock

LIBRARY_NAMES: dict[str, str] = {
    "vpl": "Vancouver Public Library",
    "yourlibrary": "Richmond Public Library",
}

_SLUG_RE = re.compile(r"/libraries/([^/]+)/")
_FAMILY_AUDIENCE_RE = re.compile(r"bab|toddler|preschool|child|famil|kid|school age", re.IGNORECASE)


def library_slug(url: str) -> str:
    """BiblioCommons library slug from a gateway URL ('vpl' in .../libraries/vpl/events)."""
    m = _SLUG_RE.search(url)

    return m.group(1) if m else ""


def page_count(data: dict) -> int:
    """Total result pages reported by the search (1 when absent)."""
    return int(data.get("events", {}).get("pagination", {}).get("pages") or 1)


def _category(definition: dict, entities: dict) -> str:
    audiences = [entities.get("eventAudiences", {}).get(a, {}).get("name", "") for a in definition.get("audienceIds", [])]

    if any(_FAMILY_AUDIENCE_RE.search(a) for a in audiences):
        return "family"

    types = [entities.get("eventTypes", {}).get(t, {}).get("name") for t in definition.get("typeIds", [])]

    return next((c for c in map(map_source_category, types) if c), "community")


def parse_bibliocommons(data: dict, source_url: str, from_date: date, to_date: date) -> list[Event]:
    """Parse library events starting within the range; cancelled and non-Canadian ones are skipped."""
    slug = library_slug(source_url)
    entities = data.get("entities", {})
    locations = entities.get("locations", {})
    events = []

    for item in entities.get("events", {}).values():
        definition = item.get("definition", {})

        try:
            start = datetime.fromisoformat(definition["start"])
        except (KeyError, ValueError):
            continue

        if definition.get("isCancelled") or not from_date <= start.date() <= to_date:
            continue

        loc = locations.get(definition.get("branchLocationId") or "", {})
        addr = loc.get("address") or {}

        if addr.get("country") not in (None, "CA"):
            continue

        street = " ".join(p.strip() for p in (addr.get("number") or "", addr.get("street") or "") if p.strip())

        events.append(Event(
            name=(definition.get("title") or "").strip(),
            city=addr.get("city") or None,
            address=street or None,
            time=format_clock(start.hour, start.minute),
            event_date=start.date(),
            source_name=LIBRARY_NAMES.get(slug, slug),
            source_url=f"https://{slug}.bibliocommons.com/v2/events/{item.get('id', '')}",
            venue=loc.get("name"),
            category=_category(definition, entities),
            price="Free",
        ))

    return events
