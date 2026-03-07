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
python3 -m src --date {YYYY-MM-DD} --format {markdown|html} [--cities CITY1,CITY2,...] [--output {FILE}]
```

Choose `--format` and `--output` based on the user's query. Default: `--format html` with `--output events-{YYYY-MM-DD}.html`.

This fetches all 5 sources in parallel, parses them with source-specific parsers, and writes the output file.

## Step 3: Deduplicate

Read the output file produced in Step 2, then scan the event table for duplicates — the same real-world event listed multiple times across different sources.

Rules:
- Same event at different times (e.g. 7:00 PM vs 9:30 PM) are NOT duplicates — they are separate shows.
- Different names for the same event at the same venue/time ARE duplicates (e.g. "Festival du Bois" and "37th Annual Festival du Bois").
- When removing a duplicate, keep the entry with the most complete information (city, address, time filled in).

Remove duplicates from the table and update the event count in the summary header.

After deduplicating, edit the output file to remove the same duplicate entries and update the event count. This works for any format — remove `<tr>` rows in HTML, table rows in markdown. Do not leave blank lines where removed rows were — the table must remain contiguous.

## Step 4: Present Results

Present the deduplicated output to the user:
1. **Summary header**: "Found X events across Y cities from Z/5 sources"
2. **Event table** in markdown format
3. **Sources checked footer** with event counts and errors

If the user specified activity types, filter the results to only show matching event types based on event names.

If no events match, say so clearly and suggest broadening the search.

## Step 5: Confirm Export

Confirm the output file path and note that it has been updated with deduplicated results.
