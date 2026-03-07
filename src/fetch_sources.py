"""Fetches event sources in parallel and returns raw HTML/JSON."""

import asyncio
import json
from datetime import date

import aiohttp

from src.models import FetchResult


SOURCES = {
    "do604": {
        "name": "Do604",
        "url_template": "https://do604.com/events/{YYYY}/{MM}/{DD}",
    },
    "dailyhive": {
        "name": "Daily Hive",
        "url_template": "https://dailyhive.com/vancouver/listed/events?after={date}&before={date}",
    },
    "rhythmchanges": {
        "name": "Rhythm Changes",
        "url_template": "https://rhythmchanges.ca/gigs/",
    },
    "showhub": {
        "name": "ShowHub",
        "url_template": "https://showhub.ca/weekly-listings/",
    },
    "infidelsjazz": {
        "name": "Infidels Jazz",
        "url_template": "https://theinfidelsjazz.ca/wp-json/tribe/events/v1/events/?start_date={date}&end_date={date}",
    },
}


def build_source_url(source_id: str, target_date: date) -> str:
    source = SOURCES[source_id]
    template = source["url_template"]
    return template.format(
        YYYY=f"{target_date.year:04d}",
        MM=f"{target_date.month:02d}",
        DD=f"{target_date.day:02d}",
        date=target_date.isoformat(),
    )


def calculate_week_number(target_date: date) -> int:
    """Calculate which Sun-Sat week of the month a date falls in.

    Week 1 starts on the 1st regardless of day-of-week and runs until
    the first Saturday. Subsequent weeks run Sunday through Saturday.

    Example for March 2026 (starts on Sunday):
      Week 1: Mar 1-7 (Sun-Sat)
      Week 2: Mar 8-14, Week 3: Mar 15-21, etc.

    Example for a month starting on Wednesday:
      Week 1: 1st-4th (Wed-Sat), Week 2: 5th-11th (Sun-Sat), etc.
    """
    first_of_month = target_date.replace(day=1)
    first_day_weekday = first_of_month.weekday()  # Mon=0..Sun=6

    # Last day (inclusive) of week 1 = first Saturday of the month
    if first_day_weekday == 6:  # Month starts on Sunday
        last_day_of_week1 = 7   # Full Sun-Sat week
    else:
        last_day_of_week1 = 6 - first_day_weekday  # Days until Saturday

    if target_date.day <= last_day_of_week1:
        return 1

    days_past_week1 = target_date.day - last_day_of_week1 - 1
    return 2 + days_past_week1 // 7


async def _fetch_one_raw(
    session: aiohttp.ClientSession, source_id: str, target_date: date
) -> FetchResult:
    source = SOURCES[source_id]
    name = source["name"]
    url = build_source_url(source_id, target_date)

    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            resp.raise_for_status()
            raw = await resp.text()
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        return FetchResult(
            source_id=source_id,
            source_name=name,
            url=url,
            content=None,
            error=str(e),
            target_date=target_date,
        )

    content: str | dict
    if source_id == "infidelsjazz":
        try:
            content = json.loads(raw)
        except json.JSONDecodeError as e:
            return FetchResult(
                source_id=source_id,
                source_name=name,
                url=url,
                content=None,
                error=f"Invalid JSON from {name}: {e}",
                target_date=target_date,
            )
    else:
        content = raw

    return FetchResult(
        source_id=source_id,
        source_name=name,
        url=url,
        content=content,
        error=None,
        target_date=target_date,
    )


async def fetch_raw_sources(target_date: date) -> list[FetchResult]:
    """Fetch all sources and return raw HTML/JSON as FetchResult objects."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = [
            _fetch_one_raw(session, source_id, target_date)
            for source_id in SOURCES
        ]
        return await asyncio.gather(*tasks)
