"""Tests for events/renderers/markdown_renderer.py"""

from datetime import date

from src.renderers.markdown_renderer import render_markdown


def test_render_contains_summary(sample_events, sample_statuses):
    md = render_markdown(sample_events, sample_statuses, date(2026, 3, 7), date(2026, 3, 7))
    assert "Found 2 events across 2 cities from 2/5 sources" in md


def test_render_contains_table_header(sample_events, sample_statuses):
    md = render_markdown(sample_events, sample_statuses, date(2026, 3, 7), date(2026, 3, 7))
    assert "Event Name" in md
    assert "Date" in md
    assert "City" in md
    assert "Exact Address" in md
    assert "Time" in md
    assert "Source Link" in md


def test_render_contains_events(sample_events, sample_statuses):
    md = render_markdown(sample_events, sample_statuses, date(2026, 3, 7), date(2026, 3, 7))
    assert "Jazz Night" in md
    assert "Rock Show" in md
    assert "Vancouver" in md
    assert "Burnaby" in md


def test_render_contains_date_column(sample_events, sample_statuses):
    md = render_markdown(sample_events, sample_statuses, date(2026, 3, 7), date(2026, 3, 7))
    assert "Sat, Mar 7" in md


def test_render_missing_fields_use_em_dash(sample_events, sample_statuses):
    md = render_markdown(sample_events, sample_statuses, date(2026, 3, 7), date(2026, 3, 7))
    assert "\u2014" in md  # em dash for Rock Show's missing address


def test_render_contains_sources_footer(sample_events, sample_statuses):
    md = render_markdown(sample_events, sample_statuses, date(2026, 3, 7), date(2026, 3, 7))
    assert "Sources checked:" in md
    assert "Do604 (1)" in md
    assert "ShowHub (1)" in md
    assert "Rhythm Changes (ERROR: Connection timeout)" in md


def test_render_empty_events(sample_statuses):
    md = render_markdown([], sample_statuses, date(2026, 3, 7), date(2026, 3, 7))
    assert "Found 0 events" in md


def test_render_source_links(sample_events, sample_statuses):
    md = render_markdown(sample_events, sample_statuses, date(2026, 3, 7), date(2026, 3, 7))
    assert "https://do604.com/events/jazz" in md
    assert "https://showhub.ca/show/rock" in md


def test_render_address_has_maps_link(sample_events, sample_statuses):
    md = render_markdown(sample_events, sample_statuses, date(2026, 3, 7), date(2026, 3, 7))
    assert "[732 Main St](https://www.google.com/maps/search/" in md


def test_render_none_address_no_maps_link(sample_events, sample_statuses):
    md = render_markdown(sample_events, sample_statuses, date(2026, 3, 7), date(2026, 3, 7))
    lines = md.split("\n")
    rock_show_line = [l for l in lines if "Rock Show" in l][0]
    assert "google.com/maps" not in rock_show_line
