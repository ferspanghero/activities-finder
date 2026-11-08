"""Edge-case tests for error branches across parsers, fetch, pipeline, and formatting."""

import argparse
import json
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from aioresponses import aioresponses

from src.cli_utils import add_filter_arguments
from src.dedup import dedupe
from src.fetch_sources import build_source_url, fetch_raw_sources, page_url
from src.models import Event, FetchResult
from src.parsers.bcaletrail import parse_bcaletrail
from src.parsers.common import format_price
from src.parsers.dailyhive import parse_dailyhive
from src.parsers.eventbrite import parse_eventbrite
from src.parsers.kidsoutandabout import parse_kidsoutandabout, split_location
from src.pipeline import run_pipeline
from src.renderers.formatting import location_text, safe_url
from src.renderers.html_renderer import format_date_display
from src.renderers.markdown_renderer import render_markdown
from src.sources import SOURCES
from src.timeparse import UNKNOWN_TIME, parse_time_to_minutes
from src.venues import VenueBook

DAY = date(2026, 3, 7)


def _event(**kw: object) -> Event:
    base: dict = {"name": "E", "city": None, "address": None, "time": None, "event_date": DAY,
                  "source_name": "S", "source_url": "u"}

    return Event(**{**base, **kw})


# --- parsers -----------------------------------------------------------------

@pytest.mark.parametrize(
    "card",
    [
        '<div class="event-item"></div>',
        '<div class="event-item" data-event-times="{bad json"></div>',
        '<div class="event-item" data-event-times="[]"></div>',
        """<div class="event-item" data-event-times='[{"upcoming_times":[{"start":"nope"}]}]'><h2>X</h2></div>""",
        """<div class="event-item" data-event-times='[{"upcoming_times":[{"start":"2026-03-07T10:00:00"}]}]'><h2></h2></div>""",
    ],
)
def test_bcaletrail_skips_malformed_cards(card: str) -> None:
    # Arrange, Act
    events = parse_bcaletrail(card, "https://bcaletrail.ca/events/", DAY, DAY)

    # Assert
    assert events == []


def test_dailyhive_returns_empty_for_missing_or_invalid_payload() -> None:
    # Arrange
    pages = ["<html></html>", '<script id="__NEXT_DATA__">{not json</script>']

    # Act
    results = [parse_dailyhive(p, "u", DAY, DAY) for p in pages]

    # Assert
    assert results == [[], []]


def test_dailyhive_includes_event_with_unparseable_dates_without_time() -> None:
    # Arrange
    item = {"title": "X", "start_datetime": "soon", "end_datetime": "later", "venue_details": {}}
    page = f'<script id="__NEXT_DATA__">{json.dumps({"props": {"pageProps": {"upcomingEvents": [item]}}})}</script>'

    # Act
    events = parse_dailyhive(page, "u", DAY, DAY)

    # Assert
    assert (events[0].event_date, events[0].time) == (DAY, None)


def test_eventbrite_handles_invalid_json_bad_dates_and_bad_times() -> None:
    # Arrange
    broken = "<script>window.__SERVER_DATA__ = {not json</script>"
    items = [
        {"name": "Bad date", "start_date": "soon"},
        {"name": "Odd time", "start_date": "2026-03-07", "start_time": "noon"},
    ]
    page = f"<script>window.__SERVER_DATA__ = {json.dumps({'search_data': {'events': {'results': items}}})};</script>"

    # Act
    events = parse_eventbrite(page, "u", DAY, DAY)

    # Assert
    assert parse_eventbrite(broken, "u", DAY, DAY) == []
    assert [(e.name, e.time) for e in events] == [("Odd time", None)]


def test_kidsoutandabout_skips_rows_without_title_and_ignores_bad_dates() -> None:
    # Arrange
    no_title = '<div class="views-row"><div class="group-activity-details"><h2><a href="/x"></a></h2></div></div>'
    bad_date = """<div class="views-row">
      <div class="field field-name-field-venue-places-api"><div class="field-items"><div class="field-item">
        <div>Hall, Surrey, BC</div></div></div></div>
      <div class="group-activity-details"><h2><a href="/x">Fun</a></h2>
        <span class="date-display-single">13/45/2026</span></div></div>"""

    # Act
    events = parse_kidsoutandabout(no_title + bad_date, "https://vancouver.kidsoutandabout.com/x", DAY, DAY)

    # Assert
    assert [(e.name, e.time) for e in events] == [("Fun", None)]


def test_split_location_with_only_province_parts() -> None:
    # Arrange, Act, Assert
    assert split_location("BC, Canada") == (None, None, None)


def test_format_price_ignores_non_numeric_values() -> None:
    # Arrange, Act, Assert
    assert format_price("TBA", "") is None


# --- time, formatting, venues, dedup -------------------------------------------

@pytest.mark.parametrize("text", ["13 pm", "25"])
def test_parse_time_rejects_out_of_range_hours(text: str) -> None:
    # Arrange, Act, Assert
    assert parse_time_to_minutes(text) == UNKNOWN_TIME


def test_location_text_drops_venue_repeated_in_address() -> None:
    # Arrange
    event = _event(venue="Science World", address="Science World, 1455 Quebec St")

    # Act, Assert
    assert location_text(event) == "Science World, 1455 Quebec St"


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        (date(2026, 3, 7), date(2026, 4, 2), "March 7 – April 2, 2026"),
        (date(2026, 12, 30), date(2027, 1, 2), "December 30, 2026 – January 2, 2027"),
    ],
)
def test_format_date_display_spans_months_and_years(start: date, end: date, expected: str) -> None:
    # Arrange, Act, Assert
    assert format_date_display(start, end) == expected


def test_venue_book_ignores_punctuation_only_venue() -> None:
    # Arrange
    book = VenueBook()

    # Act
    book.learn([_event(venue="!!!", city="Vancouver")])

    # Assert
    assert len(book) == 0


def test_dedupe_ignores_unrelated_names_sharing_a_token() -> None:
    # Arrange
    events = [_event(name="Jazz Brunch", source_name="A"), _event(name="Jazz Funeral Procession", source_name="B")]

    # Act
    result = dedupe(events)

    # Assert
    assert (result.removed, result.candidates) == (0, [])


def test_add_filter_arguments_registers_flags() -> None:
    # Arrange
    parser = argparse.ArgumentParser()

    # Act
    add_filter_arguments(parser)
    args = parser.parse_args(["--add-cities", "Whistler", "--types", "music"])

    # Assert
    assert (args.cities, args.add_cities, args.types) == (None, "Whistler", "music")


# --- fetch and pipeline ----------------------------------------------------------

@pytest.mark.asyncio
async def test_fetch_reports_invalid_json() -> None:
    # Arrange
    url = build_source_url("infidelsjazz", DAY, DAY)

    with aioresponses() as mocked:
        mocked.get(url, body="{not json")

        # Act
        results = await fetch_raw_sources(DAY, DAY, sources={"infidelsjazz": SOURCES["infidelsjazz"]})

    # Assert
    assert results[0].content is None and "Invalid JSON" in results[0].error


@pytest.mark.asyncio
async def test_until_empty_pagination_keeps_failed_page_as_error() -> None:
    # Arrange
    base = build_source_url("do604", DAY, DAY)
    card = '<div data-card-kind="event"></div>'

    with aioresponses() as mocked:
        mocked.get(base, body=card)
        for p in range(2, 6):
            mocked.get(page_url(base, p), status=404)

        # Act
        results = await fetch_raw_sources(DAY, DAY, sources={"do604": SOURCES["do604"]})

    # Assert
    assert results[0].error is None and results[-1].error is not None


@pytest.mark.asyncio
async def test_pipeline_reports_parser_exception_as_error() -> None:
    # Arrange
    fr = FetchResult("infidelsjazz", "Infidels Jazz", "u", {"events": "not a list"}, None, DAY, DAY)

    # Act
    with patch("src.pipeline.fetch_raw_sources", new_callable=AsyncMock, return_value=[fr]):
        result = await run_pipeline(DAY, DAY)

    # Assert
    assert result.source_statuses[0].error.startswith("parser error:")


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://x.com/a b(c)", "https://x.com/a%20b%28c%29"),
        ("http://x.com", "http://x.com"),
        ("javascript:alert(1)", None),
        ("data:text/html,x", None),
        ("", None),
    ],
)
def test_safe_url_allows_only_http_links(url: str, expected: str | None) -> None:
    # Arrange, Act, Assert
    assert safe_url(url) == expected


def test_safe_url_strips_control_characters() -> None:
    # Arrange, Act, Assert
    assert safe_url("https://a/\nb\t<c>") == "https://a/bc"


def test_markdown_cells_escape_link_and_html_syntax() -> None:
    # Arrange
    event = _event(name="Click [here](javascript:x) <img src=x>\nnext", source_name="S", source_url="https://ok")

    # Act
    md = render_markdown([event], [], DAY, DAY)

    # Assert
    row = next(line for line in md.split("\n") if "Click" in line)
    assert "\\[here\\]" in row and "\\<img" in row and "next" in row


@pytest.mark.asyncio
async def test_pipeline_status_hides_exception_detail() -> None:
    # Arrange
    fr = FetchResult("infidelsjazz", "Infidels Jazz", "u", {"events": "not a list"}, None, DAY, DAY)

    # Act
    with patch("src.pipeline.fetch_raw_sources", new_callable=AsyncMock, return_value=[fr]):
        result = await run_pipeline(DAY, DAY)

    # Assert
    assert result.source_statuses[0].error == "parser error: AttributeError"
