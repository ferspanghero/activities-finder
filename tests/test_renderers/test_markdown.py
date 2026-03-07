"""Tests for events/renderers/markdown_renderer.py"""

from src.models import Event, SourceStatus
from src.renderers.markdown_renderer import render_markdown


EVENTS = [
    Event(name="Jazz Night", city="Vancouver", address="732 Main St", time="8:00 PM",
          source_name="Do604", source_url="https://do604.com/events/jazz"),
    Event(name="Rock Show", city="Burnaby", address=None, time="9:00 PM",
          source_name="ShowHub", source_url="https://showhub.ca/show/rock"),
]

STATUSES = [
    SourceStatus(name="Do604", count=1, error=None),
    SourceStatus(name="Daily Hive", count=0, error=None),
    SourceStatus(name="Rhythm Changes", count=0, error="Connection timeout"),
    SourceStatus(name="ShowHub", count=1, error=None),
    SourceStatus(name="Infidels Jazz", count=0, error=None),
]


def test_render_contains_summary():
    md = render_markdown(EVENTS, STATUSES, "2026-03-07")
    assert "Found 2 events across 2 cities from 2/5 sources" in md


def test_render_contains_table_header():
    md = render_markdown(EVENTS, STATUSES, "2026-03-07")
    assert "Event Name" in md
    assert "City" in md
    assert "Exact Address" in md
    assert "Time" in md
    assert "Source Link" in md


def test_render_contains_events():
    md = render_markdown(EVENTS, STATUSES, "2026-03-07")
    assert "Jazz Night" in md
    assert "Rock Show" in md
    assert "Vancouver" in md
    assert "Burnaby" in md


def test_render_missing_fields_use_em_dash():
    md = render_markdown(EVENTS, STATUSES, "2026-03-07")
    assert "\u2014" in md  # em dash for Rock Show's missing address


def test_render_contains_sources_footer():
    md = render_markdown(EVENTS, STATUSES, "2026-03-07")
    assert "Sources checked:" in md
    assert "Do604 (1)" in md
    assert "ShowHub (1)" in md
    assert "Rhythm Changes (ERROR: Connection timeout)" in md


def test_render_empty_events():
    md = render_markdown([], STATUSES, "2026-03-07")
    assert "Found 0 events" in md


def test_render_source_links():
    md = render_markdown(EVENTS, STATUSES, "2026-03-07")
    assert "https://do604.com/events/jazz" in md
    assert "https://showhub.ca/show/rock" in md
