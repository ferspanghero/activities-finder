"""CLI entry point: python3 -m src --from YYYY-MM-DD --to YYYY-MM-DD [--format markdown|html] [--output FILE]"""

import argparse
import asyncio
import logging
import sys
from datetime import date

from src.pipeline import run_pipeline
from src.renderers.markdown_renderer import render_markdown
from src.renderers.html_renderer import render_html, parse_time_to_minutes

logger = logging.getLogger(__name__)

MAX_RANGE_DAYS = 14


def main():
    parser = argparse.ArgumentParser(description="Deterministic event extraction pipeline")
    parser.add_argument("--from", dest="from_date", required=True, help="Start date in YYYY-MM-DD format")
    parser.add_argument("--to", dest="to_date", required=True, help="End date in YYYY-MM-DD format")
    parser.add_argument("--format", choices=["markdown", "html"], default="html",
                        help="Output format (default: html)")
    parser.add_argument("--output", help="Output file path (default: events-DATE.html or events-DATE.md)")
    parser.add_argument("--cities", help="Comma-separated list of cities to filter by")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )

    try:
        from_date = date.fromisoformat(args.from_date)
    except ValueError:
        logger.error("Invalid start date format '%s'. Use YYYY-MM-DD.", args.from_date)
        sys.exit(1)

    try:
        to_date = date.fromisoformat(args.to_date)
    except ValueError:
        logger.error("Invalid end date format '%s'. Use YYYY-MM-DD.", args.to_date)
        sys.exit(1)

    if from_date > to_date:
        logger.error("Start date %s is after end date %s.", from_date, to_date)
        sys.exit(1)

    range_days = (to_date - from_date).days + 1
    if range_days > MAX_RANGE_DAYS:
        logger.error("Date range of %d days exceeds maximum of %d days.", range_days, MAX_RANGE_DAYS)
        sys.exit(1)

    logger.info("Pipeline starting for %s to %s (%d days)", from_date, to_date, range_days)
    result = asyncio.run(run_pipeline(from_date, to_date))

    # Apply city filter if specified
    if args.cities:
        allowed = {c.strip() for c in args.cities.split(",")}
        before = len(result.events)
        result.events = [e for e in result.events if e.city and e.city in allowed]
        logger.info("City filter applied: %d → %d events", before, len(result.events))

    result.events.sort(key=lambda e: (e.event_date, parse_time_to_minutes(e.time)))

    ext = "md" if args.format == "markdown" else "html"
    if args.output:
        output_path = args.output
    elif from_date == to_date:
        output_path = f"events-{from_date.isoformat()}.{ext}"
    else:
        output_path = f"events-{from_date.isoformat()}_to_{to_date.isoformat()}.{ext}"

    if args.format == "markdown":
        content = render_markdown(result.events, result.source_statuses, from_date, to_date)
    else:
        content = render_html(result.events, result.source_statuses, from_date, to_date)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info("Exported to %s", output_path)


if __name__ == "__main__":
    main()
