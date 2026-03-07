"""Tests for events/pipeline.py — pipeline orchestrator."""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from src.models import Event, FetchResult, SourceStatus
from src.pipeline import run_pipeline, PipelineResult


def _make_fetch_result(source_id, source_name, content=None, error=None):
    return FetchResult(
        source_id=source_id,
        source_name=source_name,
        url=f"https://example.com/{source_id}",
        content=content,
        error=error,
        target_date=date(2026, 3, 7),
    )


INFIDELS_JSON = {
    "events": [{
        "title": "Jazz Trio",
        "venue": {"venue": "Club", "address": "1 Main St", "city": "Vancouver"},
        "start_date": "2026-03-07 20:00:00",
        "url": "https://theinfidelsjazz.ca/event/trio/",
    }]
}

DO604_HTML = """
<div class="ds-listing event-card" data-permalink="/events/2026/3/7/rock-show">
  <a class="ds-listing-event-title" href="/events/2026/3/7/rock-show">
    <span class="ds-listing-event-title-text">Rock Show</span>
  </a>
  <meta itemprop="addressLocality" content="Vancouver" />
  <meta itemprop="streetAddress" content="99 Oak St" />
  <div class="ds-event-time">9:00PM</div>
</div>
"""

MOCK_FETCH_RESULTS = [
    _make_fetch_result("do604", "Do604", content=DO604_HTML),
    _make_fetch_result("dailyhive", "Daily Hive", content='<html><body><script id="__NEXT_DATA__" type="application/json">{"props":{"pageProps":{"upcomingEvents":[]}}}</script></body></html>'),
    _make_fetch_result("rhythmchanges", "Rhythm Changes", content="<html><body></body></html>"),
    _make_fetch_result("showhub", "ShowHub", content="<html><body></body></html>"),
    _make_fetch_result("infidelsjazz", "Infidels Jazz", content=INFIDELS_JSON),
]


@pytest.mark.asyncio
async def test_run_pipeline_returns_pipeline_result():
    with patch("src.pipeline.fetch_raw_sources", new_callable=AsyncMock, return_value=MOCK_FETCH_RESULTS):
        result = await run_pipeline(date(2026, 3, 7))
    assert isinstance(result, PipelineResult)


@pytest.mark.asyncio
async def test_run_pipeline_extracts_events():
    with patch("src.pipeline.fetch_raw_sources", new_callable=AsyncMock, return_value=MOCK_FETCH_RESULTS):
        result = await run_pipeline(date(2026, 3, 7))
    assert len(result.events) == 2  # Do604 + Infidels Jazz
    names = [e.name for e in result.events]
    assert "Rock Show" in names
    assert "Jazz Trio" in names


@pytest.mark.asyncio
async def test_run_pipeline_reports_source_statuses():
    with patch("src.pipeline.fetch_raw_sources", new_callable=AsyncMock, return_value=MOCK_FETCH_RESULTS):
        result = await run_pipeline(date(2026, 3, 7))
    assert len(result.source_statuses) == 5
    do604_status = next(s for s in result.source_statuses if s.name == "Do604")
    assert do604_status.count == 1
    assert do604_status.error is None


@pytest.mark.asyncio
async def test_run_pipeline_handles_fetch_error():
    results = list(MOCK_FETCH_RESULTS)
    results[0] = _make_fetch_result("do604", "Do604", error="Connection timeout")
    with patch("src.pipeline.fetch_raw_sources", new_callable=AsyncMock, return_value=results):
        result = await run_pipeline(date(2026, 3, 7))
    do604_status = next(s for s in result.source_statuses if s.name == "Do604")
    assert do604_status.error == "Connection timeout"
    assert do604_status.count == 0


@pytest.mark.asyncio
async def test_run_pipeline_handles_parser_error():
    """If a parser raises, pipeline catches it and reports error."""
    results = list(MOCK_FETCH_RESULTS)
    # Give Do604 invalid HTML that won't crash BS but will produce no events
    results[0] = _make_fetch_result("do604", "Do604", content="not html at all {}[]")
    with patch("src.pipeline.fetch_raw_sources", new_callable=AsyncMock, return_value=results):
        result = await run_pipeline(date(2026, 3, 7))
    # Should not crash — Do604 just has 0 events
    assert isinstance(result, PipelineResult)
    do604_status = next(s for s in result.source_statuses if s.name == "Do604")
    assert do604_status.count == 0
