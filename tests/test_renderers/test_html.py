"""Tests for events/renderers/html_renderer.py"""

from src.models import Event, SourceStatus
from src.renderers.html_renderer import render_html


EVENTS = [
    Event(name="Jazz Night", city="Vancouver", address="732 Main St", time="8:00 PM",
          source_name="Do604", source_url="https://do604.com/events/jazz"),
    Event(name="Rock Show", city="Burnaby", address=None, time="9:00 PM",
          source_name="ShowHub", source_url="https://showhub.ca/show/rock"),
]

STATUSES = [
    SourceStatus(name="Do604", count=1, error=None),
    SourceStatus(name="ShowHub", count=1, error=None),
    SourceStatus(name="Daily Hive", count=0, error=None),
    SourceStatus(name="Rhythm Changes", count=0, error="Timeout"),
    SourceStatus(name="Infidels Jazz", count=0, error=None),
]


def test_render_html_returns_html():
    html = render_html(EVENTS, STATUSES, "2026-03-07")
    assert "<!DOCTYPE html>" in html
    assert "</html>" in html


def test_render_html_contains_events():
    html = render_html(EVENTS, STATUSES, "2026-03-07")
    assert "Jazz Night" in html
    assert "Rock Show" in html


def test_render_html_contains_summary():
    html = render_html(EVENTS, STATUSES, "2026-03-07")
    assert "Found 2 events" in html


def test_render_html_contains_sources_footer():
    html = render_html(EVENTS, STATUSES, "2026-03-07")
    assert "Do604 (1)" in html
    assert "Rhythm Changes (ERROR: Timeout)" in html


def test_render_html_contains_date():
    html = render_html(EVENTS, STATUSES, "2026-03-07")
    assert "Saturday, March 7, 2026" in html


def test_render_html_has_table():
    html = render_html(EVENTS, STATUSES, "2026-03-07")
    assert "<table" in html
    assert "<thead>" in html


def test_render_html_empty_events():
    html = render_html([], STATUSES, "2026-03-07")
    assert "No events found" in html
