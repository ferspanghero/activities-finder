"""Tests for events/__main__.py — CLI entry point."""

import subprocess
import sys

import pytest


def test_cli_help():
    result = subprocess.run(
        [sys.executable, "-m", "src", "--help"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    assert "--from" in result.stdout
    assert "--to" in result.stdout
    assert "--format" in result.stdout


def test_cli_invalid_from_date():
    result = subprocess.run(
        [sys.executable, "-m", "src", "--from", "not-a-date", "--to", "2026-03-07"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0
    assert "Invalid start date" in result.stderr


def test_cli_invalid_to_date():
    result = subprocess.run(
        [sys.executable, "-m", "src", "--from", "2026-03-07", "--to", "not-a-date"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0
    assert "Invalid end date" in result.stderr


def test_cli_reversed_range():
    result = subprocess.run(
        [sys.executable, "-m", "src", "--from", "2026-03-10", "--to", "2026-03-07"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0
    assert "after" in result.stderr


def test_cli_range_too_large():
    result = subprocess.run(
        [sys.executable, "-m", "src", "--from", "2026-03-01", "--to", "2026-03-31"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0
    assert "exceeds maximum" in result.stderr


def test_cli_missing_from():
    result = subprocess.run(
        [sys.executable, "-m", "src", "--to", "2026-03-07"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0


def test_cli_missing_to():
    result = subprocess.run(
        [sys.executable, "-m", "src", "--from", "2026-03-07"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0


@pytest.mark.integration
def test_cli_runs_end_to_end(tmp_path):
    """Full end-to-end run producing markdown file."""
    output_file = tmp_path / "events-test.md"
    result = subprocess.run(
        [sys.executable, "-m", "src", "--from", "2026-03-07", "--to", "2026-03-07",
         "--format", "markdown", "--output", str(output_file)],
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0
    assert output_file.exists()
    content = output_file.read_text()
    assert "Found" in content
    assert "Sources checked:" in content


@pytest.mark.integration
def test_cli_html_output(tmp_path):
    """Full end-to-end run producing HTML file."""
    output_file = tmp_path / "events-test.html"
    result = subprocess.run(
        [sys.executable, "-m", "src", "--from", "2026-03-07", "--to", "2026-03-07",
         "--format", "html", "--output", str(output_file)],
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0
    assert output_file.exists()
    content = output_file.read_text()
    assert "<!DOCTYPE html>" in content
