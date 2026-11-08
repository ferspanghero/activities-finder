"""Live canary: hits every real source for today and fails when one breaks or goes silent.

Run with `pytest -m integration`. A failure here usually means a site changed its layout.
"""

import asyncio
from datetime import date

import pytest

from src.pipeline import PipelineResult, run_pipeline
from src.sources import SOURCES

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def live_result() -> PipelineResult:
    today = date.today()

    return asyncio.run(run_pipeline(today, today))


def _status(result: PipelineResult, name: str):
    return next(s for s in result.source_statuses if s.name == name)


@pytest.mark.parametrize("source_id", sorted(SOURCES))
def test_source_fetches_without_error(live_result: PipelineResult, source_id: str) -> None:
    # Arrange, Act
    status = _status(live_result, SOURCES[source_id].name)

    # Assert
    assert status.error is None, status.label()


@pytest.mark.parametrize("source_id", sorted(sid for sid, spec in SOURCES.items() if spec.expect_events))
def test_always_populated_source_returns_events(live_result: PipelineResult, source_id: str) -> None:
    # Arrange, Act
    status = _status(live_result, SOURCES[source_id].name)

    # Assert
    assert status.count > 0 and status.warning is None, status.label()


def test_most_events_have_a_city(live_result: PipelineResult) -> None:
    # Arrange, Act
    with_city = sum(1 for e in live_result.events if e.city)

    # Assert
    assert with_city / max(len(live_result.events), 1) >= 0.7
