"""Tests for events/parsers/infidelsjazz.py — Infidels Jazz JSON parser."""

import json
from datetime import date
from pathlib import Path

from src.models import Event
from src.parsers.infidelsjazz import parse_infidelsjazz


FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "infidelsjazz_sample.json"
TARGET_DATE = date(2026, 3, 7)
SOURCE_URL = "https://theinfidelsjazz.ca/wp-json/tribe/events/v1/events/"


def _load_fixture() -> dict:
    return json.loads(FIXTURE.read_text())


def test_parse_returns_list_of_events():
    data = _load_fixture()
    events = parse_infidelsjazz(data, SOURCE_URL, TARGET_DATE, TARGET_DATE)
    assert isinstance(events, list)
    assert all(isinstance(e, Event) for e in events)


def test_parse_extracts_event_name():
    data = _load_fixture()
    events = parse_infidelsjazz(data, SOURCE_URL, TARGET_DATE, TARGET_DATE)
    assert len(events) == 1
    # Title should have HTML entities decoded
    assert "Adam Robert Thomas Trio" in events[0].name
    assert "&#" not in events[0].name


def test_parse_extracts_venue():
    data = _load_fixture()
    events = parse_infidelsjazz(data, SOURCE_URL, TARGET_DATE, TARGET_DATE)
    assert events[0].address == "755 Beatty St"


def test_parse_extracts_city():
    data = _load_fixture()
    events = parse_infidelsjazz(data, SOURCE_URL, TARGET_DATE, TARGET_DATE)
    assert events[0].city == "Vancouver"


def test_parse_extracts_time():
    data = _load_fixture()
    events = parse_infidelsjazz(data, SOURCE_URL, TARGET_DATE, TARGET_DATE)
    assert events[0].time == "11:00 PM"


def test_parse_extracts_source_url():
    data = _load_fixture()
    events = parse_infidelsjazz(data, SOURCE_URL, TARGET_DATE, TARGET_DATE)
    assert events[0].source_url == "https://theinfidelsjazz.ca/event/adam-robert-thomas-trio-at-frankies-after-dark/"


def test_parse_source_name():
    data = _load_fixture()
    events = parse_infidelsjazz(data, SOURCE_URL, TARGET_DATE, TARGET_DATE)
    assert events[0].source_name == "Infidels Jazz"


def test_parse_event_date():
    data = _load_fixture()
    events = parse_infidelsjazz(data, SOURCE_URL, TARGET_DATE, TARGET_DATE)
    assert events[0].event_date == TARGET_DATE


def test_parse_empty_events():
    data = {"events": [], "total": 0, "total_pages": 0}
    events = parse_infidelsjazz(data, SOURCE_URL, TARGET_DATE, TARGET_DATE)
    assert events == []


def test_parse_missing_venue():
    data = {
        "events": [{
            "title": "Solo Piano Night",
            "start_date": "2026-03-07 20:00:00",
            "url": "https://theinfidelsjazz.ca/event/solo/",
        }],
        "total": 1,
    }
    events = parse_infidelsjazz(data, SOURCE_URL, TARGET_DATE, TARGET_DATE)
    assert len(events) == 1
    assert events[0].name == "Solo Piano Night"
    assert events[0].city is None
    assert events[0].address is None
    assert events[0].event_date == TARGET_DATE


def test_parse_multiple_events():
    data = {
        "events": [
            {
                "title": "Event One",
                "start_date": "2026-03-07 19:00:00",
                "url": "https://theinfidelsjazz.ca/event/one/",
                "venue": {"venue": "Club A", "address": "1 Main St", "city": "Vancouver"},
            },
            {
                "title": "Event Two",
                "start_date": "2026-03-07 21:00:00",
                "url": "https://theinfidelsjazz.ca/event/two/",
                "venue": {"venue": "Club B", "address": "2 Main St", "city": "Burnaby"},
            },
        ],
        "total": 2,
    }
    events = parse_infidelsjazz(data, SOURCE_URL, TARGET_DATE, TARGET_DATE)
    assert len(events) == 2
    assert events[0].name == "Event One"
    assert events[1].name == "Event Two"
    assert events[0].city == "Vancouver"
    assert events[1].city == "Burnaby"
    assert events[0].event_date == TARGET_DATE
    assert events[1].event_date == TARGET_DATE
