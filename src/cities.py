"""City list, name normalization, detection in free text, and city filtering."""

import re

from src.models import Event

DEFAULT_CITIES: tuple[str, ...] = (
    "Vancouver", "Burnaby", "New Westminster", "Richmond", "North Vancouver (City)",
    "Lynn Valley", "Deep Cove", "West Vancouver", "Horseshoe Bay", "Surrey", "White Rock",
    "Port Moody", "Port Coquitlam", "Coquitlam", "Langley (City)", "Langley (Township)",
    "Delta", "Pitt Meadows", "Maple Ridge", "Mission", "Abbotsford", "Chilliwack",
    "Squamish", "Anmore", "Belcarra",
)

# Cities recognised inside free text (venue names, location strings). Covers the
# default list plus nearby places sources mention, so out-of-region events get a city too.
_KNOWN_CITIES: tuple[str, ...] = (
    "Vancouver", "North Vancouver", "West Vancouver", "Burnaby", "New Westminster",
    "Richmond", "Surrey", "White Rock", "Port Moody", "Port Coquitlam", "Coquitlam",
    "Langley", "Delta", "Tsawwassen", "Ladner", "Pitt Meadows", "Maple Ridge", "Mission",
    "Abbotsford", "Chilliwack", "Squamish", "Whistler", "Anmore", "Belcarra",
    "Lynn Valley", "Deep Cove", "Horseshoe Bay", "Fort Langley", "Victoria", "Kelowna",
)

# Communities that belong to a listed municipality, keyed by normalized name.
_COMMUNITY_OF: dict[str, str] = {
    "fort langley": "langley",
    "tsawwassen": "delta",
    "ladner": "delta",
    "lynn valley": "north vancouver",
    "deep cove": "north vancouver",
    "horseshoe bay": "west vancouver",
}

# "Victoria Drive" or "Burnaby St" names a street, not a city.
_STREET_SUFFIX = r"(drive|dr|street|st|avenue|ave|road|rd|way|boulevard|blvd|crescent|place|pl)\b"

_QUALIFIER_RE = re.compile(r"\s*\((city|township|district)\)\s*$|\s+(township|city)$", re.IGNORECASE)
_PROVINCE_RE = re.compile(r",\s*(bc|british columbia)$", re.IGNORECASE)


def _display_names() -> dict[str, str]:
    return {c.lower(): c for c in _KNOWN_CITIES if c.lower() not in _COMMUNITY_OF}


def normalize_city(name: str) -> str:
    """Canonical comparison key: lowercase, no province suffix or qualifier, communities folded.

    'Langley (Township)' and 'Fort Langley' both become 'langley'.
    """
    key = " ".join(name.split())
    key = _PROVINCE_RE.sub("", key)
    key = _QUALIFIER_RE.sub("", key).strip().lower()

    return _COMMUNITY_OF.get(key, key)


_DISPLAY_NAMES = _display_names()


def canonical_city(name: str) -> str:
    """Display name for a city: known cities and their communities map to the municipality name."""
    key = normalize_city(name)

    return _DISPLAY_NAMES.get(key) or key.title()


def city_from_text(text: str | None) -> str | None:
    """Find a known city named in free text, preferring the longest match.

    Longest-first stops "Vancouver" from matching inside "North Vancouver"; a city name
    followed by a street suffix ("Victoria Drive") is ignored.
    Returns None when no known city appears.
    """
    if not text:
        return None

    for city in sorted(_KNOWN_CITIES, key=len, reverse=True):
        if re.search(rf"(?<![\w-]){re.escape(city)}(?![\w-])(?!\s+{_STREET_SUFFIX})", text, re.IGNORECASE):
            return city

    return None


def _split(csv: str) -> set[str]:
    return {normalize_city(c) for c in csv.split(",") if c.strip()}


def resolve_allowed_cities(only: str | None, add: str | None) -> tuple[set[str], bool]:
    """Resolve CLI city flags into (allowed normalized cities, keep events with unknown city).

    `only` replaces the default list and drops unknown-city events; `add` extends it.
    Raises ValueError when both are given.
    """
    if only and add:
        raise ValueError("--cities and --add-cities are mutually exclusive")

    if only:
        return _split(only), False

    allowed = {normalize_city(c) for c in DEFAULT_CITIES}

    if add:
        allowed |= _split(add)

    return allowed, True


def filter_by_cities(events: list[Event], allowed: set[str], keep_unknown: bool) -> list[Event]:
    """Keep events whose normalized city is allowed; unknown-city events per `keep_unknown`."""
    return [
        e for e in events
        if (normalize_city(e.city) in allowed if e.city else keep_unknown)
    ]
