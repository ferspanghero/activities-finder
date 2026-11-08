"""Registry of event sources: URL, parser, pagination, and health-check hooks per source."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal
from urllib.parse import urlparse

from src.models import Event
from src.parsers import (
    bcaletrail,
    bibliocommons,
    dailyhive,
    do604,
    eventbrite,
    infidelsjazz,
    kidsoutandabout,
    rhythmchanges,
    showhub,
)

Pagination = Literal["none", "count", "until_empty"]


@dataclass(frozen=True)
class SourceSpec:
    """How to fetch and parse one source.

    `pagination`: "count" reads the page total from page 1 via `page_count`;
    "until_empty" keeps requesting pages until `has_events` is false.
    `concurrency` caps simultaneous requests to this source (rate-limited sites).
    `venue_pages`: each event's `source_url` is its own page carrying the venue's schema.org address.
    `trusted_venues`: venue names and addresses are curated, so they may be saved to the venue book
    (false for open-submission sites, where anyone can post a venue).
    `expect_events`: zero parsed events from a successful fetch is reported as a
    warning (likely layout change). `listed_through` reports the last listed day
    for sources whose page covers a fixed window.
    """

    name: str
    url_template: str
    parser: Callable[[Any, str, date, date], list[Event]]
    per_day: bool = False
    json: bool = False
    pagination: Pagination = "none"
    page_count: Callable[[Any], int] | None = None
    has_events: Callable[[str], bool] | None = None
    max_pages: int = 1
    expect_events: bool = False
    concurrency: int | None = None
    venue_pages: bool = False
    trusted_venues: bool = True
    listed_through: Callable[[str, date], date | None] | None = None


def source_host(spec: SourceSpec) -> str:
    """Host of the source's own site, e.g. 'showhub.ca'."""
    return urlparse(spec.url_template).netloc


_BIBLIOCOMMONS_URL = (
    "https://gateway.bibliocommons.com/v2/libraries/{slug}/events/search"
    "?startDate={{from_date}}&endDate={{to_date}}&limit=100"
)

SOURCES: dict[str, SourceSpec] = {
    "do604": SourceSpec(
        name="Do604",
        url_template="https://do604.com/events/{YYYY}/{M}/{D}",
        parser=do604.parse_do604,
        per_day=True,
        pagination="until_empty",
        has_events=do604.has_events,
        max_pages=40,
        expect_events=True,
        venue_pages=True,
    ),
    "dailyhive": SourceSpec(
        name="Daily Hive",
        url_template="https://dailyhive.com/vancouver/listed/events?after={from_date}&before={to_date}",
        parser=dailyhive.parse_dailyhive,
        pagination="count",
        page_count=dailyhive.page_count,
        max_pages=10,
    ),
    "rhythmchanges": SourceSpec(
        name="Rhythm Changes",
        url_template="https://rhythmchanges.ca/gigs/",
        parser=rhythmchanges.parse_rhythmchanges,
        expect_events=True,
        listed_through=rhythmchanges.listed_through,
    ),
    "showhub": SourceSpec(
        name="ShowHub",
        url_template="https://showhub.ca/weekly-listings/",
        parser=showhub.parse_showhub,
        expect_events=True,
        venue_pages=True,
        listed_through=showhub.listed_through,
    ),
    "infidelsjazz": SourceSpec(
        name="Infidels Jazz",
        url_template="https://theinfidelsjazz.ca/wp-json/tribe/events/v1/events/?start_date={from_date}&end_date={to_date}",
        parser=infidelsjazz.parse_infidelsjazz,
        json=True,
    ),
    "bcaletrail": SourceSpec(
        name="BC Ale Trail",
        url_template="https://bcaletrail.ca/events/?date-start={from_date}&date-end={to_date}",
        parser=bcaletrail.parse_bcaletrail,
        expect_events=True,
    ),
    "kidsoutandabout": SourceSpec(
        name="Kids Out and About",
        url_template="https://vancouver.kidsoutandabout.com/event-list/{from_date}",
        parser=kidsoutandabout.parse_kidsoutandabout,
        per_day=True,
        expect_events=True,
    ),
    "eventbrite": SourceSpec(
        name="Eventbrite",
        url_template="https://www.eventbrite.ca/d/canada--vancouver/all-events/?start_date={from_date}&end_date={to_date}",
        parser=eventbrite.parse_eventbrite,
        # One range query: per-day paging (about 20 pages a day) trips Eventbrite's rate limit.
        trusted_venues=False,
        pagination="count",
        page_count=eventbrite.page_count,
        max_pages=50,
        expect_events=True,
        concurrency=2,
    ),
    "vpl": SourceSpec(
        name=bibliocommons.LIBRARY_NAMES["vpl"],
        url_template=_BIBLIOCOMMONS_URL.format(slug="vpl"),
        parser=bibliocommons.parse_bibliocommons,
        json=True,
        pagination="count",
        page_count=bibliocommons.page_count,
        max_pages=10,
    ),
    "richmondpl": SourceSpec(
        name=bibliocommons.LIBRARY_NAMES["yourlibrary"],
        url_template=_BIBLIOCOMMONS_URL.format(slug="yourlibrary"),
        parser=bibliocommons.parse_bibliocommons,
        json=True,
        pagination="count",
        page_count=bibliocommons.page_count,
        max_pages=10,
    ),
}
