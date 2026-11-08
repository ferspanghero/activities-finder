"""CLI entry point: python3 -m src --from YYYY-MM-DD --to YYYY-MM-DD [--format markdown|html] [--output FILE]"""

import argparse
import asyncio
import logging
import sys

from src.cli_utils import (
    VENUE_CACHE,
    FilterOptions,
    add_filter_arguments,
    build_output_path,
    finalize_events,
    parse_and_validate_dates,
    recount_sources,
    validate_filter_options,
)
from src.pipeline import run_pipeline
from src.renderers.html_renderer import render_html
from src.renderers.markdown_renderer import render_markdown

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Deterministic event extraction pipeline")
    parser.add_argument("--from", dest="from_date", required=True, help="Start date in YYYY-MM-DD format")
    parser.add_argument("--to", dest="to_date", required=True, help="End date in YYYY-MM-DD format")
    parser.add_argument("--format", choices=["markdown", "html"], default="html",
                        help="Output format (default: html)")
    parser.add_argument("--output", help="Output file path (default: events-DATE.html or events-DATE.md)")
    add_filter_arguments(parser)
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )
    logging.getLogger("aiohttp").setLevel(logging.WARNING)

    from_date, to_date = parse_and_validate_dates(args.from_date, args.to_date)
    options = FilterOptions(cities=args.cities, add_cities=args.add_cities, types=args.types)

    try:
        validate_filter_options(options)
    except ValueError as e:
        parser.error(str(e))

    range_days = (to_date - from_date).days + 1
    logger.info("Pipeline starting for %s to %s (%d days)", from_date, to_date, range_days)
    result = asyncio.run(run_pipeline(from_date, to_date, venue_cache=VENUE_CACHE))
    deduped = finalize_events(result.events, options)
    statuses = recount_sources(deduped.events, result.source_statuses)
    logger.info("Merged %d duplicates", deduped.removed)

    output_path = build_output_path(from_date, to_date, args.format, args.output)

    if args.format == "markdown":
        content = render_markdown(deduped.events, statuses, from_date, to_date)
    else:
        content = render_html(deduped.events, statuses, from_date, to_date)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info("Exported to %s", output_path)


if __name__ == "__main__":
    main()
