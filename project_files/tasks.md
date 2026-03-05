# Tasks

## Project Setup

- [ ] **T1**: Create `project_files/overview.md`
- [ ] **T2**: Create `project_files/plan.md`
- [ ] **T3**: Create `project_files/tasks.md`

## Fetch Script (scripts/fetch_sources.py)

- [ ] **T4**: Create `requirements.txt` with aiohttp and html2text
- [ ] **T5**: Create `scripts/fetch_sources.py` with source URL construction from `--date` argument
- [ ] **T6**: Add parallel fetching with asyncio/aiohttp for all 5 sources
- [ ] **T7**: Add HTML→markdown conversion with html2text for HTML sources
- [ ] **T8**: Add JSON API handling for Infidels Jazz — format structured JSON as readable text
- [ ] **T9**: Add Rhythm Changes week calculation — determine which week section the target date falls in and note it in output header
- [ ] **T10**: Add stdout output with source delimiters (`=== SOURCE: Name (url) ===`)
- [ ] **T11**: Add error handling — unreachable sources print error instead of content, script exits 0

## Agent Configuration (CLAUDE.md)

- [ ] **T12**: Create `CLAUDE.md` with default city list (25 Metro Vancouver municipalities)
- [ ] **T13**: Add city modes documentation (default / additive / override) with examples of user phrasing for each mode
- [ ] **T14**: Add activity types list (8 categories)
- [ ] **T15**: Add source list with structured metadata (5 sources: type, strategy, URL pattern, date filtering, available fields)
- [ ] **T16**: Add behavior rules (exhaustive search, free+ticketed, holiday awareness, regular programming)
- [ ] **T17**: Add output format specification (markdown table: Event Name | City | Exact Address | Time | Source Link)

## Slash Command (.claude/commands/find-activities.md)

- [ ] **T18**: Create `.claude/commands/` directory
- [ ] **T19**: Write parameter parsing instructions — date (default: today), cities (mode detection), activity types (default: all)
- [ ] **T20**: Write city mode resolution logic — detect user intent from phrasing ("only X" = override, "also X" = additive, nothing = default)
- [ ] **T21**: Write instruction to run fetch script — `python3 scripts/fetch_sources.py --date {YYYY-MM-DD}`
- [ ] **T22**: Write event extraction instructions — parse script output for event name, city, address, time, category
- [ ] **T23**: Write filtering logic — exact date match (for static-URL sources), city match, activity type match
- [ ] **T24**: Write output formatting — markdown table, summary line, unreachable source notes
- [ ] **T25**: Write error handling — unreachable sources noted, no results messaging

## Manual QA

- [ ] **T26**: Test fetch script standalone — `python3 scripts/fetch_sources.py --date 2026-03-07` outputs content from all 5 sources
- [ ] **T27**: Test fetch script error handling — verify graceful output when a source is unreachable
- [ ] **T28**: Run `/find-activities` with no parameters — all sources fetched, today's date, all cities, all types
- [ ] **T29**: Run `/find-activities` with specific city ("only Port Moody") — results filtered correctly
- [ ] **T30**: Run `/find-activities` with specific activity type ("live music") — only matching events

## Future Tasks (not v1)

- [ ] **T31**: Create deduplication command/skill — separate pass to tidy up raw results, merge duplicates across sources
- [ ] **T32**: Re-add vancouversbestplaces.com once headless browser is available or a usable API is found
- [ ] **T33**: Explore source URL subsections for targeted fetching (e.g., do604.com/events/music/today)
- [ ] **T34**: Evaluate adding individual brewery/winery/restaurant venue sites as sources
- [ ] **T35**: Evaluate MCP server for caching and programmatic dedup
