# v5 Tasks — Date Range Support

## Models

- [x] **M1**: Add `event_date: date` field to `Event` dataclass
- [x] **M2**: Replace `target_date` with `from_date`/`to_date` in `FetchResult`

## Fetch Layer

- [x] **F1**: Update URL templates (`{from_date}`/`{to_date}`, `per_day` flag for Do604)
- [x] **F2**: Update `build_source_url(source_id, from_date, to_date)`
- [x] **F3**: Update `_fetch_one_raw` signature (from_date, to_date)
- [x] **F4**: Update `fetch_raw_sources(from_date, to_date)` with per-day Do604 logic

## Parsers

- [x] **P1**: Update `parse_do604` — add from_date/to_date params, set event_date
- [x] **P2**: Update `parse_dailyhive` — range overlap filter, set event_date
- [x] **P3**: Update `parse_rhythmchanges` — range filter, set event_date
- [x] **P4**: Update `parse_showhub` — range filter, return event_date
- [x] **P5**: Update `parse_infidelsjazz` — add from_date/to_date, parse event_date from JSON
- [x] **P6**: Update `parse_bcaletrail` — range filter, set event_date

## Pipeline

- [x] **PL1**: Update `run_pipeline(from_date, to_date)`
- [x] **PL2**: Update `_dispatch_parser` to read dates from FetchResult
- [x] **PL3**: Add source status merging by name

## CLI

- [x] **C1**: Replace `--date` with `--from`/`--to` flags
- [x] **C2**: Add validation (from <= to, max 14 days)
- [x] **C3**: Sort by (event_date, time), range-aware filenames

## Renderers

- [x] **R1**: HTML renderer — add Date column, update JS sort, range title
- [x] **R2**: Markdown renderer — add Date column, range header

## Slash Command

- [x] **SC1**: Update find-activities.md for date range support

## Tests

- [x] **T1**: Update parser tests (all 6) for new signatures and event_date
- [x] **T2**: Update renderer tests and fixtures for Date column
- [x] **T3**: Update pipeline tests for from_date/to_date and status merging
- [x] **T4**: Update CLI tests for --from/--to flags
- [x] **T5**: Update fetch tests for range URL building

## Documentation

- [x] **D1**: Update CLAUDE.md — --from/--to syntax, Date column
