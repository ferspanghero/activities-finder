# Find Activities

Search for events and activities across Metro Vancouver sources.

User query: $ARGUMENTS

## Step 1: Parse Parameters

Extract from the user query:

- **Date**: If the user specifies a date, use it (format: YYYY-MM-DD). Default: today's date.
- **Cities**: Determine the mode:
  - No cities mentioned → use the full default city list from CLAUDE.md
  - "also include [cities]" → add those cities to the default list
  - "only [cities]" → use only those cities, ignore the default list
- **Activity types**: If the user specifies types (e.g., "live music", "festivals"), filter to those. Default: all types.

State the resolved parameters before proceeding.

## Step 2: Fetch Sources

Run the fetch script with the resolved date:

```bash
python3 -m scripts.fetch_sources --date {YYYY-MM-DD}
```

This fetches all 5 sources in parallel and outputs raw content with `=== SOURCE: Name (url) ===` delimiters.

## Step 3: Extract Events

For each source section in the output:

1. Identify individual events in the content
2. For each event, extract:
   - **Event name**
   - **City** (or location/neighbourhood)
   - **Exact address** (if available)
   - **Time** (start time, or time range)
   - **Source link** (event page URL if available, otherwise the source URL from the delimiter)
3. Categorize by activity type based on the event description/name

For sources without date filtering in the URL (Rhythm Changes, ShowHub):
- Only extract events that match the target date exactly
- For Rhythm Changes, the output includes a week hint — focus on events in that week, then filter to the exact target date

For Daily Hive:
- Check that multi-day events actually occur on the target date

## Step 4: Filter

Apply filters in order:
1. **City**: Keep only events in the resolved city list
2. **Activity type**: If the user specified types, keep only matching categories

## Step 5: Output

Present the results using the format from CLAUDE.md:

1. **Summary header**: "Found X events across Y cities from Z/5 sources"
2. **Event table** grouped by city (if results span multiple cities):

| Event Name | City | Exact Address | Time | Source Link |
|---|---|---|---|---|

3. **Sources checked footer** with event counts per source and any errors:
```
Sources checked: Do604 (12), Daily Hive (8), Rhythm Changes (5), ShowHub (3), Infidels Jazz (1)
```

If a source had an error, show it: `Rhythm Changes (ERROR: Connection timeout)`

If no events match the filters, say so clearly and suggest broadening the search.
