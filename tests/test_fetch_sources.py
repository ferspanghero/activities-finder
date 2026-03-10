"""Tests for src/fetch_sources.py"""

import json
from datetime import date

import aiohttp
import pytest
from aioresponses import aioresponses

from src.fetch_sources import (
    build_source_url,
    calculate_week_number,
    fetch_raw_sources,
    SOURCES,
)
from src.models import FetchResult


def test_build_url_do604():
    url = build_source_url("do604", date(2026, 3, 7), date(2026, 3, 7))
    assert url == "https://do604.com/events/2026/03/07"


def test_build_url_dailyhive():
    url = build_source_url("dailyhive", date(2026, 3, 7), date(2026, 3, 7))
    assert url == "https://dailyhive.com/vancouver/listed/events?after=2026-03-07&before=2026-03-07"


def test_build_url_dailyhive_range():
    url = build_source_url("dailyhive", date(2026, 3, 7), date(2026, 3, 10))
    assert url == "https://dailyhive.com/vancouver/listed/events?after=2026-03-07&before=2026-03-10"


def test_build_url_rhythmchanges():
    url = build_source_url("rhythmchanges", date(2026, 3, 7), date(2026, 3, 7))
    assert url == "https://rhythmchanges.ca/gigs/"


def test_build_url_showhub():
    url = build_source_url("showhub", date(2026, 3, 7), date(2026, 3, 7))
    assert url == "https://showhub.ca/weekly-listings/"


def test_build_url_infidelsjazz():
    url = build_source_url("infidelsjazz", date(2026, 3, 7), date(2026, 3, 7))
    assert url == "https://theinfidelsjazz.ca/wp-json/tribe/events/v1/events/?start_date=2026-03-07&end_date=2026-03-07"


def test_build_url_infidelsjazz_range():
    url = build_source_url("infidelsjazz", date(2026, 3, 7), date(2026, 3, 10))
    assert url == "https://theinfidelsjazz.ca/wp-json/tribe/events/v1/events/?start_date=2026-03-07&end_date=2026-03-10"


def test_build_url_bcaletrail():
    url = build_source_url("bcaletrail", date(2026, 3, 7), date(2026, 3, 7))
    assert url == "https://bcaletrail.ca/events/?date-start=2026-03-07&date-end=2026-03-07"


def test_build_url_bcaletrail_range():
    url = build_source_url("bcaletrail", date(2026, 3, 7), date(2026, 3, 10))
    assert url == "https://bcaletrail.ca/events/?date-start=2026-03-07&date-end=2026-03-10"


def test_build_url_different_date():
    url = build_source_url("do604", date(2026, 2, 28), date(2026, 2, 28))
    assert url == "https://do604.com/events/2026/02/28"

    url = build_source_url("dailyhive", date(2026, 2, 28), date(2026, 2, 28))
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


# --- fetch_raw_sources tests ---

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


def _mock_all_sources(mocked, from_date, to_date):
    """Register mock responses for all sources."""
    from datetime import timedelta
    for source_id, source in SOURCES.items():
        if source.get("per_day"):
            d = from_date
            while d <= to_date:
                url = build_source_url(source_id, d, d)
                mocked.get(url, body=SAMPLE_HTML, content_type="text/html")
                d += timedelta(days=1)
        else:
            url = build_source_url(source_id, from_date, to_date)
            if source_id == "infidelsjazz":
                mocked.get(url, body=SAMPLE_INFIDELS_API_RESPONSE, content_type="application/json")
            else:
                mocked.get(url, body=SAMPLE_HTML, content_type="text/html")


@pytest.mark.asyncio
async def test_fetch_raw_sources_returns_fetch_results():
    target = date(2026, 3, 7)
    with aioresponses() as mocked:
        _mock_all_sources(mocked, target, target)
        results = await fetch_raw_sources(target, target)

    assert len(results) == len(SOURCES)
    assert all(isinstance(r, FetchResult) for r in results)
    assert all(r.error is None for r in results)


@pytest.mark.asyncio
async def test_fetch_raw_sources_returns_raw_html():
    """HTML sources should return raw HTML, not markdown."""
    target = date(2026, 3, 7)
    with aioresponses() as mocked:
        _mock_all_sources(mocked, target, target)
        results = await fetch_raw_sources(target, target)

    do604 = next(r for r in results if r.source_id == "do604")
    assert isinstance(do604.content, str)
    assert "<html>" in do604.content  # Raw HTML, not markdown


@pytest.mark.asyncio
async def test_fetch_raw_sources_returns_parsed_json():
    """Infidels Jazz should return parsed dict, not raw string."""
    target = date(2026, 3, 7)
    with aioresponses() as mocked:
        _mock_all_sources(mocked, target, target)
        results = await fetch_raw_sources(target, target)

    infidels = next(r for r in results if r.source_id == "infidelsjazz")
    assert isinstance(infidels.content, dict)
    assert "events" in infidels.content


@pytest.mark.asyncio
async def test_fetch_raw_sources_handles_errors():
    target = date(2026, 3, 7)
    with aioresponses() as mocked:
        # Mock Do604 as error, all others as success
        do604_url = build_source_url("do604", target, target)
        mocked.get(do604_url, exception=aiohttp.ClientConnectionError("Connection timeout"))
        for source_id, source in SOURCES.items():
            if source_id == "do604":
                continue
            url = build_source_url(source_id, target, target)
            if source_id == "infidelsjazz":
                mocked.get(url, body=SAMPLE_INFIDELS_API_RESPONSE, content_type="application/json")
            else:
                mocked.get(url, body=SAMPLE_HTML, content_type="text/html")

        results = await fetch_raw_sources(target, target)

    assert len(results) == len(SOURCES)
    do604 = next(r for r in results if r.source_id == "do604")
    assert do604.error is not None
    assert do604.content is None
    # Other sources should succeed
    others = [r for r in results if r.source_id != "do604"]
    assert all(r.error is None for r in others)


@pytest.mark.asyncio
async def test_fetch_raw_sources_per_day_do604_range():
    """Do604 should produce one FetchResult per day in a multi-day range."""
    from_date = date(2026, 3, 7)
    to_date = date(2026, 3, 9)
    with aioresponses() as mocked:
        _mock_all_sources(mocked, from_date, to_date)
        results = await fetch_raw_sources(from_date, to_date)

    do604_results = [r for r in results if r.source_id == "do604"]
    assert len(do604_results) == 3  # 3 days
    do604_dates = [(r.from_date, r.to_date) for r in do604_results]
    assert (date(2026, 3, 7), date(2026, 3, 7)) in do604_dates
    assert (date(2026, 3, 8), date(2026, 3, 8)) in do604_dates
    assert (date(2026, 3, 9), date(2026, 3, 9)) in do604_dates

    # Other sources should still be single fetch
    other_results = [r for r in results if r.source_id != "do604"]
    assert len(other_results) == len(SOURCES) - 1
