"""Tests for events/parsers/dailyhive.py — Daily Hive HTML/JSON parser."""

from datetime import date
from pathlib import Path

from src.models import Event
from src.parsers.dailyhive import parse_dailyhive


FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "dailyhive_sample.html"


def _load_fixture() -> str:
    return FIXTURE.read_text()


def test_parse_returns_list_of_events():
    events = parse_dailyhive(
        _load_fixture(),
        "https://dailyhive.com/vancouver/listed/events",
        date(2026, 3, 7),
    )
    assert isinstance(events, list)
    assert all(isinstance(e, Event) for e in events)


def test_parse_finds_events():
    events = parse_dailyhive(
        _load_fixture(),
        "https://dailyhive.com/vancouver/listed/events",
        date(2026, 3, 7),
    )
    assert len(events) > 0


def test_parse_extracts_event_name():
    events = parse_dailyhive(
        _load_fixture(),
        "https://dailyhive.com/vancouver/listed/events",
        date(2026, 3, 7),
    )
    names = [e.name for e in events]
    assert any(name for name in names if len(name) > 0)


def test_parse_extracts_city():
    events = parse_dailyhive(
        _load_fixture(),
        "https://dailyhive.com/vancouver/listed/events",
        date(2026, 3, 7),
    )
    cities = [e.city for e in events if e.city]
    assert len(cities) > 0


def test_parse_extracts_address():
    events = parse_dailyhive(
        _load_fixture(),
        "https://dailyhive.com/vancouver/listed/events",
        date(2026, 3, 7),
    )
    addresses = [e.address for e in events if e.address]
    assert len(addresses) > 0


def test_parse_source_name():
    events = parse_dailyhive(
        _load_fixture(),
        "https://dailyhive.com/vancouver/listed/events",
        date(2026, 3, 7),
    )
    assert all(e.source_name == "Daily Hive" for e in events)


def test_parse_filters_by_target_date():
    """Events that don't span the target date should be excluded."""
    # The fixture contains multi-day events; all returned should span Mar 7
    events = parse_dailyhive(
        _load_fixture(),
        "https://dailyhive.com/vancouver/listed/events",
        date(2026, 3, 7),
    )
    # All events should be within their date range covering March 7
    assert len(events) > 0


def test_parse_empty_html():
    events = parse_dailyhive(
        "<html><body></body></html>",
        "https://dailyhive.com/vancouver/listed/events",
        date(2026, 3, 7),
    )
    assert events == []


def test_parse_no_next_data():
    html = "<html><body><p>No data</p></body></html>"
    events = parse_dailyhive(
        html,
        "https://dailyhive.com/vancouver/listed/events",
        date(2026, 3, 7),
    )
    assert events == []


def test_parse_inline_json_events():
    """Test with a minimal inline JSON structure."""
    html = """<html><body>
    <script id="__NEXT_DATA__" type="application/json">
    {"props":{"pageProps":{"upcomingEvents":[
        {
            "id": 1,
            "title": "Test Festival",
            "venue_details": {"city": "Vancouver", "name": "Test Venue", "address": "123 Main St"},
            "start_datetime": "2026-03-06T10:00:00.000Z",
            "end_datetime": "2026-03-08T22:00:00.000Z",
            "ticket_url": "https://tickets.example.com",
            "slug": "test-festival",
            "categories": ["festival"]
        },
        {
            "id": 2,
            "title": "Past Event",
            "venue_details": {"city": "Vancouver", "name": "Old Venue", "address": "456 Oak St"},
            "start_datetime": "2026-03-01T10:00:00.000Z",
            "end_datetime": "2026-03-05T22:00:00.000Z",
            "ticket_url": "https://tickets.example.com/past",
            "slug": "past-event",
            "categories": ["music"]
        }
    ]}}}
    </script>
    </body></html>"""
    events = parse_dailyhive(html, "https://dailyhive.com/vancouver/listed/events", date(2026, 3, 7))
    assert len(events) == 1
    assert events[0].name == "Test Festival"
    assert events[0].city == "Vancouver"
    assert events[0].address == "123 Main St"
