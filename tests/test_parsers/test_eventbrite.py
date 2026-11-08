"""Tests for src/parsers/eventbrite.py: Eventbrite search-page parser."""

import json
from datetime import date
from pathlib import Path

from src.parsers.eventbrite import page_count, parse_eventbrite

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "eventbrite_sample.html"
DAY = date(2026, 11, 7)
URL = "https://www.eventbrite.ca/d/canada--vancouver/all-events/?start_date=2026-11-07&end_date=2026-11-07"


def _page(results: list[dict], page_total: int = 1) -> str:
    data = {"search_data": {"events": {"results": results, "pagination": {"page_count": page_total}}}}

    return f"<html><script>window.__SERVER_DATA__ = {json.dumps(data)};</script></html>"


def _result(**overrides: object) -> dict:
    base = {
        "name": "Show", "start_date": "2026-11-07", "start_time": "19:30", "end_date": "2026-11-07",
        "url": "https://www.eventbrite.ca/e/show-1", "is_online_event": False, "is_cancelled": False,
        "primary_venue": {"name": "Hall", "address": {"address_1": "1 Main St", "city": "Burnaby"}},
        "tags": [{"prefix": "EventbriteCategory", "display_name": "Music"}],
    }

    return {**base, **overrides}


def test_parse_reads_all_fixture_events() -> None:
    # Arrange, Act
    events = parse_eventbrite(FIXTURE.read_text(), URL, DAY, DAY)

    # Assert
    assert len(events) == 10


def test_parse_extracts_venue_address_city_time_and_category() -> None:
    # Arrange
    events = parse_eventbrite(FIXTURE.read_text(), URL, DAY, DAY)

    # Act
    kupo = next(e for e in events if e.name.startswith("KupoCon"))

    # Assert
    assert (kupo.venue, kupo.address, kupo.city, kupo.time) == (
        "Hilton Vancouver Metrotown", "6083 McKay Avenue", "Burnaby", "9:00 AM",
    )
    chest = next(e for e in events if e.name.startswith("Chest Fever"))
    assert chest.category == "music"


def test_parse_skips_online_and_cancelled_events() -> None:
    # Arrange
    html = _page([_result(is_online_event=True), _result(is_cancelled=True), _result()])

    # Act
    events = parse_eventbrite(html, URL, DAY, DAY)

    # Assert
    assert len(events) == 1


def test_parse_clamps_multi_day_event_to_range_start_without_time() -> None:
    # Arrange
    html = _page([_result(start_date="2026-11-01", end_date="2026-11-30")])

    # Act
    events = parse_eventbrite(html, URL, DAY, DAY)

    # Assert
    assert (events[0].event_date, events[0].time) == (DAY, None)


def test_parse_skips_events_outside_range() -> None:
    # Arrange
    html = _page([_result(start_date="2026-11-09", end_date="2026-11-09")])

    # Act
    events = parse_eventbrite(html, URL, DAY, DAY)

    # Assert
    assert events == []


def test_parse_returns_empty_when_server_data_missing() -> None:
    # Arrange, Act
    events = parse_eventbrite("<html></html>", URL, DAY, DAY)

    # Assert
    assert events == []


def test_parse_tolerates_missing_venue() -> None:
    # Arrange
    html = _page([_result(primary_venue=None)])

    # Act
    events = parse_eventbrite(html, URL, DAY, DAY)

    # Assert
    assert (events[0].venue, events[0].city) == (None, None)


def test_page_count_reads_pagination() -> None:
    # Arrange, Act, Assert
    assert page_count(FIXTURE.read_text()) == 20
    assert page_count("<html></html>") == 1
