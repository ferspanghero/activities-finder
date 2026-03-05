# Implementation Plan

## Output

Two files:
- `CLAUDE.md` — Agent configuration (cities, activity types, sources, behavior rules)
- `.claude/commands/find-activities.md` — Slash command with search procedure

---

## Step 1: CLAUDE.md — Default City List

Define the curated Metro Vancouver city list that serves as the default search scope:

```
Vancouver, Burnaby, New Westminster, Richmond, North Vancouver (City),
Lynn Valley, Deep Cove, West Vancouver, Horseshoe Bay, Surrey, White Rock,
Port Moody, Port Coquitlam, Coquitlam, Langley (City), Langley (Township),
Delta, Pitt Meadows, Maple Ridge, Mission, Abbotsford, Chilliwack, Squamish,
Anmore, Belcarra
```

Document the three city modes:
1. No cities specified -> use full default list
2. User says "also include [cities]" -> add to default list
3. User says "only [cities]" -> replace default list entirely

---

## Step 2: CLAUDE.md — Activity Types

Define the 8 activity categories:

1. Live music
2. Festivals
3. Sports events
4. Art exhibitions / gallery openings
5. Food/drink events (tastings, markets)
6. Outdoor activities (hikes, group runs)
7. Community events (markets, fairs)
8. Trivia nights / pub events

Default behavior: search all types. User narrows by specifying types in their query.

---

## Step 3: CLAUDE.md — Source List

Define the 14 curated sources with their URLs:

**Local aggregators:**
- https://do604.com/events/
- https://604now.com/events
- https://miss604.com/events/
- dailyhive.com/vancouver/listed

**Venue/genre-specific:**
- vancouvercivictheatres.com/events/
- rhythmchanges.ca/gigs/
- theinfidelsjazz.ca/events/list/

**Broad aggregators:**
- showhub.ca/weekly-listings/ (live music at bars/breweries/venues)
- vancouversbestplaces.com/events-calendar/ (broad events)
- straight.com/listings/events (Georgia Straight)
- vancouverisawesome.com/local-events (event calendar)
- thefraservalley.ca/events-directory/ (Fraser Valley: Langley, Abbotsford, etc.)
- destinationvancouver.com/explore-vancouver/events (tourism/major events)
- songkick.com/metro-areas/27398-canada-vancouver (concerts/touring artists)

Each source is fetched directly via WebFetch. No broad web search.

---

## Step 4: CLAUDE.md — Behavior Rules

- Be exhaustive: check ALL sources, don't stop early
- Include both free and ticketed events
- Note if venues are closed due to holidays
- Search for both scheduled events AND regular recurring programming
- Date filtering is exact (only the specified date, default today)
- If a source is unreachable, note it and continue with remaining sources

---

## Step 5: CLAUDE.md — Output Format

Define the output table format:

```
| Event Name | City | Exact Address | Time | Source Link |
|---|---|---|---|---|
```

---

## Step 6: Slash Command — Parameter Parsing

`.claude/commands/find-activities.md` starts by instructing Claude to parse:

- **Date**: from user query, default to today's date
- **Cities**: determine mode (default / additive / override) based on user phrasing
- **Activity types**: from user query, default to all types
- **Venue types**: from user query, default to no venue filter

---

## Step 7: Slash Command — Source Fetching

For each source in the curated list:
1. Construct the appropriate URL (some sources may need date-specific URLs)
2. WebFetch the page
3. If fetch fails, note the source as unreachable and continue

---

## Step 8: Slash Command — Event Extraction

For each fetched page:
1. Parse the page content to identify individual events
2. Extract: event name, location/city, exact address (if available), time, event page URL
3. Categorize by activity type based on content

---

## Step 9: Slash Command — Filtering

Apply filters in order:
1. **Date**: keep only events matching the target date exactly
2. **City**: keep only events in the resolved city list
3. **Activity type**: if specified, keep only matching categories

---

## Step 10: Slash Command — Deduplication

Identify duplicate events across sources:
- Same event name + same venue + same date = duplicate
- Keep the entry with the most complete information (address, time)
- Note in Source Link column if found on multiple sources

---

## Step 11: Slash Command — Output

Format results as the markdown table. Group by city if results span multiple cities. Include:
- Summary line: "Found X events across Y cities from Z sources"
- The table
- Notes about any unreachable sources
- Notes about any venues closed for holidays

---

## Step 12: Ground Truth Testing

Build a regression test baseline:
1. Run `/find-activities` for a past date (Feb 28, 2026 and March 1, 2026)
2. Store the full output (all events found, from all sources)
3. User reviews and validates the output manually
4. This becomes the "golden" dataset — future prompt changes must still retrieve these same events
5. If a prompt change causes events to be missed, the diff highlights what broke

---

## Future Enhancements (not v1)

- Custom MCP server for parallel fetching, caching, and programmatic dedup
- Add general aggregators (Eventbrite, Ticketmaster, SeatGeek, Bandsintown)
- Add more local sources (venue websites, city tourism pages)
- Save results to file for reference
- Date range support ("this weekend", "next 7 days")
- Explore source URL subsections for targeted fetching (e.g., do604.com/events/music/today instead of do604.com)
