"""Tests for src/renderers/filters.py: filter choices offered by the HTML report."""

from datetime import date

from src.models import Event
from src.renderers.filters import UNSET, report_filters


def _event(city: str | None, category: str | None, source: str) -> Event:
    return Event(name="E", city=city, address=None, time=None, event_date=date(2026, 3, 7),
                 source_name=source, source_url="u", category=category)


def test_report_filters_lists_distinct_values_sorted_with_unknowns_last() -> None:
    # Arrange
    events = [
        _event("Vancouver", "music", "ShowHub"),
        _event(None, None, "Do604"),
        _event("Burnaby", "family", "Do604"),
        _event("Vancouver", "music", "Eventbrite"),
    ]

    # Act
    filters = report_filters(events)

    # Assert
    assert filters.cities == (("Burnaby", "Burnaby"), ("Vancouver", "Vancouver"), (UNSET, "Unknown"))
    assert filters.types == (("music", "Live music"), ("family", "Family"), (UNSET, "Untyped"))
    assert filters.sources == (("Do604", "Do604"), ("Eventbrite", "Eventbrite"), ("ShowHub", "ShowHub"))


def test_report_filters_omits_unknown_entries_when_every_event_has_values() -> None:
    # Arrange
    events = [_event("Surrey", "food", "BC Ale Trail")]

    # Act
    filters = report_filters(events)

    # Assert
    assert filters.cities == (("Surrey", "Surrey"),) and filters.types == (("food", "Food & drink"),)


def test_report_filters_is_empty_for_no_events() -> None:
    # Arrange, Act
    filters = report_filters([])

    # Assert
    assert (filters.cities, filters.types, filters.sources) == ((), (), ())


def test_report_filters_counts_unknown_category_keys_as_untyped() -> None:
    # Arrange
    events = [_event("Vancouver", "karaoke", "S")]

    # Act
    filters = report_filters(events)

    # Assert
    assert filters.types == ((UNSET, "Untyped"),)


def test_report_filters_are_immutable_tuples() -> None:
    # Arrange, Act
    filters = report_filters([_event("Vancouver", "music", "S")])

    # Assert
    assert isinstance(filters.cities, tuple) and isinstance(filters.types, tuple) and isinstance(filters.sources, tuple)
