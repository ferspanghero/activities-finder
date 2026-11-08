"""Markdown table renderer for Event objects."""

from datetime import date

from src.models import Event, SourceStatus
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
from src.timeparse import display_time

_MARKDOWN_ESCAPES = str.maketrans({c: f"\\{c}" for c in "|[]<>"})


def _cell(value: str | None) -> str:
    """Table cell text: one line, with table, link, and HTML syntax escaped; em-dash when empty."""
    return " ".join(value.split()).translate(_MARKDOWN_ESCAPES) if value else "—"


def _row(e: Event) -> str:
    location = location_text(e)
    maps_url = build_maps_url(maps_query(e))
    location_cell = f"[{_cell(location)}]({maps_url})" if maps_url else _cell(location)
    source_url = safe_url(e.source_url)
    link = f"[{_cell(e.source_name)}]({source_url})" if source_url else _cell(e.source_name)
    cells = (
        _cell(e.name), _cell(category_label(e.category)), _cell(e.city), location_cell,
        format_short_date(e.event_date), _cell(display_time(e.time)), _cell(e.price), link,
    )

    return "| " + " | ".join(cells) + " |"


def render_markdown(events: list[Event], source_statuses: list[SourceStatus], from_date: date, to_date: date) -> str:
    """Render events as a markdown table with summary header and sources footer."""
    lines = [
        summary_line(events, source_statuses),
        "",
        "| Event Name | Type | City | Location | Date | Time | Price | Source Link |",
        "|---|---|---|---|---|---|---|---|",
        *(_row(e) for e in events),
        "",
        sources_footer(source_statuses),
    ]

    return "\n".join(lines)
