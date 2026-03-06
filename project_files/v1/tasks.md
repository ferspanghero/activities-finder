# Tasks

## Project Setup

- [x] **T1**: Create `project_files/overview.md`
- [x] **T2**: Create `project_files/plan.md`
- [x] **T3**: Create `project_files/tasks.md`

## Fetch Script (scripts/fetch_sources.py)

- [x] **T4**: Create `requirements.txt` with aiohttp, html2text, pytest, pytest-asyncio, aioresponses
- [x] **T5**: Create `scripts/fetch_sources.py` with source URL construction from `--date` argument
- [x] **T6**: Add parallel fetching with asyncio/aiohttp for all 5 sources
- [x] **T7**: Add HTML→markdown conversion with html2text for HTML sources
- [x] **T8**: Add JSON API handling for Infidels Jazz — format structured JSON as readable text
- [x] **T9**: Add Rhythm Changes week calculation — determine which week section the target date falls in and note it in output header
- [x] **T10**: Add stdout output with source delimiters (`=== SOURCE: Name (url) ===`)
- [x] **T11**: Add error handling — unreachable sources print error instead of content, script exits 0

## Agent Configuration (CLAUDE.md)

- [x] **T12**: Create `CLAUDE.md` with default city list (25 Metro Vancouver municipalities)
- [x] **T13**: Add city modes documentation (default / additive / override) with examples of user phrasing for each mode
- [x] **T14**: Add activity types list (8 categories)
- [x] **T15**: Add source list with structured metadata (5 sources: type, strategy, URL pattern, date filtering, available fields)
- [x] **T16**: Add behavior rules (exhaustive search, free+ticketed, holiday awareness, regular programming)
- [x] **T17**: Add output format specification (markdown table: Event Name | City | Exact Address | Time | Source Link)

## Slash Command (.claude/commands/find-activities.md)

- [x] **T18**: Create `.claude/commands/` directory
- [x] **T19**: Write parameter parsing instructions — date (default: today), cities (mode detection), activity types (default: all)
- [x] **T20**: Write city mode resolution logic — detect user intent from phrasing ("only X" = override, "also X" = additive, nothing = default)
- [x] **T21**: Write instruction to run fetch script — `python3 scripts/fetch_sources.py --date {YYYY-MM-DD}`
- [x] **T22**: Write event extraction instructions — parse script output for event name, city, address, time, category
- [x] **T23**: Write filtering logic — exact date match (for static-URL sources), city match, activity type match
- [x] **T24**: Write output formatting — markdown table, summary line, unreachable source notes
- [x] **T25**: Write error handling — unreachable sources noted, no results messaging

## Fetch Script Tests (tests/test_fetch_sources.py)

### Unit tests (no network)

- [x] **T26**: Test URL construction — given a date, assert correct URL for each of the 5 sources
- [x] **T27**: Test Rhythm Changes week calculation — dates across different weeks (Mar 1, Mar 8, Mar 15, Mar 29) return correct week number
- [x] **T28**: Test output delimiters — assert each source section starts with `=== SOURCE: Name (url) ===`
- [x] **T29**: Test Infidels Jazz JSON formatting — given sample API JSON, assert readable text output
- [x] **T30**: Test HTML→markdown conversion — given sample HTML, assert clean markdown

### Unit tests (mocked HTTP)

- [x] **T31**: Test parallel fetching — mock all 5 sources, assert output contains 5 sections with content
- [x] **T32**: Test partial failure — mock 1 source as unreachable, assert error for that source + content for other 4
- [x] **T33**: Test all sources down — mock all failing, assert 5 error sections and exit 0

### Integration test

- [x] **T34**: Test end-to-end with real sources — run script with a known date, assert 5 source sections with non-empty content. Mark with `@pytest.mark.integration`.

## Manual QA (slash command)

- [x] **T35**: Run `/find-activities` with no parameters — all sources fetched, today's date, all cities, all types
- [x] **T36**: Run `/find-activities` with specific city ("only Port Moody") — results filtered correctly
- [x] **T37**: Run `/find-activities` with specific activity type ("live music") — only matching events

## Future Tasks (not v1)

- [ ] **T38**: Create deduplication command/skill — separate pass to tidy up raw results, merge duplicates across sources
- [ ] **T39**: Evaluate adding individual brewery/winery/restaurant venue sites as sources
- [ ] **T40**: Evaluate MCP server for caching and programmatic dedup
