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
    event_date: date
    source_name: str
    source_url: str

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "city": self.city,
            "address": self.address,
            "time": self.time,
            "event_date": self.event_date.isoformat(),
            "source_name": self.source_name,
            "source_url": self.source_url,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Event":
        return cls(
            name=d["name"],
            city=d.get("city"),
            address=d.get("address"),
            time=d.get("time"),
            event_date=date.fromisoformat(d["event_date"]),
            source_name=d["source_name"],
            source_url=d["source_url"],
        )


@dataclass(slots=True)
class FetchResult:
    source_id: str
    source_name: str
    url: str
    content: Optional[str | dict]
    error: Optional[str]
    from_date: date
    to_date: date


@dataclass(slots=True)
class SourceStatus:
    name: str
    count: int
    error: Optional[str]

    def to_dict(self) -> dict:
        return {"name": self.name, "count": self.count, "error": self.error}

    @classmethod
    def from_dict(cls, d: dict) -> "SourceStatus":
        return cls(name=d["name"], count=d["count"], error=d.get("error"))
