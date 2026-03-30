# Find Activities

Search for events and activities across Metro Vancouver sources.

User query: $ARGUMENTS

## Step 1: Parse Parameters

Extract from the user query:

- **Date**: If the user specifies a single date, use it for both `--from` and `--to` (format: YYYY-MM-DD). If the user specifies a date range (e.g., "this weekend", "March 7-10"), resolve to `--from YYYY-MM-DD --to YYYY-MM-DD`. Default: today's date for both.
- **Cities**: Determine the mode:
  - No cities mentioned → no `--cities` flag (pipeline returns all cities)
  - "also include [cities]" → add those cities to the default city list from CLAUDE.md, pass as `--cities`
  - "only [cities]" → use only those cities, pass as `--cities`
- **Activity types**: If the user specifies types (e.g., "live music", "festivals"), note them for post-filtering.

State the resolved parameters before proceeding.

## Step 2: Fetch Events

Run the fetch step to get a compact event list and cache the data:

```bash
python3 -m src.compact fetch --from {YYYY-MM-DD} --to {YYYY-MM-DD} [--cities CITY1,CITY2,...]
```

This fetches all 6 sources in parallel, parses them, prints a compact numbered event list to stdout, and saves a JSON cache to `.events-cache.json`. No output file is created yet.

## Step 3: Deduplicate

Scan the compact event list from the Step 2 stdout output for duplicates — the same real-world event listed multiple times across different sources.

Rules:
- Same event at different times (e.g. 7:00 PM vs 9:30 PM) are NOT duplicates — they are separate shows.
- Different names for the same event at the same venue/time ARE duplicates (e.g. "Festival du Bois" and "37th Annual Festival du Bois").
- When removing a duplicate, keep the entry with the most complete information (city, address, time filled in).

Do NOT display a table or detailed list of duplicates — just state how many were found and removed.

Collect all duplicate indexes to remove, then render the clean file in one command:

```bash
python3 -m src.compact render .events-cache.json --exclude {INDEXES} --format {markdown|html} [--output {FILE}]
```

Choose `--format` and `--output` based on the user's query. Default: `--format html`. This removes the duplicates from the event list, renders the clean output file, and deletes the cache.

## Step 4: Present Results

Print a brief console summary only (do NOT print the full event table):
1. **Summary header**: "Found X events across Y cities from Z/6 sources"
2. **Duplicates**: "Removed N duplicates"
3. **Sources checked footer** with per-source event counts and errors

If the user specified activity types, filter the output file to only show matching event types and mention how many matched.

If no events match, say so clearly and suggest broadening the search.

## Step 5: Export

Confirm the output file path, then open it in Firefox.
