"""Tests for events/parsers/showhub.py — ShowHub HTML parser."""

from datetime import date
from pathlib import Path

from src.models import Event
from src.parsers.showhub import parse_showhub


FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "showhub_sample.html"
TARGET_DATE = date(2026, 3, 7)
SOURCE_URL = "https://showhub.ca/weekly-listings/"


def _load_fixture() -> str:
    return FIXTURE.read_text()


def _parse_fixture(from_date: date = TARGET_DATE, to_date: date = TARGET_DATE) -> list[Event]:
    return parse_showhub(_load_fixture(), SOURCE_URL, from_date, to_date)


def test_parse_returns_list_of_events():
    events = _parse_fixture()
    assert isinstance(events, list)
    assert all(isinstance(e, Event) for e in events)


def test_parse_filters_to_target_date():
    events_mar7 = _parse_fixture(date(2026, 3, 7), date(2026, 3, 7))
    events_mar8 = _parse_fixture(date(2026, 3, 8), date(2026, 3, 8))
    assert len(events_mar7) == 36
    assert len(events_mar8) == 18


def test_parse_extracts_event_name():
    events = _parse_fixture()
    names = [e.name for e in events]
    assert "Tracey Kofoed" in names
    assert "The Rattlers" in names


def test_parse_extracts_venue_as_address():
    events = _parse_fixture()
    ev = next(e for e in events if e.name == "Tracey Kofoed")
    assert ev.address == "Riley\u2019s"


def test_parse_extracts_time():
    events = _parse_fixture()
    ev = next(e for e in events if e.name == "Tracey Kofoed")
    assert ev.time == "11:00 AM"


def test_parse_extracts_source_url():
    events = _parse_fixture()
    for e in events:
        assert e.source_url.startswith("http")


def test_parse_source_name():
    events = _parse_fixture()
    assert all(e.source_name == "ShowHub" for e in events)


def test_parse_event_date():
    events = _parse_fixture()
    assert all(e.event_date == TARGET_DATE for e in events)


def test_parse_empty_html():
    events = parse_showhub("<html><body></body></html>", SOURCE_URL, TARGET_DATE, TARGET_DATE)
    assert events == []


def test_parse_date_range_includes_target():
    """Events with date ranges spanning the target date should be included."""
    html = """<html><body>
    <ul class="show-list">
    <li><a href="https://example.com/fest">Big Festival at Venue X</a><br>Friday, Mar 6 – Sunday, Mar 8</li>
    </ul>
    </body></html>"""
    events = parse_showhub(html, SOURCE_URL, date(2026, 3, 7), date(2026, 3, 7))
    assert len(events) == 1
    assert "Big Festival" in events[0].name
    assert events[0].event_date == date(2026, 3, 7)


def test_parse_excludes_wrong_date():
    html = """<html><body>
    <ul class="show-list">
    <li><a href="https://example.com/show">Solo Show at Club Y</a><br>Friday, Mar 6 at 8:00 PM</li>
    </ul>
    </body></html>"""
    events = parse_showhub(html, SOURCE_URL, date(2026, 3, 7), date(2026, 3, 7))
    assert len(events) == 0


def test_parse_exact_date_match():
    html = """<html><body>
    <ul class="show-list">
    <li><a href="https://example.com/show">Jazz Night at The Roxy</a><br>Saturday, Mar 7 at 9:00 PM</li>
    </ul>
    </body></html>"""
    events = parse_showhub(html, SOURCE_URL, date(2026, 3, 7), date(2026, 3, 7))
    assert len(events) == 1
    assert events[0].name == "Jazz Night"
    assert events[0].address == "The Roxy"
    assert events[0].time == "9:00 PM"
    assert events[0].event_date == date(2026, 3, 7)
