# Activities Searcher

## What

An automated tool that aggregates event listings from curated local sources, filters them by date, city, and activity type, deduplicates across sources, and presents a consolidated list of things to do.

## How It Works

- Configured with a list of event sources (aggregator sites, venue calendars, genre-specific listings)
- For each source, fetches the events page and extracts event details (name, city, address, time, category)
- Filters by exact date match (default: today), city, and activity type
- Deduplicates across sources (same event on multiple sites appears once)
- Outputs a formatted table of results

## Key Concepts

### Sources

The source list is the database. Each source is a URL to an events page that gets fetched directly. Sources can be:
- **Local aggregators** — regional event listing sites
- **Venue/genre-specific** — individual venue calendars or genre-focused listings
- **Broad aggregators** — larger event platforms with regional coverage

No broad web search is used. The curated source list determines coverage.

### Cities

A configurable list of cities/communities to search. Three modes:
1. No cities specified -> use the full default list
2. Additive -> specified cities + default list
3. Override -> only the specified cities

### Activity Types

A configurable list of event categories. Default: search all types. User can narrow to specific types.

## Output Format

### Event table

| Event Name | City | Exact Address | Time | Source Link |
|---|---|---|---|---|
| Jazz Night at The Infidels | Vancouver | 732 Main St | 8:00 PM | [link](https://example.com/events/...) |
| Trivia Tuesday at Brewhall | Vancouver | 97 E 2nd Ave | 7:00 PM | [link](https://example.com/events/...) |
| Night Market | Surrey | 10555 King George Blvd | 6:00 PM - 11:00 PM | [link](https://example.com/events/...) |
| Live Music: The Harpoonist | Port Moody | 121 Brew St | 8:30 PM | [link](https://example.com/...) |
| Art Walk | Langley | Multiple locations | 10:00 AM - 4:00 PM | [link](https://example.com/events/...) |

### Summary header

```
Found 47 events across 12 cities from 13/14 sources (source-x unreachable)
```

### Sources checked footer

```
Sources checked: source-a (12), source-b (8), source-c (UNREACHABLE), source-d (6), ...
```

## Behavior Rules

- Be exhaustive: check ALL sources, don't stop early
- Include both free and ticketed events
- Note if venues are closed due to holidays
- Search for both scheduled events AND regular recurring programming
- Date filtering is exact (only the specified date, default today)
- If a source is unreachable, note it and continue with remaining sources
