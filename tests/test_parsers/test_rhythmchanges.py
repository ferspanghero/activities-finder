"""Tests for events/parsers/rhythmchanges.py — Rhythm Changes HTML parser."""

from datetime import date
from pathlib import Path

from src.models import Event
from src.parsers.rhythmchanges import parse_rhythmchanges


FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "rhythmchanges_sample.html"


def _load_fixture() -> str:
    return FIXTURE.read_text()


def test_parse_returns_list_of_events():
    events = parse_rhythmchanges(_load_fixture(), "https://rhythmchanges.ca/gigs/", date(2026, 3, 7))
    assert isinstance(events, list)
    assert all(isinstance(e, Event) for e in events)


def test_parse_filters_to_target_date():
    events = parse_rhythmchanges(_load_fixture(), "https://rhythmchanges.ca/gigs/", date(2026, 3, 7))
    assert len(events) == 10


def test_parse_extracts_event_name():
    events = parse_rhythmchanges(_load_fixture(), "https://rhythmchanges.ca/gigs/", date(2026, 3, 7))
    names = [e.name for e in events]
    assert any("Tamas Balai Trio" in n for n in names)


def test_parse_extracts_venue_as_address():
    events = parse_rhythmchanges(_load_fixture(), "https://rhythmchanges.ca/gigs/", date(2026, 3, 7))
    tamas = next(e for e in events if "Tamas Balai" in e.name)
    assert tamas.address == "La Fabrique St-George"


def test_parse_extracts_time():
    events = parse_rhythmchanges(_load_fixture(), "https://rhythmchanges.ca/gigs/", date(2026, 3, 7))
    tamas = next(e for e in events if "Tamas Balai" in e.name)
    assert tamas.time == "2:00 PM"


def test_parse_source_name():
    events = parse_rhythmchanges(_load_fixture(), "https://rhythmchanges.ca/gigs/", date(2026, 3, 7))
    assert all(e.source_name == "Rhythm Changes" for e in events)


def test_parse_source_url():
    events = parse_rhythmchanges(_load_fixture(), "https://rhythmchanges.ca/gigs/", date(2026, 3, 7))
    for e in events:
        assert e.source_url == "https://rhythmchanges.ca/gigs/"


def test_parse_different_date():
    """March 1 gigs are struck through in the fixture (past), so returns 0."""
    events = parse_rhythmchanges(_load_fixture(), "https://rhythmchanges.ca/gigs/", date(2026, 3, 1))
    assert len(events) == 0


def test_parse_date_not_in_page():
    """A date not in the fixture should return empty."""
    events = parse_rhythmchanges(_load_fixture(), "https://rhythmchanges.ca/gigs/", date(2026, 4, 15))
    assert events == []


def test_parse_empty_html():
    events = parse_rhythmchanges("<html><body></body></html>", "https://rhythmchanges.ca/gigs/", date(2026, 3, 7))
    assert events == []


def test_parse_inline_html():
    html = """<html><body>
    <h2 id="week-1">Week 1</h2>
    <h4 id="friday-march-7">Friday, March 7</h4>
    <ul>
      <li>8:00 PM - Jazz Club, Mike Smith Trio ($10)</li>
      <li>9:30 PM - Blues Bar, Amy Jones Quartet (no cover)</li>
    </ul>
    </body></html>"""
    events = parse_rhythmchanges(html, "https://rhythmchanges.ca/gigs/", date(2026, 3, 7))
    assert len(events) == 2
    assert events[0].name == "Mike Smith Trio"
    assert events[0].address == "Jazz Club"
    assert events[0].time == "8:00 PM"
    assert events[1].name == "Amy Jones Quartet"
    assert events[1].address == "Blues Bar"
