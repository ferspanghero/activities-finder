# Activities Searcher

An automated tool that aggregates event listings from curated Metro Vancouver sources, filters by date/city/activity type, and presents a consolidated table.

Read `README.md` for full project description and architecture.

## Project Structure

- `src/` — deterministic extraction pipeline (models, parsers, renderers, fetch, CLI)
- `tests/` — pytest test suites (including `test_parsers/`, `test_renderers/`, `fixtures/`)
- `project_files/` — project documentation (v1/, v2/, v3/, v4/ subdirectories + backlog)
- `.claude/commands/` — slash command definitions

## Key Files

- `src/models.py` — `Event`, `FetchResult`, `SourceStatus` dataclasses
- `src/pipeline.py` — orchestrator: fetch → parse → aggregate
- `src/parsers/` — source-specific parsers (do604, dailyhive, rhythmchanges, showhub, infidelsjazz)
- `src/renderers/` — markdown and HTML renderers
- `src/fetch_sources.py` — async parallel fetcher (raw HTML/JSON)
- `src/__main__.py` — CLI entry point for `python3 -m src`
- `.claude/commands/find-activities.md` — `/find-activities` slash command definition
- `pytest.ini` — test configuration

## Commands

- `python3 -m src --date YYYY-MM-DD [--format markdown|html] [--output FILE]` — deterministic pipeline
- `pytest` — run all tests
- `pytest -m "not integration"` — run unit tests only

## Default City List

Vancouver, Burnaby, New Westminster, Richmond, North Vancouver (City), Lynn Valley, Deep Cove, West Vancouver, Horseshoe Bay, Surrey, White Rock, Port Moody, Port Coquitlam, Coquitlam, Langley (City), Langley (Township), Delta, Pitt Meadows, Maple Ridge, Mission, Abbotsford, Chilliwack, Squamish, Anmore, Belcarra

### City Modes

1. **Default** — No cities specified → use the full list above
2. **Additive** — User says "also include [cities]" → add to the default list
3. **Override** — User says "only [cities]" → replace the default list entirely

Examples:
- "What's happening today?" → default (all cities)
- "What's happening today, also include Whistler" → additive
- "What's happening in Port Moody only" → override (only Port Moody)

## Activity Types

1. Live music
2. Festivals
3. Sports events
4. Art exhibitions / gallery openings
5. Food/drink events (tastings, markets)
6. Outdoor activities (hikes, group runs)
7. Community events (markets, fairs)
8. Trivia nights / pub events

Default: search all types. User narrows by specifying types in their query.

## Sources

Curated sources fetched and parsed by the `src/` pipeline. No broad web search.

### Source 1: Do604
- **Type:** Local aggregator (all event types)
- **Strategy:** HTML scrape
- **URL pattern:** `https://do604.com/events/{YYYY}/{MM}/{DD}`
- **Date in URL:** Yes — returns only events for the target date
- **Fields:** Event name, venue, city, time

### Source 2: Daily Hive Vancouver
- **Type:** Local aggregator (all event types)
- **Strategy:** Parse `__NEXT_DATA__` JSON embedded in HTML
- **URL pattern:** `https://dailyhive.com/vancouver/listed/events?after={date}&before={date}`
- **Date in URL:** Yes — returns events overlapping the target date
- **Fields:** Event name, venue, city, date range
- **Note:** Returns multi-day events. Parser filters to events spanning the target date.

### Source 3: Rhythm Changes
- **Type:** Jazz & live music listings
- **Strategy:** HTML scrape
- **URL pattern:** `https://rhythmchanges.ca/gigs/`
- **Date in URL:** No — page lists an entire month organized by week (Sun-Sat). The script notes which week the target date falls in.
- **Fields:** Event name, venue, date, time

### Source 4: ShowHub
- **Type:** Local live music & shows
- **Strategy:** HTML scrape
- **URL pattern:** `https://showhub.ca/weekly-listings/`
- **Date in URL:** No — page lists an entire week. Filter by target date from content.
- **Fields:** Event name, venue, date, time

### Source 5: Infidels Jazz
- **Type:** Jazz events
- **Strategy:** WordPress REST API (JSON)
- **URL pattern:** `https://theinfidelsjazz.ca/wp-json/tribe/events/v1/events/?start_date={date}&end_date={date}`
- **Date in URL:** Yes — returns only events on the target date
- **Fields:** Event name, venue, city, address, time, ticket price, description, event URL

## Behavior Rules

- Be exhaustive: process ALL source sections from the script output, don't stop early
- Include both free and ticketed events
- Note if venues are closed due to holidays
- Search for both scheduled events AND regular recurring programming
- Date filtering is exact (only the specified date, default today)
- If a source section shows an ERROR, note it and continue with remaining sources

## Output Format

### Summary header
```
Found X events across Y cities from Z sources
```

### Event table
| Event Name | City | Exact Address | Time | Source Link |
|---|---|---|---|---|

### Sources checked footer
```
Sources checked: Do604 (12), Daily Hive (8), Rhythm Changes (ERROR: ...), ShowHub (6), Infidels Jazz (1)
```

### Output files
- `--format html` → `events-YYYY-MM-DD.html` — self-contained HTML with sortable columns and clickable links. Generated by `src/renderers/html_renderer.py`.
- `--format markdown` → `events-YYYY-MM-DD.md` — markdown table. Generated by `src/renderers/markdown_renderer.py`.
