# Activities Searcher

An automated tool that aggregates event listings from curated Metro Vancouver sources, filters them by date, city, and activity type, and presents a consolidated list of things to do.

## How It Works

1. Pipeline fetches all sources in parallel, returning raw HTML/JSON
2. Source-specific BeautifulSoup parsers extract structured `Event` objects deterministically
3. Renderer produces output file (markdown or HTML with sortable columns)
4. Optional: Claude Code slash command deduplicates the event table before presenting results

```
fetch HTML/JSON → source-specific parsers → list[Event] → renderers → output file
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

### CLI

```bash
# Install dependencies
pip install -r requirements.txt

# Run for a specific date (default: today)
python3 -m src --date 2026-03-08

# Output as HTML (default) or markdown
python3 -m src --date 2026-03-08 --format html --output events-2026-03-08.html
python3 -m src --date 2026-03-08 --format markdown --output events-2026-03-08.md
```

### Claude Code Slash Command

If using [Claude Code](https://docs.anthropic.com/en/docs/claude-code), the `/find-activities` slash command runs the pipeline, deduplicates results, and presents them interactively:

```
/find-activities march 8th html
/find-activities tomorrow, only Vancouver
/find-activities live music this weekend
```

## Default City List

Vancouver, Burnaby, New Westminster, Richmond, North Vancouver (City), Lynn Valley, Deep Cove, West Vancouver, Horseshoe Bay, Surrey, White Rock, Port Moody, Port Coquitlam, Coquitlam, Langley (City), Langley (Township), Delta, Pitt Meadows, Maple Ridge, Mission, Abbotsford, Chilliwack, Squamish, Anmore, Belcarra

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
