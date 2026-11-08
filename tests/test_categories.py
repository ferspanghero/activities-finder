"""Tests for src/categories.py: activity-type mapping, classification, filtering."""

from datetime import date

import pytest

from src.categories import (
    CATEGORY_LABELS,
    categorize,
    filter_by_types,
    map_source_category,
    parse_types,
)
from src.models import Event


def _event(name: str, category: str | None = None, source: str = "Do604") -> Event:
    return Event(
        name=name, city=None, address=None, time=None,
        event_date=date(2026, 3, 7), source_name=source, source_url="u",
        category=category,
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Music", "music"),
        ("DJ/Parties", "music"),
        ("Theatre & Performing Arts", "theatre"),
        ("Comedy", "theatre"),
        ("Art & Culture", "art"),
        ("Festival", "festivals"),
        ("Food & Drink", "food"),
        ("Sports", "sports"),
        ("Sport", "sports"),
        ("Trivia", "trivia"),
        ("Family Event", "family"),
        ("kids-family", "family"),
        ("community", "community"),
        ("Storytimes", "family"),
        ("Event", None),
        ("", None),
        (None, None),
    ],
)
def test_map_source_category_maps_known_labels(raw: str | None, expected: str | None) -> None:
    # Arrange, Act
    result = map_source_category(raw)

    # Assert
    assert result == expected


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Tuesday Trivia Night", "trivia"),
        ("Fort Langley Farmers' Market", "community"),
        ("Diwali Celebration at Central City", "cultural"),
        ("Saturday Run Club", "outdoor"),
        ("Guided Hike to Quarry Rock", "outdoor"),
        ("Jade Music Fest", "festivals"),
        ("Phil Dwyer Quintet", "music"),
        ("Improv Roulette", "theatre"),
        ("Family Storytime", "family"),
        ("Untitled thing", None),
    ],
)
def test_categorize_falls_back_to_name_keywords(name: str, expected: str | None) -> None:
    # Arrange
    event = _event(name)

    # Act
    result = categorize(event)

    # Assert
    assert result == expected


def test_categorize_keeps_existing_category() -> None:
    # Arrange
    event = _event("Trivia at the Theatre", category="theatre")

    # Act
    result = categorize(event)

    # Assert
    assert result == "theatre"


def test_parse_types_accepts_keys_case_insensitively() -> None:
    # Arrange, Act
    result = parse_types("Music, trivia")

    # Assert
    assert result == {"music", "trivia"}


def test_parse_types_rejects_unknown_key() -> None:
    # Arrange, Act, Assert
    with pytest.raises(ValueError):
        parse_types("music,karaoke")


def test_filter_by_types_keeps_matching_categories_only() -> None:
    # Arrange
    events = [_event("A", "music"), _event("B", "food"), _event("C", None)]

    # Act
    result = filter_by_types(events, {"music"})

    # Assert
    assert [e.name for e in result] == ["A"]


def test_every_category_key_has_a_label() -> None:
    # Arrange
    expected_keys = {
        "music", "festivals", "sports", "art", "food", "outdoor",
        "community", "trivia", "theatre", "cultural", "family",
    }

    # Act, Assert
    assert set(CATEGORY_LABELS) == expected_keys
