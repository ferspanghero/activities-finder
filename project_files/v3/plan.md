# v3 Implementation Plan — Deterministic Event Extraction Pipeline

## Goal

Replace LLM-based event extraction with Python-based source-specific parsers. The current pipeline sends raw HTML/markdown to the LLM for parsing, which costs tens of thousands of tokens per run, is slow (~10-20s), and produces non-deterministic results. v3 introduces BeautifulSoup parsers that produce structured `Event` objects, removing the LLM from the main execution path.

## Architecture

```
Current:  fetch HTML → html2text → markdown → [LLM parses] → [LLM formats] → output
New:      fetch HTML/JSON → source-specific parsers → list[Event] → renderers → output
```

The LLM role is reduced to: parameter parsing from natural language (in the slash command) and optional activity type classification post-extraction.

---

## Phase A: Foundation

**A1. HTML Reconnaissance — Save fixtures from live sources**
- Fetch live HTML/JSON from each source and save to `tests/fixtures/`
- Inspect DOM structure to identify CSS selectors for each source
- Files: `tests/fixtures/{do604,dailyhive,rhythmchanges,showhub}_sample.html`, `tests/fixtures/infidelsjazz_sample.json`

**A2. Event model and package structure**
- Create `src/models.py` with `Event` dataclass (`slots=True`, typed fields)
- Create package scaffolding: `src/__init__.py`, `src/parsers/__init__.py`, `src/renderers/__init__.py`

```python
@dataclass(slots=True)
class Event:
    name: str
    city: Optional[str]
    address: Optional[str]
    time: Optional[str]
    source_name: str
    source_url: str
```

Supporting models:
- `FetchResult` — raw content from a source fetch (source_id, source_name, url, content, error, target_date)
- `SourceStatus` — per-source summary for footer (name, count, error)

---

## Phase B: Parsers (one per source, TDD)

Each parser: `parse_<source>(raw, ...) -> list[Event]`
Each has a dedicated test file using saved HTML fixtures. No live network in tests.

**B1. Infidels Jazz parser** (easiest — JSON API, start here)
- File: `src/parsers/infidelsjazz.py`
- Test: `tests/test_parsers/test_infidelsjazz.py`
- Reuses JSON structure knowledge from existing `format_infidelsjazz_json()` in `fetch_sources.py`

**B2. Do604 parser**
- File: `src/parsers/do604.py`
- Test: `tests/test_parsers/test_do604.py`
- CSS selectors determined from fixture

**B3. Daily Hive parser**
- File: `src/parsers/dailyhive.py`
- Test: `tests/test_parsers/test_dailyhive.py`
- Multi-day events — parser extracts date ranges, pipeline filters by target date

**B4. ShowHub parser**
- File: `src/parsers/showhub.py`
- Test: `tests/test_parsers/test_showhub.py`
- Needs `target_date` param to filter to correct day (page shows full week)

**B5. Rhythm Changes parser**
- File: `src/parsers/rhythmchanges.py`
- Test: `tests/test_parsers/test_rhythmchanges.py`
- Needs `target_date` param; reuses `calculate_week_number()` from `fetch_sources.py`

---

## Phase C: Fetch Layer

**C1. Implement `src/fetch_sources.py`**
- `SOURCES` config dict with URL templates per source
- `build_source_url(source_id, target_date) -> str`
- `calculate_week_number(target_date) -> int` for Rhythm Changes
- `async def fetch_raw_sources(target_date) -> list[FetchResult]` — returns raw HTML/JSON, no markdown conversion

---

## Phase D: Pipeline & Renderers

**D1. Pipeline orchestrator**
- File: `src/pipeline.py`
- `PipelineResult` dataclass with `events: list[Event]` and `source_statuses: list[SourceStatus]`
- `async def run_pipeline(target_date) -> PipelineResult` — fetches all sources, dispatches to parsers, aggregates
- Each parser failure is caught and logged; doesn't crash the pipeline

**D2. Markdown renderer**
- File: `src/renderers/markdown_renderer.py`
- `render_markdown(events, source_statuses, date_str) -> str`
- Outputs: summary header + markdown table + sources footer
- Missing fields → em dash

**D3. HTML renderer**
- File: `src/renderers/html_renderer.py`
- `render_html(events, source_statuses, target_date) -> str`
- Self-contained: converts Event objects → dicts, generates full HTML with CSS and sortable-table JS inline

---

## Phase E: CLI & Integration

**E1. Unified CLI entry point**
- File: `src/__main__.py`
- Usage: `python3 -m src --date YYYY-MM-DD [--format markdown|html|both] [--output FILE]`
- Optional: `--cities CITY1,CITY2` for city filtering
- Runs pipeline → applies city filter → invokes renderer(s)

**E2. Update slash command**
- File: `.claude/commands/find-activities.md` (modify)
- Simplified flow: (1) Parse params from user query, (2) Run `python3 -m src`, (3) Present results
- LLM role reduced to: parameter parsing + optional type classification

**E3. Update CLAUDE.md and docs**
- Update commands, key files, architecture description
- Create `project_files/v3/plan.md` and `project_files/v3/tasks.md`

---

## Phase F: Cleanup & Refactor

**F1.** Remove legacy `scripts/` directory (fetch logic already in `src/fetch_sources.py`)
**F2.** Remove `html2text` dependency (no longer needed — parsers use BeautifulSoup on raw HTML)
**F3.** Clean up any deprecated code paths or stale duplicates

---

## New Dependency

- `beautifulsoup4` (import as `bs4`) — HTML parsing for source-specific parsers
- `html.parser` (stdlib) as the parser backend — no need for `lxml`

---

## File Manifest

```
src/
  __init__.py
  __main__.py
  models.py
  pipeline.py
  fetch_sources.py
  parsers/
    __init__.py
    do604.py
    dailyhive.py
    rhythmchanges.py
    showhub.py
    infidelsjazz.py
  renderers/
    __init__.py
    markdown_renderer.py
    html_renderer.py

tests/
  test_cli.py
  test_fetch_sources.py
  test_pipeline.py
  test_parsers/
    __init__.py
    test_do604.py
    test_dailyhive.py
    test_rhythmchanges.py
    test_showhub.py
    test_infidelsjazz.py
  test_renderers/
    __init__.py
    test_markdown.py
    test_html.py
  fixtures/
    do604_sample.html
    dailyhive_sample.html
    rhythmchanges_sample.html
    showhub_sample.html
    infidelsjazz_sample.json
```

---

## Verification

1. `pytest` — all existing + new tests pass (88 tests)
2. `pytest -m "not integration"` — unit tests only (no network)
3. `python3 -m src --date 2026-03-07` — end-to-end run, produces markdown + HTML
4. Compare output against a manual `/find-activities` run for the same date
5. Verify HTML report opens correctly in browser with sortable columns

---

## Implementation Order

```
A1 → A2 → B1 → B2 → B3 → B4 → B5 → C1 → D1 → D2 → D3 → E1 → E2 → E3 → F1-F4
      ↑                                ↑
  foundation                     can parallel with B3-B5
```

Work one parser at a time (TDD: write test first, then implement). After all parsers work, wire up the pipeline and renderers. CLI and slash command come last.
