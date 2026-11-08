"""Tests for events/renderers/markdown_renderer.py"""

from datetime import date

from src.models import Event, SourceStatus
from src.renderers.markdown_renderer import render_markdown


def test_render_contains_summary(sample_events, sample_statuses):
    md = render_markdown(sample_events, sample_statuses, date(2026, 3, 7), date(2026, 3, 7))
    assert "Found 2 events across 2 cities from 2/5 sources" in md


def test_render_contains_table_header(sample_events, sample_statuses):
    md = render_markdown(sample_events, sample_statuses, date(2026, 3, 7), date(2026, 3, 7))
    assert "Event Name" in md
    assert "Date" in md
    assert "City" in md
    assert "Location" in md
    assert "Type" in md
    assert "Price" in md
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
    assert "[732 Main St](https://www.google.com/maps/search/?api=1&query=732%20Main%20St%2C%20Vancouver)" in md


def test_render_none_address_no_maps_link(sample_events, sample_statuses):
    md = render_markdown(sample_events, sample_statuses, date(2026, 3, 7), date(2026, 3, 7))
    lines = md.split("\n")
    rock_show_line = next(line for line in lines if "Rock Show" in line)
    assert "google.com/maps" not in rock_show_line


def test_render_shows_type_label_venue_and_price(sample_statuses):
    # Arrange
    event = Event(name="Trio", city="Vancouver", address="755 Beatty St", time="8 pm", event_date=date(2026, 3, 7),
                  source_name="Infidels Jazz", source_url="u", venue="Frankie's", category="music", price="$10")

    # Act
    md = render_markdown([event], sample_statuses, date(2026, 3, 7), date(2026, 3, 7))

    # Assert
    row = next(line for line in md.split("\n") if "Trio" in line)
    assert "| Live music |" in row and "Frankie's, 755 Beatty St" in row and "| $10 |" in row


def test_render_links_venue_only_location_to_maps(sample_statuses):
    # Arrange
    event = Event(name="Gig", city="Vancouver", address=None, time=None, event_date=date(2026, 3, 7),
                  source_name="ShowHub", source_url="u", venue="The Roxy")

    # Act
    md = render_markdown([event], sample_statuses, date(2026, 3, 7), date(2026, 3, 7))

    # Assert
    assert "[The Roxy](https://www.google.com/maps/search/?api=1&query=The%20Roxy%2C%20Vancouver)" in md


def test_render_footer_shows_source_warning(sample_events):
    # Arrange
    statuses = [SourceStatus(name="Do604", count=0, error=None, warning="layout may have changed")]

    # Act
    md = render_markdown(sample_events, statuses, date(2026, 3, 7), date(2026, 3, 7))

    # Assert
    assert "Do604 (0, WARNING: layout may have changed)" in md


def test_render_escapes_pipes_in_cells(sample_statuses):
    # Arrange
    event = Event(name="A | B", city=None, address=None, time=None, event_date=date(2026, 3, 7),
                  source_name="S", source_url="u")

    # Act
    md = render_markdown([event], sample_statuses, date(2026, 3, 7), date(2026, 3, 7))

    # Assert
    assert "A \\| B" in md


def test_render_markdown_guards_source_urls(sample_statuses):
    # Arrange
    bad = Event(name="Bad", city=None, address=None, time=None, event_date=date(2026, 3, 7),
                source_name="Daily Hive", source_url="javascript:alert(1)")
    odd = Event(name="Odd", city=None, address=None, time=None, event_date=date(2026, 3, 7),
                source_name="Eventbrite", source_url="https://x.com/a b(c)")

    # Act
    md = render_markdown([bad, odd], sample_statuses, date(2026, 3, 7), date(2026, 3, 7))

    # Assert
    assert "javascript:" not in md
    assert "[Eventbrite](https://x.com/a%20b%28c%29)" in md


def test_render_markdown_shows_time_ranges_in_clock_format() -> None:
    # Arrange
    event = Event(name="Gig", city="Vancouver", address=None, time="1 pm - 1:45 pm", event_date=date(2026, 3, 7),
                  source_name="S", source_url="https://example.com/g")

    # Act
    md = render_markdown([event], [SourceStatus(name="S", count=1, error=None)], date(2026, 3, 7), date(2026, 3, 7))

    # Assert
    assert "| 1:00 PM - 1:45 PM |" in md
