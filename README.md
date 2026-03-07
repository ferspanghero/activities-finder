# Activities Searcher

An automated tool that aggregates event listings from curated sources, filters them by date, city, and activity type, and presents a consolidated list of things to do. Currently configured with Metro Vancouver sources, but extensible to any region by adding new parsers.

## How It Works

1. Pipeline fetches all sources in parallel, returning raw HTML/JSON
2. Source-specific BeautifulSoup parsers extract structured `Event` objects deterministically
3. Renderer produces output file (markdown or HTML with sortable columns)
4. The `/find-activities` slash command deduplicates cross-source duplicates (same event listed by multiple sources) and presents the cleaned results

```
fetch HTML/JSON → source-specific parsers → list[Event] → renderers → output file → dedup
```

## Sources

| Source | Type | Strategy |
|---|---|---|
| [Do604](https://do604.com) | Local aggregator (all event types) | HTML scrape |
| [Daily Hive Vancouver](https://dailyhive.com/vancouver) | Local aggregator (all event types) | `__NEXT_DATA__` JSON in HTML |
| [Rhythm Changes](https://rhythmchanges.ca) | Jazz & live music | HTML scrape |
| [ShowHub](https://showhub.ca) | Local live music & shows | HTML scrape |
| [Infidels Jazz](https://theinfidelsjazz.ca) | Jazz events | WordPress REST API (JSON) |

No broad web search is used. The curated source list determines coverage.

## Activity Types

Live music, festivals, sports events, art exhibitions/gallery openings, food/drink events, outdoor activities, community events, trivia nights/pub events.

## Usage

Requires [Claude Code](https://docs.anthropic.com/en/docs/claude-code). Run the `/find-activities` slash command:

```
/find-activities march 8th html
/find-activities tomorrow, only Vancouver
/find-activities live music this weekend
```

The pipeline can also be run directly, but deduplication is only performed through the slash command:

```bash
python3 -m src --date 2026-03-08 --format html --output events-2026-03-08.html
```

See [`examples/`](examples/) for sample output.

## Project Structure

```
src/
  __main__.py          # CLI entry point
  models.py            # Event, FetchResult, SourceStatus dataclasses
  pipeline.py          # Orchestrator: fetch → parse → aggregate
  fetch_sources.py     # Async parallel fetcher
  parsers/             # Source-specific parsers (do604, dailyhive, rhythmchanges, showhub, infidelsjazz)
  renderers/           # Markdown and HTML renderers
tests/
  test_parsers/        # Parser unit tests
  test_renderers/      # Renderer unit tests
  fixtures/            # Sample HTML/JSON for tests
project_files/         # Design docs and backlog
.claude/commands/      # Claude Code slash command definitions
```

## Tests

```bash
pytest                       # all tests
pytest -m "not integration"  # unit tests only
```
