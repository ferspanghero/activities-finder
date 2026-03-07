"""Core data models for the event extraction pipeline."""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(slots=True)
class Event:
    name: str
    city: Optional[str]
    address: Optional[str]
    time: Optional[str]
    source_name: str
    source_url: str


@dataclass(slots=True)
class FetchResult:
    source_id: str
    source_name: str
    url: str
    content: Optional[str | dict]
    error: Optional[str]
    target_date: date


@dataclass(slots=True)
class SourceStatus:
    name: str
    count: int
    error: Optional[str]
