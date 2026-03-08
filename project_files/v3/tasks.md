# v3 Tasks — Deterministic Event Extraction Pipeline

## Phase A: Foundation

- [x] **A1**: Save HTML/JSON fixtures from live sources to `tests/fixtures/`
- [x] **A2**: Create `src/models.py` with `Event`, `FetchResult`, `SourceStatus` dataclasses
- [x] **A3**: Create package scaffolding (`src/__init__.py`, `src/parsers/__init__.py`, `src/renderers/__init__.py`)
- [x] **A4**: Install `beautifulsoup4` dependency

## Phase B: Parsers (TDD)

### B1: Infidels Jazz (JSON API)
- [x] **B1a**: Write `tests/test_parsers/test_infidelsjazz.py` with fixture-based tests
- [x] **B1b**: Implement `src/parsers/infidelsjazz.py` — `parse_infidelsjazz(data) -> list[Event]`
- [x] **B1c**: All tests pass

### B2: Do604
- [x] **B2a**: Write `tests/test_parsers/test_do604.py` with fixture-based tests
- [x] **B2b**: Implement `src/parsers/do604.py` — `parse_do604(html, url) -> list[Event]`
- [x] **B2c**: All tests pass

### B3: Daily Hive
- [x] **B3a**: Write `tests/test_parsers/test_dailyhive.py` with fixture-based tests
- [x] **B3b**: Implement `src/parsers/dailyhive.py` — `parse_dailyhive(html, url, target_date) -> list[Event]`
- [x] **B3c**: All tests pass

### B4: ShowHub
- [x] **B4a**: Write `tests/test_parsers/test_showhub.py` with fixture-based tests
- [x] **B4b**: Implement `src/parsers/showhub.py` — `parse_showhub(html, url, target_date) -> list[Event]`
- [x] **B4c**: All tests pass

### B5: Rhythm Changes
- [x] **B5a**: Write `tests/test_parsers/test_rhythmchanges.py` with fixture-based tests
- [x] **B5b**: Implement `src/parsers/rhythmchanges.py` — `parse_rhythmchanges(html, url, target_date) -> list[Event]`
- [x] **B5c**: All tests pass

## Phase C: Fetch Layer

- [x] **C1**: Implement `src/fetch_sources.py` with `fetch_raw_sources(target_date) -> list[FetchResult]`
- [x] **C2**: Add tests for `fetch_raw_sources()` in `tests/test_fetch_sources.py`
- [x] **C3**: Verify all tests pass

## Phase D: Pipeline & Renderers

### D1: Pipeline orchestrator
- [x] **D1a**: Write `tests/test_pipeline.py` with mocked fetch + inline fixtures
- [x] **D1b**: Implement `src/pipeline.py` — `run_pipeline(target_date) -> PipelineResult`
- [x] **D1c**: All tests pass

### D2: Markdown renderer
- [x] **D2a**: Write `tests/test_renderers/test_markdown.py`
- [x] **D2b**: Implement `src/renderers/markdown_renderer.py` — `render_markdown(events, source_statuses, date_str) -> str`
- [x] **D2c**: All tests pass

### D3: HTML renderer
- [x] **D3a**: Write `tests/test_renderers/test_html.py`
- [x] **D3b**: Implement `src/renderers/html_renderer.py` — self-contained HTML generation with sortable columns
- [x] **D3c**: All tests pass

## Phase E: CLI & Integration

- [x] **E1**: Implement `src/__main__.py` CLI entry point
- [x] **E2**: Write `tests/test_cli.py`
- [x] **E3**: Update `.claude/commands/find-activities.md` — simplified flow using `python3 -m src`
- [x] **E4**: Update `CLAUDE.md` — new commands, key files, architecture
- [x] **E5**: Update `project_files/overview.md` — new architecture description

## Phase F: Cleanup & Refactor

- [x] **F1**: Consolidated fetch logic into `src/fetch_sources.py` (removed `scripts/fetch_sources.py`)
- [x] **F2**: Made `src/renderers/html_renderer.py` self-contained (removed `scripts/generate_html.py`)
- [x] **F3**: Removed `html2text` dependency (parsers use BeautifulSoup on raw HTML)
- [x] **F4**: Removed `scripts/` directory and `events/` duplicate — all code now lives in `src/`

## Manual QA

- [x] **QA1**: Run `python3 -m src --date 2026-03-06` end-to-end, verify markdown output
- [x] **QA2**: Verify HTML report has sortable columns and clickable links
- [x] **QA3**: Compare output against previous pipeline run for March 6 — event counts and sources align
- [x] **QA4**: Run `/find-activities` via slash command with new pipeline, verify results
