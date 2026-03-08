"""HTML renderer — generates self-contained HTML event report."""

import html as html_lib
import re
from datetime import date

from src.models import Event, SourceStatus
from src.renderers.maps import build_maps_url


_CSS = """\
*,*::before,*::after{box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;margin:0;padding:20px;background:#f8f9fa;color:#212529}
.container{max-width:1200px;margin:0 auto}
h1{margin:0 0 4px;font-size:1.6rem}
.summary{color:#495057;margin:0 0 16px;font-size:1rem}
.table-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.1)}
thead{position:sticky;top:0;z-index:1}
th{background:#343a40;color:#fff;padding:10px 12px;text-align:left;cursor:pointer;user-select:none;white-space:nowrap}
th:hover{background:#495057}
.sort-arrow{font-size:.75rem;margin-left:4px}
td{padding:8px 12px;border-bottom:1px solid #dee2e6}
tbody tr:nth-child(even){background:#f8f9fa}
tbody tr:hover{background:#e9ecef}
a{color:#0d6efd;text-decoration:none}
a:hover{text-decoration:underline}
.footer{margin-top:16px;color:#6c757d;font-size:.875rem}
.no-events{text-align:center;color:#6c757d;padding:40px 0;font-size:1.1rem}"""

_JS = """\
(function(){
  const table=document.getElementById("events-table");
  if(!table)return;
  const headers=table.querySelectorAll("th");
  let sortCol=-1,sortAsc=true;
  headers.forEach(th=>{
    th.addEventListener("click",()=>{
      const col=parseInt(th.dataset.col);
      if(sortCol===col){sortAsc=!sortAsc}else{sortCol=col;sortAsc=true}
      const tbody=table.querySelector("tbody");
      const rows=Array.from(tbody.querySelectorAll("tr"));
      rows.sort((a,b)=>{
        let av,bv;
        if(col===3){
          av=parseInt(a.children[col].dataset.sortValue)||0;
          bv=parseInt(b.children[col].dataset.sortValue)||0;
        }else{
          av=a.children[col].textContent.trim().toLowerCase();
          bv=b.children[col].textContent.trim().toLowerCase();
        }
        if(av<bv)return sortAsc?-1:1;
        if(av>bv)return sortAsc?1:-1;
        return 0;
      });
      rows.forEach(r=>tbody.appendChild(r));
      headers.forEach(h=>h.querySelector(".sort-arrow").textContent="");
      th.querySelector(".sort-arrow").textContent=sortAsc?"\\u25b2":"\\u25bc";
    });
  });
})();"""


def format_date_display(iso_date: str) -> str:
    """'2026-03-08' -> 'Sunday, March 8, 2026'"""
    d = date.fromisoformat(iso_date)
    return f"{d.strftime('%A, %B')} {d.day}, {d.year}"


def escape_and_format(value: str | None) -> str:
    """HTML-escape a value. None or empty string becomes an em-dash."""
    if not value:
        return "\u2014"
    return html_lib.escape(value, quote=True)


def parse_time_to_minutes(time_str: str | None) -> int:
    """Parse a time string like '8:00 PM' to minutes since midnight for sorting.

    Returns 9999 for unparseable times so they sort to the end.
    """
    if not time_str:
        return 9999
    match = re.match(r"(\d{1,2}):(\d{2})\s*(AM|PM)", time_str.strip(), re.IGNORECASE)
    if not match:
        return 9999
    hour, minute, period = int(match.group(1)), int(match.group(2)), match.group(3).upper()
    if period == "AM" and hour == 12:
        hour = 0
    elif period == "PM" and hour != 12:
        hour += 12
    return hour * 60 + minute


def build_event_row(event: Event) -> str:
    name = escape_and_format(event.name)
    city = escape_and_format(event.city)
    address = escape_and_format(event.address)
    time = escape_and_format(event.time)
    sort_value = parse_time_to_minutes(event.time)
    source_name = html_lib.escape(event.source_name, quote=True)
    source_url = html_lib.escape(event.source_url, quote=True)

    maps_url = build_maps_url(event.address)
    if maps_url:
        maps_url_escaped = html_lib.escape(maps_url, quote=True)
        address_cell = f'<a href="{maps_url_escaped}" target="_blank" rel="noopener noreferrer">{address}</a>'
    else:
        address_cell = address

    return (
        f"<tr>"
        f"<td>{name}</td>"
        f"<td>{city}</td>"
        f"<td>{address_cell}</td>"
        f'<td data-sort-value="{sort_value}">{time}</td>'
        f'<td><a href="{source_url}" target="_blank" rel="noopener noreferrer">{source_name}</a></td>'
        f"</tr>"
    )


def build_sources_footer(statuses: list[SourceStatus]) -> str:
    parts = []
    for s in statuses:
        if s.error:
            parts.append(f"{s.name} (ERROR: {s.error})")
        else:
            parts.append(f"{s.name} ({s.count})")
    return "Sources checked: " + ", ".join(parts)


def render_html(events: list[Event], source_statuses: list[SourceStatus], date_str: str) -> str:
    """Convert Event objects to a self-contained HTML report."""
    date_display = format_date_display(date_str)
    cities = {e.city for e in events if e.city}
    sources_reporting = sum(1 for s in source_statuses if s.count > 0)

    summary_text = (
        f"Found {len(events)} events across {len(cities)} "
        f"cities from {sources_reporting}/{len(source_statuses)} sources"
    )
    footer_text = build_sources_footer(source_statuses)

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
{_CSS}
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
{_JS}
</script>
</body>
</html>"""
