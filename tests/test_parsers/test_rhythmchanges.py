"""Tests for events/parsers/rhythmchanges.py — Rhythm Changes HTML parser."""

from datetime import date
from pathlib import Path

from src.models import Event
from src.parsers.rhythmchanges import parse_rhythmchanges, _parse_gig_line, _parse_day_header


FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "rhythmchanges_sample.html"


def _load_fixture() -> str:
    return FIXTURE.read_text()


def test_parse_returns_list_of_events():
    events = parse_rhythmchanges(_load_fixture(), "https://rhythmchanges.ca/gigs/", date(2026, 3, 7), date(2026, 3, 7))
    assert isinstance(events, list)
    assert all(isinstance(e, Event) for e in events)


def test_parse_filters_to_target_date():
    events = parse_rhythmchanges(_load_fixture(), "https://rhythmchanges.ca/gigs/", date(2026, 3, 7), date(2026, 3, 7))
    assert len(events) == 10


def test_parse_extracts_event_name():
    events = parse_rhythmchanges(_load_fixture(), "https://rhythmchanges.ca/gigs/", date(2026, 3, 7), date(2026, 3, 7))
    names = [e.name for e in events]
    assert any("Tamas Balai Trio" in n for n in names)


def test_parse_extracts_venue_as_address():
    events = parse_rhythmchanges(_load_fixture(), "https://rhythmchanges.ca/gigs/", date(2026, 3, 7), date(2026, 3, 7))
    tamas = next(e for e in events if "Tamas Balai" in e.name)
    assert tamas.address == "La Fabrique St-George"


def test_parse_extracts_time():
    events = parse_rhythmchanges(_load_fixture(), "https://rhythmchanges.ca/gigs/", date(2026, 3, 7), date(2026, 3, 7))
    tamas = next(e for e in events if "Tamas Balai" in e.name)
    assert tamas.time == "2:00 PM"


def test_parse_source_name():
    events = parse_rhythmchanges(_load_fixture(), "https://rhythmchanges.ca/gigs/", date(2026, 3, 7), date(2026, 3, 7))
    assert all(e.source_name == "Rhythm Changes" for e in events)


def test_parse_source_url():
    events = parse_rhythmchanges(_load_fixture(), "https://rhythmchanges.ca/gigs/", date(2026, 3, 7), date(2026, 3, 7))
    for e in events:
        assert e.source_url == "https://rhythmchanges.ca/gigs/"


def test_parse_event_date():
    events = parse_rhythmchanges(_load_fixture(), "https://rhythmchanges.ca/gigs/", date(2026, 3, 7), date(2026, 3, 7))
    assert all(e.event_date == date(2026, 3, 7) for e in events)


def test_parse_different_date():
    """March 1 gigs are struck through in the fixture (past), so returns 0."""
    events = parse_rhythmchanges(_load_fixture(), "https://rhythmchanges.ca/gigs/", date(2026, 3, 1), date(2026, 3, 1))
    assert len(events) == 0


def test_parse_date_not_in_page():
    """A date not in the fixture should return empty."""
    events = parse_rhythmchanges(_load_fixture(), "https://rhythmchanges.ca/gigs/", date(2026, 4, 15), date(2026, 4, 15))
    assert events == []


def test_parse_empty_html():
    events = parse_rhythmchanges("<html><body></body></html>", "https://rhythmchanges.ca/gigs/", date(2026, 3, 7), date(2026, 3, 7))
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
    events = parse_rhythmchanges(html, "https://rhythmchanges.ca/gigs/", date(2026, 3, 7), date(2026, 3, 7))
    assert len(events) == 2
    assert events[0].name == "Mike Smith Trio"
    assert events[0].address == "Jazz Club"
    assert events[0].time == "8:00 PM"
    assert events[0].event_date == date(2026, 3, 7)
    assert events[1].name == "Amy Jones Quartet"
    assert events[1].address == "Blues Bar"


def test_parse_date_range():
    """Multiple days in a range should return events for all matching days."""
    html = """<html><body>
    <h4 id="friday-march-7">Friday, March 7</h4>
    <ul>
      <li>8:00 PM - Jazz Club, Friday Gig</li>
    </ul>
    <h4 id="saturday-march-8">Saturday, March 8</h4>
    <ul>
      <li>9:00 PM - Blues Bar, Saturday Gig</li>
    </ul>
    </body></html>"""
    events = parse_rhythmchanges(html, "https://rhythmchanges.ca/gigs/", date(2026, 3, 7), date(2026, 3, 8))
    assert len(events) == 2
    assert events[0].event_date == date(2026, 3, 7)
    assert events[1].event_date == date(2026, 3, 8)


# --- _parse_gig_line fallback tests ---


def test_gig_line_no_separator():
    """Line with no ' - ' separator returns full text as event name."""
    time, venue, name = _parse_gig_line("Just a plain text line")
    assert time is None
    assert venue is None
    assert name == "Just a plain text line"


def test_gig_line_fallback_with_comma():
    """Non-standard time format falls back to split on ' - ' and ','."""
    time, venue, name = _parse_gig_line("Evening - The Cellar, Blues Jam ($5)")
    assert time == "Evening"
    assert venue == "The Cellar"
    assert name == "Blues Jam"


def test_gig_line_fallback_no_comma():
    """Fallback with ' - ' but no comma returns no venue."""
    time, venue, name = _parse_gig_line("Late - Open Mic Night")
    assert time == "Late"
    assert venue is None
    assert name == "Open Mic Night"


def test_gig_line_fallback_strips_price():
    """Fallback path strips trailing parenthetical price."""
    time, venue, name = _parse_gig_line("TBA - Venue X, Band Name ($10)")
    assert time == "TBA"
    assert venue == "Venue X"
    assert name == "Band Name"


# --- _parse_day_header tests ---


def test_parse_day_header_valid():
    result = _parse_day_header("Friday, March 7", 2026)
    assert result == date(2026, 3, 7)


def test_parse_day_header_unrecognized_format():
    result = _parse_day_header("Not a date header", 2026)
    assert result is None


def test_parse_day_header_unknown_month():
    result = _parse_day_header("Friday, Smarch 7", 2026)
    assert result is None


def test_parse_day_header_invalid_day():
    result = _parse_day_header("Friday, February 30", 2026)
    assert result is None


# --- integration of fallback through parse_rhythmchanges ---


def test_parse_fallback_gig_format():
    """Gig lines that don't match the regex should still produce events."""
    html = """<html><body>
    <h4 id="friday-march-7">Friday, March 7</h4>
    <ul>
      <li>Evening - The Cellar, Open Blues Jam</li>
    </ul>
    </body></html>"""
    events = parse_rhythmchanges(html, "https://rhythmchanges.ca/gigs/", date(2026, 3, 7), date(2026, 3, 7))
    assert len(events) == 1
    assert events[0].name == "Open Blues Jam"
    assert events[0].address == "The Cellar"
    assert events[0].time == "Evening"
