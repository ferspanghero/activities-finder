# v2 Implementation Plan — HTML Export

## Goal

Add HTML export to `/find-activities` so results can be opened in a browser with sortable columns and clickable links.

## Architecture

The slash command already produces structured event data (name, city, address, time, source) before formatting it as markdown. A new Python script (`scripts/generate_html.py`) takes this data as JSON on stdin and outputs a self-contained HTML file.

```
/find-activities "March 8, only Burnaby"
  → Steps 1-4: same as v1 (fetch, extract, filter)
  → Step 5: Claude outputs markdown table in conversation (unchanged)
  → Step 6 (new): Claude serializes events as JSON, pipes to generate_html.py
  → Output: events-2026-03-08.html
```

### Why JSON as input (not markdown)

Claude has the structured data as separate fields before formatting to markdown. Serializing to JSON is trivial. Parsing markdown tables back into structured data would be fragile (pipes in content, em-dashes, markdown link syntax, city headers). JSON is unambiguous, testable, and needs no extra dependencies.

## Output

New deliverables:
- `scripts/generate_html.py` — HTML generator (JSON stdin → HTML file)
- `tests/test_generate_html.py` — unit + CLI tests
- Updated `.claude/commands/find-activities.md` — Step 6 for HTML export
- Updated `CLAUDE.md` — HTML export docs, updated key files/commands

---

## Script: `scripts/generate_html.py`

**CLI:** `echo '<json>' | python3 -m scripts.generate_html --output events-2026-03-08.html`

**JSON input schema:**
```json
{
  "date": "2026-03-08",
  "summary": { "total_events": 3, "total_cities": 1, "sources_reporting": 3, "sources_total": 5 },
  "events": [
    { "name": "...", "city": "...", "address": "..." or null, "time": "5:00 PM", "source_name": "Do604", "source_url": "https://..." }
  ],
  "sources": [
    { "name": "Do604", "count": 1, "error": null },
    { "name": "Rhythm Changes", "count": 0, "error": "Connection timeout" }
  ]
}
```

**Key functions:**
- `format_date_display(iso_date)` — "2026-03-08" → "Sunday, March 8, 2026"
- `escape_and_format(value)` — None/empty → em-dash, otherwise html.escape()
- `build_event_row(event)` — returns one `<tr>`
- `build_sources_footer(sources)` — "Do604 (1), Rhythm Changes (ERROR: ...)"
- `generate_html(data)` — assembles full HTML from template + data

**HTML features:**
- Self-contained (inline CSS + JS, no external dependencies)
- Same structure as CLAUDE.md output format: summary header → event table → sources footer
- Sortable columns via vanilla JS: click `<th>` to toggle asc/desc
- Time column: `data-sort-value` with minutes since midnight for numeric sorting
- Source links: `<a target="_blank" rel="noopener noreferrer">`
- CSS: system font stack, zebra striping, sticky header, hover highlight, responsive
- All user text HTML-escaped
- Empty events → "No events found" message

---

## Slash Command Update

Add Step 6 to `.claude/commands/find-activities.md`:

1. Build JSON from the parsed events (same data used for the markdown table)
2. Pipe to: `python3 -m scripts.generate_html --output events-{YYYY-MM-DD}.html`
3. Confirm export to user

---

## Tests: `tests/test_generate_html.py`

**Pure function tests:** format_date_display, escape_and_format, build_event_row, build_sources_footer

**HTML generation tests:** contains summary, all events, footer, style/script tags, valid structure, empty events, special chars escaped

**CLI tests:** valid JSON produces file, invalid JSON exits non-zero
