"""Markdown table renderer for Event objects."""

from src.models import Event, SourceStatus


def _em_dash(value: str | None) -> str:
    return value if value else "\u2014"


def render_markdown(events: list[Event], source_statuses: list[SourceStatus], date_str: str) -> str:
    """Render events as a markdown table with summary header and sources footer."""
    cities = {e.city for e in events if e.city}
    sources_reporting = sum(1 for s in source_statuses if s.count > 0)
    total_sources = len(source_statuses)

    lines = [
        f"Found {len(events)} events across {len(cities)} cities from {sources_reporting}/{total_sources} sources",
        "",
        "| Event Name | City | Exact Address | Time | Source Link |",
        "|---|---|---|---|---|",
    ]

    for e in events:
        name = _em_dash(e.name)
        city = _em_dash(e.city)
        address = _em_dash(e.address)
        time = _em_dash(e.time)
        link = f"[{e.source_name}]({e.source_url})" if e.source_url else e.source_name
        lines.append(f"| {name} | {city} | {address} | {time} | {link} |")

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
