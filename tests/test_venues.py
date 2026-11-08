"""Tests for src/venues.py: venue to city/address lookup learned from sources."""

import json
from datetime import date
from pathlib import Path

import pytest

from src.models import Event
from src.venues import VenueBook, VenueInfo, venue_key


def _event(venue: str | None, city: str | None = None, address: str | None = None) -> Event:
    return Event(
        name="E", city=city, address=address, time=None, event_date=date(2026, 3, 7),
        source_name="S", source_url="u", venue=venue,
    )


def test_venue_key_ignores_case_punctuation_and_leading_article() -> None:
    # Arrange, Act
    keys = {venue_key("The Fox Cabaret"), venue_key("fox cabaret"), venue_key("Fox Cabaret!")}

    # Assert
    assert keys == {"fox cabaret"}


def test_fill_adds_city_and_address_for_known_venue() -> None:
    # Arrange
    book = VenueBook()
    book.learn([_event("Frankie's Jazz Club", city="Vancouver", address="755 Beatty St")])

    # Act
    filled = book.fill([_event("Frankie's Jazz Club")])

    # Assert
    assert (filled[0].city, filled[0].address) == ("Vancouver", "755 Beatty St")


def test_fill_keeps_existing_fields() -> None:
    # Arrange
    book = VenueBook()
    book.learn([_event("Hall", city="Burnaby", address="1 A St")])

    # Act
    filled = book.fill([_event("Hall", city="Surrey", address="9 Z St")])

    # Assert
    assert (filled[0].city, filled[0].address) == ("Surrey", "9 Z St")


def test_fill_leaves_unknown_venue_unchanged() -> None:
    # Arrange
    book = VenueBook()
    event = _event("Mystery Room")

    # Act
    filled = book.fill([event])

    # Assert
    assert filled[0] == event


def test_learn_ignores_events_without_venue_or_city() -> None:
    # Arrange
    book = VenueBook()

    # Act
    book.learn([_event(None, city="Vancouver"), _event("Hall")])

    # Assert
    assert len(book) == 0


def test_learn_upgrades_entry_missing_address() -> None:
    # Arrange
    book = VenueBook()
    book.learn([_event("Hall", city="Vancouver")])

    # Act
    book.learn([_event("Hall", city="Vancouver", address="1 A St")])

    # Assert
    assert book.fill([_event("Hall")])[0].address == "1 A St"


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    # Arrange
    path = tmp_path / "venues.json"
    book = VenueBook()
    book.learn([_event("Hall", city="Vancouver", address="1 A St")])

    # Act
    book.save(path)
    loaded = VenueBook.load(path)

    # Assert
    assert loaded.fill([_event("Hall")])[0].city == "Vancouver"


def test_load_returns_empty_book_for_missing_file(tmp_path: Path) -> None:
    # Arrange, Act
    book = VenueBook.load(tmp_path / "absent.json")

    # Assert
    assert len(book) == 0


def test_load_returns_empty_book_for_corrupt_file(tmp_path: Path) -> None:
    # Arrange
    path = tmp_path / "venues.json"
    path.write_text("{not json", encoding="utf-8")

    # Act
    book = VenueBook.load(path)

    # Assert
    assert len(book) == 0


def test_load_skips_malformed_entries(tmp_path: Path) -> None:
    # Arrange
    path = tmp_path / "venues.json"
    path.write_text(json.dumps({"venues": {"hall": {"city": "Vancouver", "address": None}, "bad": "x"}}), encoding="utf-8")

    # Act
    book = VenueBook.load(path)

    # Assert
    assert len(book) == 1


def test_learn_ignores_events_without_street_address() -> None:
    # Arrange
    book = VenueBook()

    # Act
    book.learn([_event("Cafe on Victoria", city="Victoria")])

    # Assert
    assert len(book) == 0


TODAY = date(2026, 11, 7)


def test_needs_lookup_lists_unknown_city_venues_once_by_frequency() -> None:
    # Arrange
    book = VenueBook()
    book.learn([_event("Known Hall", city="Vancouver", address="1 A St")])
    events = [_event("Bar B"), _event("Bar A"), _event("Bar B"), _event("Known Hall"),
              _event("Has City", city="Surrey"), _event(None)]

    # Act
    names = book.needs_lookup(events, TODAY)

    # Assert
    assert names == ["Bar B", "Bar A"]


def test_needs_lookup_skips_recent_misses_and_retries_stale_ones() -> None:
    # Arrange
    book = VenueBook()
    book.record("Recent", None, date(2026, 11, 1))
    book.record("Stale", None, date(2026, 9, 1))

    # Act
    names = book.needs_lookup([_event("Recent"), _event("Stale")], TODAY)

    # Assert
    assert names == ["Stale"]


def test_record_stores_lookup_result_and_fill_uses_it() -> None:
    # Arrange
    book = VenueBook()

    # Act
    book.record("The Heatley", VenueInfo(city="Vancouver", address="696 E Hastings", origin="osm"), TODAY)

    # Assert
    assert book.fill([_event("Heatley")])[0].city == "Vancouver"


def test_fill_ignores_misses() -> None:
    # Arrange
    book = VenueBook()
    book.record("Nowhere", None, TODAY)

    # Act
    filled = book.fill([_event("Nowhere")])

    # Assert
    assert filled[0].city is None


def test_manual_entries_are_never_overwritten(tmp_path: Path) -> None:
    # Arrange
    path = tmp_path / "venues.json"
    path.write_text(json.dumps({"venues": {"hall": {"city": "Burnaby", "address": None, "origin": "manual"}}}))
    book = VenueBook.load(path)

    # Act
    book.learn([_event("Hall", city="Surrey", address="9 Z St")])
    book.record("Hall", VenueInfo(city="Delta", address=None, origin="osm"), TODAY)

    # Assert
    assert book.fill([_event("Hall")])[0].city == "Burnaby"


def test_source_data_replaces_lookup_results() -> None:
    # Arrange
    book = VenueBook()
    book.record("Hall", VenueInfo(city="Delta", address=None, origin="osm"), TODAY)

    # Act
    book.learn([_event("Hall", city="Surrey", address="9 Z St")])

    # Assert
    assert book.fill([_event("Hall")])[0].city == "Surrey"


def test_save_writes_attribution_origin_and_checked_date(tmp_path: Path) -> None:
    # Arrange
    path = tmp_path / "venues.json"
    book = VenueBook()
    book.record("The Heatley", VenueInfo(city="Vancouver", address=None, origin="osm"), TODAY)
    book.record("Nowhere", None, TODAY)

    # Act
    book.save(path)
    data = json.loads(path.read_text())

    # Assert
    assert "OpenStreetMap" in data["attribution"]
    assert data["venues"]["heatley"] == {
        "name": "The Heatley", "city": "Vancouver", "address": None, "origin": "osm", "checked": "2026-11-07",
    }
    assert data["venues"]["nowhere"]["origin"] == "miss"
    assert VenueBook.load(path).needs_lookup([_event("Nowhere")], TODAY) == []


def test_corrupt_file_is_never_overwritten(tmp_path: Path) -> None:
    # Arrange
    path = tmp_path / "venues.json"
    broken = '{"venues": {"hall": {"city": "Burnaby", "origin": "manual"},}}'
    path.write_text(broken, encoding="utf-8")
    book = VenueBook.load(path)
    book.learn([_event("Other", city="Vancouver", address="1 A St")])

    # Act
    book.save(path)

    # Assert
    assert path.read_text(encoding="utf-8") == broken


def test_load_rekeys_hand_written_entries() -> None:
    # Arrange
    raw = {"venues": {"The Rio Theatre": {"name": "The Rio Theatre", "city": "Vancouver", "origin": "manual"}}}

    # Act
    book = VenueBook.from_data(raw)

    # Assert
    assert book.fill([_event("Rio Theatre")])[0].city == "Vancouver"


@pytest.mark.parametrize("origin", ["source", "page", "manual"])
def test_record_never_replaces_published_or_manual_entries(origin: str) -> None:
    # Arrange
    book = VenueBook.from_data({"venues": {"hall": {"name": "Hall", "city": "Burnaby", "origin": origin}}})

    # Act
    book.record("Hall", VenueInfo(city="Delta", address=None, origin="osm"), TODAY)

    # Assert
    assert book.fill([_event("Hall")])[0].city == "Burnaby"


def test_record_miss_does_not_erase_a_hit() -> None:
    # Arrange
    book = VenueBook()
    book.record("Hall", VenueInfo(city="Delta", address=None, origin="osm"), TODAY)

    # Act
    book.record("Hall", None, TODAY)

    # Assert
    assert book.fill([_event("Hall")])[0].city == "Delta"


def test_record_replaces_stale_miss_with_hit() -> None:
    # Arrange
    book = VenueBook()
    book.record("Hall", None, date(2026, 1, 1))

    # Act
    book.record("Hall", VenueInfo(city="Delta", address=None, origin="osm"), TODAY)

    # Assert
    assert book.fill([_event("Hall")])[0].city == "Delta"


def test_venue_key_treats_curly_and_straight_apostrophes_alike() -> None:
    # Arrange, Act, Assert
    assert venue_key("Frankie’s Jazz Club") == venue_key("Frankie's Jazz Club") == "frankies jazz club"
