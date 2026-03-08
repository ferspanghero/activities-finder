"""Tests for events/renderers/html_renderer.py"""

from src.renderers.html_renderer import render_html


def test_render_html_returns_html(sample_events, sample_statuses):
    html = render_html(sample_events, sample_statuses, "2026-03-07")
    assert "<!DOCTYPE html>" in html
    assert "</html>" in html


def test_render_html_contains_events(sample_events, sample_statuses):
    html = render_html(sample_events, sample_statuses, "2026-03-07")
    assert "Jazz Night" in html
    assert "Rock Show" in html


def test_render_html_contains_summary(sample_events, sample_statuses):
    html = render_html(sample_events, sample_statuses, "2026-03-07")
    assert "Found 2 events" in html


def test_render_html_contains_sources_footer(sample_events, sample_statuses):
    html = render_html(sample_events, sample_statuses, "2026-03-07")
    assert "Do604 (1)" in html
    assert "Rhythm Changes (ERROR: Connection timeout)" in html


def test_render_html_contains_date(sample_events, sample_statuses):
    html = render_html(sample_events, sample_statuses, "2026-03-07")
    assert "Saturday, March 7, 2026" in html


def test_render_html_has_table(sample_events, sample_statuses):
    html = render_html(sample_events, sample_statuses, "2026-03-07")
    assert "<table" in html
    assert "<thead>" in html


def test_render_html_empty_events(sample_statuses):
    html = render_html([], sample_statuses, "2026-03-07")
    assert "No events found" in html


def test_render_html_address_has_maps_link(sample_events, sample_statuses):
    html = render_html(sample_events, sample_statuses, "2026-03-07")
    assert '<a href="https://www.google.com/maps/search/?api=1&amp;query=732%20Main%20St" target="_blank" rel="noopener noreferrer">732 Main St</a>' in html


def test_render_html_none_address_no_maps_link(sample_events, sample_statuses):
    html = render_html(sample_events, sample_statuses, "2026-03-07")
    assert "\u2014</td>" in html
    assert "Rock Show" in html
