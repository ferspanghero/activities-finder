"""Tests for src/parsers/dates.py: year inference for year-less dates."""

from datetime import date

import pytest

from src.parsers.dates import infer_year


@pytest.mark.parametrize(
    ("month", "day", "ref", "expected"),
    [
        (3, 7, date(2026, 3, 7), date(2026, 3, 7)),
        (1, 2, date(2026, 12, 30), date(2027, 1, 2)),
        (12, 30, date(2027, 1, 2), date(2026, 12, 30)),
        (6, 15, date(2026, 3, 7), date(2026, 6, 15)),
    ],
)
def test_infer_year_picks_date_closest_to_reference(month: int, day: int, ref: date, expected: date) -> None:
    # Arrange, Act
    result = infer_year(month, day, ref)

    # Assert
    assert result == expected


def test_infer_year_returns_none_for_impossible_date() -> None:
    # Arrange, Act
    result = infer_year(2, 30, date(2026, 3, 7))

    # Assert
    assert result is None


def test_infer_year_handles_leap_day_in_adjacent_year() -> None:
    # Arrange, Act
    result = infer_year(2, 29, date(2027, 12, 31))

    # Assert
    assert result == date(2028, 2, 29)
