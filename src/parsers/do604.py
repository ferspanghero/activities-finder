"""Parser for Do604 event listings (HTML)."""

from bs4 import BeautifulSoup

from src.models import Event

BASE_URL = "https://do604.com"


def parse_do604(html: str, source_url: str) -> list[Event]:
    """Parse Do604 HTML into Event objects."""
    soup = BeautifulSoup(html, "html.parser")
    events = []

    for card in soup.select("div.ds-listing.event-card"):
        name_el = card.select_one("span.ds-listing-event-title-text")
        if not name_el:
            continue

        city_el = card.select_one('meta[itemprop="addressLocality"]')
        street_el = card.select_one('meta[itemprop="streetAddress"]')
        time_el = card.select_one("div.ds-event-time")
        permalink = card.get("data-permalink", "")

        time_text = " ".join(time_el.get_text().split()) if time_el else None

        events.append(Event(
            name=name_el.get_text(strip=True),
            city=city_el["content"] if city_el else None,
            address=street_el["content"] if street_el else None,
            time=time_text,
            source_name="Do604",
            source_url=BASE_URL + permalink if permalink else source_url,
        ))

    return events
