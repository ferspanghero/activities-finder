# Activities Searcher

## What

An automated tool that aggregates event listings from curated Metro Vancouver sources, filters them by date, city, and activity type, and presents a consolidated list of things to do.

## How It Works

1. User runs `/find-activities` with optional date, city, and activity type filters
2. Python script (`scripts/fetch_sources.py`) fetches all sources in parallel, converts HTML to markdown
3. Claude parses the raw output, extracts individual events, filters by city/type
4. Results are presented as a markdown table in conversation
5. Results are also exported to `events-YYYY-MM-DD.html` — a self-contained HTML file with sortable columns and clickable links

## Key Concepts

### Sources

The source list is the database. Each source is a URL to an events page that gets fetched directly. Sources can be:
- **Local aggregators** — regional event listing sites
- **Venue/genre-specific** — individual venue calendars or genre-focused listings

No broad web search is used. The curated source list determines coverage.

See `CLAUDE.md` for the full source list, city list, activity types, behavior rules, and output format.
