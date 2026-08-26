"""Testy architektury: lockfile musi być obecny i śledzony przez Git."""

import subprocess
from pathlib import Path

import pytest

LOCKFILE = Path("uv.lock")


def test_uv_lock_exists() -> None:
    """uv.lock musi istnieć w repozytorium."""
    assert LOCKFILE.exists(), "uv.lock nie istnieje — uruchom 'uv lock'"


def test_uv_lock_is_tracked_by_git() -> None:
    """uv.lock musi być śledzony przez Git."""
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(LOCKFILE)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"uv.lock nie jest śledzony przez Git: {result.stderr}"