"""Tests for events/renderers/html_renderer.py"""

from datetime import date

from src.models import Event, SourceStatus
from src.renderers.html_renderer import render_html


def test_render_html_returns_html(sample_events, sample_statuses):
    html = render_html(sample_events, sample_statuses, date(2026, 3, 7), date(2026, 3, 7))
    assert "<!DOCTYPE html>" in html
    assert "</html>" in html


def test_render_html_contains_events(sample_events, sample_statuses):
    html = render_html(sample_events, sample_statuses, date(2026, 3, 7), date(2026, 3, 7))
    assert "Jazz Night" in html
    assert "Rock Show" in html


def test_render_html_contains_summary(sample_events, sample_statuses):
    html = render_html(sample_events, sample_statuses, date(2026, 3, 7), date(2026, 3, 7))
    assert "Found 2 events" in html


def test_render_html_contains_sources_footer(sample_events, sample_statuses):
    html = render_html(sample_events, sample_statuses, date(2026, 3, 7), date(2026, 3, 7))
    assert "Do604 (1)" in html
    assert "Rhythm Changes (ERROR: Connection timeout)" in html


def test_render_html_contains_date(sample_events, sample_statuses):
    html = render_html(sample_events, sample_statuses, date(2026, 3, 7), date(2026, 3, 7))
    assert "Saturday, March 7, 2026" in html


def test_render_html_has_table(sample_events, sample_statuses):
    html = render_html(sample_events, sample_statuses, date(2026, 3, 7), date(2026, 3, 7))
    assert "<table" in html
    assert "<thead>" in html


def test_render_html_has_date_column(sample_events, sample_statuses):
    html = render_html(sample_events, sample_statuses, date(2026, 3, 7), date(2026, 3, 7))
    assert "Date" in html
    assert "Sat, Mar 7" in html


def test_render_html_empty_events(sample_statuses):
    html = render_html([], sample_statuses, date(2026, 3, 7), date(2026, 3, 7))
    assert "No events found" in html


def test_render_html_address_has_maps_link(sample_events, sample_statuses):
    html = render_html(sample_events, sample_statuses, date(2026, 3, 7), date(2026, 3, 7))
    assert '<a href="https://www.google.com/maps/search/?api=1&amp;query=732%20Main%20St%2C%20Vancouver" target="_blank" rel="noopener noreferrer">732 Main St</a>' in html


def test_render_html_none_address_no_maps_link(sample_events, sample_statuses):
    html = render_html(sample_events, sample_statuses, date(2026, 3, 7), date(2026, 3, 7))
    assert "\u2014</td>" in html
    assert "Rock Show" in html


def test_render_html_date_range_title(sample_events, sample_statuses):
    html = render_html(sample_events, sample_statuses, date(2026, 3, 7), date(2026, 3, 10))
    assert "March 7\u201310, 2026" in html


def test_render_html_date_range_no_events(sample_statuses):
    html = render_html([], sample_statuses, date(2026, 3, 7), date(2026, 3, 10))
    assert "No events found for this date range" in html


def test_render_html_has_type_location_and_price_columns(sample_events, sample_statuses):
    # Arrange, Act
    html = render_html(sample_events, sample_statuses, date(2026, 3, 7), date(2026, 3, 7))

    # Assert
    for header in ("Type", "Location", "Price"):
        assert f">{header} <span" in html


def test_render_html_shows_category_label_and_price(sample_statuses):
    # Arrange
    event = Event(name="Trio", city="Vancouver", address=None, time="8 pm", event_date=date(2026, 3, 7),
                  source_name="Infidels Jazz", source_url="u", venue="Frankie's", category="music", price="$10")

    # Act
    html = render_html([event], sample_statuses, date(2026, 3, 7), date(2026, 3, 7))

    # Assert
    assert "<td>Live music</td>" in html and "<td>$10</td>" in html and "Frankie&#x27;s</a>" in html


def test_render_html_sorts_time_column_by_minutes(sample_statuses):
    # Arrange
    event = Event(name="Gig", city=None, address=None, time="7 pm", event_date=date(2026, 3, 7),
                  source_name="S", source_url="u")

    # Act
    html = render_html([event], sample_statuses, date(2026, 3, 7), date(2026, 3, 7))

    # Assert
    assert 'data-sort-value="1140">7:00 PM</td>' in html


def test_render_html_footer_shows_warning(sample_events):
    # Arrange
    statuses = [SourceStatus(name="ShowHub", count=2, error=None, warning="lists events only through 2026-03-08")]

    # Act
    html = render_html(sample_events, statuses, date(2026, 3, 7), date(2026, 3, 10))

    # Assert
    assert "ShowHub (2, WARNING: lists events only through 2026-03-08)" in html


def test_render_html_does_not_link_non_http_source_urls(sample_statuses):
    # Arrange
    event = Event(name="Bad", city=None, address=None, time=None, event_date=date(2026, 3, 7),
                  source_name="Daily Hive", source_url="javascript:alert(1)")

    # Act
    html = render_html([event], sample_statuses, date(2026, 3, 7), date(2026, 3, 7))

    # Assert
    assert "javascript:" not in html and "<td>Daily Hive</td>" in html


def test_render_html_rows_carry_filter_attributes(sample_statuses):
    # Arrange
    event = Event(name="Trio", city="Vancouver", address=None, time="7 pm", event_date=date(2026, 3, 7),
                  source_name="Do604", source_url="https://do604.com/e", category="music")

    # Act
    html = render_html([event], sample_statuses, date(2026, 3, 7), date(2026, 3, 7))

    # Assert
    assert '<tr data-city="Vancouver" data-type="music" data-source="Do604" data-minutes="1140">' in html


def test_render_html_rows_mark_missing_values_as_unset(sample_statuses):
    # Arrange
    event = Event(name="Gig", city=None, address=None, time="varies", event_date=date(2026, 3, 7),
                  source_name="S", source_url="u")

    # Act
    html = render_html([event], sample_statuses, date(2026, 3, 7), date(2026, 3, 7))

    # Assert
    assert '<tr data-city="" data-type="" data-source="S" data-minutes="">' in html


def test_render_html_includes_filter_bar_with_choices(sample_events, sample_statuses):
    # Arrange, Act
    html = render_html(sample_events, sample_statuses, date(2026, 3, 7), date(2026, 3, 7))

    # Assert
    assert 'id="filters"' in html
    assert 'name="city" value="Burnaby"' in html and 'name="source" value="ShowHub"' in html
    assert 'id="filter-from"' in html and 'id="filter-to"' in html
    assert "<select" not in html
    assert 'id="shown-count"' in html


def test_render_html_escapes_filter_values(sample_statuses):
    # Arrange
    event = Event(name="X", city='Van"<couver', address=None, time=None, event_date=date(2026, 3, 7),
                  source_name="S", source_url="u")

    # Act
    html = render_html([event], sample_statuses, date(2026, 3, 7), date(2026, 3, 7))

    # Assert
    assert 'Van"<couver' not in html
    assert 'data-city="Van&quot;&lt;couver"' in html and 'value="Van&quot;&lt;couver"' in html


def test_render_html_omits_filter_bar_without_events(sample_statuses):
    # Arrange, Act
    html = render_html([], sample_statuses, date(2026, 3, 7), date(2026, 3, 7))

    # Assert
    assert 'id="filters"' not in html


def test_render_html_time_range_ends_at_end_of_day(sample_events, sample_statuses):
    # Arrange, Act
    html = render_html(sample_events, sample_statuses, date(2026, 3, 7), date(2026, 3, 7))

    # Assert
    assert '<input type="radio" name="to" value="1440"> end of day</label>' in html


def test_render_html_time_bounds_default_to_any_time(sample_events, sample_statuses):
    # Arrange, Act
    html = render_html(sample_events, sample_statuses, date(2026, 3, 7), date(2026, 3, 7))

    # Assert
    assert '<input type="radio" name="from" value="" checked> any time</label>' in html
    assert '<input type="radio" name="to" value="" checked> any time</label>' in html


def test_render_html_labels_time_range_and_announces_count(sample_events, sample_statuses):
    # Arrange, Act
    html = render_html(sample_events, sample_statuses, date(2026, 3, 7), date(2026, 3, 7))

    # Assert
    assert 'role="group" aria-label="Start time"' in html
    assert 'role="radiogroup" aria-label="Starts from"' in html
    assert 'id="shown-count" aria-live="polite"' in html


def test_render_html_treats_unknown_category_as_untyped(sample_statuses):
    # Arrange
    event = Event(name="Odd", city="Vancouver", address=None, time=None, event_date=date(2026, 3, 7),
                  source_name="S", source_url="u", category="karaoke")

    # Act
    html = render_html([event], sample_statuses, date(2026, 3, 7), date(2026, 3, 7))

    # Assert
    assert 'data-type=""' in html and 'name="type" value=""' in html


def test_render_html_neutralizes_hostile_values_in_every_filter_field(sample_statuses):
    # Arrange
    evil = '"><img src=x onerror=alert(1)>'
    event = Event(name=evil, city=evil, address=None, time=None, event_date=date(2026, 3, 7),
                  source_name=evil, source_url="u", venue=evil, category=evil)

    # Act
    html = render_html([event], sample_statuses, date(2026, 3, 7), date(2026, 3, 7))

    # Assert
    assert "<img" not in html
    assert 'data-source="&quot;&gt;&lt;img src=x onerror=alert(1)&gt;"' in html


def test_render_html_sorts_events_without_time_before_timed_ones(sample_statuses):
    # Arrange
    event = Event(name="Open House", city=None, address=None, time="varies", event_date=date(2026, 3, 7),
                  source_name="S", source_url="u")

    # Act
    html = render_html([event], sample_statuses, date(2026, 3, 7), date(2026, 3, 7))

    # Assert
    assert 'data-sort-value="-1">varies</td>' in html
