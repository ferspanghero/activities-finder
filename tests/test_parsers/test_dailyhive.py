"""Tests for events/parsers/dailyhive.py — Daily Hive HTML/JSON parser."""

from datetime import date
from pathlib import Path

from src.models import Event
from src.parsers.dailyhive import parse_dailyhive


FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "dailyhive_sample.html"
TARGET_DATE = date(2026, 3, 7)
SOURCE_URL = "https://dailyhive.com/vancouver/listed/events"


def _load_fixture() -> str:
    return FIXTURE.read_text()


def _parse_fixture(target_date: date = TARGET_DATE) -> list[Event]:
    return parse_dailyhive(_load_fixture(), SOURCE_URL, target_date)


def test_parse_returns_list_of_events():
    events = _parse_fixture()
    assert isinstance(events, list)
    assert all(isinstance(e, Event) for e in events)


def test_parse_finds_all_events():
    events = _parse_fixture()
    assert len(events) == 6


def test_parse_extracts_event_name():
    events = _parse_fixture()
    names = [e.name for e in events]
    assert "I Saw You" in names
    assert "VIMFF 2026" in names
    assert "Blockbuster" in names


def test_parse_extracts_city():
    events = _parse_fixture()
    ev = next(e for e in events if e.name == "I Saw You")
    assert ev.city == "Vancouver"


def test_parse_extracts_address():
    events = _parse_fixture()
    ev = next(e for e in events if e.name == "I Saw You")
    assert ev.address == "1502 Duranleau Street"


def test_parse_extracts_source_url():
    events = _parse_fixture()
    ev = next(e for e in events if e.name == "VIMFF 2026")
    assert ev.source_url == "https://tickets.vimff.org/dailyhive-calendar"


def test_parse_source_name():
    events = _parse_fixture()
    assert all(e.source_name == "Daily Hive" for e in events)


def test_parse_filters_by_target_date():
    """Events that don't span the target date should be excluded."""
    events_mar7 = _parse_fixture(date(2026, 3, 7))
    events_apr1 = _parse_fixture(date(2026, 4, 1))
    assert len(events_mar7) == 6
    assert len(events_apr1) == 2
    # Gathered Vintage is Mar 7 only — should not appear on Apr 1
    apr1_names = [e.name for e in events_apr1]
    assert not any("Gathered Vintage" in n for n in apr1_names)


def test_parse_empty_html():
    events = parse_dailyhive(
        "<html><body></body></html>", SOURCE_URL, TARGET_DATE,
    )
    assert events == []


def test_parse_no_next_data():
    html = "<html><body><p>No data</p></body></html>"
    events = parse_dailyhive(html, SOURCE_URL, TARGET_DATE)
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
    events = parse_dailyhive(html, SOURCE_URL, TARGET_DATE)
    assert len(events) == 1
    assert events[0].name == "Test Festival"
    assert events[0].city == "Vancouver"
    assert events[0].address == "123 Main St"
