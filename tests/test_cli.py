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
    assert "--date" in result.stdout
    assert "--format" in result.stdout


def test_cli_invalid_date():
    result = subprocess.run(
        [sys.executable, "-m", "src", "--date", "not-a-date"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0
    assert "Invalid date" in result.stderr


@pytest.mark.integration
def test_cli_runs_end_to_end(tmp_path):
    """Full end-to-end run producing markdown file."""
    output_file = tmp_path / "events-test.md"
    result = subprocess.run(
        [sys.executable, "-m", "src", "--date", "2026-03-07",
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
        [sys.executable, "-m", "src", "--date", "2026-03-07",
         "--format", "html", "--output", str(output_file)],
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0
    assert output_file.exists()
    content = output_file.read_text()
    assert "<!DOCTYPE html>" in content
