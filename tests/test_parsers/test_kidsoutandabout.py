"""Tests for src/parsers/kidsoutandabout.py: Kids Out and About day-list parser."""

from datetime import date
from pathlib import Path

import pytest

from src.parsers.kidsoutandabout import parse_kidsoutandabout, split_location

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "kidsoutandabout_sample.html"
DAY = date(2026, 11, 7)
PAGE_URL = "https://vancouver.kidsoutandabout.com/event-list/2026-11-07"


def _row(location: str, dates: str = "<span class='date-display-single'>11/07/2026</span>", title: str = "Event") -> str:
    return f"""
    <div class="views-row"><div class="node">
      <div class="field field-name-field-venue-places-api"><div class="field-items"><div class="field-item">
        <div>{location}</div><div>See map: <a href="#">Google Maps</a></div></div></div></div>
      <div class="group-activity-details">
        <h2><a href="/content/event">{title}</a></h2>
        <div class="field field-field-activity-dates"><div class="field-items">{dates}</div></div>
        <div class="field field-name-field-time"><div class="field-items"><div class="field-item">2-5 pm</div></div></div>
      </div>
    </div></div>"""


@pytest.fixture(scope="module")
def events():
    return parse_kidsoutandabout(FIXTURE.read_text(), PAGE_URL, DAY, DAY)


def test_parse_skips_online_and_out_of_country_listings(events) -> None:
    # Arrange, Act
    names = {e.name for e in events}

    # Assert
    assert "ERA's 9th Annual Kids Poster Contest 2026" not in names
    assert not any("Virtual" in n or "Race" in n for n in names)


def test_parse_extracts_city_venue_address_and_time(events) -> None:
    # Arrange, Act
    diwali = next(e for e in events if e.name == "Diwali in Vancouver 2026")

    # Assert
    assert (diwali.city, diwali.venue, diwali.address, diwali.time) == (
        "Vancouver", "Roundhouse Community Centre", "Roundhouse Mews", "2-5 pm",
    )


def test_parse_marks_events_as_family_with_absolute_urls(events) -> None:
    # Arrange, Act, Assert
    assert all(e.category == "family" for e in events)
    assert all(e.source_url.startswith("https://vancouver.kidsoutandabout.com/") for e in events)


def test_parse_skips_rows_not_on_the_page_date() -> None:
    # Arrange
    html = _row("Hall, Surrey, BC, Canada", dates="<span class='date-display-single'>11/09/2026</span>")

    # Act
    events = parse_kidsoutandabout(html, PAGE_URL, DAY, DAY)

    # Assert
    assert events == []


def test_parse_keeps_rows_without_listed_dates() -> None:
    # Arrange
    html = _row("Hall, Surrey, BC, Canada", dates="")

    # Act
    events = parse_kidsoutandabout(html, PAGE_URL, DAY, DAY)

    # Assert
    assert [e.city for e in events] == ["Surrey"]


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        ("Maplewood Farm, 405 Seymour River Place, North Vancouver, BC V7H 1S6, Canada",
         ("Maplewood Farm", "405 Seymour River Place", "North Vancouver")),
        ("33700 Prentis Avenue, Mission, BC, Canada", (None, "33700 Prentis Avenue", "Mission")),
        ("Granville Island, Vancouver, BC, Canada", ("Granville Island", None, "Vancouver")),
        ("Various Recreation Centres throughout Surrey", ("Various Recreation Centres throughout Surrey", None, "Surrey")),
    ],
)
def test_split_location_separates_venue_address_city(location: str, expected: tuple) -> None:
    # Arrange, Act
    result = split_location(location)

    # Assert
    assert result == expected


def test_parse_takes_only_city_from_contact_block_rows() -> None:
    # Arrange
    html = _row("x").replace(
        '<div class="field field-name-field-venue-places-api"><div class="field-items"><div class="field-item">\n        <div>x</div><div>See map: <a href="#">Google Maps</a></div></div></div></div>',
        '<div class="field field-name-field-contact-info">Organization: Lab Location: 1 Rd Burnaby BC</div>',
    )

    # Act
    events = parse_kidsoutandabout(html, PAGE_URL, DAY, DAY)

    # Assert
    assert (events[0].venue, events[0].address, events[0].city) == (None, None, "Burnaby")


def test_parse_skips_rows_without_location() -> None:
    # Arrange
    html = _row("x").replace("field-name-field-venue-places-api", "field-name-other")

    # Act
    events = parse_kidsoutandabout(html, PAGE_URL, DAY, DAY)

    # Assert
    assert events == []
