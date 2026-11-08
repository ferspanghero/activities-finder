"""Tests for src/fetch_sources.py"""

import asyncio
import json
import re
from dataclasses import replace
from datetime import date, timedelta

import aiohttp
import pytest
from aioresponses import CallbackResult, aioresponses

from src.fetch_sources import (
    backoff_seconds,
    build_source_url,
    calculate_week_number,
    fetch_raw_sources,
    page_url,
)
from src.models import FetchResult
from src.sources import SOURCES


def test_build_url_do604():
    url = build_source_url("do604", date(2026, 3, 7), date(2026, 3, 7))
    assert url == "https://do604.com/events/2026/3/7"


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
    assert url == "https://do604.com/events/2026/2/28"

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
    """Register single-page mock responses for every source request."""
    for source_id, spec in SOURCES.items():
        windows = [(d, d) for d in _days(from_date, to_date)] if spec.per_day else [(from_date, to_date)]
        for f, t in windows:
            url = build_source_url(source_id, f, t)
            if source_id == "infidelsjazz":
                mocked.get(url, body=SAMPLE_INFIDELS_API_RESPONSE, content_type="application/json")
            elif spec.json:
                mocked.get(url, body=json.dumps({"events": {"pagination": {"pages": 1}}}), content_type="application/json")
            else:
                mocked.get(url, body=SAMPLE_HTML, content_type="text/html")


def _days(from_date, to_date):
    return [from_date + timedelta(days=i) for i in range((to_date - from_date).days + 1)]


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
        mocked.get(do604_url, exception=aiohttp.ClientConnectionError("Connection timeout"))
        _mock_all_sources(mocked, target, target)

        results = await fetch_raw_sources(target, target, retries=0)

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

    # Per-day sources make one request per day; range-capable sources make one in total
    for source_id, spec in SOURCES.items():
        windows = {(r.from_date, r.to_date) for r in results if r.source_id == source_id}
        assert len(windows) == (3 if spec.per_day else 1), source_id


# --- source registry URLs ---

@pytest.mark.parametrize(
    ("source_id", "expected"),
    [
        ("kidsoutandabout", "https://vancouver.kidsoutandabout.com/event-list/2026-03-07"),
        ("eventbrite", "https://www.eventbrite.ca/d/canada--vancouver/all-events/?start_date=2026-03-07&end_date=2026-03-07"),
        ("vpl", "https://gateway.bibliocommons.com/v2/libraries/vpl/events/search?startDate=2026-03-07&endDate=2026-03-08&limit=100"),
        ("richmondpl", "https://gateway.bibliocommons.com/v2/libraries/yourlibrary/events/search?startDate=2026-03-07&endDate=2026-03-08&limit=100"),
    ],
)
def test_build_url_new_sources(source_id: str, expected: str) -> None:
    # Arrange
    to_date = date(2026, 3, 8) if source_id in ("vpl", "richmondpl") else date(2026, 3, 7)

    # Act
    url = build_source_url(source_id, date(2026, 3, 7), to_date)

    # Assert
    assert url == expected


@pytest.mark.parametrize(
    ("url", "page", "expected"),
    [
        ("https://do604.com/events/2026/3/7", 1, "https://do604.com/events/2026/3/7"),
        ("https://do604.com/events/2026/3/7", 3, "https://do604.com/events/2026/3/7?page=3"),
        ("https://x.com/a?b=1", 2, "https://x.com/a?b=1&page=2"),
    ],
)
def test_page_url_appends_page_parameter(url: str, page: int, expected: str) -> None:
    # Arrange, Act
    result = page_url(url, page)

    # Assert
    assert result == expected


# --- pagination and retry ---

DAY = date(2026, 3, 7)
CARD = '<div class="standard-card" data-card-kind="event"><h3>X</h3></div>'


def _only(source_id: str):
    return {source_id: SOURCES[source_id]}


@pytest.mark.asyncio
async def test_until_empty_pagination_stops_at_first_empty_page() -> None:
    # Arrange
    base = build_source_url("do604", DAY, DAY)

    with aioresponses() as mocked:
        mocked.get(base, body=CARD)
        mocked.get(page_url(base, 2), body=CARD)
        mocked.get(page_url(base, 3), body="<html>none</html>")
        for p in range(4, 10):
            mocked.get(page_url(base, p), body="<html>none</html>")

        # Act
        results = await fetch_raw_sources(DAY, DAY, sources=_only("do604"))

    # Assert
    assert [r.url for r in results] == [base, page_url(base, 2)]


@pytest.mark.asyncio
async def test_until_empty_pagination_respects_max_pages() -> None:
    # Arrange
    spec = replace(SOURCES["do604"], max_pages=3)
    base = build_source_url("do604", DAY, DAY)

    with aioresponses() as mocked:
        for p in range(1, 10):
            mocked.get(page_url(base, p), body=CARD)

        # Act
        results = await fetch_raw_sources(DAY, DAY, sources={"do604": spec})

    # Assert
    assert len(results) == 3


@pytest.mark.asyncio
async def test_count_pagination_fetches_reported_pages() -> None:
    # Arrange
    base = build_source_url("vpl", DAY, DAY)
    body = json.dumps({"events": {"pagination": {"pages": 3}}})

    with aioresponses() as mocked:
        for p in (1, 2, 3):
            mocked.get(page_url(base, p), body=body, content_type="application/json")

        # Act
        results = await fetch_raw_sources(DAY, DAY, sources=_only("vpl"))

    # Assert
    assert sorted(r.url for r in results) == sorted(page_url(base, p) for p in (1, 2, 3))
    assert all(isinstance(r.content, dict) for r in results)


@pytest.mark.asyncio
async def test_count_pagination_caps_at_max_pages() -> None:
    # Arrange
    spec = replace(SOURCES["vpl"], max_pages=2)
    base = build_source_url("vpl", DAY, DAY)
    body = json.dumps({"events": {"pagination": {"pages": 50}}})

    with aioresponses() as mocked:
        for p in (1, 2):
            mocked.get(page_url(base, p), body=body, content_type="application/json")

        # Act
        results = await fetch_raw_sources(DAY, DAY, sources={"vpl": spec})

    # Assert
    assert len(results) == 2


@pytest.mark.asyncio
async def test_fetch_retries_once_on_server_error() -> None:
    # Arrange
    url = build_source_url("showhub", DAY, DAY)

    with aioresponses() as mocked:
        mocked.get(url, status=503)
        mocked.get(url, body=SAMPLE_HTML)

        # Act
        results = await fetch_raw_sources(DAY, DAY, sources=_only("showhub"), retry_delay=0)

    # Assert
    assert results[0].error is None and results[0].content == SAMPLE_HTML


@pytest.mark.asyncio
async def test_fetch_reports_error_after_retry_exhausted() -> None:
    # Arrange
    url = build_source_url("showhub", DAY, DAY)

    with aioresponses() as mocked:
        mocked.get(url, status=503)
        mocked.get(url, status=503)

        # Act
        results = await fetch_raw_sources(DAY, DAY, sources=_only("showhub"), retries=1, retry_delay=0)

    # Assert
    assert results[0].content is None and "503" in results[0].error


@pytest.mark.asyncio
async def test_fetch_does_not_retry_client_errors() -> None:
    # Arrange
    url = build_source_url("showhub", DAY, DAY)

    with aioresponses() as mocked:
        mocked.get(url, status=404)
        mocked.get(url, body=SAMPLE_HTML)

        # Act
        results = await fetch_raw_sources(DAY, DAY, sources=_only("showhub"), retry_delay=0)

    # Assert
    assert "404" in results[0].error


@pytest.mark.asyncio
async def test_fetch_limits_concurrent_requests() -> None:
    # Arrange
    in_flight = 0
    peak = 0

    async def slow(url, **kwargs):
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        await asyncio.sleep(0.01)
        in_flight -= 1
        return CallbackResult(body="<html>none</html>")

    with aioresponses() as mocked:
        mocked.get(re.compile(r"https://do604\.com/.*"), callback=slow, repeat=True)

        # Act
        await fetch_raw_sources(DAY, DAY + timedelta(days=9), sources=_only("do604"), concurrency=3)

    # Assert
    assert peak <= 3


@pytest.mark.asyncio
async def test_fetch_limits_concurrency_per_source() -> None:
    # Arrange
    in_flight = 0
    peak = 0

    async def slow(url, **kwargs):
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        await asyncio.sleep(0.01)
        in_flight -= 1
        return CallbackResult(body="<html></html>")

    spec = replace(SOURCES["eventbrite"], concurrency=2)

    with aioresponses() as mocked:
        mocked.get(re.compile(r"https://www\.eventbrite\.ca/.*"), callback=slow, repeat=True)

        # Act
        await fetch_raw_sources(DAY, DAY + timedelta(days=9), sources={"eventbrite": spec}, concurrency=8)

    # Assert
    assert peak <= 2


@pytest.mark.asyncio
async def test_fetch_honours_retry_after_on_429() -> None:
    # Arrange
    url = build_source_url("showhub", DAY, DAY)

    with aioresponses() as mocked:
        mocked.get(url, status=429, headers={"Retry-After": "0"})
        mocked.get(url, status=429, headers={"Retry-After": "0"})
        mocked.get(url, body=SAMPLE_HTML)

        # Act
        results = await fetch_raw_sources(DAY, DAY, sources=_only("showhub"), retry_delay=0)

    # Assert
    assert results[0].error is None


@pytest.mark.parametrize(
    ("header", "attempt", "expected"),
    [("3", 1, 3.0), ("999", 1, 15.0), (None, 1, 2.0), (None, 2, 4.0), ("soon", 1, 2.0)],
)
def test_backoff_uses_retry_after_then_exponential(header: str | None, attempt: int, expected: float) -> None:
    # Arrange, Act
    delay = backoff_seconds(header, attempt, base=1.0)

    # Assert
    assert delay == expected


@pytest.mark.asyncio
async def test_count_pagination_warns_when_capped() -> None:
    # Arrange
    spec = replace(SOURCES["vpl"], max_pages=2)
    base = build_source_url("vpl", DAY, DAY)
    body = json.dumps({"events": {"pagination": {"pages": 5}}})

    with aioresponses() as mocked:
        for p in (1, 2):
            mocked.get(page_url(base, p), body=body, content_type="application/json")

        # Act
        results = await fetch_raw_sources(DAY, DAY, sources={"vpl": spec})

    # Assert
    assert results[0].warning == "showing first 2 of 5 result pages"
    assert results[1].warning is None


@pytest.mark.asyncio
async def test_until_empty_pagination_warns_when_capped() -> None:
    # Arrange
    spec = replace(SOURCES["do604"], max_pages=2)
    base = build_source_url("do604", DAY, DAY)

    with aioresponses() as mocked:
        for p in (1, 2):
            mocked.get(page_url(base, p), body=CARD)

        # Act
        results = await fetch_raw_sources(DAY, DAY, sources={"do604": spec})

    # Assert
    assert results[0].warning == "stopped at the 2-page limit"


def test_eventbrite_uses_one_range_query() -> None:
    # Arrange, Act
    url = build_source_url("eventbrite", date(2026, 3, 7), date(2026, 3, 20))

    # Assert
    assert SOURCES["eventbrite"].per_day is False
    assert url.endswith("start_date=2026-03-07&end_date=2026-03-20")


@pytest.mark.asyncio
async def test_fetch_reports_timeout_as_error_after_retries() -> None:
    # Arrange
    url = build_source_url("showhub", DAY, DAY)

    with aioresponses() as mocked:
        for _ in range(3):
            mocked.get(url, exception=asyncio.TimeoutError())

        # Act
        results = await fetch_raw_sources(DAY, DAY, sources=_only("showhub"), retry_delay=0)

    # Assert
    assert results[0].content is None and results[0].error == "TimeoutError"


@pytest.mark.asyncio
async def test_unreadable_page_count_keeps_first_page_with_warning() -> None:
    # Arrange
    base = build_source_url("vpl", DAY, DAY)

    with aioresponses() as mocked:
        mocked.get(base, body=json.dumps({"events": {"pagination": {"pages": "many"}}}), content_type="application/json")

        # Act
        results = await fetch_raw_sources(DAY, DAY, sources=_only("vpl"))

    # Assert
    assert len(results) == 1 and results[0].error is None
    assert results[0].warning.startswith("pagination unreadable")


@pytest.mark.asyncio
async def test_unreadable_has_events_keeps_first_page_with_warning() -> None:
    # Arrange
    def broken(html: str) -> bool:
        raise AttributeError("layout changed")

    spec = replace(SOURCES["do604"], has_events=broken)

    with aioresponses() as mocked:
        mocked.get(build_source_url("do604", DAY, DAY), body=CARD)

        # Act
        results = await fetch_raw_sources(DAY, DAY, sources={"do604": spec})

    # Assert
    assert len(results) == 1 and results[0].warning.startswith("pagination unreadable")
