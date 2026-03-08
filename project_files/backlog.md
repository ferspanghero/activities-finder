# Backlog

Ideas and future enhancements — not scheduled.

## New sources

### Georgia Straight — recommended next source (researched 2026-03-08)
- **URL:** `https://www.straight.com/listings/thingstodo/{YYYY}-{MM}-{DD}`
- **Type:** Broad local aggregator — theatre, film, galleries, markets, dance, comedy, literary, community events
- **Strategy:** HTML scrape (server-rendered Drupal). Date-based URL filtering. ~25 events/page with pagination.
- **Data quality:** Name, venue, category from listing page. Time, address, city on detail pages (extra HTTP requests needed).
- **Overlap tested:** 63% new content (17/27 unique for Mar 8). Fills gaps in theatre, galleries, markets, dance, literary.
- **Effort:** Low-medium. Standard HTML scrape, follows existing parser pattern.
- **HTML structure (observed, needs confirmation with real aiohttp fetch):**
  - Events: `<h2>` inside `<a href="/listings/events/{ID}">`
  - Venue: `<p>` tag after the title link
  - Category: `<a href="/listings/events/{category-slug}">`
  - Images: class `gs_thumbnail`
- **Detail pages** (e.g. `/listings/events/1463555`): have full data — street address, city, time, description, ticket link. Could be scraped async for richer data in a future iteration.

### Other candidates (not researched in depth)
- **Eventbrite API** — REST API with OAuth. Community events, workshops, niche gatherings. Good data but auth setup required.
- **604 Now** (`604now.com/events`) — Hybrid rendered, event cards with categories. Needs detail page scraping for venue/address.

### Evaluated and rejected
- **Bandsintown** — API is artist-centric only, can't query by city/date.
- **Songkick** — API locked behind licensing fees, not accepting new applications.
- **AllEvents.in** — Fully JS-rendered (Vue.js), needs headless browser.
- **Destination Vancouver** — Next.js SPA, curated highlights only (~10 events), low volume.
- **To Do Canada** — 403 blocked fetches, anti-bot protections.

## Pipeline improvements

- Date range support ("this weekend", "next 7 days")
- Add retry logic to `fetch_raw_sources` — a single transient failure (e.g., 503) drops all events from that source; one retry with short delay would help
- Improve city name discovery — ShowHub and Rhythm Changes have no city, only venue names. Could map known venues to cities.
- Explore source URL subsections for targeted fetching (e.g., do604.com/events/music/today)

## Infrastructure

- Custom MCP server for caching and programmatic dedup
- **Web app / hosted service** — A hosted page with input filters (date, event types, cities, sources). Runs the pipeline + LLM dedup on demand, renders results in the browser. Turns the CLI tool into a self-service app accessible from any device (phone, tablet). Could be a simple Flask/FastAPI backend serving the existing HTML renderer output, with a lightweight form UI for parameters.
