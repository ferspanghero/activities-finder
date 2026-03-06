"""Fetches event sources in parallel and outputs raw markdown content."""

import asyncio
import json
from datetime import date

import aiohttp
import html2text


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


def calculate_week_number(target_date: date) -> int:
    """Calculate which Sun-Sat week of the month a date falls in.

    Week 1 starts on the 1st of the month regardless of day-of-week.
    Subsequent weeks start on Sunday.
    """
    first_of_month = target_date.replace(day=1)
    # Find the first Sunday after (or on) day 2
    # Days until first Sunday: (6 - weekday) % 7 where weekday is Mon=0..Sun=6
    first_day_weekday = first_of_month.weekday()  # Mon=0..Sun=6
    if first_day_weekday == 6:
        # Month starts on Sunday — week 1 is just day 1? No, week 1 is the full Sun-Sat
        # Actually: Week 1 starts on the 1st. Next week starts next Sunday.
        # If the 1st is Sunday, week 2 starts on the 8th.
        days_to_next_sunday = 7
    else:
        # Days from the 1st until the next Sunday
        days_to_next_sunday = 6 - first_day_weekday

    first_week_end_day = 1 + days_to_next_sunday - 1  # last day of week 1 (Saturday)

    if target_date.day <= first_week_end_day:
        return 1

    # After week 1, each week is 7 days starting from the next Sunday
    days_past_week1 = target_date.day - first_week_end_day - 1
    return 2 + days_past_week1 // 7


def format_source_output(
    name: str, url: str, content: str | None, error: str | None = None, week_hint: str | None = None
) -> str:
    if error:
        return f"=== SOURCE: {name} (ERROR: {error}) ==="
    header = f"=== SOURCE: {name} ({url}) ==="
    parts = [header]
    if week_hint:
        parts.append(week_hint)
    parts.append(content)
    return "\n".join(parts)


def format_infidelsjazz_json(data: dict) -> str:
    events = data.get("events", [])
    if not events:
        return "No events found."
    lines = []
    for event in events:
        venue_info = event.get("venue", {})
        lines.append(f"Event: {event.get('title', 'Unknown')}")
        lines.append(f"  Venue: {venue_info.get('venue', 'Unknown')}")
        if venue_info.get("address"):
            lines.append(f"  Address: {venue_info['address']}")
        if venue_info.get("city"):
            lines.append(f"  City: {venue_info['city']}")
        if event.get("start_date"):
            lines.append(f"  Time: {event['start_date']}")
        if event.get("cost"):
            lines.append(f"  Cost: {event['cost']}")
        if event.get("url"):
            lines.append(f"  URL: {event['url']}")
        lines.append("")
    return "\n".join(lines)


def build_source_url(source_id: str, target_date: date) -> str:
    source = SOURCES[source_id]
    template = source["url_template"]
    return template.format(
        YYYY=f"{target_date.year:04d}",
        MM=f"{target_date.month:02d}",
        DD=f"{target_date.day:02d}",
        date=target_date.isoformat(),
    )


def _convert_html_to_markdown(html_content: str) -> str:
    converter = html2text.HTML2Text()
    converter.ignore_links = False
    converter.ignore_images = True
    converter.body_width = 0
    return converter.handle(html_content)


async def _fetch_one_source(
    session: aiohttp.ClientSession, source_id: str, target_date: date
) -> str:
    source = SOURCES[source_id]
    name = source["name"]
    url = build_source_url(source_id, target_date)

    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            resp.raise_for_status()
            raw = await resp.text()

        if source_id == "infidelsjazz":
            data = json.loads(raw)
            content = format_infidelsjazz_json(data)
        else:
            content = _convert_html_to_markdown(raw)

        week_hint = None
        if source_id == "rhythmchanges":
            week_num = calculate_week_number(target_date)
            week_hint = f"Target date falls in Week {week_num}. Focus on events in that week section."

        return format_source_output(name, url, content, week_hint=week_hint)

    except Exception as e:
        return format_source_output(name, url, None, error=str(e))


async def fetch_all_sources(target_date: date) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ActivitiesSearcher/1.0)"}
    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = [
            _fetch_one_source(session, source_id, target_date)
            for source_id in SOURCES
        ]
        results = await asyncio.gather(*tasks)
    return "\n\n".join(results)


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Fetch event sources for a given date")
    parser.add_argument("--date", required=True, help="Target date in YYYY-MM-DD format")
    args = parser.parse_args()

    try:
        target_date = date.fromisoformat(args.date)
    except ValueError:
        print(f"Error: Invalid date format '{args.date}'. Use YYYY-MM-DD.", file=sys.stderr)
        sys.exit(1)

    print(asyncio.run(fetch_all_sources(target_date)))
