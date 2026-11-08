"""Tests for src/models.py: Event and SourceStatus serialization."""

from datetime import date

from src.models import Event, SourceStatus


def _full_event() -> Event:
    return Event(
        name="Jazz Night",
        city="Vancouver",
        address="732 Main St",
        time="8:00 PM",
        event_date=date(2026, 3, 7),
        source_name="Do604",
        source_url="https://do604.com/events/jazz",
        venue="The Ironworks",
        category="music",
        price="$20",
    )


def test_event_optional_fields_default_to_none() -> None:
    # Arrange, Act
    event = Event(
        name="X", city=None, address=None, time=None,
        event_date=date(2026, 3, 7), source_name="S", source_url="u",
    )

    # Assert
    assert (event.venue, event.category, event.price) == (None, None, None)


def test_event_round_trips_through_dict() -> None:
    # Arrange
    event = _full_event()

    # Act
    restored = Event.from_dict(event.to_dict())

    # Assert
    assert restored == event


def test_event_from_dict_tolerates_missing_optional_keys() -> None:
    # Arrange
    legacy = {
        "name": "Old", "event_date": "2026-03-07",
        "source_name": "Do604", "source_url": "u",
    }

    # Act
    event = Event.from_dict(legacy)

    # Assert
    assert event.venue is None and event.category is None and event.price is None


def test_source_status_round_trips_warning() -> None:
    # Arrange
    status = SourceStatus(name="Do604", count=0, error=None, warning="layout may have changed")

    # Act
    restored = SourceStatus.from_dict(status.to_dict())

    # Assert
    assert restored == status


def test_source_status_warning_defaults_to_none() -> None:
    # Arrange, Act
    status = SourceStatus(name="Do604", count=3, error=None)

    # Assert
    assert status.warning is None


def test_source_status_label_shows_count_error_and_warning() -> None:
    # Arrange
    ok = SourceStatus(name="A", count=3, error=None)
    failed = SourceStatus(name="B", count=0, error="timeout")
    warned = SourceStatus(name="C", count=0, error=None, warning="no events parsed")

    # Act
    labels = [s.label() for s in (ok, failed, warned)]

    # Assert
    assert labels == ["A (3)", "B (ERROR: timeout)", "C (0, WARNING: no events parsed)"]
