"""Tests for scripts/fetch_sources.py"""

import json
from datetime import date

import pytest
from aioresponses import aioresponses

from scripts.fetch_sources import (
    build_source_url,
    calculate_week_number,
    fetch_all_sources,
    format_source_output,
    format_infidelsjazz_json,
    SOURCES,
)


def test_build_url_do604():
    url = build_source_url("do604", date(2026, 3, 7))
    assert url == "https://do604.com/events/2026/03/07"


def test_build_url_dailyhive():
    url = build_source_url("dailyhive", date(2026, 3, 7))
    assert url == "https://dailyhive.com/vancouver/listed/events?after=2026-03-07&before=2026-03-07"


def test_build_url_rhythmchanges():
    url = build_source_url("rhythmchanges", date(2026, 3, 7))
    assert url == "https://rhythmchanges.ca/gigs/"


def test_build_url_showhub():
    url = build_source_url("showhub", date(2026, 3, 7))
    assert url == "https://showhub.ca/weekly-listings/"


def test_build_url_infidelsjazz():
    url = build_source_url("infidelsjazz", date(2026, 3, 7))
    assert url == "https://theinfidelsjazz.ca/wp-json/tribe/events/v1/events/?start_date=2026-03-07&end_date=2026-03-07"


def test_build_url_different_date():
    url = build_source_url("do604", date(2026, 2, 28))
    assert url == "https://do604.com/events/2026/02/28"

    url = build_source_url("dailyhive", date(2026, 2, 28))
    assert url == "https://dailyhive.com/vancouver/listed/events?after=2026-02-28&before=2026-02-28"


# --- Rhythm Changes week calculation ---

def test_week_number_week1():
    """Mar 1 (Sun) through Mar 7 (Sat) = Week 1"""
    assert calculate_week_number(date(2026, 3, 1)) == 1
    assert calculate_week_number(date(2026, 3, 7)) == 1


def test_week_number_week2():
    """Mar 8 (Sun) through Mar 14 (Sat) = Week 2"""
    assert calculate_week_number(date(2026, 3, 8)) == 2
    assert calculate_week_number(date(2026, 3, 14)) == 2


def test_week_number_week3():
    """Mar 15 (Sun) through Mar 21 (Sat) = Week 3"""
    assert calculate_week_number(date(2026, 3, 15)) == 3


def test_week_number_week5():
    """Mar 29 (Sun) through Mar 31 (Tue) = Week 5"""
    assert calculate_week_number(date(2026, 3, 29)) == 5
    assert calculate_week_number(date(2026, 3, 31)) == 5


# --- Output formatting ---

def test_format_source_output_success():
    output = format_source_output("Do604", "https://do604.com/events/2026/03/07", "# Events\n- Jazz Night")
    assert output.startswith("=== SOURCE: Do604 (https://do604.com/events/2026/03/07) ===")
    assert "# Events\n- Jazz Night" in output


def test_format_source_output_error():
    output = format_source_output("Do604", "https://do604.com/events/2026/03/07", None, error="Connection timeout")
    assert "=== SOURCE: Do604 (ERROR: Connection timeout) ===" in output


def test_format_source_output_rhythmchanges_includes_week():
    output = format_source_output(
        "Rhythm Changes", "https://rhythmchanges.ca/gigs/", "some content",
        week_hint="Target date falls in Week 1 (Sun Mar 1 - Sat Mar 7)"
    )
    assert "Target date falls in Week 1" in output


# --- Infidels Jazz JSON formatting ---

SAMPLE_INFIDELS_JSON = {
    "events": [
        {
            "title": "Adam Robert Thomas Trio",
            "venue": {"venue": "Frankie's Jazz Club", "address": "755 Beatty Street", "city": "Vancouver"},
            "start_date": "2026-03-07 23:00:00",
            "end_date": "2026-03-08 00:15:00",
            "cost": "$10",
            "url": "https://theinfidelsjazz.ca/event/adam-robert-thomas-trio/",
        }
    ]
}


def test_format_infidelsjazz_json():
    result = format_infidelsjazz_json(SAMPLE_INFIDELS_JSON)
    assert "Adam Robert Thomas Trio" in result
    assert "Frankie's Jazz Club" in result
    assert "755 Beatty Street" in result
    assert "Vancouver" in result
    assert "$10" in result


def test_format_infidelsjazz_json_empty():
    result = format_infidelsjazz_json({"events": []})
    assert "no events" in result.lower()


# --- Mocked HTTP tests ---

SAMPLE_HTML = "<html><body><h1>Events</h1><p>Jazz Night at 8pm</p></body></html>"
SAMPLE_INFIDELS_API_RESPONSE = json.dumps({
    "events": [
        {
            "title": "Test Jazz Trio",
            "venue": {"venue": "Test Club", "address": "123 Main St", "city": "Vancouver"},
            "start_date": "2026-03-07 20:00:00",
            "cost": "$15",
            "url": "https://theinfidelsjazz.ca/event/test/",
        }
    ]
})


@pytest.mark.asyncio
async def test_fetch_all_sources_success():
    """All 5 sources return content — output has 5 sections."""
    target = date(2026, 3, 7)
    with aioresponses() as mocked:
        for source_id in SOURCES:
            url = build_source_url(source_id, target)
            if source_id == "infidelsjazz":
                mocked.get(url, body=SAMPLE_INFIDELS_API_RESPONSE, content_type="application/json")
            else:
                mocked.get(url, body=SAMPLE_HTML, content_type="text/html")

        result = await fetch_all_sources(target)

    assert result.count("=== SOURCE:") == 5
    for source in SOURCES.values():
        assert source["name"] in result
    assert "ERROR" not in result


@pytest.mark.asyncio
async def test_fetch_partial_failure():
    """1 source fails — output has 4 content sections + 1 error section."""
    target = date(2026, 3, 7)
    with aioresponses() as mocked:
        for source_id in SOURCES:
            url = build_source_url(source_id, target)
            if source_id == "do604":
                mocked.get(url, exception=Exception("Connection timeout"))
            elif source_id == "infidelsjazz":
                mocked.get(url, body=SAMPLE_INFIDELS_API_RESPONSE, content_type="application/json")
            else:
                mocked.get(url, body=SAMPLE_HTML, content_type="text/html")

        result = await fetch_all_sources(target)

    assert result.count("=== SOURCE:") == 5
    assert "Do604 (ERROR:" in result
    assert result.count("ERROR") == 1


@pytest.mark.asyncio
async def test_fetch_all_sources_down():
    """All sources fail — output has 5 error sections."""
    target = date(2026, 3, 7)
    with aioresponses() as mocked:
        for source_id in SOURCES:
            url = build_source_url(source_id, target)
            mocked.get(url, exception=Exception("Connection refused"))

        result = await fetch_all_sources(target)

    assert result.count("=== SOURCE:") == 5
    assert result.count("ERROR") == 5


# --- CLI tests ---

import subprocess
import sys


@pytest.mark.integration
def test_cli_runs_with_date_arg():
    """Script runs via CLI with --date and exits 0."""
    result = subprocess.run(
        [sys.executable, "-m", "scripts.fetch_sources", "--date", "2026-03-07"],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0
    assert "=== SOURCE:" in result.stdout


def test_cli_missing_date_arg():
    """Script fails with clear error when --date is missing."""
    result = subprocess.run(
        [sys.executable, "-m", "scripts.fetch_sources"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0


# --- Integration test ---

@pytest.mark.integration
def test_integration_real_sources():
    """End-to-end: fetch real sources for a known date."""
    result = subprocess.run(
        [sys.executable, "-m", "scripts.fetch_sources", "--date", "2026-03-07"],
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0
    output = result.stdout
    # All 5 sources should appear
    for name in ["Do604", "Daily Hive", "Rhythm Changes", "ShowHub", "Infidels Jazz"]:
        assert f"=== SOURCE: {name}" in output, f"Missing source: {name}"
