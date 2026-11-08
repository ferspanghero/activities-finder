"""HTML renderer: generates a self-contained HTML event report."""

import html as html_lib
from datetime import date

from src.models import Event, SourceStatus
from src.renderers.filters import ReportFilters, report_filters, type_value
from src.renderers.formatting import (
    category_label,
    format_short_date,
    location_text,
    maps_query,
    safe_url,
    sources_footer,
    summary_line,
)
from src.renderers.maps import build_maps_url
from src.timeparse import (
    UNKNOWN_TIME,
    display_time,
    format_clock,
    parse_time_to_minutes,
    sort_minutes,
)

_CSS = """\
*,*::before,*::after{box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;margin:0;padding:20px 5vw;background:#f8f9fa;color:#212529}
h1{margin:0 0 4px;font-size:1.6rem}
.summary{color:#495057;margin:0 0 16px;font-size:1rem}
.table-wrap.scroll{overflow-x:auto}
table{width:100%;border-collapse:collapse;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.1)}
thead{position:sticky;top:0;z-index:1}
th{background:#343a40;color:#fff;padding:10px 12px;text-align:left;cursor:pointer;user-select:none;white-space:nowrap}
th:hover{background:#495057}
.sort-arrow{font-size:.75rem;margin-left:4px}
td{padding:8px 12px;border-bottom:1px solid #dee2e6}
td:nth-child(5){min-width:110px}
td:nth-child(1),td:nth-child(4){overflow-wrap:anywhere}
td:nth-child(2),td:nth-child(3),td:nth-child(5),td:nth-child(6),td:nth-child(8){white-space:nowrap}
.table-wrap.tight td,.table-wrap.tight th{white-space:normal}
tbody tr.alt{background:#f8f9fa}
tbody tr:hover{background:#e9ecef}
a{color:#0d6efd;text-decoration:none}
a:hover{text-decoration:underline}
.footer{margin-top:16px;color:#6c757d;font-size:.875rem}
.filters{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 12px}
.filter{position:relative}
.filter summary{list-style:none;cursor:pointer;padding:6px 10px;border:1px solid #ced4da;border-radius:6px;background:#fff;white-space:nowrap}
.filter summary::-webkit-details-marker{display:none}
.filter summary::after{content:" \\25BE";color:#6c757d}
.filter .sel{color:#0d6efd}
.vh{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.filter .options{position:absolute;z-index:3;top:calc(100% + 4px);left:0;background:#fff;border:1px solid #ced4da;border-radius:6px;padding:6px 10px;max-height:280px;overflow:auto;min-width:140px;max-width:90vw;box-shadow:0 4px 12px rgba(0,0,0,.12)}
.filter .options label{display:block;white-space:nowrap;padding:3px 0;cursor:pointer}
.time-range{display:flex;align-items:center;gap:6px;white-space:nowrap}
.filters button{padding:6px 8px;border:1px solid #ced4da;border-radius:6px;background:#fff;font:inherit;cursor:pointer}
#shown-count{margin-left:auto;color:#495057;font-size:.9rem}
tr[hidden]{display:none}
@media (max-width:600px){.filters{position:relative}.filter{position:static}.filter .options{left:0;right:0;max-width:none}.time-range{flex-wrap:wrap}}
.no-events{text-align:center;color:#6c757d;padding:40px 0;font-size:1.1rem}"""

_FILTER_JS = """\
(function(){
  const table=document.getElementById("events-table");
  const bar=document.getElementById("filters");
  const wrap=table&&table.closest(".table-wrap");
  if(!table||!bar||!wrap)return;
  const rows=Array.from(table.tBodies[0].rows);
  const groups=["city","type","source"];
  const bound=n=>{const c=ticked(n)[0];return c&&c.value!==""?parseInt(c.value,10):null;};
  const count=document.getElementById("shown-count"),none=document.getElementById("no-matches");
  // Short columns stay on one line while the table fits; when the window is too narrow they wrap
  // instead of pushing columns out of view, and only a table that still overflows scrolls sideways
  // (a scrolling wrapper would stop the sticky header from sticking).
  function fit(){
    wrap.classList.remove("tight","scroll");
    if(wrap.scrollWidth>wrap.clientWidth)wrap.classList.add("tight");
    if(wrap.scrollWidth>wrap.clientWidth)wrap.classList.add("scroll");
  }
  const ticked=g=>Array.from(bar.querySelectorAll('input[name="'+g+'"]:checked'));
  function apply(){
    const sets={};
    groups.forEach(g=>{sets[g]=new Set(ticked(g).map(i=>i.value));});
    const lo=bound("from"),hi=bound("to");
    let shown=0;
    rows.forEach(r=>{
      let ok=groups.every(g=>sets[g].size===0||sets[g].has(r.dataset[g]));
      if(ok&&(lo!==null||hi!==null)){
        const m=r.dataset.minutes===""?null:parseInt(r.dataset.minutes,10);
        // A "from" later than "to" is a window across midnight, e.g. 10 PM to 2 AM.
        const wraps=lo!==null&&hi!==null&&lo>hi;
        ok=m!==null&&(wraps?(m>=lo||m<=hi):((lo===null||m>=lo)&&(hi===null||m<=hi)));
      }
      r.hidden=!ok;
      if(ok){r.classList.toggle("alt",shown%2===1);shown++;}
    });
    groups.forEach(g=>{
      const on=ticked(g),label=bar.querySelector("#filter-"+g+" .sel");
      label.textContent=on.length===0?"All":on.length===1?on[0].parentElement.textContent.trim():on.length+" selected";
    });
    ["from","to"].forEach(n=>{
      bar.querySelector("#filter-"+n+" .sel").textContent=ticked(n)[0].parentElement.textContent.trim();
    });
    count.textContent="Showing "+shown+" of "+rows.length+" events";
    none.hidden=shown!==0;
    fit();
  }
  bar.addEventListener("change",apply);
  // A mouse pick of a time closes its dropdown; arrow keys (click detail 0) leave it open.
  bar.addEventListener("click",e=>{
    if(e.detail>0&&e.target.type==="radio"){
      const d=e.target.closest("details");
      d.open=false;
      d.querySelector("summary").focus();
    }
  });
  document.getElementById("reset-filters").addEventListener("click",()=>{
    bar.querySelectorAll('input[type="checkbox"]:checked').forEach(i=>{i.checked=false;});
    bar.querySelectorAll('input[type="radio"][value=""]').forEach(i=>{i.checked=true;});
    apply();
  });
  // Close the other dropdowns on the click itself; the "toggle" event fires later, asynchronously.
  bar.querySelectorAll("details.filter > summary").forEach(sm=>sm.addEventListener("click",()=>{
    bar.querySelectorAll("details.filter[open]").forEach(o=>{if(o!==sm.parentElement)o.open=false;});
  }));
  document.addEventListener("keydown",e=>{
    if(e.key!=="Escape")return;
    bar.querySelectorAll("details.filter[open]").forEach(o=>{
      if(o.contains(document.activeElement))o.querySelector("summary").focus();
      o.open=false;
    });
  });
  document.addEventListener("click",e=>{
    if(!e.target.closest("details.filter"))bar.querySelectorAll("details.filter[open]").forEach(o=>{o.open=false;});
  });
  apply();
  // Back/forward navigation restores ticked boxes after this script ran; re-apply them.
  window.addEventListener("pageshow",apply);
  // Re-fit once resizing pauses, and only when the width changed: each fit lays out the table.
  let resizing,fitted=wrap.clientWidth;
  window.addEventListener("resize",()=>{
    clearTimeout(resizing);
    resizing=setTimeout(()=>{if(wrap.clientWidth!==fitted){fitted=wrap.clientWidth;fit();}},100);
  });
})();"""

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
        if(col===4||col===5){
          const svA=a.children[col].dataset.sortValue;
          const svB=b.children[col].dataset.sortValue;
          if(col===5){av=parseInt(svA)||0;bv=parseInt(svB)||0;}
          else{av=svA||"";bv=svB||"";}
        }else{
          av=a.children[col].textContent.trim().toLowerCase();
          bv=b.children[col].textContent.trim().toLowerCase();
        }
        if(av<bv)return sortAsc?-1:1;
        if(av>bv)return sortAsc?1:-1;
        return 0;
      });
      rows.forEach(r=>tbody.appendChild(r));
      let n=0;
      rows.forEach(r=>{if(!r.hidden){r.classList.toggle("alt",n%2===1);n++;}});
      headers.forEach(h=>h.querySelector(".sort-arrow").textContent="");
      th.querySelector(".sort-arrow").textContent=sortAsc?"\\u25b2":"\\u25bc";
    });
  });
})();"""


def format_date_display(from_date: date, to_date: date) -> str:
    """Format a date range for display in headings."""
    if from_date == to_date:
        return f"{from_date.strftime('%A, %B')} {from_date.day}, {from_date.year}"
    if from_date.year == to_date.year and from_date.month == to_date.month:
        return f"{from_date.strftime('%B')} {from_date.day}\u2013{to_date.day}, {from_date.year}"
    if from_date.year == to_date.year:
        return f"{from_date.strftime('%B')} {from_date.day} \u2013 {to_date.strftime('%B')} {to_date.day}, {from_date.year}"
    return f"{from_date.strftime('%B')} {from_date.day}, {from_date.year} \u2013 {to_date.strftime('%B')} {to_date.day}, {to_date.year}"


def escape_and_format(value: str | None) -> str:
    """HTML-escape a value. None or empty string becomes an em-dash."""
    if not value:
        return "\u2014"
    return html_lib.escape(value, quote=True)


def _attr(value: str) -> str:
    return html_lib.escape(value, quote=True)


def build_event_row(event: Event) -> str:
    """One <tr> for the events table; date and time cells carry sortable values, and the row
    carries the city, type, source, and start minute the filter bar matches on. Cell order is
    referenced by position in `_CSS` (nth-child) and the sort script."""
    location = escape_and_format(location_text(event))
    maps_url = build_maps_url(maps_query(event))
    source_name = html_lib.escape(event.source_name, quote=True)
    url = safe_url(event.source_url)
    source_cell = (
        f'<a href="{html_lib.escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{source_name}</a>'
        if url else source_name
    )

    if maps_url:
        location = f'<a href="{html_lib.escape(maps_url, quote=True)}" target="_blank" rel="noopener noreferrer">{location}</a>'

    minutes = parse_time_to_minutes(event.time)
    row_attrs = (
        f'data-city="{_attr(event.city or "")}" data-type="{_attr(type_value(event))}" '
        f'data-source="{_attr(event.source_name)}" data-minutes="{"" if minutes == UNKNOWN_TIME else minutes}"'
    )

    return (
        f"<tr {row_attrs}>"
        f"<td>{escape_and_format(event.name)}</td>"
        f"<td>{escape_and_format(category_label(event.category))}</td>"
        f"<td>{escape_and_format(event.city)}</td>"
        f"<td>{location}</td>"
        f'<td data-sort-value="{event.event_date.isoformat()}">{format_short_date(event.event_date)}</td>'
        f'<td data-sort-value="{sort_minutes(event.time)}">{escape_and_format(display_time(event.time))}</td>'
        f"<td>{escape_and_format(event.price)}</td>"
        f"<td>{source_cell}</td>"
        f"</tr>"
    )


def _dropdown(group: str, title: str, choices: tuple[tuple[str, str], ...]) -> str:
    options = "".join(
        f'<label><input type="checkbox" name="{group}" value="{_attr(value)}"> {html_lib.escape(label)}</label>'
        for value, label in choices
    )

    return (
        f'<details class="filter" id="filter-{group}"><summary>{title} <span class="sel">All</span></summary>'
        f'<div class="options">{options}</div></details>'
    )


def _hour_label(hour: int) -> str:
    return "end of day" if hour == 24 else format_clock(hour, 0).replace(":00", "")


def _time_dropdown(bound: str, label: str, hours: range) -> str:
    """Single-choice start-time bound: radio buttons in an in-page dropdown, like the other filters.

    Not a native <select>: its popup fails to commit a pick in some Firefox setups.
    """
    choices = [("", "any time")] + [(str(h * 60), _hour_label(h)) for h in hours]
    options = "".join(
        f'<label><input type="radio" name="{bound}" value="{value}"{" checked" if not value else ""}> {text}</label>'
        for value, text in choices
    )

    return (
        f'<details class="filter" id="filter-{bound}"><summary><span class="vh">{label} </span>'
        f'<span class="sel">any time</span></summary>'
        f'<div class="options" role="radiogroup" aria-label="{label}">{options}</div></details>'
    )


def build_filter_bar(filters: ReportFilters, total: int) -> str:
    """Filter controls above the table: city, type, and source checklists plus a start-time range."""
    return (
        '<div class="filters" id="filters">'
        + _dropdown("city", "City", filters.cities)
        + _dropdown("type", "Type", filters.types)
        + _dropdown("source", "Source", filters.sources)
        + '<span class="time-range" role="group" aria-label="Start time">Starts '
        + _time_dropdown("from", "Starts from", range(24))
        + " to "
        + _time_dropdown("to", "Starts by", range(1, 25))
        + '</span><button type="button" id="reset-filters">Reset</button>'
        + f'<span id="shown-count" aria-live="polite">Showing {total} of {total} events</span></div>'
        + '<p id="no-matches" class="no-events" hidden>No events match these filters.</p>'
    )


def render_html(events: list[Event], source_statuses: list[SourceStatus], from_date: date, to_date: date) -> str:
    """Convert Event objects to a self-contained HTML report."""
    date_display = format_date_display(from_date, to_date)
    summary_text = summary_line(events, source_statuses)
    footer_text = html_lib.escape(sources_footer(source_statuses))

    if events:
        rows = "\n".join(build_event_row(e) for e in events)
        table_html = build_filter_bar(report_filters(events), len(events)) + f"""<div class="table-wrap">
<table id="events-table">
<thead>
<tr>
<th data-col="0">Event Name <span class="sort-arrow"></span></th>
<th data-col="1">Type <span class="sort-arrow"></span></th>
<th data-col="2">City <span class="sort-arrow"></span></th>
<th data-col="3">Location <span class="sort-arrow"></span></th>
<th data-col="4">Date <span class="sort-arrow"></span></th>
<th data-col="5">Time <span class="sort-arrow"></span></th>
<th data-col="6">Price <span class="sort-arrow"></span></th>
<th data-col="7">Source <span class="sort-arrow"></span></th>
</tr>
</thead>
<tbody>
{rows}
</tbody>
</table>
</div>"""
    else:
        no_events_label = "date range" if from_date != to_date else "date"
        table_html = f'<p class="no-events">No events found for this {no_events_label}.</p>'

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
{_FILTER_JS}
</script>
</body>
</html>"""
