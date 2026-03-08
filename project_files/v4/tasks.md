# v4 Tasks — Event Deduplication via Slash Command

## Revert API-based dedup

- [x] **R1**: Delete `src/dedup.py` and `tests/test_dedup.py`
- [x] **R2**: Remove `dedup` and `api_key` params from `run_pipeline()` in `src/pipeline.py`
- [x] **R3**: Remove `--dedupe` and `--llm-api-key` flags from `src/__main__.py`
- [x] **R4**: Uninstall `anthropic` dependency

## Slash Command Dedup

- [x] **S1**: Update `.claude/commands/find-activities.md` — add dedup step, format-agnostic export, output file editing

## Documentation

- [x] **D1**: Update `CLAUDE.md` — revert CLI docs, remove dedup module reference
- [x] **D2**: Update `project_files/overview.md` — note dedup in slash command
- [x] **D3**: Update `project_files/v4/plan.md` and `tasks.md`

## Verification

- [x] **V1**: All tests pass (`pytest`)
- [x] **V2**: CLI works without dedup flags
- [x] **V3**: `/find-activities` slash command deduplicates results
