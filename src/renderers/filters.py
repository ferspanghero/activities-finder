"""Filter choices for the HTML report: the cities, activity types, and sources present."""

from dataclasses import dataclass

from src.categories import CATEGORY_LABELS
from src.models import Event

# Filter value for events with no city or no type.
UNSET = ""


@dataclass(frozen=True)
class ReportFilters:
    """(value, label) choices per filter, in display order; unknowns come last."""

    cities: tuple[tuple[str, str], ...]
    types: tuple[tuple[str, str], ...]
    sources: tuple[tuple[str, str], ...]


def type_value(event: Event) -> str:
    """The event's activity-type key, or UNSET when missing or not a known key."""
    return event.category if event.category in CATEGORY_LABELS else UNSET


def report_filters(events: list[Event]) -> ReportFilters:
    """Choices offered by the report's filter bar for these events."""
    cities = sorted({e.city for e in events if e.city})
    present_types = {type_value(e) for e in events}
    sources = sorted({e.source_name for e in events})
    city_choices = [(c, c) for c in cities]
    type_choices = [(k, label) for k, label in CATEGORY_LABELS.items() if k in present_types]

    if any(not e.city for e in events):
        city_choices.append((UNSET, "Unknown"))

    if UNSET in present_types:
        type_choices.append((UNSET, "Untyped"))

    return ReportFilters(
        cities=tuple(city_choices), types=tuple(type_choices), sources=tuple((s, s) for s in sources),
    )
