"""Tests for src/parsers/bcaletrail.py — BC Ale Trail HTML parser."""

from datetime import date
from pathlib import Path

from src.models import Event
from src.parsers.bcaletrail import parse_bcaletrail


FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "bcaletrail_sample.html"
TARGET_DATE = date(2026, 3, 8)
SOURCE_URL = "https://bcaletrail.ca/events/"


def _load_fixture() -> str:
    return FIXTURE.read_text()


def _parse_fixture(target_date: date = TARGET_DATE) -> list[Event]:
    return parse_bcaletrail(_load_fixture(), SOURCE_URL, target_date)


def test_parse_returns_list_of_events():
    events = _parse_fixture()
    assert isinstance(events, list)
    assert all(isinstance(e, Event) for e in events)


def test_parse_filters_to_target_date():
    """Should include events on Mar 8 only (events 1, 3, 5)."""
    events = _parse_fixture()
    assert len(events) == 3


def test_parse_excludes_wrong_date():
    """Mar 11 event (Paint Night) should not appear for Mar 8."""
    events = _parse_fixture()
    names = [e.name for e in events]
    assert "Paint Night at Mariner Brewing" not in names


def test_parse_recurring_event_matches_target_date():
    """Trivia Night has Mar 1, Mar 8, Mar 15 — should match Mar 8."""
    events = _parse_fixture()
    names = [e.name for e in events]
    assert "Trivia Night at Farm Country Brewing" in names


def test_parse_recurring_event_excludes_non_matching():
    """Yoga has Mar 2, Mar 9, Mar 16 — should NOT match Mar 8."""
    events = _parse_fixture()
    names = [e.name for e in events]
    assert "Yoga at Lillooet Brewing" not in names


def test_parse_extracts_event_name():
    events = _parse_fixture()
    names = [e.name for e in events]
    assert "Live Music at Five Roads Brewing" in names


def test_parse_extracts_city():
    events = _parse_fixture()
    ev = next(e for e in events if "Five Roads" in e.name)
    assert ev.city == "Langley"


def test_parse_extracts_address():
    events = _parse_fixture()
    ev = next(e for e in events if "Five Roads" in e.name)
    assert ev.address == "#1 - 6263 202 St"


def test_parse_extracts_time():
    events = _parse_fixture()
    ev = next(e for e in events if "Five Roads" in e.name)
    assert ev.time == "4:00 PM"


def test_parse_extracts_source_url():
    events = _parse_fixture()
    ev = next(e for e in events if "Five Roads" in e.name)
    assert ev.source_url == "https://bcaletrail.ca/event/live-music-at-five-roads-brewing/"


def test_parse_source_name():
    events = _parse_fixture()
    assert all(e.source_name == "BC Ale Trail" for e in events)


def test_parse_missing_location():
    """Events with empty locations list should have city=None, address=None."""
    events = _parse_fixture()
    ev = next(e for e in events if "Abandoned Rail" in e.name)
    assert ev.city is None
    assert ev.address is None


def test_parse_empty_html():
    events = parse_bcaletrail("<html><body></body></html>", SOURCE_URL, TARGET_DATE)
    assert events == []
