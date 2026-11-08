"""Tests for src/parsers/bibliocommons.py: public-library events JSON parser."""

import json
from datetime import date
from pathlib import Path

from src.parsers.bibliocommons import page_count, parse_bibliocommons

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "bibliocommons_sample.json"
URL = "https://gateway.bibliocommons.com/v2/libraries/vpl/events/search?startDate=2026-11-07&endDate=2026-11-08&limit=100"


def _data() -> dict:
    return json.loads(FIXTURE.read_text())


def _single(definition: dict, location: dict | None = None) -> dict:
    base = {
        "start": "2026-11-07T10:00", "title": "Talk", "branchLocationId": "CEN",
        "isCancelled": False, "audienceIds": [], "typeIds": [],
    }
    loc = location if location is not None else {
        "CEN": {"id": "CEN", "name": "Central Library",
                "address": {"number": "350", "street": "W Georgia St", "city": "Vancouver", "country": "CA"}},
    }

    return {
        "events": {"pagination": {"pages": 1}},
        "entities": {
            "events": {"e1": {"id": "e1", "definition": {**base, **definition}}},
            "locations": loc, "eventAudiences": {}, "eventTypes": {},
        },
    }


def test_parse_returns_all_events_in_range() -> None:
    # Arrange, Act
    events = parse_bibliocommons(_data(), URL, date(2026, 11, 7), date(2026, 11, 8))

    # Assert
    assert len(events) == 28


def test_parse_filters_to_requested_dates() -> None:
    # Arrange, Act
    events = parse_bibliocommons(_data(), URL, date(2026, 11, 8), date(2026, 11, 8))

    # Assert
    assert len(events) == 11 and all(e.event_date == date(2026, 11, 8) for e in events)


def test_parse_extracts_branch_venue_address_city_and_time() -> None:
    # Arrange
    events = parse_bibliocommons(_data(), URL, date(2026, 11, 7), date(2026, 11, 8))

    # Act
    stay = next(e for e in events if e.name == "Family Stay and Play")

    # Assert
    assert (stay.venue, stay.address, stay.city, stay.time, stay.price) == (
        "West Point Grey Branch", "4566 West 10th Ave.", "Vancouver", "9:30 AM", "Free",
    )
    assert stay.source_url == "https://vpl.bibliocommons.com/v2/events/6a67b41c88e9bf280033ae54"
    assert stay.source_name == "Vancouver Public Library"


def test_parse_classifies_children_audiences_as_family() -> None:
    # Arrange
    events = parse_bibliocommons(_data(), URL, date(2026, 11, 7), date(2026, 11, 8))

    # Act
    stay = next(e for e in events if e.name == "Family Stay and Play")

    # Assert
    assert stay.category == "family"


def test_parse_skips_cancelled_events() -> None:
    # Arrange
    data = _single({"isCancelled": True})

    # Act
    events = parse_bibliocommons(data, URL, date(2026, 11, 7), date(2026, 11, 7))

    # Assert
    assert events == []


def test_parse_skips_locations_outside_canada() -> None:
    # Arrange
    data = _single({}, {"CEN": {"id": "CEN", "name": "Boston", "address": {"city": "Boston", "country": "US"}}})

    # Act
    events = parse_bibliocommons(data, URL, date(2026, 11, 7), date(2026, 11, 7))

    # Assert
    assert events == []


def test_parse_handles_missing_location() -> None:
    # Arrange
    data = _single({"branchLocationId": None}, {})

    # Act
    events = parse_bibliocommons(data, URL, date(2026, 11, 7), date(2026, 11, 7))

    # Assert
    assert (events[0].venue, events[0].city) == (None, None)


def test_parse_names_richmond_library_from_slug() -> None:
    # Arrange
    url = URL.replace("/vpl/", "/yourlibrary/")

    # Act
    events = parse_bibliocommons(_single({}), url, date(2026, 11, 7), date(2026, 11, 7))

    # Assert
    assert events[0].source_name == "Richmond Public Library"
    assert events[0].source_url.startswith("https://yourlibrary.bibliocommons.com/")


def test_page_count_reads_pagination() -> None:
    # Arrange, Act, Assert
    assert page_count(_data()) == 1
    assert page_count({}) == 1
