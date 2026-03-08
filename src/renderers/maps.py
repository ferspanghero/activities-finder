"""Google Maps URL builder for event addresses."""

from urllib.parse import quote


def build_maps_url(address: str | None) -> str | None:
    """Build a Google Maps search URL from an address. Returns None if address is falsy."""
    if not address:
        return None
    return f"https://www.google.com/maps/search/?api=1&query={quote(address, safe='')}"
