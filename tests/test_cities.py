"""Tests for src/cities.py: city normalization, detection, and filtering."""

from datetime import date

import pytest

from src.cities import (
    DEFAULT_CITIES,
    canonical_city,
    city_from_text,
    filter_by_cities,
    normalize_city,
    resolve_allowed_cities,
)
from src.models import Event


def _event(city: str | None, name: str = "E") -> Event:
    return Event(
        name=name, city=city, address=None, time=None,
        event_date=date(2026, 3, 7), source_name="S", source_url="u",
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Vancouver", "vancouver"),
        ("  VANCOUVER ", "vancouver"),
        ("North Vancouver (City)", "north vancouver"),
        ("Langley (Township)", "langley"),
        ("Langley Township", "langley"),
        ("Vancouver, BC", "vancouver"),
        ("Port  Moody", "port moody"),
    ],
)
def test_normalize_city_canonicalizes_variants(raw: str, expected: str) -> None:
    # Arrange, Act
    result = normalize_city(raw)

    # Assert
    assert result == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Central City, King George Boulevard, Surrey, BC, Canada", "Surrey"),
        ("City of Burnaby", "Burnaby"),
        ("MONOVA: Museum of North Vancouver, Esplanade West, North Vancouver, BC", "North Vancouver"),
        ("Granville Island, Vancouver, BC, Canada", "Vancouver"),
        ("West Vancouver", "West Vancouver"),
        ("Various Locations", None),
        ("", None),
        (None, None),
    ],
)
def test_city_from_text_prefers_longest_known_city(text: str | None, expected: str | None) -> None:
    # Arrange, Act
    result = city_from_text(text)

    # Assert
    assert result == expected


def test_resolve_allowed_cities_defaults_to_default_list() -> None:
    # Arrange, Act
    allowed, keep_unknown = resolve_allowed_cities(None, None)

    # Assert
    assert allowed == {normalize_city(c) for c in DEFAULT_CITIES}
    assert keep_unknown is True


def test_resolve_allowed_cities_additive_extends_default_list() -> None:
    # Arrange, Act
    allowed, keep_unknown = resolve_allowed_cities(None, "Whistler, Victoria")

    # Assert
    assert {"whistler", "victoria", "vancouver"} <= allowed
    assert keep_unknown is True


def test_resolve_allowed_cities_override_replaces_list_and_drops_unknown() -> None:
    # Arrange, Act
    allowed, keep_unknown = resolve_allowed_cities("Port Moody", None)

    # Assert
    assert allowed == {"port moody"}
    assert keep_unknown is False


def test_resolve_allowed_cities_rejects_both_modes() -> None:
    # Arrange, Act, Assert
    with pytest.raises(ValueError):
        resolve_allowed_cities("Vancouver", "Whistler")


def test_filter_by_cities_matches_normalized_names() -> None:
    # Arrange
    events = [_event("Langley"), _event("North Vancouver"), _event("Kelowna")]
    allowed, keep_unknown = resolve_allowed_cities(None, None)

    # Act
    result = filter_by_cities(events, allowed, keep_unknown)

    # Assert
    assert [e.city for e in result] == ["Langley", "North Vancouver"]


def test_filter_by_cities_keeps_unknown_city_when_requested() -> None:
    # Arrange
    events = [_event(None), _event("Vancouver")]

    # Act
    result = filter_by_cities(events, {"vancouver"}, keep_unknown=True)

    # Assert
    assert len(result) == 2


def test_filter_by_cities_drops_unknown_city_in_override_mode() -> None:
    # Arrange
    events = [_event(None), _event("Vancouver")]

    # Act
    result = filter_by_cities(events, {"vancouver"}, keep_unknown=False)

    # Assert
    assert [e.city for e in result] == ["Vancouver"]


def test_filter_by_cities_returns_empty_for_empty_input() -> None:
    # Arrange, Act
    result = filter_by_cities([], {"vancouver"}, keep_unknown=True)

    # Assert
    assert result == []


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("Fort Langley", "langley"), ("Tsawwassen", "delta"), ("Ladner", "delta"), ("Deep Cove", "north vancouver")],
)
def test_normalize_city_folds_communities_into_their_municipality(raw: str, expected: str) -> None:
    # Arrange, Act
    result = normalize_city(raw)

    # Assert
    assert result == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("vancouver", "Vancouver"),
        ("Surrey, BC", "Surrey"),
        ("Langley Township", "Langley"),
        ("Fort Langley", "Langley"),
        ("NORTH VANCOUVER", "North Vancouver"),
        ("Gibsons", "Gibsons"),
        ("gibsons, bc", "Gibsons"),
    ],
)
def test_canonical_city_returns_display_name(raw: str, expected: str) -> None:
    # Arrange, Act
    result = canonical_city(raw)

    # Assert
    assert result == expected


@pytest.mark.parametrize("text", ["Cafe on Victoria Drive", "123 Richmond Street", "Burnaby St Lounge"])
def test_city_from_text_ignores_street_names(text: str) -> None:
    # Arrange, Act, Assert
    assert city_from_text(text) is None
