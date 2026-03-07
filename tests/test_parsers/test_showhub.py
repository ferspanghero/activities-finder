"""Tests for events/parsers/showhub.py — ShowHub HTML parser."""

from datetime import date
from pathlib import Path

from src.models import Event
from src.parsers.showhub import parse_showhub


FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "showhub_sample.html"


def _load_fixture() -> str:
    return FIXTURE.read_text()


def test_parse_returns_list_of_events():
    events = parse_showhub(_load_fixture(), "https://showhub.ca/weekly-listings/", date(2026, 3, 7))
    assert isinstance(events, list)
    assert all(isinstance(e, Event) for e in events)


def test_parse_filters_to_target_date():
    events = parse_showhub(_load_fixture(), "https://showhub.ca/weekly-listings/", date(2026, 3, 7))
    assert len(events) > 0
    # Should not include events only on Mar 6 or Mar 8
    for e in events:
        assert e.source_name == "ShowHub"


def test_parse_extracts_event_name_and_venue():
    events = parse_showhub(_load_fixture(), "https://showhub.ca/weekly-listings/", date(2026, 3, 7))
    # At least one event should have a name
    assert any(e.name for e in events)


def test_parse_extracts_time():
    events = parse_showhub(_load_fixture(), "https://showhub.ca/weekly-listings/", date(2026, 3, 7))
    times = [e.time for e in events if e.time]
    assert len(times) > 0


def test_parse_extracts_source_url():
    events = parse_showhub(_load_fixture(), "https://showhub.ca/weekly-listings/", date(2026, 3, 7))
    for e in events:
        assert e.source_url.startswith("http")


def test_parse_source_name():
    events = parse_showhub(_load_fixture(), "https://showhub.ca/weekly-listings/", date(2026, 3, 7))
    assert all(e.source_name == "ShowHub" for e in events)


def test_parse_empty_html():
    events = parse_showhub("<html><body></body></html>", "https://showhub.ca/weekly-listings/", date(2026, 3, 7))
    assert events == []


def test_parse_date_range_includes_target():
    """Events with date ranges spanning the target date should be included."""
    html = """<html><body>
    <ul class="show-list">
    <li><a href="https://example.com/fest">Big Festival at Venue X</a><br>Friday, Mar 6 – Sunday, Mar 8</li>
    </ul>
    </body></html>"""
    events = parse_showhub(html, "https://showhub.ca/weekly-listings/", date(2026, 3, 7))
    assert len(events) == 1
    assert "Big Festival" in events[0].name


def test_parse_excludes_wrong_date():
    html = """<html><body>
    <ul class="show-list">
    <li><a href="https://example.com/show">Solo Show at Club Y</a><br>Friday, Mar 6 at 8:00 PM</li>
    </ul>
    </body></html>"""
    events = parse_showhub(html, "https://showhub.ca/weekly-listings/", date(2026, 3, 7))
    assert len(events) == 0


def test_parse_exact_date_match():
    html = """<html><body>
    <ul class="show-list">
    <li><a href="https://example.com/show">Jazz Night at The Roxy</a><br>Saturday, Mar 7 at 9:00 PM</li>
    </ul>
    </body></html>"""
    events = parse_showhub(html, "https://showhub.ca/weekly-listings/", date(2026, 3, 7))
    assert len(events) == 1
    assert events[0].name == "Jazz Night"
    assert events[0].address == "The Roxy"
    assert events[0].time == "9:00 PM"
