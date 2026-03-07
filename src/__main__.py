"""CLI entry point: python3 -m src --date YYYY-MM-DD [--format markdown|html|both] [--output FILE]"""

import argparse
import asyncio
import sys
from datetime import date

from src.pipeline import run_pipeline
from src.renderers.markdown_renderer import render_markdown
from src.renderers.html_renderer import render_html


def main():
    parser = argparse.ArgumentParser(description="Deterministic event extraction pipeline")
    parser.add_argument("--date", required=True, help="Target date in YYYY-MM-DD format")
    parser.add_argument("--format", choices=["markdown", "html", "both"], default="both",
                        help="Output format (default: both)")
    parser.add_argument("--output", help="Output file path for HTML (default: events-DATE.html)")
    parser.add_argument("--cities", help="Comma-separated list of cities to filter by")
    args = parser.parse_args()

    try:
        target_date = date.fromisoformat(args.date)
    except ValueError:
        print(f"Error: Invalid date format '{args.date}'. Use YYYY-MM-DD.", file=sys.stderr)
        sys.exit(1)

    result = asyncio.run(run_pipeline(target_date))

    # Apply city filter if specified
    if args.cities:
        allowed = {c.strip() for c in args.cities.split(",")}
        result.events = [e for e in result.events if e.city and e.city in allowed]

    date_str = target_date.isoformat()

    if args.format in ("markdown", "both"):
        md = render_markdown(result.events, result.source_statuses, date_str)
        print(md)

    if args.format in ("html", "both"):
        html_content = render_html(result.events, result.source_statuses, date_str)
        output_path = args.output or f"events-{date_str}.html"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"HTML exported to {output_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
