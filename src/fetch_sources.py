"""Fetches event sources in parallel and returns raw HTML/JSON."""

import asyncio
import json
import logging
from datetime import date, timedelta

import aiohttp

from src.models import FetchResult

logger = logging.getLogger(__name__)


SOURCES = {
    "do604": {
        "name": "Do604",
        "url_template": "https://do604.com/events/{YYYY}/{MM}/{DD}",
        "per_day": True,
    },
    "dailyhive": {
        "name": "Daily Hive",
        "url_template": "https://dailyhive.com/vancouver/listed/events?after={from_date}&before={to_date}",
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
        "url_template": "https://theinfidelsjazz.ca/wp-json/tribe/events/v1/events/?start_date={from_date}&end_date={to_date}",
    },
    "bcaletrail": {
        "name": "BC Ale Trail",
        "url_template": "https://bcaletrail.ca/events/?date-start={from_date}&date-end={to_date}",
    },
}


def build_source_url(source_id: str, from_date: date, to_date: date) -> str:
    source = SOURCES[source_id]
    template = source["url_template"]
    return template.format(
        YYYY=f"{from_date.year:04d}",
        MM=f"{from_date.month:02d}",
        DD=f"{from_date.day:02d}",
        from_date=from_date.isoformat(),
        to_date=to_date.isoformat(),
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
    session: aiohttp.ClientSession, source_id: str, from_date: date, to_date: date
) -> FetchResult:
    source = SOURCES[source_id]
    name = source["name"]
    url = build_source_url(source_id, from_date, to_date)

    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            resp.raise_for_status()
            raw = await resp.text()
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        logger.warning("Fetch failed for %s: %s", name, e)
        return FetchResult(
            source_id=source_id,
            source_name=name,
            url=url,
            content=None,
            error=str(e),
            from_date=from_date,
            to_date=to_date,
        )

    content: str | dict
    if source_id == "infidelsjazz":
        try:
            content = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning("Invalid JSON from %s: %s", name, e)
            return FetchResult(
                source_id=source_id,
                source_name=name,
                url=url,
                content=None,
                error=f"Invalid JSON from {name}: {e}",
                from_date=from_date,
                to_date=to_date,
            )
    else:
        content = raw

    logger.debug("Fetched %s (%d bytes)", name, len(raw))
    return FetchResult(
        source_id=source_id,
        source_name=name,
        url=url,
        content=content,
        error=None,
        from_date=from_date,
        to_date=to_date,
    )


async def fetch_raw_sources(from_date: date, to_date: date) -> list[FetchResult]:
    """Fetch all sources and return raw HTML/JSON as FetchResult objects."""
    logger.info("Fetching %d sources for %s to %s", len(SOURCES), from_date, to_date)
    # Browser-like UA required — Daily Hive returns 0 events for bot-like User-Agents
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = []
        for source_id, source in SOURCES.items():
            if source.get("per_day"):
                d = from_date
                while d <= to_date:
                    tasks.append(_fetch_one_raw(session, source_id, d, d))
                    d += timedelta(days=1)
            else:
                tasks.append(_fetch_one_raw(session, source_id, from_date, to_date))
        results = await asyncio.gather(*tasks)
    succeeded = sum(1 for r in results if r.error is None)
    logger.info("Fetched %d/%d sources successfully", succeeded, len(results))
    return list(results)
