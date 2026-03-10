"""Markdown table renderer for Event objects."""

from datetime import date

from src.models import Event, SourceStatus
from src.renderers.formatting import format_short_date
from src.renderers.maps import build_maps_url


def _em_dash(value: str | None) -> str:
    return value if value else "\u2014"


def render_markdown(events: list[Event], source_statuses: list[SourceStatus], from_date: date, to_date: date) -> str:
    """Render events as a markdown table with summary header and sources footer."""
    cities = {e.city for e in events if e.city}
    sources_reporting = sum(1 for s in source_statuses if s.count > 0)
    total_sources = len(source_statuses)

    lines = [
        f"Found {len(events)} events across {len(cities)} cities from {sources_reporting}/{total_sources} sources",
        "",
        "| Event Name | City | Exact Address | Date | Time | Source Link |",
        "|---|---|---|---|---|---|",
    ]

    for e in events:
        name = _em_dash(e.name)
        event_date = format_short_date(e.event_date)
        city = _em_dash(e.city)
        maps_url = build_maps_url(e.address)
        address = f"[{e.address}]({maps_url})" if maps_url else _em_dash(e.address)
        time = _em_dash(e.time)
        link = f"[{e.source_name}]({e.source_url})" if e.source_url else e.source_name
        lines.append(f"| {name} | {city} | {address} | {event_date} | {time} | {link} |")

    # Sources footer
    parts = []
    for s in source_statuses:
        if s.error:
            parts.append(f"{s.name} (ERROR: {s.error})")
        else:
            parts.append(f"{s.name} ({s.count})")

    lines.append("")
    lines.append("Sources checked: " + ", ".join(parts))

    return "\n".join(lines)
