# Implementation Plan

## Architecture

Hybrid approach: a Python script fetches all sources in parallel and outputs raw markdown content to stdout. A Claude Code slash command runs the script, reads the output, and extracts/filters/formats events.

```
/find-activities "March 7, only Vancouver, live music"
  → Claude parses parameters (date, cities, activity types)
  → Claude runs: python3 scripts/fetch_sources.py --date 2026-03-07
  → Script fetches all 5 sources in parallel, converts HTML→markdown, outputs to stdout
  → Claude reads stdout, extracts events, filters by city/type, formats output table
```

## Output

Three deliverables:
- `scripts/fetch_sources.py` — Python script that fetches all sources in parallel and outputs raw content
- `CLAUDE.md` — Agent configuration (cities, activity types, sources, behavior rules)
- `.claude/commands/find-activities.md` — Slash command that runs the script, extracts events, filters, and formats output

---

## Step 1: CLAUDE.md — Default City List

Define the curated Metro Vancouver city list that serves as the default search scope:

```
Vancouver, Burnaby, New Westminster, Richmond, North Vancouver (City),
Lynn Valley, Deep Cove, West Vancouver, Horseshoe Bay, Surrey, White Rock,
Port Moody, Port Coquitlam, Coquitlam, Langley (City), Langley (Township),
Delta, Pitt Meadows, Maple Ridge, Mission, Abbotsford, Chilliwack, Squamish,
Anmore, Belcarra
```

Document the three city modes:
1. No cities specified -> use full default list
2. User says "also include [cities]" -> add to default list
3. User says "only [cities]" -> replace default list entirely

---

## Step 2: CLAUDE.md — Activity Types

Define the 8 activity categories:

1. Live music
2. Festivals
3. Sports events
4. Art exhibitions / gallery openings
5. Food/drink events (tastings, markets)
6. Outdoor activities (hikes, group runs)
7. Community events (markets, fairs)
8. Trivia nights / pub events

Default behavior: search all types. User narrows by specifying types in their query.

---

## Step 3: CLAUDE.md — Source List

5 curated sources. Each source is fetched by the Python script (`scripts/fetch_sources.py`). No broad web search.

For all URL patterns below, `{YYYY}`, `{MM}`, and `{DD}` are replaced with the target date values.

---

### Source 1: Do604

- **Type:** Local aggregator (all event types)
- **Strategy:** HTML scrape
- **URL pattern:** `https://do604.com/events/{YYYY}/{MM}/{DD}`
- **Date filtering:** Built into URL — returns only events for the target date
- **Date in URL:** Yes
- **Fields available:** Event name, venue, city, time
- **Example:** `https://do604.com/events/2026/03/07`

---

### Source 2: Daily Hive Vancouver

- **Type:** Local aggregator (all event types)
- **Strategy:** HTML scrape
- **URL pattern:** `https://dailyhive.com/vancouver/listed/events?after={YYYY}-{MM}-{DD}&before={YYYY}-{MM}-{DD}`
- **Date filtering:** Built into URL query params — returns events overlapping the target date
- **Date in URL:** Yes
- **Fields available:** Event name, venue, city, date range
- **Note:** Returns multi-day events that span the target date, not just single-day events. Agent must check if the event actually occurs on the target date.
- **Example:** `https://dailyhive.com/vancouver/listed/events?after=2026-03-07&before=2026-03-07`

---

### Source 3: Rhythm Changes

- **Type:** Jazz & live music listings
- **Strategy:** HTML scrape
- **URL pattern:** `https://rhythmchanges.ca/gigs/`
- **Date filtering:** Not in URL — page lists an entire month of gigs organized by week (Sun-Sat). The script calculates which week the target date falls in and notes it in the output header so Claude can focus on the right section.
- **Date in URL:** No (static URL)
- **Week sections on page:** Week 1 (Sun Mar 1 – Sat Mar 7), Week 2 (Sun Mar 8 – Sat Mar 14), etc.
- **Fields available:** Event name, venue, city, date, time
- **Example:** `https://rhythmchanges.ca/gigs/`

---

### Source 4: ShowHub

- **Type:** Local live music & shows
- **Strategy:** HTML scrape
- **URL pattern:** `https://showhub.ca/weekly-listings/`
- **Date filtering:** Not in URL — page lists an entire week of shows. Agent must filter events by the target date from the page content.
- **Date in URL:** No (static URL)
- **Fields available:** Event name, venue, city, date, time
- **Example:** `https://showhub.ca/weekly-listings/`

---

### Source 5: Infidels Jazz

- **Type:** Jazz events
- **Strategy:** WordPress REST API (JSON) — the HTML pages are JS-rendered and return empty shells, so we use the API directly
- **URL pattern:** `https://theinfidelsjazz.ca/wp-json/tribe/events/v1/events/?start_date={YYYY}-{MM}-{DD}&end_date={YYYY}-{MM}-{DD}`
- **Date filtering:** Built into URL query params — returns only events on the target date
- **Date in URL:** Yes
- **Fields available:** Event name, venue, city, address, time, ticket price, description, event URL
- **Example:** `https://theinfidelsjazz.ca/wp-json/tribe/events/v1/events/?start_date=2026-03-07&end_date=2026-03-07`

---

### Dropped sources

- **vancouversbestplaces.com** — JS-rendered HTML returns no content; WP REST API (`/wp-json/wp/v2/posts`) returns editorial blog posts (e.g., "Spring Break guide"), not structured event listings. Not useful for individual event extraction.

---

## Step 4: CLAUDE.md — Behavior Rules

- Be exhaustive: check ALL sources, don't stop early
- Include both free and ticketed events
- Note if venues are closed due to holidays
- Search for both scheduled events AND regular recurring programming
- Date filtering is exact (only the specified date, default today)
- If a source is unreachable, note it and continue with remaining sources

---

## Step 5: CLAUDE.md — Output Format

Define the output table format:

```
| Event Name | City | Exact Address | Time | Source Link |
|---|---|---|---|---|
```

---

## Step 6: Fetch Script — `scripts/fetch_sources.py`

Python script that fetches all sources in parallel.

**Input:** `--date YYYY-MM-DD` (required)

**Dependencies:** `aiohttp`, `html2text` (listed in `requirements.txt`; test deps: `pytest`, `pytest-asyncio`, `aioresponses`)

**Behavior:**
- Construct source URLs from the target date using the patterns in Step 3
- Fetch all 5 sources concurrently with asyncio/aiohttp
- Convert HTML responses to markdown via html2text
- For Infidels Jazz (JSON API): format the JSON response as readable text (event name, venue, time, etc.)
- For Rhythm Changes: calculate which week section the target date falls in and note it in the output header
- Print each source's content to stdout with clear delimiters:
  ```
  === SOURCE: Do604 (https://do604.com/events/2026/03/07) ===
  [markdown content]

  === SOURCE: Daily Hive (...) ===
  [markdown content]
  ```
- If a source fails, print error instead of content:
  ```
  === SOURCE: Do604 (ERROR: Connection timeout) ===
  ```
- Exit 0 even if some sources fail (partial results are fine)

---

## Step 7: Slash Command — Parameter Parsing

`.claude/commands/find-activities.md` starts by instructing Claude to parse:

- **Date**: from user query, default to today's date
- **Cities**: determine mode (default / additive / override) based on user phrasing
- **Activity types**: from user query, default to all types

---

## Step 8: Slash Command — Run Fetch Script

Run `python3 scripts/fetch_sources.py --date {YYYY-MM-DD}` and read the stdout output.

---

## Step 9: Slash Command — Event Extraction

For each source section in the script output:
1. Parse the content to identify individual events
2. Extract: event name, location/city, exact address (if available), time, event page URL
3. Categorize by activity type based on content

---

## Step 10: Slash Command — Filtering

Apply filters in order:
1. **Date**: keep only events matching the target date exactly (for sources without date-filtered URLs)
2. **City**: keep only events in the resolved city list
3. **Activity type**: if specified, keep only matching categories

---

## Step 11: Slash Command — Output

Format results as the markdown table. Group by city if results span multiple cities. Include:
- Summary line: "Found X events across Y cities from Z sources"
- The table
- Notes about any unreachable sources
- Notes about any venues closed for holidays

---

## Step 12: Fetch Script Tests

Tests for `scripts/fetch_sources.py` using pytest. Test file: `tests/test_fetch_sources.py`.

### Unit tests (no network)

- **URL construction**: Given a date, assert correct URL for each of the 5 sources
- **Rhythm Changes week calculation**: Given dates across different weeks (Mar 1, Mar 8, Mar 15, Mar 29), assert correct week number
- **Output delimiters**: Assert each source section starts with `=== SOURCE: Name (url) ===`
- **Infidels Jazz JSON formatting**: Given sample API JSON response, assert readable text output with event name, venue, time
- **HTML→markdown conversion**: Given sample HTML snippet, assert clean markdown output

### Unit tests (mocked HTTP)

- **Parallel fetching**: Mock aiohttp responses for all 5 sources, assert all are fetched and output contains 5 sections
- **Partial failure**: Mock 1 source as unreachable (timeout/connection error), assert output contains error for that source and content for the other 4
- **All sources down**: Mock all sources failing, assert output has 5 error sections and script exits 0

### Integration test (hits real sources, slow)

- **End-to-end**: Run script with a known date, assert output contains all 5 source sections with non-empty content (or expected errors)
- Mark with `@pytest.mark.integration` so it can be skipped in fast runs

---

## Future Enhancements (not v1)

- Deduplication command/skill — separate pass to tidy up the raw table, merge duplicates across sources
- Custom MCP server for caching and programmatic dedup
- Add general aggregators (Eventbrite, Ticketmaster, SeatGeek, Bandsintown)
- Add more local sources (venue websites, city tourism pages)
- Save results to file for reference
- Date range support ("this weekend", "next 7 days")
- Explore source URL subsections for targeted fetching (e.g., do604.com/events/music/today instead of do604.com)
