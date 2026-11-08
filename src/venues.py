"""Venue book: venue to city/address, learned from sources and online lookups, persisted as JSON."""

import json
import logging
import os
import re
import tempfile
import unicodedata
from collections import Counter
from dataclasses import dataclass, replace
from datetime import date, timedelta
from pathlib import Path

from src.models import Event

logger = logging.getLogger(__name__)

ATTRIBUTION = (
    "Entries with origin 'osm' come from OpenStreetMap: "
    "(c) OpenStreetMap contributors, ODbL 1.0, https://www.openstreetmap.org/copyright"
)
MISS_RETRY = timedelta(days=30)
_REPLACEABLE = frozenset({"osm", "miss"})


def venue_key(name: str) -> str:
    """Lookup key for a venue name: accent-folded, lowercase, no punctuation or leading 'the'."""
    folded = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    # Apostrophes join their word ("Frankie's" -> "frankies"); curly ones vanish in the fold above.
    words = re.findall(r"[a-z0-9]+", folded.replace("'", "").replace("`", ""))

    if words and words[0] == "the":
        words = words[1:]

    return " ".join(words)


@dataclass(frozen=True)
class VenueInfo:
    """Where a venue is. `city` is None for a lookup miss.

    `origin`: "source" (an event source published it), "page" (read from the event's own
    page), "osm" (OpenStreetMap lookup), "manual" (hand-edited; never overwritten), or "miss"
    (lookup found nothing).
    """

    city: str | None
    address: str | None
    origin: str = "source"
    checked: str | None = None
    name: str | None = None


class VenueBook:
    """Mutable venue-key to VenueInfo map, persisted as JSON between runs."""

    def __init__(self) -> None:
        self._entries: dict[str, VenueInfo] = {}
        # Set when the file exists but cannot be parsed: saving would erase hand edits.
        self._read_only = False

    def __len__(self) -> int:
        return len(self._entries)

    @classmethod
    def load(cls, path: Path) -> "VenueBook":
        """Load from `path`. A missing file yields an empty book; an unreadable one yields an
        empty, read-only book so the file is never overwritten.
        """
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return cls()
        except (OSError, json.JSONDecodeError) as e:
            logger.error("Venue file %s is unreadable (%s); fix it by hand, it will not be saved", path, e)
            book = cls()
            book._read_only = True
            return book

        return cls.from_data(raw)

    @classmethod
    def from_data(cls, raw: object) -> "VenueBook":
        """Build from parsed file data, re-keying entries so hand-written keys still match."""
        book = cls()
        venues = raw.get("venues") if isinstance(raw, dict) else None

        for key, value in venues.items() if isinstance(venues, dict) else ():
            if not (isinstance(value, dict) and (isinstance(value.get("city"), str) or value.get("origin") == "miss")):
                continue

            normalized = venue_key(value.get("name") or key)

            if normalized in book._entries:
                logger.warning("Duplicate venue entry %r in venue file; keeping the first", key)
                continue

            book._entries[normalized] = VenueInfo(
                city=value.get("city"),
                address=value.get("address"),
                origin=value.get("origin", "source"),
                checked=value.get("checked"),
                name=value.get("name"),
            )

        return book

    def save(self, path: Path) -> None:
        """Write the book to `path` as JSON with the OpenStreetMap attribution, keys sorted.

        Skipped for a book loaded from an unreadable file. The write is atomic.
        """
        if self._read_only:
            return

        data = {
            "attribution": ATTRIBUTION,
            "venues": {
                k: {"name": v.name, "city": v.city, "address": v.address, "origin": v.origin, "checked": v.checked}
                for k, v in sorted(self._entries.items())
            },
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False) as tmp:
            tmp.write(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
            tmp.flush()
            os.fsync(tmp.fileno())

        try:
            os.replace(tmp.name, path)
        except OSError:
            os.unlink(tmp.name)
            raise

    def learn(self, events: list[Event]) -> None:
        """Record venues from events with a city and street address (structured source data).

        Source data replaces OpenStreetMap results, misses, and address-less source entries;
        page-read and hand-edited entries are kept.
        """
        for e in events:
            if not (e.venue and e.city and e.address):
                continue

            key = venue_key(e.venue)
            known = self._entries.get(key)
            replaceable = known is None or known.origin in _REPLACEABLE or (
                known.origin == "source" and known.address is None
            )

            if key and replaceable:
                self._entries[key] = VenueInfo(city=e.city, address=e.address, origin="source", name=e.venue)

    def record(self, name: str, info: VenueInfo | None, today: date) -> None:
        """Store an online lookup result for `name`, or a dated miss when `info` is None.

        Source, page, and hand-edited entries are never replaced by a lookup, and a miss never
        erases a found city.
        """
        key = venue_key(name)
        known = self._entries.get(key)

        if not key or (known is not None and known.origin not in _REPLACEABLE):
            return

        if info is None and known is not None and known.city:
            return

        found = info or VenueInfo(city=None, address=None, origin="miss")
        self._entries[key] = replace(found, checked=today.isoformat(), name=name)

    def needs_lookup(self, events: list[Event], today: date) -> list[str]:
        """Venue names of city-less events not yet known, most frequent first.

        A recorded miss is retried once it is older than MISS_RETRY.
        """
        counts = Counter(e.venue for e in events if e.venue and not e.city)
        names: list[str] = []
        seen: set[str] = set()

        for name, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
            key = venue_key(name)
            known = self._entries.get(key)

            if key in seen or not key:
                continue

            seen.add(key)

            if known is None or (known.origin == "miss" and self._stale(known, today)):
                names.append(name)

        return names

    @staticmethod
    def _stale(info: VenueInfo, today: date) -> bool:
        try:
            return today - date.fromisoformat(info.checked or "") >= MISS_RETRY
        except ValueError:
            return True

    def fill(self, events: list[Event]) -> list[Event]:
        """Return events with missing city/address filled from known venues (misses are skipped)."""
        filled = []

        for e in events:
            info = self._entries.get(venue_key(e.venue)) if e.venue else None

            if info and info.city and (e.city is None or e.address is None):
                e = replace(e, city=e.city or info.city, address=e.address or info.address)

            filled.append(e)

        return filled
