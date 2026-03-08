# v2 Tasks — HTML Export

## HTML Generator Script

- [x] **T1**: Create `scripts/generate_html.py` with JSON input schema and CLI (`--output` flag)
- [x] **T2**: Implement `format_date_display()` — ISO date to human-readable
- [x] **T3**: Implement `escape_and_format()` — HTML escaping with em-dash fallback
- [x] **T4**: Implement `build_event_row()` — single `<tr>` from event dict
- [x] **T5**: Implement `build_sources_footer()` — source counts with error handling
- [x] **T6**: Implement `generate_html()` — full HTML assembly with template
- [x] **T7**: Add inline CSS (system fonts, zebra striping, sticky header, responsive)
- [x] **T8**: Add inline JS for sortable columns (click header to toggle asc/desc)
- [x] **T9**: Add time column numeric sort via `data-sort-value`

## Tests

- [x] **T10**: Create `tests/test_generate_html.py` with shared fixtures
- [x] **T11**: Pure function tests (format_date_display, escape_and_format, build_event_row, build_sources_footer)
- [x] **T12**: HTML generation tests (summary, events, footer, style/script tags, structure, empty events, special chars)
- [x] **T13**: CLI tests (valid JSON → file, invalid JSON → error)

## Integration

- [x] **T14**: Update `.claude/commands/find-activities.md` — add Step 6 for HTML export
- [x] **T15**: Update `.gitignore` — add `events-*.html`
- [x] **T16**: Update `CLAUDE.md` — add HTML export to output format, key files, commands

## Manual QA

- [x] **T17**: Run `generate_html.py` with sample JSON, open HTML in browser, verify table renders
- [x] **T18**: Verify column sorting works (all columns, asc/desc toggle)
- [x] **T19**: Verify source links open in new tabs
- [x] **T20**: Run `/find-activities` end-to-end, verify both markdown and HTML output
