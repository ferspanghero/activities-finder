# Activities Searcher

## What

An automated tool that aggregates event listings from curated Metro Vancouver sources, filters them by date, city, and activity type, and presents a consolidated list of things to do.

## How It Works (v3 — Deterministic Pipeline)

1. User runs `/find-activities` with optional date, city, and activity type filters
2. Pipeline fetches all sources in parallel, returning raw HTML/JSON
3. Source-specific BeautifulSoup parsers extract structured `Event` objects deterministically
4. Renderers produce markdown table (in conversation) and HTML report (exported file)
5. LLM role is limited to: parsing user parameters from natural language + optional activity type classification

```
fetch HTML/JSON → source-specific parsers → list[Event] → renderers → output
```

## Key Concepts

### Sources

The source list is the database. Each source is a URL to an events page that gets fetched directly. Sources can be:
- **Local aggregators** — regional event listing sites
- **Venue/genre-specific** — individual venue calendars or genre-focused listings

No broad web search is used. The curated source list determines coverage.

See `CLAUDE.md` for the full source list, city list, activity types, behavior rules, and output format.
