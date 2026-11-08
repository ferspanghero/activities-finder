"""Tests for src/parsers/do604.py: Do604 day-page parser."""

from datetime import date
from pathlib import Path

import pytest

from src.parsers.do604 import has_events, parse_do604

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "do604_sample.html"
DAY = date(2026, 11, 7)
PAGE_URL = "https://do604.com/events/2026/11/07"


def _card(enrichment: str, venue: str = "The Fox Cabaret", when: str = "Today | 7 pm", title: str = "Show") -> str:
    return f"""
    <div class="standard-card" data-card-kind="event">
      <a class="card-link" href="../../../events/2026/11/7/show-tickets">
        <div class="details">
          <p class="eyebrow">Presenter</p>
          <h3>{title}</h3>
          <p class="date">{when}</p>
          <p>{venue}</p>
          <p class="enrichment">{enrichment}</p>
        </div>
      </a>
    </div>"""


@pytest.fixture(scope="module")
def events():
    return parse_do604(FIXTURE.read_text(), PAGE_URL, DAY, DAY)


def test_parse_finds_every_card_on_the_page(events) -> None:
    # Arrange, Act, Assert
    assert len(events) == 20


def test_parse_extracts_title_venue_time_and_date(events) -> None:
    # Arrange, Act
    luzia = next(e for e in events if e.name == "LUZIA")

    # Assert
    assert (luzia.venue, luzia.time, luzia.event_date) == ("Concord Pacific Place", "7 pm", DAY)


def test_parse_maps_category_and_neighbourhood_city(events) -> None:
    # Arrange, Act
    luzia = next(e for e in events if e.name == "LUZIA")

    # Assert
    assert (luzia.category, luzia.city) == ("music", "Vancouver")


def test_parse_builds_absolute_event_url(events) -> None:
    # Arrange, Act
    luzia = next(e for e in events if e.name == "LUZIA")

    # Assert
    assert luzia.source_url == "https://do604.com/events/2026/11/4/luzia-tickets"


def test_parse_leaves_city_unknown_for_unmapped_location(events) -> None:
    # Arrange, Act
    crawl = next(e for e in events if e.name == "Eastside Culture Crawl 2026")

    # Assert
    assert (crawl.city, crawl.category) == (None, "festivals")


@pytest.mark.parametrize(
    ("enrichment", "venue", "expected_city"),
    [
        ("Art & Culture • North Vancouver / Shipyards", "Griffin Art Projects", "North Vancouver"),
        ("Music • Central City / Guildford", "Hall", "Surrey"),
        ("Music • Metrotown / Brentwood", "Hall", "Burnaby"),
        ("Event", "New Westminster", "New Westminster"),
        ("Event", "Some Pub", None),
    ],
)
def test_parse_resolves_city_from_neighbourhood_then_venue(enrichment: str, venue: str, expected_city: str | None) -> None:
    # Arrange
    html = _card(enrichment, venue=venue)

    # Act
    events = parse_do604(html, PAGE_URL, DAY, DAY)

    # Assert
    assert events[0].city == expected_city


def test_parse_treats_date_only_line_as_no_time() -> None:
    # Arrange
    html = _card("Event", when="Every Saturday")

    # Act
    events = parse_do604(html, PAGE_URL, DAY, DAY)

    # Assert
    assert events[0].time is None


def test_parse_skips_cards_without_title() -> None:
    # Arrange
    html = _card("Event", title="")

    # Act
    events = parse_do604(html, PAGE_URL, DAY, DAY)

    # Assert
    assert events == []


def test_has_events_detects_cards() -> None:
    # Arrange, Act, Assert
    assert has_events(FIXTURE.read_text()) is True
    assert has_events("<html><body>No more events</body></html>") is False


@pytest.mark.parametrize("when", ["Oct 22 - Nov 27 | 4 am", "Mar 8 - Nov 24 | 1 am - 1 am", "Nov 5 – Nov 8 | 12 am"])
def test_parse_drops_series_start_time_on_multi_day_listings(when: str) -> None:
    # Arrange
    html = _card("Event", when=when)

    # Act
    events = parse_do604(html, PAGE_URL, DAY, DAY)

    # Assert
    assert events[0].time is None


@pytest.mark.parametrize(
    "when",
    ["Sat, Nov 7 | 12 am - 11:59 pm", "Today | 12 AM - 11:59 PM", "Nov 5 - Nov 8 | 12 am - 11:59 pm",
     "Today | 12:00 am – 11:59 pm"],
)
def test_parse_reads_midnight_to_midnight_as_all_day(when: str) -> None:
    # Arrange
    html = _card("Event", when=when)

    # Act
    events = parse_do604(html, PAGE_URL, DAY, DAY)

    # Assert
    assert events[0].time == "all day"


def test_parse_keeps_real_show_time_of_a_long_run() -> None:
    # Arrange
    html = _card("Event", when="Nov 4, 2026 - Jan 10, 2027 | 7 pm")

    # Act
    events = parse_do604(html, PAGE_URL, DAY, DAY)

    # Assert
    assert events[0].time == "7 pm"


def test_parse_keeps_single_day_times() -> None:
    # Arrange
    html = _card("Event", when="Sat, Nov 7 | 7:30 pm - 11 pm")

    # Act
    events = parse_do604(html, PAGE_URL, DAY, DAY)

    # Assert
    assert events[0].time == "7:30 pm - 11 pm"
