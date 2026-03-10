# v5 Implementation Plan — Date Range Support

## Goal

Replace the single `--date` flag with `--from`/`--to` flags so users can query multiple days. The range logic lives in the fetch and parser layers — the pipeline remains structurally unchanged. Sources with native range support (Daily Hive, Infidels Jazz, BC Ale Trail) make a single HTTP request. Do604 (date-in-URL) fetches one page per day. Fixed-URL sources (Rhythm Changes, ShowHub) fetch once and filter.

## Architecture

```
CLI:       --from YYYY-MM-DD --to YYYY-MM-DD (same date for single day)
Pipeline:  run_pipeline(from_date, to_date) → fetch → parse → aggregate
Fetch:     per-day for Do604, single request for range-capable sources
Parsers:   receive from_date/to_date, set event_date on each Event
Renderers: new Date column, sorted by date then time
```

### Do604 Multi-Fetch Design

Do604's URL is `/events/YYYY/MM/DD`. For a range, the fetch layer produces multiple FetchResults (one per day). The pipeline loop handles them naturally. Source statuses are merged by name after processing.

## Implementation

### 1. Models (`src/models.py`)
- Add `event_date: date` field to `Event` (after `time`, before `source_name`)
- Replace `target_date: date` in `FetchResult` with `from_date: date` and `to_date: date`

### 2. Fetch layer (`src/fetch_sources.py`)
- URL templates: use `{from_date}`/`{to_date}` for range sources, keep `{YYYY}/{MM}/{DD}` for Do604
- Add `"per_day": True` flag to Do604 source config
- `build_source_url(source_id, from_date, to_date)` — formats both sets of placeholders
- `_fetch_one_raw(session, source_id, from_date, to_date)` — passes range to URL builder and FetchResult
- `fetch_raw_sources(from_date, to_date)` — generates per-day tasks for Do604, single task for others

### 3. Parsers (all 6 in `src/parsers/`)
- All change signature to `(content, source_url, from_date, to_date)`
- All set `event_date` on every `Event(...)` constructor
- Date-filtering parsers updated from single-date to range comparison

### 4. Pipeline (`src/pipeline.py`)
- `run_pipeline(from_date, to_date)` — passes range to fetch layer
- `_dispatch_parser(fetch_result)` — reads dates from FetchResult, passes to parser
- Merge source statuses by name after processing loop

### 5. CLI (`src/__main__.py`)
- Replace `--date` with required `--from` and `--to`
- Validate range (from <= to, max 14 days)
- Sort by `(event_date, time)`, range-aware output filenames

### 6. Renderers (`src/renderers/`)
- Add Date column (after Event Name)
- Signature: `(events, source_statuses, from_date, to_date)`
- Range-aware title display

### 7. Slash command (`.claude/commands/find-activities.md`)
- Support date ranges in parameter parsing
- Update command examples

## Verification

1. `pytest` — all tests pass
2. `python3 -m src --from 2026-03-09 --to 2026-03-09 --format html` — single day
3. `python3 -m src --from 2026-03-09 --to 2026-03-11 --format html` — multi-day range
4. Reversed range errors correctly
