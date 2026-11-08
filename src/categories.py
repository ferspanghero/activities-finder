"""Activity-type keys, mapping of source category labels, keyword classification, filtering."""

import re

from src.models import Event

CATEGORY_LABELS: dict[str, str] = {
    "music": "Live music",
    "festivals": "Festivals",
    "sports": "Sports",
    "art": "Art & exhibitions",
    "food": "Food & drink",
    "outdoor": "Outdoor",
    "community": "Community",
    "trivia": "Trivia & pub",
    "theatre": "Theatre & performing arts",
    "cultural": "Cultural",
    "family": "Family",
}

# Source labels (lowercased) from Do604, Daily Hive, Eventbrite, and BiblioCommons.
_SOURCE_LABELS: dict[str, str] = {
    "music": "music",
    "live music": "music",
    "dj/parties": "music",
    "concert": "music",
    "theatre & performing arts": "theatre",
    "performing & visual arts": "theatre",
    "theatre": "theatre",
    "arts-theatre": "theatre",
    "comedy": "theatre",
    "dance": "theatre",
    "art & culture": "art",
    "arts": "art",
    "art": "art",
    "exhibitions": "art",
    "festival": "festivals",
    "festivals": "festivals",
    "food & drink": "food",
    "food-drink": "food",
    "food and drink": "food",
    "sports": "sports",
    "sport": "sports",
    "sports & fitness": "sports",
    "trivia": "trivia",
    "family event": "family",
    "kids-family": "family",
    "family & education": "family",
    "storytimes": "family",
    "community": "community",
    "community & culture": "community",
    "markets": "community",
    "travel & outdoor": "outdoor",
    "outdoors": "outdoor",
    "outdoor": "outdoor",
}

# Ordered: the first matching rule wins, so specific types precede broad ones.
_KEYWORD_RULES: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (key, re.compile(pattern, re.IGNORECASE))
    for key, pattern in (
        ("trivia", r"\b(trivia|quiz|bingo)\b"),
        ("outdoor", r"\b(hike|hiking|run club|running club|group run|trail run|guided walk|nature walk|bike ride|kayak\w*|paddl\w*)\b"),
        ("cultural", r"\b(diwali|powwow|pow wow|lunar new year|hanukkah|vaisakhi|nowruz|day of the dead|d[ií]a de (los )?muertos)\b"),
        ("festivals", r"\b(fest|festival)\b"),
        ("family", r"\b(storytime|kids|family|children|toddlers?)\b"),
        ("community", r"\b(market|fair|flea|swap|clean-?up)\b"),
        ("sports", r"\b(vs\.?|canucks|whitecaps|bc lions|home game)\b"),
        ("food", r"\b(tasting|brunch|beer|wine|cider|brewery|food)\b"),
        ("theatre", r"\b(comedy|improv|stand-up|theatre|ballet|opera|musical|drag)\b"),
        ("music", r"\b(jazz|trio|quartet|quintet|band|concert|dj|live music|symphony|orchestra|choir|album release)\b"),
        ("art", r"\b(exhibition|exhibit|gallery|art show|curator)\b"),
    )
)


def map_source_category(raw: str | None) -> str | None:
    """Map a source's own category label to an activity-type key, or None when generic/unknown."""
    if not raw:
        return None

    return _SOURCE_LABELS.get(raw.strip().lower())


def categorize(event: Event) -> str | None:
    """Return the event's category, falling back to keyword rules on its name."""
    if event.category:
        return event.category

    for key, pattern in _KEYWORD_RULES:
        if pattern.search(event.name):
            return key

    return None


def parse_types(csv: str) -> set[str]:
    """Parse a comma-separated list of activity-type keys. Raises ValueError on unknown keys."""
    keys = {t.strip().lower() for t in csv.split(",") if t.strip()}
    unknown = keys - CATEGORY_LABELS.keys()

    if unknown:
        raise ValueError(f"unknown activity types {sorted(unknown)}; valid: {sorted(CATEGORY_LABELS)}")

    return keys


def filter_by_types(events: list[Event], types: set[str]) -> list[Event]:
    """Keep events whose category is one of `types`; uncategorized events are dropped."""
    return [e for e in events if e.category in types]
