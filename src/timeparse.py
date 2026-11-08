"""Parse free-form event time strings ('7 pm', '10:30 pm - 1:59 am', '19:00') for sorting and display."""

import re

UNKNOWN_TIME = 9999
# Sort key for events without a readable time; the report's Time column sorts on it too.
UNTIMED_SORT_KEY = -1

_TOKEN_RE = re.compile(r"(?<!\d)(\d{1,2})(?::(\d{2}))?:?\s*(?:([ap])\.?\s*m\b\.?)?", re.IGNORECASE)
# A bare start hour borrows the meridiem of a range end: '2-5 pm' starts at 2 PM.
# A start hour above the end hour crosses noon or midnight: '10 - 2 am' starts at 10 PM.
_RANGE_END_RE = re.compile(r"\s*(?:[-–]|to)\s*(\d{1,2})(?::\d{2})?\s*([ap])\.?\s*m\b", re.IGNORECASE)


def parse_time_to_minutes(text: str | None) -> int:
    """Minutes since midnight of the first clock time in `text`, or UNKNOWN_TIME."""
    if not text:
        return UNKNOWN_TIME

    m = _TOKEN_RE.search(text)

    if not m:
        return UNKNOWN_TIME

    hour = int(m.group(1))
    minute = int(m.group(2) or 0)
    meridiem = m.group(3)

    if not meridiem and (borrowed := _RANGE_END_RE.match(text, m.end())):
        end_meridiem = borrowed.group(2).lower()
        crosses = hour % 12 > int(borrowed.group(1)) % 12
        meridiem = {"a": "p", "p": "a"}[end_meridiem] if crosses else end_meridiem

    if minute > 59:
        return UNKNOWN_TIME

    if meridiem:
        if not 1 <= hour <= 12:
            return UNKNOWN_TIME

        return (hour % 12 + (12 if meridiem.lower() == "p" else 0)) * 60 + minute

    if m.group(2) is not None and hour <= 23:
        return hour * 60 + minute

    return UNKNOWN_TIME


def sort_minutes(text: str | None) -> int:
    """Sort key for a start time: events without a readable time come first."""
    minutes = parse_time_to_minutes(text)

    return UNTIMED_SORT_KEY if minutes == UNKNOWN_TIME else minutes


def format_clock(hour: int, minute: int) -> str:
    """Format a 24-hour clock time as '7:30 PM'."""
    suffix = "AM" if hour < 12 else "PM"

    return f"{hour % 12 or 12}:{minute:02d} {suffix}"


_CLOCK = r"(\d{1,2})(?::\d{2})?(?:\s*([ap])\.?\s*m\b\.?)?"
_SINGLE_RE = re.compile(_CLOCK, re.IGNORECASE)
_RANGE_RE = re.compile(rf"{_CLOCK}\s*(?:[-–]|to)\s*{_CLOCK}", re.IGNORECASE)


def _clock(minutes: int) -> str:
    return format_clock(*divmod(minutes, 60))


def _unambiguous(hour: str, meridiem: str | None) -> bool:
    """A bound reads as one clock time: it has AM/PM, or a 24-hour hour no 12-hour clock uses."""
    return bool(meridiem) or int(hour) == 0 or int(hour) >= 13


def display_time(text: str | None) -> str | None:
    """A time or range in one style ('7:00 PM', '1:00 PM - 1:45 PM'); other text is returned as is.

    A bound that could be morning or evening ('7:30') keeps the original text rather than a guess.
    """
    if not text:
        return text

    stripped = text.strip()

    single = _SINGLE_RE.fullmatch(stripped)

    if single and _unambiguous(*single.groups()) and (start := parse_time_to_minutes(stripped)) != UNKNOWN_TIME:
        return _clock(start)

    if m := _RANGE_RE.fullmatch(stripped):
        start_hour, start_meridiem, end_hour, end_meridiem = m.groups()
        # A bare start borrows the end's AM/PM ('7 to 9 pm'); a bare end borrows nothing.
        readable = _unambiguous(end_hour, end_meridiem) and (end_meridiem or _unambiguous(start_hour, start_meridiem))
        start, end = parse_time_to_minutes(stripped), parse_time_to_minutes(stripped[m.start(3):])

        if readable and UNKNOWN_TIME not in (start, end):
            return f"{_clock(start)} - {_clock(end)}"

    return text
