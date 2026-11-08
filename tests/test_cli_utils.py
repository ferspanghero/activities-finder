"""Tests for src/cli_utils.py: shared filtering, sorting, and dedup for both CLIs."""

from datetime import date

import pytest

from src.cli_utils import (
    FilterOptions,
    finalize_events,
    recount_sources,
    validate_filter_options,
)
from src.models import Event, SourceStatus


def _event(name: str, city: str | None, time: str | None = None, day: int = 7,
           category: str | None = None, venue: str | None = None, source: str = "Do604") -> Event:
    return Event(
        name=name, city=city, address=None, time=time, event_date=date(2026, 3, day),
        source_name=source, source_url=f"u/{name}/{source}", venue=venue, category=category,
    )


def test_finalize_applies_default_cities_and_keeps_unknown() -> None:
    # Arrange
    events = [_event("A", "Vancouver"), _event("B", "Kelowna"), _event("C", None)]

    # Act
    result = finalize_events(events, FilterOptions())

    # Assert
    assert [e.name for e in result.events] == ["A", "C"]


def test_finalize_override_cities_drops_unknown() -> None:
    # Arrange
    events = [_event("A", "Vancouver"), _event("B", "Burnaby"), _event("C", None)]

    # Act
    result = finalize_events(events, FilterOptions(cities="Burnaby"))

    # Assert
    assert [e.name for e in result.events] == ["B"]


def test_finalize_additive_cities_extends_default() -> None:
    # Arrange
    events = [_event("A", "Vancouver"), _event("B", "Kelowna")]

    # Act
    result = finalize_events(events, FilterOptions(add_cities="Kelowna"))

    # Assert
    assert {e.name for e in result.events} == {"A", "B"}


def test_finalize_filters_by_types() -> None:
    # Arrange
    events = [_event("A", "Vancouver", category="music"), _event("B", "Vancouver", category="food")]

    # Act
    result = finalize_events(events, FilterOptions(types="food"))

    # Assert
    assert [e.name for e in result.events] == ["B"]


def test_finalize_sorts_by_date_then_time_with_untimed_events_first() -> None:
    # Arrange
    events = [
        _event("Late", "Vancouver", time="9 pm"),
        _event("NextDay", "Vancouver", time="8 am", day=8),
        _event("Early", "Vancouver", time="10:00 AM"),
        _event("NoTime", "Vancouver"),
    ]

    # Act
    result = finalize_events(events, FilterOptions())

    # Assert
    assert [e.name for e in result.events] == ["NoTime", "Early", "Late", "NextDay"]


def test_finalize_merges_duplicates_and_reports_count() -> None:
    # Arrange
    events = [
        _event("Same Show", "Vancouver", time="8 pm", venue="Hall"),
        _event("Same Show", "Vancouver", time="8:00 PM", venue="The Hall", source="ShowHub"),
    ]

    # Act
    result = finalize_events(events, FilterOptions())

    # Assert
    assert (len(result.events), result.removed) == (1, 1)


def test_finalize_rejects_conflicting_city_flags() -> None:
    # Arrange, Act, Assert
    with pytest.raises(ValueError):
        finalize_events([], FilterOptions(cities="Vancouver", add_cities="Whistler"))


def test_finalize_rejects_unknown_type() -> None:
    # Arrange, Act, Assert
    with pytest.raises(ValueError):
        finalize_events([], FilterOptions(types="karaoke"))


def test_validate_filter_options_accepts_valid_flags() -> None:
    # Arrange, Act, Assert
    validate_filter_options(FilterOptions(add_cities="Whistler", types="music,food"))


def test_validate_filter_options_rejects_unknown_type() -> None:
    # Arrange, Act, Assert
    with pytest.raises(ValueError):
        validate_filter_options(FilterOptions(types="karaoke"))


def test_recount_sources_uses_final_events_and_keeps_warnings() -> None:
    # Arrange
    events = [_event("A", "Vancouver"), _event("B", "Vancouver", source="ShowHub")]
    statuses = [
        SourceStatus(name="Do604", count=9, error=None),
        SourceStatus(name="ShowHub", count=4, error=None, warning="w"),
        SourceStatus(name="Daily Hive", count=0, error="timeout"),
    ]

    # Act
    result = recount_sources(events, statuses)

    # Assert
    assert [(s.count, s.warning, s.error) for s in result] == [(1, None, None), (1, "w", None), (0, None, "timeout")]
