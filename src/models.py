"""Core data models for the event extraction pipeline."""

from dataclasses import dataclass
from datetime import date


@dataclass(slots=True)
class Event:
    """One event occurrence on one date.

    `address` is a street address when the source provides one; `venue` is the
    venue name. `category` is an activity-type key from `src.categories`.
    """

    name: str
    city: str | None
    address: str | None
    time: str | None
    event_date: date
    source_name: str
    source_url: str
    venue: str | None = None
    category: str | None = None
    price: str | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "city": self.city,
            "address": self.address,
            "time": self.time,
            "event_date": self.event_date.isoformat(),
            "source_name": self.source_name,
            "source_url": self.source_url,
            "venue": self.venue,
            "category": self.category,
            "price": self.price,
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
            venue=d.get("venue"),
            category=d.get("category"),
            price=d.get("price"),
        )


@dataclass(slots=True)
class FetchResult:
    """One page request's outcome; `warning` flags a non-fatal fetch issue such as a page cap."""

    source_id: str
    source_name: str
    url: str
    content: str | dict | None
    error: str | None
    from_date: date
    to_date: date
    warning: str | None = None


@dataclass(slots=True)
class SourceStatus:
    """Per-source outcome of a run.

    `error` means the source failed outright; `warning` flags a suspicious but
    non-fatal result (zero events from a non-empty page, partial date coverage).
    """

    name: str
    count: int
    error: str | None
    warning: str | None = None

    def label(self) -> str:
        """Render as a sources-footer entry, e.g. 'Do604 (12)'."""
        if self.error:
            return f"{self.name} (ERROR: {self.error})"
        if self.warning:
            return f"{self.name} ({self.count}, WARNING: {self.warning})"
        return f"{self.name} ({self.count})"

    def to_dict(self) -> dict:
        return {"name": self.name, "count": self.count, "error": self.error, "warning": self.warning}

    @classmethod
    def from_dict(cls, d: dict) -> "SourceStatus":
        return cls(name=d["name"], count=d["count"], error=d.get("error"), warning=d.get("warning"))
