"""Generates a self-contained HTML event report from JSON input."""

import html
import json
import re
import sys
from datetime import date


def format_date_display(iso_date: str) -> str:
    """'2026-03-08' -> 'Sunday, March 8, 2026'"""
    d = date.fromisoformat(iso_date)
    return d.strftime("%A, %B %-d, %Y")


def escape_and_format(value: str | None) -> str:
    """HTML-escape a value. None or empty string becomes an em-dash."""
    if not value:
        return "\u2014"
    return html.escape(value, quote=True)


def parse_time_to_minutes(time_str: str | None) -> int:
    """Parse a time string like '8:00 PM' to minutes since midnight for sorting."""
    if not time_str:
        return 0
    match = re.match(r"(\d{1,2}):(\d{2})\s*(AM|PM)", time_str.strip(), re.IGNORECASE)
    if not match:
        return 0
    hour, minute, period = int(match.group(1)), int(match.group(2)), match.group(3).upper()
    if period == "AM" and hour == 12:
        hour = 0
    elif period == "PM" and hour != 12:
        hour += 12
    return hour * 60 + minute


def build_event_row(event: dict) -> str:
    name = escape_and_format(event.get("name"))
    city = escape_and_format(event.get("city"))
    address = escape_and_format(event.get("address"))
    time = escape_and_format(event.get("time"))
    sort_value = parse_time_to_minutes(event.get("time"))
    source_name = html.escape(event.get("source_name", ""), quote=True)
    source_url = html.escape(event.get("source_url", ""), quote=True)

    return (
        f"<tr>"
        f"<td>{name}</td>"
        f"<td>{city}</td>"
        f"<td>{address}</td>"
        f'<td data-sort-value="{sort_value}">{time}</td>'
        f'<td><a href="{source_url}" target="_blank" rel="noopener noreferrer">{source_name}</a></td>'
        f"</tr>"
    )


def build_sources_footer(sources: list[dict]) -> str:
    parts = []
    for s in sources:
        if s.get("error"):
            parts.append(f"{s['name']} (ERROR: {s['error']})")
        else:
            parts.append(f"{s['name']} ({s['count']})")
    return "Sources checked: " + ", ".join(parts)


def generate_html(data: dict) -> str:
    date_display = format_date_display(data["date"])
    summary = data["summary"]
    events = data["events"]
    sources = data["sources"]

    summary_text = (
        f"Found {summary['total_events']} events across {summary['total_cities']} "
        f"cities from {summary['sources_reporting']}/{summary['sources_total']} sources"
    )
    footer_text = build_sources_footer(sources)

    if events:
        rows = "\n".join(build_event_row(e) for e in events)
        table_html = f"""<div class="table-wrap">
<table id="events-table">
<thead>
<tr>
<th data-col="0">Event Name <span class="sort-arrow"></span></th>
<th data-col="1">City <span class="sort-arrow"></span></th>
<th data-col="2">Exact Address <span class="sort-arrow"></span></th>
<th data-col="3">Time <span class="sort-arrow"></span></th>
<th data-col="4">Source <span class="sort-arrow"></span></th>
</tr>
</thead>
<tbody>
{rows}
</tbody>
</table>
</div>"""
    else:
        table_html = '<p class="no-events">No events found for this date.</p>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Events for {date_display}</title>
<style>
*,*::before,*::after{{box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;margin:0;padding:20px;background:#f8f9fa;color:#212529}}
.container{{max-width:1200px;margin:0 auto}}
h1{{margin:0 0 4px;font-size:1.6rem}}
.summary{{color:#495057;margin:0 0 16px;font-size:1rem}}
.table-wrap{{overflow-x:auto}}
table{{width:100%;border-collapse:collapse;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.1)}}
thead{{position:sticky;top:0;z-index:1}}
th{{background:#343a40;color:#fff;padding:10px 12px;text-align:left;cursor:pointer;user-select:none;white-space:nowrap}}
th:hover{{background:#495057}}
.sort-arrow{{font-size:.75rem;margin-left:4px}}
td{{padding:8px 12px;border-bottom:1px solid #dee2e6}}
tbody tr:nth-child(even){{background:#f8f9fa}}
tbody tr:hover{{background:#e9ecef}}
a{{color:#0d6efd;text-decoration:none}}
a:hover{{text-decoration:underline}}
.footer{{margin-top:16px;color:#6c757d;font-size:.875rem}}
.no-events{{text-align:center;color:#6c757d;padding:40px 0;font-size:1.1rem}}
</style>
</head>
<body>
<div class="container">
<h1>Events for {date_display}</h1>
<p class="summary">{summary_text}</p>
{table_html}
<p class="footer">{footer_text}</p>
</div>
<script>
(function(){{
  const table=document.getElementById("events-table");
  if(!table)return;
  const headers=table.querySelectorAll("th");
  let sortCol=-1,sortAsc=true;
  headers.forEach(th=>{{
    th.addEventListener("click",()=>{{
      const col=parseInt(th.dataset.col);
      if(sortCol===col){{sortAsc=!sortAsc}}else{{sortCol=col;sortAsc=true}}
      const tbody=table.querySelector("tbody");
      const rows=Array.from(tbody.querySelectorAll("tr"));
      rows.sort((a,b)=>{{
        let av,bv;
        if(col===3){{
          av=parseInt(a.children[col].dataset.sortValue)||0;
          bv=parseInt(b.children[col].dataset.sortValue)||0;
        }}else{{
          av=a.children[col].textContent.trim().toLowerCase();
          bv=b.children[col].textContent.trim().toLowerCase();
        }}
        if(av<bv)return sortAsc?-1:1;
        if(av>bv)return sortAsc?1:-1;
        return 0;
      }});
      rows.forEach(r=>tbody.appendChild(r));
      headers.forEach(h=>h.querySelector(".sort-arrow").textContent="");
      th.querySelector(".sort-arrow").textContent=sortAsc?"\u25b2":"\u25bc";
    }});
  }});
}})();
</script>
</body>
</html>"""


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate HTML event report from JSON")
    parser.add_argument("--output", required=True, help="Output HTML file path")
    args = parser.parse_args()

    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    html_content = generate_html(data)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"HTML exported to {args.output}")
