"""Tests for events/pipeline.py — pipeline orchestrator."""

import json
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.models import Event, FetchResult, SourceStatus
from src.pipeline import PipelineResult, _merge_statuses, _venue_pages, run_pipeline
from src.venues import VenueInfo


def _make_fetch_result(source_id, source_name, content=None, error=None,
                       from_date=date(2026, 3, 7), to_date=date(2026, 3, 7)):
    return FetchResult(
        source_id=source_id,
        source_name=source_name,
        url=f"https://example.com/{source_id}",
        content=content,
        error=error,
        from_date=from_date,
        to_date=to_date,
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
<div class="standard-card" data-card-kind="event">
  <a class="card-link" href="/events/2026/3/7/rock-show">
    <div class="details">
      <h3>Rock Show</h3>
      <p class="date">Today | 9:00PM</p>
      <p>The Venue</p>
      <p class="enrichment">Music \u2022 Gastown</p>
    </div>
  </a>
</div>
"""

MOCK_FETCH_RESULTS = [
    _make_fetch_result("do604", "Do604", content=DO604_HTML),
    _make_fetch_result("dailyhive", "Daily Hive", content='<html><body><script id="__NEXT_DATA__" type="application/json">{"props":{"pageProps":{"upcomingEvents":[]}}}</script></body></html>'),
    _make_fetch_result("rhythmchanges", "Rhythm Changes", content="<html><body></body></html>"),
    _make_fetch_result("showhub", "ShowHub", content="<html><body></body></html>"),
    _make_fetch_result("infidelsjazz", "Infidels Jazz", content=INFIDELS_JSON),
    _make_fetch_result("bcaletrail", "BC Ale Trail", content="<html><body></body></html>"),
]


@pytest.mark.asyncio
async def test_run_pipeline_returns_pipeline_result():
    with patch("src.pipeline.fetch_raw_sources", new_callable=AsyncMock, return_value=MOCK_FETCH_RESULTS):
        result = await run_pipeline(date(2026, 3, 7), date(2026, 3, 7))
    assert isinstance(result, PipelineResult)


@pytest.mark.asyncio
async def test_run_pipeline_extracts_events():
    with patch("src.pipeline.fetch_raw_sources", new_callable=AsyncMock, return_value=MOCK_FETCH_RESULTS):
        result = await run_pipeline(date(2026, 3, 7), date(2026, 3, 7))
    assert len(result.events) == 2  # Do604 + Infidels Jazz
    names = [e.name for e in result.events]
    assert "Rock Show" in names
    assert "Jazz Trio" in names


@pytest.mark.asyncio
async def test_run_pipeline_preserves_event_fields():
    """Verify cities, addresses, times, and event_date survive the pipeline."""
    with patch("src.pipeline.fetch_raw_sources", new_callable=AsyncMock, return_value=MOCK_FETCH_RESULTS):
        result = await run_pipeline(date(2026, 3, 7), date(2026, 3, 7))
    rock = next(e for e in result.events if e.name == "Rock Show")
    assert rock.city == "Vancouver"
    assert rock.venue == "The Venue"
    assert rock.time == "9:00PM"
    assert rock.source_name == "Do604"
    assert rock.event_date == date(2026, 3, 7)

    jazz = next(e for e in result.events if e.name == "Jazz Trio")
    assert jazz.city == "Vancouver"
    assert jazz.address == "1 Main St"
    assert jazz.time == "8:00 PM"
    assert jazz.source_name == "Infidels Jazz"
    assert jazz.source_url == "https://theinfidelsjazz.ca/event/trio/"
    assert jazz.event_date == date(2026, 3, 7)


@pytest.mark.asyncio
async def test_run_pipeline_reports_source_statuses():
    with patch("src.pipeline.fetch_raw_sources", new_callable=AsyncMock, return_value=MOCK_FETCH_RESULTS):
        result = await run_pipeline(date(2026, 3, 7), date(2026, 3, 7))
    assert len(result.source_statuses) == len(MOCK_FETCH_RESULTS)
    do604_status = next(s for s in result.source_statuses if s.name == "Do604")
    assert do604_status.count == 1
    assert do604_status.error is None


@pytest.mark.asyncio
async def test_run_pipeline_handles_fetch_error():
    results = list(MOCK_FETCH_RESULTS)
    results[0] = _make_fetch_result("do604", "Do604", error="Connection timeout")
    with patch("src.pipeline.fetch_raw_sources", new_callable=AsyncMock, return_value=results):
        result = await run_pipeline(date(2026, 3, 7), date(2026, 3, 7))
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
        result = await run_pipeline(date(2026, 3, 7), date(2026, 3, 7))
    # Should not crash — Do604 just has 0 events
    assert isinstance(result, PipelineResult)
    do604_status = next(s for s in result.source_statuses if s.name == "Do604")
    assert do604_status.count == 0


def test_merge_statuses_combines_same_source():
    """Multiple statuses for the same source should be merged."""
    statuses = [
        SourceStatus(name="Do604", count=3, error=None),
        SourceStatus(name="Daily Hive", count=5, error=None),
        SourceStatus(name="Do604", count=2, error=None),
    ]
    merged = _merge_statuses(statuses)
    assert len(merged) == 2
    do604 = next(s for s in merged if s.name == "Do604")
    assert do604.count == 5
    assert do604.error is None


def test_merge_statuses_turns_partial_failure_into_warning():
    """If some requests fail and others succeed, keep the count and warn instead of erroring."""
    # Arrange
    statuses = [
        SourceStatus(name="Do604", count=0, error="Timeout"),
        SourceStatus(name="Do604", count=3, error=None),
    ]

    # Act
    merged = _merge_statuses(statuses)

    # Assert
    do604 = next(s for s in merged if s.name == "Do604")
    assert do604.count == 3
    assert do604.error is None
    assert do604.warning == "1 of 2 requests failed: Timeout"


def test_merge_statuses_keeps_error_when_every_request_fails() -> None:
    # Arrange
    statuses = [SourceStatus(name="Do604", count=0, error="Timeout"), SourceStatus(name="Do604", count=0, error="503")]

    # Act
    merged = _merge_statuses(statuses)

    # Assert
    assert (merged[0].error, merged[0].warning) == ("Timeout", None)


def test_merge_statuses_joins_distinct_warnings() -> None:
    # Arrange
    statuses = [
        SourceStatus(name="ShowHub", count=1, error=None, warning="a"),
        SourceStatus(name="ShowHub", count=1, error=None, warning="a"),
        SourceStatus(name="ShowHub", count=1, error=None, warning="b"),
    ]

    # Act
    merged = _merge_statuses(statuses)

    # Assert
    assert merged[0].warning == "a; b"


def _status(result: PipelineResult, name: str) -> SourceStatus:
    return next(s for s in result.source_statuses if s.name == name)


@pytest.mark.asyncio
async def test_pipeline_warns_when_expected_source_parses_zero_events() -> None:
    # Arrange
    results = [_make_fetch_result("do604", "Do604", content="<html>" + "x" * 5000 + "</html>")]

    # Act
    with patch("src.pipeline.fetch_raw_sources", new_callable=AsyncMock, return_value=results):
        result = await run_pipeline(date(2026, 3, 7), date(2026, 3, 7))

    # Assert
    assert "layout" in _status(result, "Do604").warning


@pytest.mark.asyncio
async def test_pipeline_does_not_warn_for_sources_that_may_be_empty() -> None:
    # Arrange
    results = [_make_fetch_result("infidelsjazz", "Infidels Jazz", content={"events": []})]

    # Act
    with patch("src.pipeline.fetch_raw_sources", new_callable=AsyncMock, return_value=results):
        result = await run_pipeline(date(2026, 3, 7), date(2026, 3, 7))

    # Assert
    assert _status(result, "Infidels Jazz").warning is None


@pytest.mark.asyncio
async def test_pipeline_warns_when_fixed_window_source_ends_before_range() -> None:
    # Arrange
    html = '<ul class="show-list"><li><a href="u">Band at Hall</a><br>Saturday, Mar 7 at 9:00 PM</li></ul>'
    results = [_make_fetch_result("showhub", "ShowHub", content=html, to_date=date(2026, 3, 10))]

    # Act
    with patch("src.pipeline.fetch_raw_sources", new_callable=AsyncMock, return_value=results):
        result = await run_pipeline(date(2026, 3, 7), date(2026, 3, 10))

    # Assert
    status = _status(result, "ShowHub")
    assert (status.count, status.warning) == (1, "lists events only through 2026-03-07")


@pytest.mark.asyncio
async def test_pipeline_fills_venue_city_and_persists_cache(tmp_path: Path) -> None:
    # Arrange
    infidels = {"events": [{
        "title": "Trio", "venue": {"venue": "The Venue", "address": "1 Main St", "city": "Vancouver"},
        "start_date": "2026-03-07 20:00:00", "url": "u",
    }]}
    showhub = '<ul class="show-list"><li><a href="u">Band at The Venue</a><br>Saturday, Mar 7 at 9:00 PM</li></ul>'
    results = [
        _make_fetch_result("infidelsjazz", "Infidels Jazz", content=infidels),
        _make_fetch_result("showhub", "ShowHub", content=showhub),
    ]
    cache = tmp_path / "venues.json"

    # Act
    with patch("src.pipeline.fetch_raw_sources", new_callable=AsyncMock, return_value=results):
        result = await run_pipeline(date(2026, 3, 7), date(2026, 3, 7), venue_cache=cache)

    # Assert
    band = next(e for e in result.events if e.name == "Band")
    assert (band.city, band.address) == ("Vancouver", "1 Main St")
    assert cache.exists()


@pytest.mark.asyncio
async def test_pipeline_categorizes_uncategorized_events_by_name() -> None:
    # Arrange
    html = """<div class="standard-card" data-card-kind="event"><a class="card-link" href="/e">
      <div class="details"><h3>Tuesday Trivia</h3><p class="date">Today | 8 pm</p><p>Pub</p>
      <p class="enrichment">Event</p></div></a></div>"""
    results = [_make_fetch_result("do604", "Do604", content=html)]

    # Act
    with patch("src.pipeline.fetch_raw_sources", new_callable=AsyncMock, return_value=results):
        result = await run_pipeline(date(2026, 3, 7), date(2026, 3, 7))

    # Assert
    assert result.events[0].category == "trivia"


@pytest.mark.asyncio
async def test_pipeline_ignores_unknown_source_ids() -> None:
    # Arrange
    results = [_make_fetch_result("mystery", "Mystery", content="<html></html>")]

    # Act
    with patch("src.pipeline.fetch_raw_sources", new_callable=AsyncMock, return_value=results):
        result = await run_pipeline(date(2026, 3, 7), date(2026, 3, 7))

    # Assert
    assert result.events == [] and _status(result, "Mystery").count == 0


@pytest.mark.asyncio
async def test_pipeline_canonicalizes_city_names() -> None:
    # Arrange
    infidels = {"events": [{"title": "Trio", "venue": {"venue": "V", "city": "vancouver, BC"},
                            "start_date": "2026-03-07 20:00:00", "url": "u"}]}
    results = [_make_fetch_result("infidelsjazz", "Infidels Jazz", content=infidels)]

    # Act
    with patch("src.pipeline.fetch_raw_sources", new_callable=AsyncMock, return_value=results):
        result = await run_pipeline(date(2026, 3, 7), date(2026, 3, 7))

    # Assert
    assert result.events[0].city == "Vancouver"


@pytest.mark.asyncio
async def test_pipeline_reports_fetch_warning() -> None:
    # Arrange
    fr = _make_fetch_result("infidelsjazz", "Infidels Jazz", content={"events": []})
    fr.warning = "showing first 30 of 40 result pages"

    # Act
    with patch("src.pipeline.fetch_raw_sources", new_callable=AsyncMock, return_value=[fr]):
        result = await run_pipeline(date(2026, 3, 7), date(2026, 3, 7))

    # Assert
    assert _status(result, "Infidels Jazz").warning == "showing first 30 of 40 result pages"


SHOWHUB_ONE = (
    '<ul class="show-list"><li><a href="https://showhub.ca/show/band/">Band at The Heatley</a>'
    "<br>Saturday, Mar 7 at 9:00 PM</li></ul>"
)


@pytest.mark.asyncio
async def test_pipeline_looks_up_unknown_venues_and_saves_them(tmp_path: Path) -> None:
    # Arrange
    results = [_make_fetch_result("showhub", "ShowHub", content=SHOWHUB_ONE)]
    venues = tmp_path / "data" / "venues.json"
    found = {"The Heatley": VenueInfo(city="Vancouver", address="696 East Hastings Street", origin="osm")}

    # Act
    with patch("src.pipeline.fetch_raw_sources", new_callable=AsyncMock, return_value=results), \
         patch("src.pipeline.lookup_from_pages", new_callable=AsyncMock, return_value={"The Heatley": None}), \
         patch("src.pipeline.lookup_venues", new_callable=AsyncMock, return_value=found) as lookup:
        result = await run_pipeline(date(2026, 3, 7), date(2026, 3, 7), venue_cache=venues)

    # Assert
    lookup.assert_awaited_once()
    assert result.events[0].city == "Vancouver"
    assert json.loads(venues.read_text())["venues"]["heatley"]["origin"] == "osm"


@pytest.mark.asyncio
async def test_pipeline_skips_lookup_without_venue_file() -> None:
    # Arrange
    results = [_make_fetch_result("showhub", "ShowHub", content=SHOWHUB_ONE)]

    # Act
    with patch("src.pipeline.fetch_raw_sources", new_callable=AsyncMock, return_value=results), \
         patch("src.pipeline.lookup_from_pages", new_callable=AsyncMock) as pages, \
         patch("src.pipeline.lookup_venues", new_callable=AsyncMock) as lookup:
        result = await run_pipeline(date(2026, 3, 7), date(2026, 3, 7))

    # Assert
    pages.assert_not_awaited()
    lookup.assert_not_awaited()
    assert result.events[0].city is None


@pytest.mark.asyncio
async def test_pipeline_skips_lookup_when_every_venue_is_known(tmp_path: Path) -> None:
    # Arrange
    venues = tmp_path / "venues.json"
    venues.write_text(json.dumps({"venues": {"heatley": {"city": "Vancouver", "address": None, "origin": "manual"}}}))
    results = [_make_fetch_result("showhub", "ShowHub", content=SHOWHUB_ONE)]

    # Act
    with patch("src.pipeline.fetch_raw_sources", new_callable=AsyncMock, return_value=results), \
         patch("src.pipeline.lookup_from_pages", new_callable=AsyncMock) as pages, \
         patch("src.pipeline.lookup_venues", new_callable=AsyncMock) as lookup:
        result = await run_pipeline(date(2026, 3, 7), date(2026, 3, 7), venue_cache=venues)

    # Assert
    pages.assert_not_awaited()
    lookup.assert_not_awaited()
    assert result.events[0].city == "Vancouver"


@pytest.mark.asyncio
async def test_pipeline_reads_venue_page_before_searching_osm(tmp_path: Path) -> None:
    # Arrange
    results = [_make_fetch_result("showhub", "ShowHub", content=SHOWHUB_ONE)]
    page = {"The Heatley": VenueInfo(city="Vancouver", address="696 E Hastings St", origin="page")}

    # Act
    with patch("src.pipeline.fetch_raw_sources", new_callable=AsyncMock, return_value=results), \
         patch("src.pipeline.lookup_from_pages", new_callable=AsyncMock, return_value=page) as pages, \
         patch("src.pipeline.lookup_venues", new_callable=AsyncMock, return_value={}) as osm:
        result = await run_pipeline(date(2026, 3, 7), date(2026, 3, 7), venue_cache=tmp_path / "v.json")

    # Assert
    assert pages.await_args.args[0] == {"The Heatley": ["https://showhub.ca/show/band/"]}
    osm.assert_not_awaited()
    assert result.events[0].city == "Vancouver"


@pytest.mark.asyncio
async def test_pipeline_searches_failed_page_venues_last_and_saves_only_hits(tmp_path: Path) -> None:
    # Arrange
    two = SHOWHUB_ONE + '<ul class="show-list"><li><a href="https://showhub.ca/show/duo/">Duo at Wolf Den</a><br>Saturday, Mar 7 at 8:00 PM</li></ul>'
    results = [_make_fetch_result("showhub", "ShowHub", content=two)]
    venues = tmp_path / "v.json"
    osm = {"Wolf Den": VenueInfo(city="Vancouver", address=None, origin="osm"), "The Heatley": None}

    # Act
    with patch("src.pipeline.fetch_raw_sources", new_callable=AsyncMock, return_value=results), \
         patch("src.pipeline.lookup_from_pages", new_callable=AsyncMock, return_value={"Wolf Den": None}), \
         patch("src.pipeline.lookup_venues", new_callable=AsyncMock, return_value=osm) as search:
        await run_pipeline(date(2026, 3, 7), date(2026, 3, 7), venue_cache=venues)

    # Assert
    assert search.await_args.args[0] == ["Wolf Den", "The Heatley"]
    saved = json.loads(venues.read_text())["venues"]
    assert saved["wolf den"]["origin"] == "osm" and "heatley" not in saved


@pytest.mark.asyncio
async def test_pipeline_searches_osm_when_venue_page_has_no_address(tmp_path: Path) -> None:
    # Arrange
    results = [_make_fetch_result("showhub", "ShowHub", content=SHOWHUB_ONE)]

    # Act
    with patch("src.pipeline.fetch_raw_sources", new_callable=AsyncMock, return_value=results), \
         patch("src.pipeline.lookup_from_pages", new_callable=AsyncMock, return_value={"The Heatley": None}), \
         patch("src.pipeline.lookup_venues", new_callable=AsyncMock, return_value={}) as osm:
        await run_pipeline(date(2026, 3, 7), date(2026, 3, 7), venue_cache=tmp_path / "v.json")

    # Assert
    assert osm.await_args.args[0] == ["The Heatley"]


@pytest.mark.parametrize(
    ("href", "expected"),
    [
        ("https://showhub.ca/show/x/", ["https://showhub.ca/show/x/"]),
        ("http://showhub.ca/show/x/", []),
        ("https://festivaldubois.ca/tickets", []),
        ("http://169.254.169.254/latest", []),
    ],
)
def test_venue_pages_only_uses_https_pages_on_the_source_domain(href: str, expected: list[str]) -> None:
    # Arrange
    event = Event(name="Gig", city=None, address=None, time=None, event_date=date(2026, 3, 7),
                  source_name="ShowHub", source_url=href, venue="Hall")

    # Act
    pages = _venue_pages([event], ["Hall"])

    # Assert
    assert pages.get("Hall", []) == expected


@pytest.mark.asyncio
async def test_pipeline_does_not_learn_venues_from_open_submission_sources(tmp_path: Path) -> None:
    # Arrange
    page = """<script>window.__SERVER_DATA__ = {"search_data": {"events": {"results": [{"name": "Show",
      "start_date": "2026-03-07", "start_time": "19:00", "url": "https://www.eventbrite.ca/e/1",
      "primary_venue": {"name": "Fake Hall", "address": {"address_1": "1 Fake St", "city": "Surrey"}}}]}}};</script>"""
    results = [_make_fetch_result("eventbrite", "Eventbrite", content=page)]
    venues = tmp_path / "v.json"

    # Act
    with patch("src.pipeline.fetch_raw_sources", new_callable=AsyncMock, return_value=results):
        await run_pipeline(date(2026, 3, 7), date(2026, 3, 7), venue_cache=venues)

    # Assert
    assert json.loads(venues.read_text())["venues"] == {}
