"""Tests for scripts/generate_html.py — HTML event report generator."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from scripts.generate_html import (
    build_event_row,
    build_sources_footer,
    escape_and_format,
    format_date_display,
    generate_html,
    parse_time_to_minutes,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MINIMAL_INPUT = {
    "date": "2026-03-08",
    "summary": {"total_events": 1, "total_cities": 1, "sources_reporting": 1, "sources_total": 5},
    "events": [
        {
            "name": "Jazz Night",
            "city": "Vancouver",
            "address": "732 Main St",
            "time": "8:00 PM",
            "source_name": "Do604",
            "source_url": "https://do604.com/events/2026/3/8/jazz-night",
        }
    ],
    "sources": [
        {"name": "Do604", "count": 1, "error": None},
        {"name": "Daily Hive", "count": 0, "error": None},
        {"name": "Rhythm Changes", "count": 0, "error": None},
        {"name": "ShowHub", "count": 0, "error": None},
        {"name": "Infidels Jazz", "count": 0, "error": None},
    ],
}

SAMPLE_INPUT = {
    "date": "2026-03-07",
    "summary": {"total_events": 3, "total_cities": 2, "sources_reporting": 3, "sources_total": 5},
    "events": [
        {
            "name": "HSBC Vancouver Sevens",
            "city": "Vancouver",
            "address": "777 Pacific Blvd (BC Place)",
            "time": "10:00 AM",
            "source_name": "Do604",
            "source_url": "https://do604.com/events/2026/3/7/sevens",
        },
        {
            "name": "Joel Faulkner Trio",
            "city": "Burnaby",
            "address": "Steamworks Taproom Burnaby",
            "time": "5:00 PM",
            "source_name": "Rhythm Changes",
            "source_url": "https://www.rhythmchanges.ca/gigs/",
        },
        {
            "name": "Jazz Night",
            "city": "Vancouver",
            "address": None,
            "time": "8:00 PM",
            "source_name": "Infidels Jazz",
            "source_url": "https://theinfidelsjazz.ca/event/jazz-night/",
        },
    ],
    "sources": [
        {"name": "Do604", "count": 1, "error": None},
        {"name": "Daily Hive", "count": 0, "error": None},
        {"name": "Rhythm Changes", "count": 1, "error": None},
        {"name": "ShowHub", "count": 0, "error": "Connection timeout"},
        {"name": "Infidels Jazz", "count": 1, "error": None},
    ],
}


# ---------------------------------------------------------------------------
# format_date_display
# ---------------------------------------------------------------------------


def test_format_date_display_sunday():
    assert format_date_display("2026-03-08") == "Sunday, March 8, 2026"


def test_format_date_display_saturday():
    assert format_date_display("2026-03-07") == "Saturday, March 7, 2026"


def test_format_date_display_weekday():
    assert format_date_display("2026-03-04") == "Wednesday, March 4, 2026"


def test_format_date_display_new_years():
    assert format_date_display("2026-01-01") == "Thursday, January 1, 2026"


# ---------------------------------------------------------------------------
# escape_and_format
# ---------------------------------------------------------------------------


def test_escape_and_format_normal():
    assert escape_and_format("732 Main St") == "732 Main St"


def test_escape_and_format_none():
    assert escape_and_format(None) == "\u2014"


def test_escape_and_format_empty():
    assert escape_and_format("") == "\u2014"


def test_escape_and_format_html_chars():
    assert escape_and_format("Tom & Jerry's <Bar>") == "Tom &amp; Jerry&#x27;s &lt;Bar&gt;"


# ---------------------------------------------------------------------------
# parse_time_to_minutes
# ---------------------------------------------------------------------------


def test_parse_time_am():
    assert parse_time_to_minutes("10:00 AM") == 600


def test_parse_time_pm():
    assert parse_time_to_minutes("8:00 PM") == 1200


def test_parse_time_12pm():
    assert parse_time_to_minutes("12:00 PM") == 720


def test_parse_time_12am():
    assert parse_time_to_minutes("12:30 AM") == 30


def test_parse_time_with_extra_text():
    assert parse_time_to_minutes("6:00 PM (doors)") == 1080


def test_parse_time_unparseable():
    assert parse_time_to_minutes("All day") == 0


def test_parse_time_none():
    assert parse_time_to_minutes(None) == 0


# ---------------------------------------------------------------------------
# build_event_row
# ---------------------------------------------------------------------------


def test_build_event_row_complete():
    event = {
        "name": "Jazz Night",
        "city": "Vancouver",
        "address": "732 Main St",
        "time": "8:00 PM",
        "source_name": "Do604",
        "source_url": "https://do604.com/events/jazz",
    }
    row = build_event_row(event)
    assert "<tr>" in row
    assert "Jazz Night" in row
    assert "Vancouver" in row
    assert "732 Main St" in row
    assert "8:00 PM" in row
    assert 'href="https://do604.com/events/jazz"' in row
    assert "Do604" in row
    assert 'target="_blank"' in row
    assert 'rel="noopener noreferrer"' in row


def test_build_event_row_missing_address():
    event = {
        "name": "Jazz Night",
        "city": "Vancouver",
        "address": None,
        "time": "8:00 PM",
        "source_name": "Do604",
        "source_url": "https://do604.com/events/jazz",
    }
    row = build_event_row(event)
    assert "\u2014" in row


def test_build_event_row_html_escaped():
    event = {
        "name": "Tom & Jerry's <Show>",
        "city": "Vancouver",
        "address": None,
        "time": "8:00 PM",
        "source_name": "Do604",
        "source_url": "https://do604.com/events/jazz",
    }
    row = build_event_row(event)
    assert "&amp;" in row
    assert "&lt;Show&gt;" in row


def test_build_event_row_time_sort_value():
    event = {
        "name": "Jazz Night",
        "city": "Vancouver",
        "address": None,
        "time": "8:00 PM",
        "source_name": "Do604",
        "source_url": "https://do604.com/events/jazz",
    }
    row = build_event_row(event)
    assert 'data-sort-value="1200"' in row


# ---------------------------------------------------------------------------
# build_sources_footer
# ---------------------------------------------------------------------------


def test_build_sources_footer_all_success():
    sources = [
        {"name": "Do604", "count": 12, "error": None},
        {"name": "Daily Hive", "count": 8, "error": None},
    ]
    footer = build_sources_footer(sources)
    assert "Do604 (12)" in footer
    assert "Daily Hive (8)" in footer


def test_build_sources_footer_with_error():
    sources = [
        {"name": "Do604", "count": 12, "error": None},
        {"name": "ShowHub", "count": 0, "error": "Connection timeout"},
    ]
    footer = build_sources_footer(sources)
    assert "Do604 (12)" in footer
    assert "ShowHub (ERROR: Connection timeout)" in footer


def test_build_sources_footer_all_errors():
    sources = [
        {"name": "Do604", "count": 0, "error": "Timeout"},
        {"name": "Daily Hive", "count": 0, "error": "404"},
    ]
    footer = build_sources_footer(sources)
    assert "Do604 (ERROR: Timeout)" in footer
    assert "Daily Hive (ERROR: 404)" in footer


# ---------------------------------------------------------------------------
# generate_html — content checks
# ---------------------------------------------------------------------------


def test_generate_html_contains_summary():
    html = generate_html(SAMPLE_INPUT)
    assert "Found 3 events across 2 cities from 3/5 sources" in html


def test_generate_html_contains_all_events():
    html = generate_html(SAMPLE_INPUT)
    assert "HSBC Vancouver Sevens" in html
    assert "Joel Faulkner Trio" in html
    assert "Jazz Night" in html


def test_generate_html_contains_footer():
    html = generate_html(SAMPLE_INPUT)
    assert "Do604 (1)" in html
    assert "ShowHub (ERROR: Connection timeout)" in html


def test_generate_html_contains_date():
    html = generate_html(SAMPLE_INPUT)
    assert "Saturday, March 7, 2026" in html


def test_generate_html_links_clickable():
    html = generate_html(SAMPLE_INPUT)
    assert 'href="https://do604.com/events/2026/3/7/sevens"' in html
    assert 'href="https://www.rhythmchanges.ca/gigs/"' in html


# ---------------------------------------------------------------------------
# generate_html — structure checks
# ---------------------------------------------------------------------------


def test_generate_html_valid_structure():
    html = generate_html(MINIMAL_INPUT)
    assert "<!DOCTYPE html>" in html
    assert "<html" in html
    assert "<head>" in html
    assert "<body>" in html
    assert "</html>" in html


def test_generate_html_self_contained():
    html = generate_html(MINIMAL_INPUT)
    assert "<style>" in html
    assert "<script>" in html


def test_generate_html_has_table():
    html = generate_html(MINIMAL_INPUT)
    assert "<table" in html
    assert "<thead>" in html
    assert "<tbody>" in html
    assert "Event Name" in html
    assert "City" in html
    assert "Exact Address" in html
    assert "Time" in html
    assert "Source" in html


# ---------------------------------------------------------------------------
# generate_html — edge cases
# ---------------------------------------------------------------------------


def test_generate_html_empty_events():
    data = {
        "date": "2026-03-08",
        "summary": {"total_events": 0, "total_cities": 0, "sources_reporting": 0, "sources_total": 5},
        "events": [],
        "sources": [
            {"name": "Do604", "count": 0, "error": None},
        ],
    }
    html = generate_html(data)
    assert "No events found" in html


def test_generate_html_special_chars_escaped():
    data = {
        "date": "2026-03-08",
        "summary": {"total_events": 1, "total_cities": 1, "sources_reporting": 1, "sources_total": 5},
        "events": [
            {
                "name": "Rock & Roll <Live>",
                "city": "Vancouver",
                "address": "O'Brien's Pub",
                "time": "8:00 PM",
                "source_name": "Do604",
                "source_url": "https://do604.com/events/rock",
            }
        ],
        "sources": [{"name": "Do604", "count": 1, "error": None}],
    }
    html = generate_html(data)
    assert "Rock &amp; Roll &lt;Live&gt;" in html
    assert "O&#x27;Brien&#x27;s Pub" in html


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------


def test_cli_generates_file():
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
        output_path = f.name

    result = subprocess.run(
        [sys.executable, "-m", "scripts.generate_html", "--output", output_path],
        input=json.dumps(MINIMAL_INPUT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    content = Path(output_path).read_text(encoding="utf-8")
    assert "Jazz Night" in content
    assert "<!DOCTYPE html>" in content
    Path(output_path).unlink()


def test_cli_invalid_json():
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
        output_path = f.name

    result = subprocess.run(
        [sys.executable, "-m", "scripts.generate_html", "--output", output_path],
        input="not valid json",
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    Path(output_path).unlink(missing_ok=True)
