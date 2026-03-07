"""Pipeline orchestrator: fetch -> parse -> aggregate."""

import logging
from dataclasses import dataclass, field
from datetime import date

from src.models import Event, FetchResult, SourceStatus

logger = logging.getLogger(__name__)
from src.parsers.do604 import parse_do604
from src.parsers.dailyhive import parse_dailyhive
from src.parsers.rhythmchanges import parse_rhythmchanges
from src.parsers.showhub import parse_showhub
from src.parsers.infidelsjazz import parse_infidelsjazz
from src.fetch_sources import fetch_raw_sources


@dataclass(slots=True)
class PipelineResult:
    events: list[Event] = field(default_factory=list)
    source_statuses: list[SourceStatus] = field(default_factory=list)


def _dispatch_parser(fetch_result: FetchResult, target_date: date) -> list[Event]:
    """Route a FetchResult to the appropriate parser."""
    sid = fetch_result.source_id
    content = fetch_result.content
    url = fetch_result.url

    if sid == "do604":
        return parse_do604(content, url)
    elif sid == "dailyhive":
        return parse_dailyhive(content, url, target_date)
    elif sid == "rhythmchanges":
        return parse_rhythmchanges(content, url, target_date)
    elif sid == "showhub":
        return parse_showhub(content, url, target_date)
    elif sid == "infidelsjazz":
        return parse_infidelsjazz(content, url)
    else:
        return []


async def run_pipeline(target_date: date) -> PipelineResult:
    """Fetch all sources, parse, and aggregate into a PipelineResult."""
    fetch_results = await fetch_raw_sources(target_date)

    all_events: list[Event] = []
    statuses: list[SourceStatus] = []

    for fr in fetch_results:
        if fr.error:
            statuses.append(SourceStatus(name=fr.source_name, count=0, error=fr.error))
            continue

        try:
            events = _dispatch_parser(fr, target_date)
        except Exception as e:
            logger.error("Parser error for %s: %s", fr.source_name, e)
            statuses.append(SourceStatus(name=fr.source_name, count=0, error=str(e)))
            continue

        logger.info("Parsed %s: %d events", fr.source_name, len(events))
        all_events.extend(events)
        statuses.append(SourceStatus(name=fr.source_name, count=len(events), error=None))

    logger.info("Pipeline complete: %d total events from %d sources", len(all_events), len(statuses))
    return PipelineResult(events=all_events, source_statuses=statuses)
