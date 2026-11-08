# Activities Searcher

An automated tool that aggregates event listings from curated Metro Vancouver sources, filters by date/city/activity type, and presents a consolidated table.

Read `README.md` for full project description and architecture.

## Project Structure

- `src/` — deterministic extraction pipeline (models, parsers, renderers, fetch, CLI)
- `tests/` — pytest test suites (including `test_parsers/`, `test_renderers/`, `fixtures/`)
- `project_files/` — project documentation (v1/, v2/, v3/, v4/, v5/ subdirectories + backlog)
- `.claude/commands/` — slash command definitions

## Key Files

- `src/models.py`: `Event`, `FetchResult`, `SourceStatus` dataclasses
- `src/sources.py`: source registry (URL template, parser, per-day vs range, pagination mode, page cap, concurrency, health-check hooks). Add a source here plus a parser in `src/parsers/`.
- `src/pipeline.py`: orchestrator: fetch, parse, health warnings, venue lookup, categorize
- `src/fetch_sources.py`: async paginated fetcher (global + per-source concurrency, retry with backoff)
- `src/cli_utils.py`: shared filter, sort, dedup flow used by both CLIs
- `src/cities.py`, `src/categories.py`: default city list and city matching; activity-type keys and mapping
- `src/dedup.py`: deterministic duplicate merging
- `src/venues.py`, `src/geocode.py`, `data/venues.json`: venue book (venue to city/address); event-page and OpenStreetMap lookups for venues without a city; the local book file (gitignored)
- `src/parsers/`: one parser per source; `src/renderers/`: markdown and HTML renderers
- `src/__main__.py`, `src/compact.py`: one-shot CLI; two-step CLI used by the slash command
- `.claude/commands/find-activities.md`: `/find-activities` slash command definition
- `pytest.ini`, `pyproject.toml`: test markers; coverage and ruff settings

## Commands

- `python3 -m src --from YYYY-MM-DD --to YYYY-MM-DD [--format markdown|html] [--output FILE] [--cities A,B | --add-cities A,B] [--types music,food]`: one-shot pipeline (max 14 day range; use same date for single day)
- `python3 -m src.compact fetch --from ... --to ... [filters]` then `python3 -m src.compact render .events-cache.json [--exclude 3,9]`: two-step flow with duplicate review
- `pytest -m "not integration"`: unit tests (offline)
- `pytest -m e2e`: Playwright tests of the HTML report's filter bar (headless Chromium; `pip install --user playwright && python3 -m playwright install chromium`)
- `pytest -m integration`: live canary against every real source for today
- `pytest -m "not integration" --cov --cov-report=term-missing`: coverage (line and branch)
- `ruff check src tests` and `mypy src --ignore-missing-imports`: lint and typecheck

## Gotchas

- Python 3.10: catch `asyncio.TimeoutError`, not the builtin `TimeoutError` (different classes before 3.11). Ruff is pinned to `py310` so its autofix does not rewrite this.
- Eventbrite rate-limits by IP (429). It is fetched as one range query at concurrency 2; avoid repeated live runs in quick succession.
- A source that returns 0 events from a successful fetch gets a `WARNING` in the footer: usually a layout change. Refresh the fixture in `tests/fixtures/` from the live page and fix the parser.
- `data/venues.json` is local (gitignored) and accumulates across runs; a fresh clone starts empty and rebuilds it. Each entry has an `origin`: `source`, `page`, `osm`, `manual`, or `miss` (retried after 30 days). Fix or add a venue by hand with `"origin": "manual"` (never overwritten); never delete the file to "rebuild". An unparseable file is left untouched and not saved.
- Only sources with `trusted_venues` teach the venue book (Eventbrite is excluded: anyone can post a venue there). Venue pages are fetched only over https on the source's own domain, without following redirects.
- Venue lookups are paced at about 1 request/second: event pages (stops for a host after a 429; ShowHub rate-limits) and Nominatim (at most 40 requests per run, Metro Vancouver box). OSM-derived entries need the ODbL credit kept in the file header and README.
- Firefox here is a snap and cannot read `/tmp`; use Playwright's Chromium for headless screenshots of the report.
- The HTML report's filtering is client-side JS in `src/renderers/html_renderer.py`; rows carry `data-city`, `data-type`, `data-source`, `data-minutes`. The same script adds `.tight` to `.table-wrap` when the table is wider than the window, letting the one-line columns wrap. Change it together with `tests/e2e/`. Use in-page `<details>` controls, never native `<select>`: the snap Firefox here does not commit a pick from a select's popup. The e2e suite runs Chromium only (Playwright's cached Firefox build does not match its client), so check filter changes in real Firefox through `/snap/bin/geckodriver` with the report saved under `$HOME`.

## Default City List

Defined in `src/cities.py` (`DEFAULT_CITIES`). Matching is case-insensitive and folds qualifiers and communities into their municipality ("Langley (Township)", "Fort Langley" and "Langley" all match).

### City Modes

1. **Default**: no cities specified → no flag; the default list applies and events with unknown city are kept
2. **Additive**: user says "also include [cities]" → `--add-cities`
3. **Override**: user says "only [cities]" → `--cities`; events with unknown city are dropped

Examples:
- "What's happening today?" → default (all cities)
- "What's happening today, also include Whistler" → additive
- "What's happening in Port Moody only" → override (only Port Moody)

## Activity Types

Keys and labels in `src/categories.py` (`CATEGORY_LABELS`): music, festivals, sports, art, food, outdoor, community, trivia, theatre, cultural, family. Source categories are mapped to these; uncategorized events get a keyword guess from the name.

Default: search all types. User narrows with `--types`.

## Sources

Curated sources fetched and parsed by the `src/` pipeline. No broad web search.

### Source 1: Do604
- **Type:** Local aggregator (all event types)
- **Strategy:** HTML scrape of Svelte cards (`div.standard-card[data-card-kind="event"]`), 20 per page, `?page=N` until a page has no cards
- **URL pattern:** `https://do604.com/events/{YYYY}/{M}/{D}` (unpadded; padded dates redirect)
- **Date in URL:** Yes, one set of pages per day
- **Fields:** Event name, venue, time, category, neighbourhood. No address; city comes from the neighbourhood label or the venue lookup.

### Source 2: Daily Hive Vancouver
- **Type:** Local aggregator (all event types)
- **Strategy:** Parse `__NEXT_DATA__` JSON embedded in HTML
- **URL pattern:** `https://dailyhive.com/vancouver/listed/events?after={from_date}&before={to_date}`
- **Date in URL:** Yes — supports date ranges natively
- **Fields:** Event name, venue, address, city, date range, start time, categories, price
- **Note:** Returns multi-day events; parser filters to events overlapping the query range. Paginated (`&page=N`, 12 per page). Timestamps carry a `Z` suffix but are local wall-clock times.

### Source 3: Rhythm Changes
- **Type:** Jazz & live music listings
- **Strategy:** HTML scrape
- **URL pattern:** `https://rhythmchanges.ca/gigs/`
- **Date in URL:** No. The page lists the current month only; a range past the month's end gets a "lists events only through" warning. Dates without a year are resolved to the year nearest the query (handles Dec to Jan).
- **Fields:** Event name, venue, date, time

### Source 4: ShowHub
- **Type:** Local live music & shows
- **Strategy:** HTML scrape
- **URL pattern:** `https://showhub.ca/weekly-listings/`
- **Date in URL:** No. The page lists the current week only; parser filters by date, and a range past the week's end gets a "lists events only through" warning.
- **Fields:** Event name, venue, date, time

### Source 5: Infidels Jazz
- **Type:** Jazz events
- **Strategy:** WordPress REST API (JSON)
- **URL pattern:** `https://theinfidelsjazz.ca/wp-json/tribe/events/v1/events/?start_date={from_date}&end_date={to_date}`
- **Date in URL:** Yes — supports date ranges natively
- **Fields:** Event name, venue, city, address, time, ticket price, description, event URL

### Source 6: BC Ale Trail
- **Type:** Brewery events aggregator (BC-wide)
- **Strategy:** Parse `data-event-times` JSON embedded in HTML event cards
- **URL pattern:** `https://bcaletrail.ca/events/?date-start={from_date}&date-end={to_date}`
- **Date in URL:** Yes — supports date ranges natively. Parser also filters by date range from embedded JSON timestamps.
- **Fields:** Event name, venue, city, address, time
- **Note:** Events span all of BC, not just Metro Vancouver. City data comes from embedded JSON. Recurring events yield one row per matching date.

### Source 7: Kids Out and About
- **Type:** Family and kids events
- **Strategy:** HTML scrape (Drupal Views), one page per day
- **URL pattern:** `https://vancouver.kidsoutandabout.com/event-list/{YYYY-MM-DD}`
- **Note:** Online and US-based listings are skipped.

### Source 8: Eventbrite
- **Type:** Community events, workshops, nightlife, shows
- **Strategy:** `window.__SERVER_DATA__` JSON embedded in HTML; one range query, paginated (`&page=N`, 20 per page)
- **URL pattern:** `https://www.eventbrite.ca/d/canada--vancouver/all-events/?start_date={from_date}&end_date={to_date}`
- **Note:** Rate-limited (see Gotchas). No prices in search results.

### Source 9: Public libraries (BiblioCommons)
- **Type:** Library programs (Vancouver Public Library `vpl`, Richmond Public Library `yourlibrary`)
- **Strategy:** JSON API `https://gateway.bibliocommons.com/v2/libraries/{slug}/events/search?startDate=...&endDate=...&limit=100`. Only `/events/search` honours the date filter.
- **Note:** Burnaby Public Library is not on BiblioCommons; the slug `bpl` is Boston.

## Behavior Rules

- Be exhaustive: process ALL source sections from the script output, don't stop early
- Include both free and ticketed events
- Note if venues are closed due to holidays
- Search for both scheduled events AND regular recurring programming
- Date filtering uses the `--from`/`--to` range (default: today for both)
- If a source section shows an ERROR, note it and continue with remaining sources
- Call out every WARNING: a zero-event warning means a likely layout change; "lists events only through" means the source does not cover the whole range

## Output Format

### Summary header
```
Found X events across Y cities from Z/N sources
```

### Event table
| Event Name | Type | City | Location | Date | Time | Price | Source Link |
|---|---|---|---|---|---|---|---|

### Sources checked footer
```
Sources checked: Do604 (12), Daily Hive (8), Rhythm Changes (ERROR: ...), ShowHub (6, WARNING: lists events only through 2026-03-08)
```

### Output files
- `--format html` → `events-YYYY-MM-DD.html` (single day) or `events-FROM_to_TO.html` (range) — self-contained HTML with sortable columns, clickable links, and a filter bar (city, type, source, start-time range). Generated by `src/renderers/html_renderer.py`.
- `--format markdown` → `events-YYYY-MM-DD.md` (single day) or `events-FROM_to_TO.md` (range) — markdown table. Generated by `src/renderers/markdown_renderer.py`.
