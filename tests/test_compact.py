"""Tests for the compact two-step CLI (src.compact) and model serialization."""

import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from src.models import Event, SourceStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_event():
    return Event(
        name="Jazz Night",
        city="Vancouver",
        address="732 Main St",
        time="8:00 PM",
        event_date=date(2026, 3, 7),
        source_name="Do604",
        source_url="https://do604.com/events/jazz",
    )


@pytest.fixture
def sample_event_nulls():
    return Event(
        name="Mystery Show",
        city=None,
        address=None,
        time=None,
        event_date=date(2026, 3, 8),
        source_name="ShowHub",
        source_url="https://showhub.ca/show/mystery",
    )


@pytest.fixture
def sample_status():
    return SourceStatus(name="Do604", count=5, error=None)


@pytest.fixture
def sample_status_error():
    return SourceStatus(name="Rhythm Changes", count=0, error="Connection timeout")


@pytest.fixture
def sample_events_list(sample_event, sample_event_nulls):
    return [sample_event, sample_event_nulls]


@pytest.fixture
def sample_statuses_list(sample_status, sample_status_error):
    return [sample_status, sample_status_error]


# ---------------------------------------------------------------------------
# Event serialization
# ---------------------------------------------------------------------------

class TestEventSerialization:
    def test_to_dict(self, sample_event):
        d = sample_event.to_dict()
        assert d["name"] == "Jazz Night"
        assert d["city"] == "Vancouver"
        assert d["address"] == "732 Main St"
        assert d["time"] == "8:00 PM"
        assert d["event_date"] == "2026-03-07"
        assert d["source_name"] == "Do604"
        assert d["source_url"] == "https://do604.com/events/jazz"

    def test_from_dict(self):
        d = {
            "name": "Rock Show",
            "city": "Burnaby",
            "address": "100 Ave",
            "time": "9:00 PM",
            "event_date": "2026-03-07",
            "source_name": "ShowHub",
            "source_url": "https://showhub.ca/show/rock",
        }
        event = Event.from_dict(d)
        assert event.name == "Rock Show"
        assert event.city == "Burnaby"
        assert event.event_date == date(2026, 3, 7)

    def test_roundtrip(self, sample_event):
        restored = Event.from_dict(sample_event.to_dict())
        assert restored == sample_event

    def test_from_dict_with_nulls(self, sample_event_nulls):
        restored = Event.from_dict(sample_event_nulls.to_dict())
        assert restored.city is None
        assert restored.address is None
        assert restored.time is None
        assert restored == sample_event_nulls


# ---------------------------------------------------------------------------
# SourceStatus serialization
# ---------------------------------------------------------------------------

class TestSourceStatusSerialization:
    def test_to_dict(self, sample_status):
        d = sample_status.to_dict()
        assert d == {"name": "Do604", "count": 5, "error": None}

    def test_from_dict(self):
        d = {"name": "ShowHub", "count": 3, "error": None}
        status = SourceStatus.from_dict(d)
        assert status.name == "ShowHub"
        assert status.count == 3
        assert status.error is None

    def test_roundtrip(self, sample_status):
        restored = SourceStatus.from_dict(sample_status.to_dict())
        assert restored == sample_status

    def test_roundtrip_with_error(self, sample_status_error):
        restored = SourceStatus.from_dict(sample_status_error.to_dict())
        assert restored == sample_status_error


# ---------------------------------------------------------------------------
# Compact output (_print_compact)
# ---------------------------------------------------------------------------

class TestPrintCompact:
    def test_header_line(self, sample_events_list, sample_statuses_list, capsys):
        from src.compact import _print_compact

        _print_compact(sample_events_list, sample_statuses_list)
        captured = capsys.readouterr().out

        lines = captured.strip().split("\n")
        assert lines[0].startswith("# |")
        assert "Name" in lines[0]
        assert "City" in lines[0]
        assert "Source" in lines[0]

    def test_output_format(self, sample_events_list, sample_statuses_list, capsys):
        from src.compact import _print_compact

        _print_compact(sample_events_list, sample_statuses_list)
        captured = capsys.readouterr().out

        lines = captured.strip().split("\n")
        # First event line after header: 1-indexed, pipe-delimited
        assert lines[1].startswith("1 | Jazz Night |")
        assert "Vancouver" in lines[1]
        assert "732 Main St" in lines[1]
        assert "Do604" in lines[1]

    def test_null_fields_show_em_dash(self, sample_events_list, sample_statuses_list, capsys):
        from src.compact import _print_compact

        _print_compact(sample_events_list, sample_statuses_list)
        captured = capsys.readouterr().out

        lines = captured.strip().split("\n")
        # Third line (index 2) is the second event with None city/address/time → em dash
        assert "\u2014" in lines[2]

    def test_sources_footer(self, sample_events_list, sample_statuses_list, capsys):
        from src.compact import _print_compact

        _print_compact(sample_events_list, sample_statuses_list)
        captured = capsys.readouterr().out

        assert "Sources:" in captured
        assert "Do604 (5)" in captured
        assert "ERROR: Connection timeout" in captured


# ---------------------------------------------------------------------------
# Cache save/load
# ---------------------------------------------------------------------------

class TestCache:
    def test_save_and_load_roundtrip(self, sample_events_list, sample_statuses_list, tmp_path, monkeypatch):
        from src.compact import _save_cache, _load_cache, CACHE_PATH

        cache_file = tmp_path / ".events-cache.json"
        monkeypatch.setattr("src.compact.CACHE_PATH", str(cache_file))

        _save_cache(sample_events_list, sample_statuses_list, date(2026, 3, 7), date(2026, 3, 8))

        assert cache_file.exists()
        cache = _load_cache(str(cache_file))

        assert len(cache["events"]) == 2
        assert len(cache["source_statuses"]) == 2

        # Verify events roundtrip through cache
        restored_events = [Event.from_dict(d) for d in cache["events"]]
        assert restored_events == sample_events_list

    def test_cache_contains_dates(self, sample_events_list, sample_statuses_list, tmp_path, monkeypatch):
        from src.compact import _save_cache, _load_cache

        cache_file = tmp_path / ".events-cache.json"
        monkeypatch.setattr("src.compact.CACHE_PATH", str(cache_file))

        _save_cache(sample_events_list, sample_statuses_list, date(2026, 3, 7), date(2026, 3, 8))

        cache = _load_cache(str(cache_file))
        assert cache["from_date"] == "2026-03-07"
        assert cache["to_date"] == "2026-03-08"


# ---------------------------------------------------------------------------
# CLI — compact fetch subcommand
# ---------------------------------------------------------------------------

class TestCompactFetchCLI:
    def test_fetch_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "src.compact", "fetch", "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "--from" in result.stdout

    def test_fetch_invalid_from_date(self):
        result = subprocess.run(
            [sys.executable, "-m", "src.compact", "fetch", "--from", "bad", "--to", "2026-03-07"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode != 0
        assert "Invalid start date" in result.stderr

    def test_fetch_invalid_to_date(self):
        result = subprocess.run(
            [sys.executable, "-m", "src.compact", "fetch", "--from", "2026-03-07", "--to", "bad"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode != 0
        assert "Invalid end date" in result.stderr

    def test_fetch_reversed_range(self):
        result = subprocess.run(
            [sys.executable, "-m", "src.compact", "fetch", "--from", "2026-03-10", "--to", "2026-03-07"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode != 0
        assert "after" in result.stderr

    def test_fetch_range_too_large(self):
        result = subprocess.run(
            [sys.executable, "-m", "src.compact", "fetch", "--from", "2026-03-01", "--to", "2026-03-31"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode != 0
        assert "exceeds maximum" in result.stderr


# ---------------------------------------------------------------------------
# CLI — compact render subcommand
# ---------------------------------------------------------------------------

class TestCompactRenderCLI:
    def test_render_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "src.compact", "render", "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "--exclude" in result.stdout

    def test_render_excludes_indexes(self, tmp_path):
        """Render with --exclude removes the correct events."""
        events = [
            Event(name=f"Event {i}", city="Vancouver", address=None, time="8:00 PM",
                  event_date=date(2026, 3, 7), source_name="Do604",
                  source_url=f"https://do604.com/e/{i}")
            for i in range(1, 4)
        ]
        statuses = [SourceStatus(name="Do604", count=3, error=None)]
        cache_file = tmp_path / ".events-cache.json"
        cache = {
            "from_date": "2026-03-07",
            "to_date": "2026-03-07",
            "events": [{"name": e.name, "city": e.city, "address": e.address,
                        "time": e.time, "event_date": e.event_date.isoformat(),
                        "source_name": e.source_name, "source_url": e.source_url}
                       for e in events],
            "source_statuses": [{"name": s.name, "count": s.count, "error": s.error}
                                for s in statuses],
        }
        cache_file.write_text(json.dumps(cache))

        output_file = tmp_path / "events.html"
        result = subprocess.run(
            [sys.executable, "-m", "src.compact", "render", str(cache_file),
             "--exclude", "2", "--format", "html", "--output", str(output_file)],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert output_file.exists()
        content = output_file.read_text()
        assert "Event 1" in content
        assert "Event 2" not in content
        assert "Event 3" in content

    def test_render_deletes_cache(self, tmp_path):
        """Cache file is deleted after successful render."""
        cache_file = tmp_path / ".events-cache.json"
        cache = {
            "from_date": "2026-03-07",
            "to_date": "2026-03-07",
            "events": [{"name": "E", "city": None, "address": None, "time": None,
                        "event_date": "2026-03-07", "source_name": "Do604",
                        "source_url": "https://do604.com/e/1"}],
            "source_statuses": [{"name": "Do604", "count": 1, "error": None}],
        }
        cache_file.write_text(json.dumps(cache))

        output_file = tmp_path / "events.html"
        subprocess.run(
            [sys.executable, "-m", "src.compact", "render", str(cache_file),
             "--format", "html", "--output", str(output_file)],
            capture_output=True, text=True, timeout=10,
        )
        assert not cache_file.exists()

    def test_render_no_exclude_keeps_all(self, tmp_path):
        """Render without --exclude keeps all events."""
        cache_file = tmp_path / ".events-cache.json"
        cache = {
            "from_date": "2026-03-07",
            "to_date": "2026-03-07",
            "events": [
                {"name": "Event A", "city": "Vancouver", "address": None, "time": "7:00 PM",
                 "event_date": "2026-03-07", "source_name": "Do604",
                 "source_url": "https://do604.com/e/a"},
                {"name": "Event B", "city": "Burnaby", "address": None, "time": "8:00 PM",
                 "event_date": "2026-03-07", "source_name": "ShowHub",
                 "source_url": "https://showhub.ca/e/b"},
            ],
            "source_statuses": [
                {"name": "Do604", "count": 1, "error": None},
                {"name": "ShowHub", "count": 1, "error": None},
            ],
        }
        cache_file.write_text(json.dumps(cache))

        output_file = tmp_path / "events.html"
        result = subprocess.run(
            [sys.executable, "-m", "src.compact", "render", str(cache_file),
             "--format", "html", "--output", str(output_file)],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        content = output_file.read_text()
        assert "Event A" in content
        assert "Event B" in content

    def test_render_markdown_format(self, tmp_path):
        """Render with --format markdown produces .md file."""
        cache_file = tmp_path / ".events-cache.json"
        cache = {
            "from_date": "2026-03-07",
            "to_date": "2026-03-07",
            "events": [{"name": "Jazz Night", "city": "Vancouver", "address": "732 Main St",
                        "time": "8:00 PM", "event_date": "2026-03-07", "source_name": "Do604",
                        "source_url": "https://do604.com/e/1"}],
            "source_statuses": [{"name": "Do604", "count": 1, "error": None}],
        }
        cache_file.write_text(json.dumps(cache))

        output_file = tmp_path / "events.md"
        result = subprocess.run(
            [sys.executable, "-m", "src.compact", "render", str(cache_file),
             "--format", "markdown", "--output", str(output_file)],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        content = output_file.read_text()
        assert "Jazz Night" in content
        assert "Sources checked:" in content

    def test_render_default_output_filename_single_day(self, tmp_path):
        """Render without --output generates default filename in cwd."""
        cache_file = tmp_path / ".events-cache.json"
        cache = {
            "from_date": "2026-03-07",
            "to_date": "2026-03-07",
            "events": [{"name": "E", "city": None, "address": None, "time": None,
                        "event_date": "2026-03-07", "source_name": "Do604",
                        "source_url": "https://do604.com/e/1"}],
            "source_statuses": [{"name": "Do604", "count": 1, "error": None}],
        }
        cache_file.write_text(json.dumps(cache))

        # Run from project root so src module is found; file lands in project root
        result = subprocess.run(
            [sys.executable, "-m", "src.compact", "render", str(cache_file), "--format", "html"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        output = Path("events-2026-03-07.html")
        assert output.exists()
        output.unlink()

    def test_render_default_output_filename_range(self, tmp_path):
        """Render without --output generates range filename in cwd."""
        cache_file = tmp_path / ".events-cache.json"
        cache = {
            "from_date": "2026-03-07",
            "to_date": "2026-03-09",
            "events": [{"name": "E", "city": None, "address": None, "time": None,
                        "event_date": "2026-03-07", "source_name": "Do604",
                        "source_url": "https://do604.com/e/1"}],
            "source_statuses": [{"name": "Do604", "count": 1, "error": None}],
        }
        cache_file.write_text(json.dumps(cache))

        result = subprocess.run(
            [sys.executable, "-m", "src.compact", "render", str(cache_file), "--format", "html"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        output = Path("events-2026-03-07_to_2026-03-09.html")
        assert output.exists()
        output.unlink()

    def test_render_exclude_out_of_range_warns(self, tmp_path):
        """Excluding indexes beyond event count logs a warning."""
        cache_file = tmp_path / ".events-cache.json"
        cache = {
            "from_date": "2026-03-07",
            "to_date": "2026-03-07",
            "events": [{"name": "E", "city": None, "address": None, "time": None,
                        "event_date": "2026-03-07", "source_name": "Do604",
                        "source_url": "https://do604.com/e/1"}],
            "source_statuses": [{"name": "Do604", "count": 1, "error": None}],
        }
        cache_file.write_text(json.dumps(cache))

        output_file = tmp_path / "events.html"
        result = subprocess.run(
            [sys.executable, "-m", "src.compact", "render", str(cache_file),
             "--exclude", "999", "--format", "html", "--output", str(output_file)],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "out of range" in result.stderr.lower()

    def test_render_exclude_updates_source_counts(self, tmp_path):
        """After excluding events, the rendered footer reflects actual counts."""
        cache_file = tmp_path / ".events-cache.json"
        cache = {
            "from_date": "2026-03-07",
            "to_date": "2026-03-07",
            "events": [
                {"name": "Do604 Event 1", "city": "Vancouver", "address": None, "time": "7:00 PM",
                 "event_date": "2026-03-07", "source_name": "Do604",
                 "source_url": "https://do604.com/e/1"},
                {"name": "Do604 Event 2", "city": "Vancouver", "address": None, "time": "8:00 PM",
                 "event_date": "2026-03-07", "source_name": "Do604",
                 "source_url": "https://do604.com/e/2"},
                {"name": "ShowHub Event", "city": "Burnaby", "address": None, "time": "9:00 PM",
                 "event_date": "2026-03-07", "source_name": "ShowHub",
                 "source_url": "https://showhub.ca/e/1"},
            ],
            "source_statuses": [
                {"name": "Do604", "count": 2, "error": None},
                {"name": "ShowHub", "count": 1, "error": None},
            ],
        }
        cache_file.write_text(json.dumps(cache))

        output_file = tmp_path / "events.html"
        # Exclude the first Do604 event (index 1)
        result = subprocess.run(
            [sys.executable, "-m", "src.compact", "render", str(cache_file),
             "--exclude", "1", "--format", "html", "--output", str(output_file)],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        content = output_file.read_text()
        # Footer should show Do604 (1) not Do604 (2), since one was excluded
        assert "Do604 (1)" in content
        assert "ShowHub (1)" in content


# ---------------------------------------------------------------------------
# Shared utilities (used by both __main__.py and compact.py)
# ---------------------------------------------------------------------------

class TestSharedUtilities:
    def test_parse_and_validate_dates_valid(self):
        from src.cli_utils import parse_and_validate_dates
        from_date, to_date = parse_and_validate_dates("2026-03-07", "2026-03-09")
        assert from_date == date(2026, 3, 7)
        assert to_date == date(2026, 3, 9)

    def test_parse_and_validate_dates_invalid_from(self):
        from src.cli_utils import parse_and_validate_dates
        with pytest.raises(SystemExit):
            parse_and_validate_dates("bad", "2026-03-07")

    def test_parse_and_validate_dates_invalid_to(self):
        from src.cli_utils import parse_and_validate_dates
        with pytest.raises(SystemExit):
            parse_and_validate_dates("2026-03-07", "bad")

    def test_parse_and_validate_dates_reversed(self):
        from src.cli_utils import parse_and_validate_dates
        with pytest.raises(SystemExit):
            parse_and_validate_dates("2026-03-10", "2026-03-07")

    def test_parse_and_validate_dates_too_large(self):
        from src.cli_utils import parse_and_validate_dates
        with pytest.raises(SystemExit):
            parse_and_validate_dates("2026-03-01", "2026-03-31")

    def test_build_output_path_single_day_html(self):
        from src.cli_utils import build_output_path
        path = build_output_path(date(2026, 3, 7), date(2026, 3, 7), "html", None)
        assert path == "events-2026-03-07.html"

    def test_build_output_path_range_markdown(self):
        from src.cli_utils import build_output_path
        path = build_output_path(date(2026, 3, 7), date(2026, 3, 9), "markdown", None)
        assert path == "events-2026-03-07_to_2026-03-09.md"

    def test_build_output_path_explicit(self):
        from src.cli_utils import build_output_path
        path = build_output_path(date(2026, 3, 7), date(2026, 3, 7), "html", "/tmp/custom.html")
        assert path == "/tmp/custom.html"


# ---------------------------------------------------------------------------
# Cache path is absolute (issue #3)
# ---------------------------------------------------------------------------

class TestCachePathAbsolute:
    def test_save_cache_uses_absolute_path(self, sample_events_list, sample_statuses_list, tmp_path, monkeypatch):
        """Cache file is written next to the project, not relative to cwd."""
        from src.compact import _save_cache, CACHE_PATH

        # Even if we chdir somewhere else, cache should use an absolute path
        assert os.path.isabs(CACHE_PATH)
