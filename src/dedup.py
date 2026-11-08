"""Deterministic duplicate detection across sources, with uncertain pairs left for review."""

import re
import unicodedata
from dataclasses import dataclass, field, replace
from datetime import date
from difflib import SequenceMatcher
from itertools import combinations

from src.cities import normalize_city
from src.models import Event
from src.timeparse import UNKNOWN_TIME, parse_time_to_minutes
from src.venues import venue_key

_NOISE_TOKENS = frozenset({"the", "presents", "pres", "presented", "by", "annual", "a", "an"})
_ORDINAL_RE = re.compile(r"^\d+(st|nd|rd|th)$|^(19|20)\d\d$")
_CANDIDATE_RATIO = 0.75
_VENUE_RATIO = 0.85
_FILLABLE = ("city", "address", "time", "venue", "category", "price")


@dataclass(frozen=True)
class DedupResult:
    """Survivors in input order, how many were merged away, and 1-based index pairs to review."""

    events: list[Event]
    removed: int
    candidates: list[tuple[int, int]] = field(default_factory=list)


def _tokens(text: str) -> list[str]:
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    # Apostrophes join their word, matching curly ones, which vanish in the fold above.
    folded = folded.replace("'", "").replace("`", "").replace("&", " and ")

    return re.findall(r"[a-z0-9]+", folded)


def normalize_name(name: str) -> str:
    """Comparison key for event names: accent-folded, lowercase, noise and ordinal tokens dropped."""
    return " ".join(t for t in _tokens(name) if t not in _NOISE_TOKENS and not _ORDINAL_RE.match(t))


def _venue_of(event: Event) -> str | None:
    venue = event.venue or event.address

    return (venue_key(venue) or None) if venue else None


def _venues_match(a: str, b: str) -> bool:
    """Same venue: equal, one's words a subset of the other's, or near-identical spelling."""
    wa, wb = set(a.split()), set(b.split())

    return wa <= wb or wb <= wa or SequenceMatcher(None, a, b).ratio() >= _VENUE_RATIO


def _street_number(address: str | None) -> str | None:
    m = re.search(r"\d+", address or "")

    return m.group(0) if m else None


def _places_conflict(a: Event, b: Event) -> bool:
    """True when known cities differ or both street numbers are known and differ."""
    if a.city and b.city and normalize_city(a.city) != normalize_city(b.city):
        return True

    na, nb = _street_number(a.address), _street_number(b.address)

    return na is not None and nb is not None and na != nb


def _times_compatible(a: Event, b: Event) -> bool:
    ta, tb = parse_time_to_minutes(a.time), parse_time_to_minutes(b.time)

    return UNKNOWN_TIME in (ta, tb) or ta == tb


def _conflict(a: Event, b: Event) -> bool:
    """True when two events cannot be the same occurrence: different time, city, address, or venue."""
    if not _times_compatible(a, b) or _places_conflict(a, b):
        return True

    va, vb = _venue_of(a), _venue_of(b)

    return va is not None and vb is not None and not _venues_match(va, vb)


def _classify(a: Event, b: Event, na: str, nb: str) -> str | None:
    """Return 'dup', 'candidate', or None for two same-date events with normalized names na/nb."""
    if _conflict(a, b):
        return None

    both_venues = _venue_of(a) is not None and _venue_of(b) is not None

    small, big = sorted((set(na.split()), set(nb.split())), key=len)
    subset = len(small) >= 2 and small <= big

    if na == nb and (both_venues or len(small) >= 3):
        return "dup"

    if subset and both_venues:
        return "dup"

    # One source rarely lists an event twice, so only cross-source near-misses need review.
    if a.source_name == b.source_name:
        return None

    if na == nb or subset or SequenceMatcher(None, na, nb).ratio() >= _CANDIDATE_RATIO:
        return "candidate"

    return None


def _completeness(event: Event) -> int:
    return sum(getattr(event, f) is not None for f in _FILLABLE)


def _first(group: list[Event], field_name: str) -> str | None:
    return next((getattr(e, field_name) for e in group if getattr(e, field_name)), None)


def _merge(group: list[Event]) -> Event:
    # On a tie, a copy with a clock time wins over 'varies' or 'all day'.
    best = max(group, key=lambda e: (_completeness(e), parse_time_to_minutes(e.time) != UNKNOWN_TIME))
    merged = replace(
        best,
        city=best.city or _first(group, "city"),
        address=best.address or _first(group, "address"),
        time=best.time or _first(group, "time"),
        venue=best.venue or _first(group, "venue"),
        category=best.category or _first(group, "category"),
        price=best.price or _first(group, "price"),
    )
    # Prefer a clock time ("7:30 pm") over a vague one ("varies") from the most complete copy.
    clock = next((e.time for e in group if parse_time_to_minutes(e.time) != UNKNOWN_TIME), None)

    return replace(merged, time=clock) if clock and parse_time_to_minutes(merged.time) == UNKNOWN_TIME else merged


def _find(parent: list[int], i: int) -> int:
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]

    return i


def dedupe(events: list[Event]) -> DedupResult:
    """Merge same-date duplicates, filling missing fields from the dropped copies.

    A pair is a duplicate when names normalize equal (or one is a 2+ token subset of the
    other) with compatible venues and times. Similar-but-unproven pairs become candidates.
    Inputs are not mutated.
    """
    names = [normalize_name(e.name) for e in events]
    parent = list(range(len(events)))
    # Members per group root. Groups merge only when no cross pair conflicts, so a listing
    # with a vague time or no venue cannot chain two separate events together.
    members = [[i] for i in range(len(events))]
    candidate_pairs: list[tuple[int, int]] = []
    by_date: dict[date, list[int]] = {}

    for i, e in enumerate(events):
        by_date.setdefault(e.event_date, []).append(i)

    for idxs in by_date.values():
        for i, j in sorted(_pairs_sharing_a_token(idxs, names)):
            verdict = _classify(events[i], events[j], names[i], names[j])

            if verdict == "dup":
                ri, rj = _find(parent, i), _find(parent, j)
                compatible = not any(
                    _conflict(events[x], events[y]) for x in members[ri] for y in members[rj]
                )

                if ri != rj and compatible:
                    parent[rj] = ri
                    members[ri] += members[rj]
            elif verdict == "candidate":
                candidate_pairs.append((i, j))

    groups: dict[int, list[int]] = {}

    for i in range(len(events)):
        groups.setdefault(_find(parent, i), []).append(i)

    survivors = sorted(groups.values(), key=lambda g: g[0])
    position = {members[0]: pos for pos, members in enumerate(survivors, 1)}
    root_pos = {_find(parent, members[0]): position[members[0]] for members in survivors}
    merged = [_merge([events[k] for k in members]) for members in survivors]
    candidates = sorted({
        (min(pi, pj), max(pi, pj))
        for i, j in candidate_pairs
        if (pi := root_pos[_find(parent, i)]) != (pj := root_pos[_find(parent, j)])
    })

    return DedupResult(events=merged, removed=len(events) - len(merged), candidates=candidates)


def _pairs_sharing_a_token(idxs: list[int], names: list[str]) -> set[tuple[int, int]]:
    """Index pairs whose normalized names share a token; avoids comparing every pair."""
    by_token: dict[str, list[int]] = {}

    for i in idxs:
        for token in set(names[i].split()):
            by_token.setdefault(token, []).append(i)

    pairs: set[tuple[int, int]] = set()

    for members in by_token.values():
        pairs.update(combinations(sorted(members), 2))

    return pairs
