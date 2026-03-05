# Tasks

## Project Setup

- [ ] **T1**: Create `project_files/overview.md`
- [ ] **T2**: Create `project_files/plan.md`
- [ ] **T3**: Create `project_files/tasks.md`

## Agent Configuration (CLAUDE.md)

- [ ] **T4**: Create `CLAUDE.md` with default city list (20+ Metro Vancouver municipalities)
- [ ] **T5**: Add city modes documentation (default / additive / override) with examples of user phrasing for each mode
- [ ] **T6**: Add activity types list (8 categories)
- [ ] **T7**: Add source list with URLs (4 local aggregators + 3 venue/genre-specific + 7 broad aggregators = 14 total)
- [ ] **T8**: Add behavior rules (exhaustive search, free+ticketed, holiday awareness, regular programming)
- [ ] **T9**: Add output format specification (markdown table: Event Name | City | Exact Address | Time | Source Link)

## Slash Command (.claude/commands/find-activities.md)

- [ ] **T10**: Create `.claude/commands/` directory
- [ ] **T11**: Write parameter parsing instructions — date (default: today), cities (mode detection), activity types (default: all)
- [ ] **T12**: Write city mode resolution logic — detect user intent from phrasing ("only X" = override, "also X" = additive, nothing = default)
- [ ] **T13**: Write source fetching procedure — WebFetch each source URL, handle failures gracefully
- [ ] **T14**: Write event extraction instructions — parse page content for event name, city, address, time, category
- [ ] **T15**: Write filtering logic — exact date match, city match, activity type match
- [ ] **T16**: Write deduplication instructions — same event name + venue + date = one entry, keep most complete info
- [ ] **T17**: Write output formatting — markdown table, summary line, unreachable source notes
- [ ] **T18**: Write error handling — unreachable sources noted, no results messaging

## Ground Truth Testing

- [ ] **T19**: Run `/find-activities` for Feb 28, 2026 — store full output
- [ ] **T20**: Run `/find-activities` for March 1, 2026 — store full output
- [ ] **T21**: User reviews and validates stored outputs
- [ ] **T22**: Establish golden dataset from validated outputs for regression testing

## Future Tasks (not v1)

- [ ] **T23**: Explore source URL subsections for targeted fetching (e.g., do604.com/events/music/today)
- [ ] **T24**: Evaluate adding individual brewery/winery/restaurant venue sites as sources
- [ ] **T25**: Evaluate MCP server for parallel fetching, caching, and programmatic dedup

## Verification

- [ ] **V1**: Run `/find-activities` with no parameters — all 14 sources fetched, today's date, all cities, all types
- [ ] **V2**: Run with specific city ("only Port Moody") — results filtered to that city only
- [ ] **V3**: Run with specific date — only that date's events shown
- [ ] **V4**: Run with specific activity type ("live music") — only matching events
- [ ] **V5**: Confirm all 14 sources are fetched and parsed
- [ ] **V6**: Confirm deduplication works (same event on do604 + 604now = one entry)
- [ ] **V7**: Confirm unreachable source is noted gracefully (not a crash)
- [ ] **V8**: Confirm sources-checked summary appears in output
