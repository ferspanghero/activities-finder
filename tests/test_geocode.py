"""Tests for src/geocode.py: OpenStreetMap venue lookup with strict match rules."""

import asyncio
import re
from unittest.mock import patch
from urllib.parse import parse_qs, unquote, urlparse

import pytest
from aioresponses import CallbackResult, aioresponses

from src.geocode import (
    NOMINATIM_URL,
    is_searchable,
    lookup_from_pages,
    lookup_venues,
    pick_match,
    place_from_jsonld,
    search_text,
)


def _hit(name: str, kind: str = "pub", city: str = "Vancouver", **addr: str) -> dict:
    return {
        "name": name, "category": "amenity", "type": kind,
        "address": {"city": city, "house_number": "696", "road": "East Hastings Street", **addr},
    }


def test_pick_match_accepts_event_venue_with_matching_name() -> None:
    # Arrange
    results = [_hit("The Heatley")]

    # Act
    info = pick_match("The Heatley", results)

    # Assert
    assert (info.city, info.address, info.origin) == ("Vancouver", "696 East Hastings Street", "osm")


@pytest.mark.parametrize(
    ("query", "result"),
    [
        ("The Admiral", {"name": "The Admiral", "category": "building", "type": "apartments",
                         "address": {"city": "Vancouver", "road": "Nelson Street"}}),
        ("Apollo's", {"name": "the Apollo Clinic", "category": "office", "type": "therapist",
                      "address": {"town": "Abbotsford"}}),
        ("Frankie's Jazz Club", _hit("Fortune Sound Club", kind="nightclub")),
    ],
)
def test_pick_match_rejects_wrong_place_type_or_name(query: str, result: dict) -> None:
    # Arrange, Act
    info = pick_match(query, [result])

    # Assert
    assert info is None


def test_pick_match_accepts_renamed_venue_whose_name_contains_the_query_words() -> None:
    # Arrange
    results = [_hit("East Café in Marpole (formerly Gigi Blin)", kind="cafe")]

    # Act
    info = pick_match("Gigi Blin East Cafe Marpole", results)

    # Assert
    assert info is not None and info.city == "Vancouver"


def test_pick_match_reads_city_from_municipality_names() -> None:
    # Arrange
    results = [_hit("Centennial Theatre", kind="theatre", city="District of North Vancouver")]

    # Act
    info = pick_match("Centennial Theatre", results)

    # Assert
    assert info.city == "North Vancouver"


def test_pick_match_uses_town_when_city_missing_and_skips_cityless_results() -> None:
    # Arrange
    no_city = {"name": "Brackendale Hall", "category": "amenity", "type": "community_centre", "address": {}}
    town = {"name": "Brackendale Hall", "category": "amenity", "type": "community_centre", "address": {"town": "Squamish"}}

    # Act
    info = pick_match("Brackendale Hall", [no_city, town])

    # Assert
    assert (info.city, info.address) == ("Squamish", None)


def test_pick_match_returns_none_for_no_results() -> None:
    # Arrange, Act, Assert
    assert pick_match("Anything", []) is None


@pytest.mark.asyncio
async def test_lookup_venues_queries_metro_vancouver_and_maps_results() -> None:
    # Arrange
    pattern = re.compile(re.escape(NOMINATIM_URL) + r".*")

    with aioresponses() as mocked:
        mocked.get(pattern, payload=[_hit("The Heatley")])
        mocked.get(pattern, payload=[])

        # Act
        found = await lookup_venues(["The Heatley", "Nowhere Lounge"], delay=0)

        # Assert
        query = parse_qs(urlparse(str(next(iter(mocked.requests))[1])).query)
    assert found["The Heatley"].city == "Vancouver"
    assert found["Nowhere Lounge"] is None
    assert query["bounded"] == ["1"] and query["countrycodes"] == ["ca"]


@pytest.mark.asyncio
async def test_lookup_venues_respects_max_lookups() -> None:
    # Arrange
    pattern = re.compile(re.escape(NOMINATIM_URL) + r".*")

    with aioresponses() as mocked:
        mocked.get(pattern, payload=[], repeat=True)

        # Act
        found = await lookup_venues(["A", "B", "C"], max_lookups=2, delay=0)

    # Assert
    assert list(found) == ["A", "B"]


@pytest.mark.asyncio
async def test_lookup_venues_stops_without_recording_on_error() -> None:
    # Arrange
    pattern = re.compile(re.escape(NOMINATIM_URL) + r".*")

    with aioresponses() as mocked:
        mocked.get(pattern, payload=[])
        mocked.get(pattern, status=429)

        # Act
        found = await lookup_venues(["A", "B", "C"], delay=0)

    # Assert
    assert found == {"A": None}


@pytest.mark.parametrize(
    ("category", "kind", "accepted"),
    [("tourism", "attraction", True), ("shop", "books", True), ("leisure", "park", True),
     ("building", "apartments", False), ("office", "therapist", False), ("place", "neighbourhood", False)],
)
def test_pick_match_accepts_place_categories_and_rejects_buildings(category: str, kind: str, accepted: bool) -> None:
    # Arrange
    result = {"name": "Fly Over Canada", "category": category, "type": kind, "address": {"city": "Vancouver"}}

    # Act
    info = pick_match("Fly Over Canada", [result])

    # Assert
    assert (info is not None) == accepted


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Emily Carr University of Art + Design", "Emily Carr University of Art and Design"),
        ("ANAF 45 ( North Van )", "ANAF 45"),
        ("Banyen Books & Sound", "Banyen Books and Sound"),
    ],
)
def test_search_text_cleans_venue_names(name: str, expected: str) -> None:
    # Arrange, Act, Assert
    assert search_text(name) == expected


@pytest.mark.parametrize(
    ("name", "expected"),
    [("Various Locations", False), ("Various parks", False), ("13750 88 Avenue", False), ("TBA", False),
     ("Online", False), ("Billboard: Fraser St at 15th Ave", False), ("Bacchus Lounge", True),
     ("8EAST", True), ("2-1555 7th Ave W", False), ("1181 Lounge", True), ("312 Main", True),
     ("100 Braid Street Studios", True)],
)
def test_is_searchable_skips_non_venues(name: str, expected: bool) -> None:
    # Arrange, Act, Assert
    assert is_searchable(name) is expected


@pytest.mark.asyncio
async def test_lookup_venues_skips_non_venues_without_requests() -> None:
    # Arrange
    pattern = re.compile(re.escape(NOMINATIM_URL) + r".*")

    with aioresponses() as mocked:
        mocked.get(pattern, payload=[_hit("The Heatley")])

        # Act
        found = await lookup_venues(["Various Locations", "The Heatley"], delay=0)

    # Assert
    assert found["Various Locations"] is None and found["The Heatley"].city == "Vancouver"


SHOWHUB_PAGE = """<script type="application/ld+json">{"@context": "https://schema.org", "@type": "MusicEvent",
 "name": "Connor Roff at The Mainstay", "location": {"@type": "Place", "name": "The Mainstay",
 "address": {"@type": "PostalAddress", "streetAddress": "123 Carrie Cates Ct", "addressLocality": "North Vancouver"}}}
</script>"""
DO604_PAGE = """<script type="application/ld+json">{"@context":"https://schema.org","@graph":[
 {"@type":"Organization","name":"Do604"},
 {"@type":"Place","name":"Biltmore Cabaret","address":{"@type":"PostalAddress",
  "streetAddress":"2755 Prince Edward St","addressLocality":"Vancouver"}}]}</script>"""


@pytest.mark.parametrize(
    ("html", "expected"),
    [
        (SHOWHUB_PAGE, ("North Vancouver", "123 Carrie Cates Ct", "page")),
        (DO604_PAGE, ("Vancouver", "2755 Prince Edward St", "page")),
    ],
)
def test_place_from_jsonld_reads_venue_address(html: str, expected: tuple) -> None:
    # Arrange, Act
    info = place_from_jsonld(html)

    # Assert
    assert (info.city, info.address, info.origin) == expected


@pytest.mark.parametrize(
    "html",
    ["<html></html>", '<script type="application/ld+json">{bad</script>',
     '<script type="application/ld+json">{"@type": "Place", "address": {"streetAddress": "1 A St"}}</script>'],
)
def test_place_from_jsonld_returns_none_without_locality(html: str) -> None:
    # Arrange, Act, Assert
    assert place_from_jsonld(html) is None


@pytest.mark.asyncio
async def test_lookup_from_pages_reads_each_venue_page_once() -> None:
    # Arrange
    pages = {"The Mainstay": ["https://showhub.ca/show/a/"], "Nowhere": ["https://showhub.ca/show/b/"]}

    with aioresponses() as mocked:
        mocked.get("https://showhub.ca/show/a/", body=SHOWHUB_PAGE)
        mocked.get("https://showhub.ca/show/b/", body="<html></html>")

        # Act
        found = await lookup_from_pages(pages, delay=0)

    # Assert
    assert found["The Mainstay"].city == "North Vancouver" and found["Nowhere"] is None


@pytest.mark.asyncio
async def test_lookup_from_pages_leaves_failed_pages_unrecorded() -> None:
    # Arrange
    with aioresponses() as mocked:
        mocked.get("https://showhub.ca/show/a/", status=500)

        # Act
        found = await lookup_from_pages({"The Mainstay": ["https://showhub.ca/show/a/"]}, delay=0)

    # Assert
    assert found == {}


@pytest.mark.asyncio
async def test_lookup_venues_retries_with_cleaned_name() -> None:
    # Arrange
    pattern = re.compile(re.escape(NOMINATIM_URL) + r".*")

    with aioresponses() as mocked:
        mocked.get(pattern, payload=[])
        mocked.get(pattern, payload=[_hit("Emily Carr University of Art and Design", kind="university")])

        # Act
        found = await lookup_venues(["Emily Carr University of Art + Design"], delay=0)

        # Assert
        # aioresponses records the query percent-encoded once more than aiohttp sends it.
        queries = [unquote(key[1].query["q"]) for key in mocked.requests]
    assert found["Emily Carr University of Art + Design"].city == "Vancouver"
    assert queries == ["Emily Carr University of Art + Design", "Emily Carr University of Art and Design"]


@pytest.mark.asyncio
async def test_lookup_from_pages_reads_pages_one_at_a_time() -> None:
    # Arrange
    in_flight = 0
    peak = 0

    async def slow(url, **kwargs):
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        await asyncio.sleep(0.01)
        in_flight -= 1
        return CallbackResult(body=SHOWHUB_PAGE)

    pages = {f"Venue {i}": [f"https://showhub.ca/show/{i}/"] for i in range(4)}

    with aioresponses() as mocked:
        mocked.get(re.compile(r"https://showhub\.ca/show/.*"), callback=slow, repeat=True)

        # Act
        found = await lookup_from_pages(pages, delay=0)

    # Assert
    assert peak == 1 and len(found) == 4


@pytest.mark.parametrize(
    ("query", "found_name"),
    [("The Sanctuary", "Reifel Migratory Bird Sanctuary"), ("Legion", "Royal Canadian Legion Branch 83"),
     ("Rio Theatre", "Rex Theatre")],
)
def test_pick_match_rejects_generic_or_near_miss_names(query: str, found_name: str) -> None:
    # Arrange
    results = [{"name": found_name, "category": "amenity", "type": "theatre", "address": {"city": "Delta"}}]

    # Act, Assert
    assert pick_match(query, results) is None


def test_pick_match_accepts_shorter_osm_name_with_two_words() -> None:
    # Arrange
    results = [_hit("Emily Carr University", kind="university")]

    # Act
    info = pick_match("Emily Carr University of Art + Design", results)

    # Assert
    assert info is not None


def test_pick_match_treats_matches_in_several_cities_as_ambiguous() -> None:
    # Arrange
    results = [_hit("Shamrock Pub", city="Vancouver"), _hit("Shamrock Pub", city="Surrey")]

    # Act, Assert
    assert pick_match("Shamrock Pub", results) is None


def test_pick_match_omits_address_without_road() -> None:
    # Arrange
    result = {"name": "Earthwise Society", "category": "leisure", "type": "garden",
              "address": {"town": "Agassiz", "house_number": "6031"}}

    # Act
    info = pick_match("Earthwise Society", [result])

    # Assert
    assert info.address is None


@pytest.mark.parametrize(
    "jsonld",
    [
        '{"@type": "MusicVenue", "name": "X", "address": {"streetAddress": "96 Kyle Street , ", "addressLocality": "Port Moody"}}',
        '{"@type": ["BarOrPub", "Place"], "address": {"streetAddress": "96 Kyle Street", "addressLocality": "Port Moody"}}',
    ],
)
def test_place_from_jsonld_accepts_place_subtypes_and_trims_address(jsonld: str) -> None:
    # Arrange
    html = f'<script type="application/ld+json">{jsonld}</script>'

    # Act
    info = place_from_jsonld(html)

    # Assert
    assert (info.city, info.address) == ("Port Moody", "96 Kyle Street")


@pytest.mark.asyncio
async def test_lookup_venues_leaves_venue_unrecorded_when_budget_ends_mid_search() -> None:
    # Arrange
    pattern = re.compile(re.escape(NOMINATIM_URL) + r".*")

    with aioresponses() as mocked:
        mocked.get(pattern, payload=[], repeat=True)

        # Act
        found = await lookup_venues(["Art + Design"], max_lookups=1, delay=0)

    # Assert
    assert found == {}


@pytest.mark.parametrize("body", [{"payload": {"error": "Bad request"}}, {"body": "{not json"}])
@pytest.mark.asyncio
async def test_lookup_venues_stops_without_recording_on_malformed_response(body: dict) -> None:
    # Arrange
    pattern = re.compile(re.escape(NOMINATIM_URL) + r".*")

    with aioresponses() as mocked:
        mocked.get(pattern, **body)

        # Act
        found = await lookup_venues(["Somewhere Hall"], delay=0)

    # Assert
    assert found == {}


@pytest.mark.asyncio
async def test_lookup_venues_paces_requests_and_identifies_itself() -> None:
    # Arrange
    pattern = re.compile(re.escape(NOMINATIM_URL) + r".*")
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    with aioresponses() as mocked, patch("src.geocode.asyncio.sleep", fake_sleep):
        mocked.get(pattern, payload=[], repeat=True)

        # Act
        await lookup_venues(["Alpha & Co", "Beta Hall"], delay=1.1)

        # Assert
        call = next(iter(mocked.requests.values()))[0]
    assert sleeps == [1.1, 1.1]  # three requests: both forms of "Alpha & Co", then "Beta Hall"
    assert "activities-searcher" in call.kwargs["headers"]["User-Agent"]


@pytest.mark.asyncio
async def test_lookup_from_pages_tries_next_page_and_stops_host_after_429() -> None:
    # Arrange
    pages = {
        "Venue A": ["https://showhub.ca/show/a1/", "https://showhub.ca/show/a2/"],
        "Venue B": ["https://showhub.ca/show/b1/"],
        "Venue C": ["https://showhub.ca/show/c1/"],
    }

    with aioresponses() as mocked:
        mocked.get("https://showhub.ca/show/a1/", status=404)
        mocked.get("https://showhub.ca/show/a2/", body=SHOWHUB_PAGE)
        mocked.get("https://showhub.ca/show/b1/", status=429)

        # Act
        found = await lookup_from_pages(pages, delay=0)

        # Assert
        requested = [str(key[1]) for key in mocked.requests]
    assert found == {"Venue A": found["Venue A"]} and found["Venue A"].city == "North Vancouver"
    assert "https://showhub.ca/show/c1/" not in requested


@pytest.mark.asyncio
async def test_lookup_from_pages_reads_undecodable_page_as_without_address() -> None:
    # Arrange
    with aioresponses() as mocked:
        mocked.get("https://showhub.ca/show/a/", body=b"\xff\xfe\x00bad", content_type="text/html; charset=utf-8")

        # Act
        found = await lookup_from_pages({"Venue A": ["https://showhub.ca/show/a/"]}, delay=0)

    # Assert
    assert found == {"Venue A": None}


def test_place_from_jsonld_prefers_event_location_over_other_places() -> None:
    # Arrange
    html = """<script type="application/ld+json">{"@type": "MusicEvent",
      "organizer": {"@type": "LocalBusiness", "address": {"addressLocality": "Surrey"}},
      "location": {"@type": "Place", "address": {"streetAddress": "1 A St", "addressLocality": "Burnaby"}}}</script>"""

    # Act
    info = place_from_jsonld(html)

    # Assert
    assert info.city == "Burnaby"


def test_place_from_jsonld_rejects_ambiguous_places_without_event_location() -> None:
    # Arrange
    html = """<script type="application/ld+json">[
      {"@type": "Place", "address": {"addressLocality": "Surrey"}},
      {"@type": "Place", "address": {"addressLocality": "Burnaby"}}]</script>"""

    # Act, Assert
    assert place_from_jsonld(html) is None


def test_place_from_jsonld_survives_deeply_nested_json() -> None:
    # Arrange
    nested = "[" * 5000 + "]" * 5000
    html = f'<script type="application/ld+json">{nested}</script>'

    # Act, Assert
    assert place_from_jsonld(html) is None


def test_pick_match_skips_malformed_results() -> None:
    # Arrange
    results = ["oops", {"name": "The Heatley", "category": "amenity", "type": "pub", "address": "bad"}, _hit("The Heatley")]

    # Act
    info = pick_match("The Heatley", results)

    # Assert
    assert info is not None and info.city == "Vancouver"


@pytest.mark.asyncio
async def test_lookup_from_pages_does_not_follow_redirects() -> None:
    # Arrange
    with aioresponses() as mocked:
        mocked.get("https://showhub.ca/show/a/", status=302, headers={"Location": "https://evil.example/"})
        mocked.get("https://evil.example/", body=SHOWHUB_PAGE)

        # Act
        found = await lookup_from_pages({"Venue A": ["https://showhub.ca/show/a/"]}, delay=0)

    # Assert
    assert found == {}
