"""Tests for events/parsers/do604.py — Do604 HTML parser."""

from datetime import date
from pathlib import Path

from src.models import Event
from src.parsers.do604 import parse_do604


FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "do604_sample.html"
TARGET_DATE = date(2026, 3, 7)


def _load_fixture() -> str:
    return FIXTURE.read_text()


def _parse_fixture() -> list[Event]:
    return parse_do604(_load_fixture(), "https://do604.com/events/2026/03/07", TARGET_DATE, TARGET_DATE)


def test_parse_returns_list_of_events():
    events = _parse_fixture()
    assert isinstance(events, list)
    assert all(isinstance(e, Event) for e in events)


def test_parse_finds_all_events():
    events = _parse_fixture()
    assert len(events) == 25


def test_parse_extracts_event_name():
    events = _parse_fixture()
    names = [e.name for e in events]
    assert "Ladysmith Black Mambazo" in names


def test_parse_extracts_venue_as_address():
    events = _parse_fixture()
    lbm = next(e for e in events if e.name == "Ladysmith Black Mambazo")
    assert lbm.address == "735 Eighth Avenue"


def test_parse_extracts_city():
    events = _parse_fixture()
    lbm = next(e for e in events if e.name == "Ladysmith Black Mambazo")
    assert lbm.city == "New Westminster"


def test_parse_extracts_time():
    events = _parse_fixture()
    lbm = next(e for e in events if e.name == "Ladysmith Black Mambazo")
    assert lbm.time == "7:30PM"


def test_parse_extracts_source_url():
    events = _parse_fixture()
    lbm = next(e for e in events if e.name == "Ladysmith Black Mambazo")
    assert lbm.source_url == "https://do604.com/events/2026/3/7/ladysmith-black-mambazo-tickets"


def test_parse_source_name():
    events = _parse_fixture()
    assert all(e.source_name == "Do604" for e in events)


def test_parse_event_date():
    events = _parse_fixture()
    assert all(e.event_date == TARGET_DATE for e in events)


def test_parse_empty_html():
    events = parse_do604("<html><body></body></html>", "https://do604.com/events/2026/03/07", TARGET_DATE, TARGET_DATE)
    assert events == []


def test_parse_event_with_missing_venue():
    html = """
    <div class="ds-listing event-card" data-permalink="/events/2026/3/7/test">
      <a class="ds-listing-event-title" href="/events/2026/3/7/test">
        <span class="ds-listing-event-title-text">Test Event</span>
      </a>
      <div class="ds-event-time">8:00PM</div>
    </div>
    """
    events = parse_do604(html, "https://do604.com/events/2026/03/07", TARGET_DATE, TARGET_DATE)
    assert len(events) == 1
    assert events[0].name == "Test Event"
    assert events[0].city is None
    assert events[0].address is None
    assert events[0].event_date == TARGET_DATE
