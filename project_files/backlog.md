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

### Freshet News — recommended (researched 2026-04-11)
- **URL:** `GET https://www.freshetnews.ca/wp-json/wp/v2/posts?slug=whats-on-{month}-{day}-{year}`
- **Type:** Hyper-local daily event listings (Burnaby, New Westminster, Tri-Cities)
- **Strategy:** WordPress REST API returns JSON with rendered HTML content. Parse event blocks from `content.rendered`.
- **Data quality:** Event name, time (regex: `\d{1,2}(?::\d{2})?\s*[ap]\.m\.`), venue, full address with city, price (sometimes), external link. Events separated by `<p>&nbsp;</p>` delimiters.
- **Overlap:** Low — community content (flea markets, library events, repair cafes, junior sports) not on aggregators.
- **Volume:** ~10-15 events/day.
- **Effort:** Medium-high. Prose parsing with regex, but consistent formatting within posts.

### Kids Out and About Vancouver — recommended (researched 2026-04-11)
- **URL:** `https://vancouver.kidsoutandabout.com/event-list/{YYYY-MM-DD}`
- **Type:** Family/kids event listings
- **Strategy:** HTML scrape (Drupal 7 Views, server-rendered). Per-day URL, same pattern as Do604.
- **Data quality:** Event name (`h2 > a`), full address with postal code (`field-name-field-venue-places-api`), dates (`span.date-display-single`, MM/DD/YYYY), time (`field-name-field-time`), organization name (embedded `dataLayer`).
- **Overlap:** Low — storytimes, kids workshops, family festivals not on Do604/Daily Hive.
- **Volume:** ~16 events/Saturday, fewer on weekdays.
- **Effort:** Low. Clean Drupal Views markup with consistent CSS field classes.

### City of Burnaby — recommended (researched 2026-04-11)
- **URL:** `https://www.burnaby.ca/recreation-and-arts/events?date_start={YYYY-MM-DD}&date_end={YYYY-MM-DD}`
- **Type:** Municipal event calendar (community, arts, recreation, civic)
- **Strategy:** HTML scrape (Drupal, server-rendered). URL-based date range filtering with pagination (`&page=0`).
- **Data quality:** Event name (`h2.events-item__title`), date (`div.events-item__date`), category (`li.events-item__tags__tag`), description, location. Detail pages add exact address, time.
- **Overlap:** Low — civic/community events (flea markets, art exhibitions, dance, theatre).
- **Volume:** ~30 events/month.
- **Effort:** Low. Clean BEM-style CSS classes.

### City of New Westminster — recommended (researched 2026-04-11)
- **URL:** `https://www.newwestcity.ca/calendar-of-events/main/177/events/{YYYY-MM}.php`
- **Type:** Municipal event calendar
- **Strategy:** HTML scrape (Smallbox CMS, server-rendered). Monthly URL pattern, client-side date filtering.
- **Data quality:** Event name (`h2.title`), date (start/end in `div.date-group`), cost (`div.cost`), description. Detail pages add time, venue, full address.
- **Overlap:** Low — community events, gallery exhibitions, theatre, civic events.
- **Volume:** ~27-30 events/month.
- **Effort:** Low-medium. Semantic HTML classes, may need detail page fetches.

### Noms Magazine — conditional (researched 2026-04-11)
- **URL:** `GET https://www.nomsmagazine.com/wp-json/wp/v2/posts?search=things+to+do+in+vancouver+this+weekend&per_page=1`
- **Type:** Food/drink weekend event roundups
- **Strategy:** WordPress REST API. Parse event blocks from `content.rendered` — `<h2>` names, `<strong>Date/Address/Cost</strong>:` patterns.
- **Data quality:** Event name, date, full address with postal code, cost, description, external link.
- **Overlap:** Moderate with Do604/Daily Hive. Unique food/drink curation.
- **Volume:** ~9-12 events/week (Friday roundups only).
- **Effort:** Medium. Well-structured but editorial template could change. Weekly cadence limits value.

### Other candidates (not researched in depth)
- **Eventbrite API** — REST API with OAuth. Community events, workshops, niche gatherings. Good data but auth setup required.
- **604 Now** (`604now.com/events`) — Hybrid rendered, event cards with categories. Needs detail page scraping for venue/address.

### Evaluated and rejected
- **Bandsintown** — API is artist-centric only, can't query by city/date.
- **Songkick** — API locked behind licensing fees, not accepting new applications.
- **AllEvents.in** — Fully JS-rendered (Vue.js), needs headless browser.
- **Destination Vancouver** — Next.js SPA, curated highlights only (~10 events), low volume.
- **To Do Canada** — 403 blocked fetches, anti-bot protections.
- **SeatGeek** (researched 2026-04-11) — Website blocked by DataDome anti-bot (403 + CAPTCHA). Public REST API exists with excellent data (city/date/geo filtering, venue details, pricing, categories) but requires developer credentials. Approval process appears broken — multiple users stuck "pending" for 1+ year with no SeatGeek response. Revisit if credentials become obtainable.
- **Miss604.com** (researched 2026-04-11) — Server-rendered WordPress, WP REST API works. Weekend roundups list ~90 events, but data per event is too thin: name + link only, no time/venue/address/city. Events would appear with mostly blank fields. High overlap with Do604/Daily Hive.
- **Peace Arch News** (researched 2026-04-11) — No event calendar or structured event data. Events only mentioned incidentally in news article prose. WP API exists but contains only news articles. Would require NLP to extract details.
- **Healthy Family Living** (researched 2026-04-11) — Editorial blog with monthly roundup posts. Freeform `<li>` items with inconsistent formatting, no structured event data, no date-filtered URLs. Kids Out and About covers the same family event niche with structured, parseable data.
- **Vancouver Is Awesome** (researched 2026-04-11) — Triple-blocked: (1) Cloudflare bot protection on all pages, (2) event calendar is a JS-rendered Evvnt widget, (3) Evvnt API requires partner credentials. Owned by Glacier/Lodestar Media (separate from Daily Hive/ZoomerMedia).
- **Municipal calendars** (researched 2026-04-11) — Most city sites are not viable:
  - *Vancouver* — 403 Forbidden on all calendar URLs (WAF/CDN blocks non-browser requests).
  - *Surrey* — 403 on main domain, 404 on event paths.
  - *Coquitlam* — Static page listing annual festival names, not a dated calendar. visitcoquitlam.ca returns 403.
  - *Port Moody* — External ecalendar platform (GovStack) is a fully JS-rendered SPA.
  - *Richmond* — First page of events is server-rendered, but pagination and date filtering require ASP.NET postbacks with 101KB ViewState. Too fragile.
  - *West Vancouver / North Vancouver District* — 403 Forbidden / ECONNREFUSED.

## Pipeline improvements

- Add retry logic to `fetch_raw_sources` — a single transient failure (e.g., 503) drops all events from that source; one retry with short delay would help
- Improve city name discovery — ShowHub and Rhythm Changes have no city, only venue names. Could map known venues to cities.
- Explore source URL subsections for targeted fetching (e.g., do604.com/events/music/today)

## Infrastructure

- Custom MCP server for caching and programmatic dedup
- **Web app / hosted service** — A hosted page with input filters (date, event types, cities, sources). Runs the pipeline + LLM dedup on demand, renders results in the browser. Turns the CLI tool into a self-service app accessible from any device (phone, tablet). Could be a simple Flask/FastAPI backend serving the existing HTML renderer output, with a lightweight form UI for parameters.
