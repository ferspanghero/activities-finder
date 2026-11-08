# Activities Searcher

An automated tool that aggregates event listings from curated sources, filters them by date, city, and activity type, and presents a consolidated list of things to do. Currently configured with Metro Vancouver sources, but extensible to any region by adding new parsers.

## How It Works

1. Pipeline fetches all sources in parallel, following each source's pagination, with rate limits and retries
2. Source-specific parsers extract structured `Event` objects (name, venue, address, city, time, type, price)
3. Health checks flag a source that suddenly returns no events (likely a site layout change) or whose listing window ends before the requested range
4. Missing cities and addresses are filled from a venue book (`data/venues.json`), built from sources that publish addresses, the event's own page, and an OpenStreetMap search for venues still unknown. Each venue is looked up once and saved locally (the file is not part of the repository; a fresh clone rebuilds it). Events without a source category are typed by keyword
5. Events are filtered by city and activity type, sorted, and deduplicated across sources
6. Renderer produces the output file: markdown, or HTML with sortable columns, map links, and a filter bar (city, type, and source checklists plus a start-time range)
7. The `/find-activities` slash command reviews the few remaining possible duplicates that cannot be decided automatically

```
fetch pages → parse → health checks → venue book + lookups → typing → filter → dedup → render → review
```

## Sources

| Source | Type | Strategy |
|---|---|---|
| [Do604](https://do604.com) | Local aggregator (all event types) | HTML scrape, paginated per day |
| [Daily Hive Vancouver](https://dailyhive.com/vancouver) | Local aggregator (all event types) | `__NEXT_DATA__` JSON in HTML |
| [Rhythm Changes](https://rhythmchanges.ca) | Jazz & live music | HTML scrape |
| [ShowHub](https://showhub.ca) | Local live music & shows | HTML scrape |
| [Infidels Jazz](https://theinfidelsjazz.ca) | Jazz events | WordPress REST API (JSON) |
| [BC Ale Trail](https://bcaletrail.ca) | Brewery events (BC-wide) | `data-event-times` JSON in HTML |
| [Kids Out and About](https://vancouver.kidsoutandabout.com) | Family and kids events | HTML scrape, per day |
| [Eventbrite](https://www.eventbrite.ca/d/canada--vancouver/all-events/) | Community events, workshops, shows | Embedded server-data JSON, paginated |
| [Vancouver](https://vpl.bibliocommons.com/v2/events) and [Richmond](https://yourlibrary.bibliocommons.com/v2/events) public libraries | Library programs (family, community) | BiblioCommons events JSON API |

No broad web search is used. The curated source list determines coverage. Each source's fetch and parse settings live in a registry in `src/sources.py`.

## Activity Types

Live music, festivals, sports, art exhibitions, food and drink, outdoor activities, community events, trivia and pub nights, theatre and performing arts, cultural celebrations, family events. Filter with `--types` (run `python3 -m src --help` for the keys).

## Usage

Requires [Claude Code](https://docs.anthropic.com/en/docs/claude-code). Run the `/find-activities` slash command:

```
/find-activities march 8th html
/find-activities tomorrow, only Vancouver
/find-activities live music this weekend
```

The pipeline can also be run directly. It deduplicates automatically; only the slash command adds the review of uncertain pairs:

```bash
python3 -m src --from 2026-03-08 --to 2026-03-08 --format html              # one day, default city list
python3 -m src --from 2026-03-06 --to 2026-03-08 --add-cities Whistler      # also include a city
python3 -m src --from 2026-03-08 --to 2026-03-08 --cities Burnaby --types music,food  # only these
```

With no city flag the default Metro Vancouver city list applies (see `CLAUDE.md`). Date ranges are capped at 14 days.

See [`examples/`](examples/) for sample output.

## Project Structure

```
src/
  __main__.py          # CLI entry point
  models.py            # Event, FetchResult, SourceStatus dataclasses
  sources.py           # Source registry: URLs, parsers, pagination, health checks
  pipeline.py          # Orchestrator: fetch → parse → health checks → enrich
  fetch_sources.py     # Async paginated fetcher with rate limits and retries
  cli_utils.py         # Shared filter → sort → dedup flow for both CLIs
  compact.py           # Two-step CLI used by the slash command
  parsers/             # Source-specific parsers (do604, dailyhive, etc.)
  renderers/           # Markdown and HTML renderers
tests/
  test_parsers/        # Parser unit tests
  test_renderers/      # Renderer unit tests
  fixtures/            # Sample HTML/JSON for tests
data/                  # Venue book: venue → city/address, updated by each run
project_files/         # Design docs and backlog
.claude/commands/      # Claude Code slash command definitions
```

## Tests

```bash
pytest -m "not integration"  # unit and browser tests (offline, fixtures only)
pytest -m e2e                # HTML report filters in headless Chromium (needs Playwright)
pytest -m integration        # live canary: every source must answer today with events
```

## License

Code: [MIT](LICENSE).

Venue data in `data/venues.json` marked `"origin": "osm"` comes from [OpenStreetMap](https://www.openstreetmap.org/copyright), © OpenStreetMap contributors, available under the Open Database License (ODbL).
