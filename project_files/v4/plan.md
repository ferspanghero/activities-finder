# v4 Implementation Plan — Event Deduplication via Slash Command

## Goal

Add deduplication of events that appear across multiple sources with different names. Instead of using an external API call, dedup happens in the `/find-activities` slash command using the current Claude Code session — no API key needed, no extra billing.

## Architecture

```
Pipeline (deterministic):  fetch → parse → list[Event] → renderers → output
Slash command:             run pipeline → deduplicate output → present to user
```

The Python pipeline stays purely deterministic. Deduplication is a post-processing step performed by the LLM in the slash command, which scans the event output for duplicate entries, presents deduplicated results, and edits the output file to match.

## Implementation

### 1. Update slash command

File: `.claude/commands/find-activities.md`

Add a dedup step (Step 3) between running the pipeline and presenting results:
- Scan the event table for same real-world event listed under different names/sources
- Rules: different times = separate shows, different names at same venue/time = duplicates
- Keep the entry with the most complete information
- Update summary event count
- Edit the output file to remove the same duplicates and update counts

### 2. Remove API-based dedup (reverted from earlier attempt)

- Delete `src/dedup.py` and `tests/test_dedup.py`
- Remove `--dedupe` and `--llm-api-key` CLI flags
- Remove `anthropic` dependency

## Verification

1. `pytest` — all tests pass
2. `python3 -m src --date 2026-03-07 --format html` — CLI works, no dedup flags
3. `/find-activities for March 7th` — slash command deduplicates results
