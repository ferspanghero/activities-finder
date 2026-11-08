"""Tests for src/timeparse.py: start-time parsing for sorting and comparison."""

import time

import pytest

from src.timeparse import (
    UNKNOWN_TIME,
    display_time,
    format_clock,
    parse_time_to_minutes,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("8:00 PM", 20 * 60),
        ("8:00PM", 20 * 60),
        ("7 pm", 19 * 60),
        ("11am", 11 * 60),
        ("12:00 AM", 0),
        ("12 pm", 12 * 60),
        ("10:30 pm - 1:59 am", 22 * 60 + 30),
        ("Saturday - 10:am - 5 pm", 10 * 60),
        ("19:00", 19 * 60),
        ("2-5 pm", 14 * 60),
        ("10 - 2 am", 22 * 60),
        ("11-1 pm", 11 * 60),
        ("12-3 pm", 12 * 60),
        ("Evening", UNKNOWN_TIME),
        ("", UNKNOWN_TIME),
        (None, UNKNOWN_TIME),
    ],
)
def test_parse_time_to_minutes_reads_first_clock_time(text: str | None, expected: int) -> None:
    # Arrange, Act
    result = parse_time_to_minutes(text)

    # Assert
    assert result == expected


@pytest.mark.parametrize(
    ("hour", "minute", "expected"),
    [(0, 0, "12:00 AM"), (9, 5, "9:05 AM"), (12, 30, "12:30 PM"), (23, 0, "11:00 PM")],
)
def test_format_clock_renders_12_hour_time(hour: int, minute: int, expected: str) -> None:
    # Arrange, Act
    result = format_clock(hour, minute)

    # Assert
    assert result == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("7 pm", "7:00 PM"),
        ("7:30PM", "7:30 PM"),
        ("19:00", "7:00 PM"),
        ("12 am", "12:00 AM"),
        ("1 pm - 1:45 pm", "1:00 PM - 1:45 PM"),
        ("9 am- 3 pm", "9:00 AM - 3:00 PM"),
        ("2-5 pm", "2:00 PM - 5:00 PM"),
        ("10:30 pm - 3 am", "10:30 PM - 3:00 AM"),
        ("12:00 PM to 4:00 PM", "12:00 PM - 4:00 PM"),
        ("8 a.m. – 11:55 p.m.", "8:00 AM - 11:55 PM"),
        ("8:00 to 11:00 PM", "8:00 PM - 11:00 PM"),
        ("7 to 9 pm", "7:00 PM - 9:00 PM"),
        ("  7 pm  ", "7:00 PM"),
        ("0:30", "12:30 AM"),
        ("19:00-21:30", "7:00 PM - 9:30 PM"),
    ],
)
def test_display_time_formats_times_and_ranges_alike(text: str, expected: str) -> None:
    # Arrange, Act
    shown = display_time(text)

    # Assert
    assert shown == expected


@pytest.mark.parametrize(
    "text",
    [
        "varies", "all day", "Open 5-9pm every night", "Saturday - 10:am - 5 pm", "7", "7 - 9", "25:00", "",
        "7:30", "7:30-9:00", "7 pm - 10:30", "9 pm - 12:00", "7:75 pm", "13:75",
    ],
)
def test_display_time_keeps_text_it_cannot_fully_read(text: str) -> None:
    # Arrange, Act
    shown = display_time(text)

    # Assert
    assert shown == text


def test_display_time_keeps_none() -> None:
    # Arrange, Act, Assert
    assert display_time(None) is None


def test_display_time_handles_long_whitespace_quickly() -> None:
    # Arrange
    text = "1" + " " * 50_000 + "x"

    # Act
    started = time.perf_counter()
    shown = display_time(text)
    elapsed = time.perf_counter() - started

    # Assert
    assert shown == text
    assert elapsed < 1.0
