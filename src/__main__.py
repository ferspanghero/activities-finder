"""CLI entry point: python3 -m src --date YYYY-MM-DD [--format markdown|html|both] [--output FILE]"""

import argparse
import asyncio
import logging
import sys
from datetime import date

from src.pipeline import run_pipeline
from src.renderers.markdown_renderer import render_markdown
from src.renderers.html_renderer import render_html

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Deterministic event extraction pipeline")
    parser.add_argument("--date", required=True, help="Target date in YYYY-MM-DD format")
    parser.add_argument("--format", choices=["markdown", "html", "both"], default="both",
                        help="Output format (default: both)")
    parser.add_argument("--output", help="Output file path for HTML (default: events-DATE.html)")
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
        target_date = date.fromisoformat(args.date)
    except ValueError:
        logger.error("Invalid date format '%s'. Use YYYY-MM-DD.", args.date)
        sys.exit(1)

    logger.info("Pipeline starting for %s", target_date)
    result = asyncio.run(run_pipeline(target_date))

    # Apply city filter if specified
    if args.cities:
        allowed = {c.strip() for c in args.cities.split(",")}
        before = len(result.events)
        result.events = [e for e in result.events if e.city and e.city in allowed]
        logger.info("City filter applied: %d → %d events", before, len(result.events))

    date_str = target_date.isoformat()

    if args.format in ("markdown", "both"):
        md = render_markdown(result.events, result.source_statuses, date_str)
        print(md)

    if args.format in ("html", "both"):
        html_content = render_html(result.events, result.source_statuses, date_str)
        output_path = args.output or f"events-{date_str}.html"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info("HTML exported to %s", output_path)


if __name__ == "__main__":
    main()
