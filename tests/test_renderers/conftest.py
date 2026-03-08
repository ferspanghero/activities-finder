"""Shared fixtures for renderer tests."""

import pytest

from src.models import Event, SourceStatus


@pytest.fixture
def sample_events():
    return [
        Event(name="Jazz Night", city="Vancouver", address="732 Main St", time="8:00 PM",
              source_name="Do604", source_url="https://do604.com/events/jazz"),
        Event(name="Rock Show", city="Burnaby", address=None, time="9:00 PM",
              source_name="ShowHub", source_url="https://showhub.ca/show/rock"),
    ]


@pytest.fixture
def sample_statuses():
    return [
        SourceStatus(name="Do604", count=1, error=None),
        SourceStatus(name="Daily Hive", count=0, error=None),
        SourceStatus(name="Rhythm Changes", count=0, error="Connection timeout"),
        SourceStatus(name="ShowHub", count=1, error=None),
        SourceStatus(name="Infidels Jazz", count=0, error=None),
    ]
