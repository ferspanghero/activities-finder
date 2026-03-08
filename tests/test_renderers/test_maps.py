"""Tests for src/renderers/maps.py"""

from src.renderers.maps import build_maps_url

MAPS_PREFIX = "https://www.google.com/maps/search/?api=1&query="


def test_returns_none_for_none_address():
    assert build_maps_url(None) is None


def test_returns_none_for_empty_address():
    assert build_maps_url("") is None


def test_basic_address():
    url = build_maps_url("732 Main St")
    assert url == f"{MAPS_PREFIX}732%20Main%20St"


def test_address_with_special_characters():
    url = build_maps_url("123 O'Brien Ave")
    assert url == f"{MAPS_PREFIX}123%20O%27Brien%20Ave"


def test_address_with_ampersand():
    url = build_maps_url("Bar & Grill, 5th Ave")
    assert url == f"{MAPS_PREFIX}Bar%20%26%20Grill%2C%205th%20Ave"


def test_address_with_slash():
    url = build_maps_url("123 Main St / Unit 5")
    assert "%2F" in url
