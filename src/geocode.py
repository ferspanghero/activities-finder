"""Find a venue's city and address: from the event's own page first, then OpenStreetMap Nominatim.

Event pages (Do604, ShowHub) publish the venue's schema.org address. Nominatim accepts only
confident matches. Its usage policy (https://operations.osmfoundation.org/policies/nominatim/):
at most one request per second, an identifying User-Agent, and cached results (the venue book
stores them).
"""

import asyncio
import json
import logging
import re
from difflib import SequenceMatcher
from urllib.parse import urlparse

import aiohttp

from src.cities import canonical_city, city_from_text
from src.fetch_sources import BROWSER_HEADERS
from src.venues import VenueInfo, venue_key

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_HEADERS = {"User-Agent": "activities-searcher/1.0 (personal event aggregator)"}
# lon/lat box covering Metro Vancouver, the Fraser Valley, and Squamish.
_VIEWBOX = "-123.5,49.8,-121.7,49.0"
_TIMEOUT = aiohttp.ClientTimeout(total=20)
# Near-identical spellings only ("Frankies" vs "Frankie's"); "Rio" vs "Rex Theatre" must fail.
_NAME_RATIO = 0.9
# OpenStreetMap categories of places that host events; buildings, offices, and areas are false hits.
_EVENT_PLACE_CATEGORIES = frozenset({"amenity", "leisure", "tourism", "shop", "club", "historic", "craft"})
# schema.org types that describe a venue (Place and the subtypes event pages use).
_PLACE_TYPES = frozenset({
    "Place", "LocalBusiness", "EventVenue", "MusicVenue", "BarOrPub", "Restaurant", "NightClub",
    "PerformingArtsTheater", "CivicStructure", "MovieTheater", "Museum", "ArtGallery", "Library",
    "CafeOrCoffeeShop", "Brewery", "Winery", "StadiumOrArena", "Park", "PlaceOfWorship",
})
_STREET_WORDS = r"(street|st|avenue|ave|road|rd|drive|dr|way|boulevard|blvd|highway|hwy|crescent|place|pl)"
# A whole street address ("13750 88 Avenue", "2-1555 7th Ave W") names no venue; "1181 Lounge" does.
_ADDRESS_RE = re.compile(
    rf"^\s*[\d-]+\s+.*\b{_STREET_WORDS}\b\.?(\s+([nsew]|north|south|east|west)\.?)?\s*$", re.IGNORECASE,
)
_PLACEHOLDER_RE = re.compile(r"\b(various|tba|tbd|online|virtual|billboard)\b", re.IGNORECASE)
_JSONLD_RE = re.compile(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.DOTALL | re.IGNORECASE)


def is_searchable(name: str) -> bool:
    """False for strings that name no single place: street addresses, 'Various Locations', 'TBA'."""
    return bool(name.strip()) and not _ADDRESS_RE.search(name) and not _PLACEHOLDER_RE.search(name)


def search_text(name: str) -> str:
    """Venue name cleaned for search: '+' and '&' read as 'and', parenthetical notes dropped."""
    text = re.sub(r"\([^)]*\)", " ", name)
    text = re.sub(r"\s*[+&]\s*", " and ", text)

    return " ".join(text.split())


def _city(raw: str) -> str:
    return city_from_text(raw) or canonical_city(raw)


def _is_place(node: dict) -> bool:
    kinds = node.get("@type")
    kinds = kinds if isinstance(kinds, list) else [kinds]

    return any(k in _PLACE_TYPES for k in kinds if isinstance(k, str))


_MAX_JSONLD_NODES = 10_000


def _walk(doc: object):
    """Every dict in a JSON-LD document, iteratively and capped, so hostile nesting cannot recurse."""
    stack, seen = [doc], 0

    while stack and seen < _MAX_JSONLD_NODES:
        node = stack.pop()
        seen += 1

        if isinstance(node, dict):
            yield node
            stack.extend(reversed(list(node.values())))
        elif isinstance(node, list):
            stack.extend(reversed(node))


def _venue_from(place: dict) -> VenueInfo | None:
    address = place.get("address")
    locality = address.get("addressLocality") if isinstance(address, dict) else None

    if not (isinstance(address, dict) and isinstance(locality, str) and locality.strip()):
        return None

    street = str(address.get("streetAddress") or "").strip(" ,")

    return VenueInfo(city=_city(locality.strip()), address=street or None, origin="page")


def place_from_jsonld(html: str) -> VenueInfo | None:
    """Venue city and street address from a page's schema.org data, or None.

    An Event's `location` wins; otherwise a Place counts only when it is the page's only one,
    so an organizer's or sponsor's address is never mistaken for the venue.
    """
    candidates: list[VenueInfo] = []

    for block in _JSONLD_RE.findall(html):
        try:
            doc = json.loads(block)
        except (json.JSONDecodeError, RecursionError):
            continue

        for node in _walk(doc):
            location = node.get("location")

            if isinstance(location, dict) and _is_place(location) and (venue := _venue_from(location)):
                return venue

            if _is_place(node) and (venue := _venue_from(node)):
                candidates.append(venue)

    return candidates[0] if len({(c.city, c.address) for c in candidates}) == 1 else None


_MAX_PAGE_BYTES = 2_000_000


async def lookup_from_pages(pages: dict[str, list[str]], *, delay: float = 1.0) -> dict[str, VenueInfo | None]:
    """Read venue event pages one at a time, `delay` seconds apart (venue name to candidate URLs).

    None marks a venue whose page loaded but carried no address. A failed page moves on to the
    venue's next URL; a 429 stops requests to that host for the run. Venues with no page that
    loaded are left out, so they are retried next run.
    """
    found: dict[str, VenueInfo | None] = {}
    blocked: set[str] = set()
    requests = 0

    async with aiohttp.ClientSession(headers=BROWSER_HEADERS) as session:
        for name, urls in pages.items():
            for url in urls:
                host = urlparse(url).netloc

                if host in blocked:
                    break

                if requests:
                    await asyncio.sleep(delay)

                requests += 1

                try:
                    # Redirects are not followed, so a page can never hand off to another host.
                    async with session.get(url, timeout=_TIMEOUT, allow_redirects=False) as resp:
                        resp.raise_for_status()

                        if resp.status != 200:
                            logger.warning("Venue page for %s redirected; skipped", name)
                            continue

                        body = await resp.content.read(_MAX_PAGE_BYTES)
                        found[name] = place_from_jsonld(body.decode(resp.charset or "utf-8", errors="replace"))
                        break
                except aiohttp.ClientResponseError as e:
                    logger.warning("Venue page failed for %s: %s", name, e.status)

                    if e.status == 429:
                        blocked.add(host)
                        logger.warning("Rate-limited by %s; its remaining venue pages wait for next run", host)
                except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
                    logger.warning("Venue page failed for %s: %s", name, type(e).__name__)

    logger.info("Read %d venue pages: %d with an address", len(found), sum(v is not None for v in found.values()))

    return found


def _names_match(query: str, found: str) -> bool:
    """Same venue name: identical words, one name's 2+ words inside the other's, or near-identical spelling."""
    q, f = venue_key(query), venue_key(found)

    if not q or not f:
        return False

    qw, fw = set(q.split()), set(f.split())
    small = min(qw, fw, key=len)

    return qw == fw or (len(small) >= 2 and (qw <= fw or fw <= qw)) or SequenceMatcher(None, q, f).ratio() >= _NAME_RATIO


def pick_match(name: str, results: list[dict]) -> VenueInfo | None:
    """The matching event-hosting place, or None when nothing matches or matches span several cities."""
    matches: list[VenueInfo] = []

    for r in results:
        if not isinstance(r, dict) or not isinstance(r.get("address") or {}, dict):
            continue

        if r.get("category") not in _EVENT_PLACE_CATEGORIES or not _names_match(name, r.get("name") or ""):
            continue

        addr = r.get("address") or {}
        raw_city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("municipality")

        if not raw_city:
            continue

        road = addr.get("road")
        street = " ".join(p for p in (addr.get("house_number"), road) if p) if road else None
        matches.append(VenueInfo(city=_city(raw_city), address=street, origin="osm"))

    if len({m.city for m in matches}) != 1:
        return None

    return matches[0]


async def lookup_venues(names: list[str], *, max_lookups: int = 40, delay: float = 1.1) -> dict[str, VenueInfo | None]:
    """Search OpenStreetMap for each venue, one request at a time `delay` seconds apart.

    Each venue is searched by its name as written, then by its cleaned form. None marks a
    confirmed miss. A request error, a malformed response, or an exhausted budget ends the
    run and leaves the remaining venues unrecorded, so they are retried next time.
    """
    found: dict[str, VenueInfo | None] = {}
    requests = 0

    async with aiohttp.ClientSession(headers=_HEADERS) as session:
        for name in names:
            if not is_searchable(name):
                found[name] = None
                continue

            queries = list(dict.fromkeys((name, search_text(name))))

            if requests + len(queries) > max_lookups:
                logger.info("Lookup budget of %d requests spent; remaining venues wait for next run", max_lookups)
                break

            match: VenueInfo | None = None

            try:
                for query in queries:
                    if requests:
                        await asyncio.sleep(delay)

                    requests += 1
                    params = {
                        "q": query, "format": "jsonv2", "addressdetails": "1", "limit": "5",
                        "countrycodes": "ca", "viewbox": _VIEWBOX, "bounded": "1",
                    }

                    async with session.get(NOMINATIM_URL, params=params, timeout=_TIMEOUT) as resp:
                        resp.raise_for_status()
                        results = await resp.json(content_type=None)

                    if not isinstance(results, list):
                        raise TypeError(f"unexpected response: {type(results).__name__}")

                    if match := pick_match(name, results):
                        break
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, TypeError) as e:
                logger.warning("Venue lookup stopped after %d requests: %s", requests, type(e).__name__)
                break

            found[name] = match

    logger.info("Searched %d venues: %d found", len(found), sum(v is not None for v in found.values()))

    return found
