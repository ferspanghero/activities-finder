# Backlog

Ideas and future enhancements — not scheduled, just a laundry list.

- Deduplication command/skill — separate pass to tidy up raw results, merge duplicates across sources
- Custom MCP server for caching and programmatic dedup
- Add more local sources (venue websites, city tourism pages, brewery/winery/restaurant sites)
- Date range support ("this weekend", "next 7 days")
- Explore source URL subsections for targeted fetching (e.g., do604.com/events/music/today)
- Add retry logic to `fetch_raw_sources` — a single transient network failure (e.g., 503) results in 0 events from that source for the entire run; one retry with a short delay would improve reliability
