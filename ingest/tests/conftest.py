"""Shared fixtures for ingest tests."""

import shutil
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
SOURCE_MV2 = PROJECT_ROOT / "data" / ".memvid" / "resume.mv2"


@pytest.fixture
def isolated_mv2(tmp_path):
    """Copy resume.mv2 to an isolated temp path for exclusive access.

    memvid-core 2.0.139+ acquires an exclusive file lock on open.
    Each test gets its own copy so tests can run in parallel without
    lock contention.
    """
    if not SOURCE_MV2.exists():
        pytest.skip(f"{SOURCE_MV2} not found. Run ingest first.")
    dest = tmp_path / "test.mv2"
    shutil.copy2(SOURCE_MV2, dest)
    yield str(dest)
    # Clean up any WAL files memvid creates alongside the copy
    for wal in tmp_path.glob("*.wal"):
        wal.unlink(missing_ok=True)
