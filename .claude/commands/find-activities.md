# Find Activities

Search for events and activities across Metro Vancouver sources.

User query: $ARGUMENTS

## Step 1: Parse Parameters

Extract from the user query:

- **Date**: If the user specifies a date, use it (format: YYYY-MM-DD). Default: today's date.
- **Cities**: Determine the mode:
  - No cities mentioned → no `--cities` flag (pipeline returns all cities)
  - "also include [cities]" → add those cities to the default city list from CLAUDE.md, pass as `--cities`
  - "only [cities]" → use only those cities, pass as `--cities`
- **Activity types**: If the user specifies types (e.g., "live music", "festivals"), note them for post-filtering.

State the resolved parameters before proceeding.

## Step 2: Run Pipeline

Run the deterministic extraction pipeline:

```bash
python3 -m src --date {YYYY-MM-DD} --format both [--cities CITY1,CITY2,...] [--output events-{YYYY-MM-DD}.html]
```

This fetches all 5 sources in parallel, parses them with source-specific parsers, and outputs:
- A markdown table to stdout
- An HTML report file

## Step 3: Present Results

The pipeline output already contains:
1. **Summary header**: "Found X events across Y cities from Z/5 sources"
2. **Event table** in markdown format
3. **Sources checked footer** with event counts and errors

Present the pipeline output to the user.

If the user specified activity types, filter the results to only show matching event types based on event names.

If no events match, say so clearly and suggest broadening the search.

## Step 4: Confirm HTML Export

Confirm: "HTML report saved to `events-{YYYY-MM-DD}.html`"
