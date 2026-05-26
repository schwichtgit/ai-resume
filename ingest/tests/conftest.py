"""Shared fixtures for ingest tests."""

import shutil
from collections.abc import Generator
from pathlib import Path

import pytest

from ingest import ingest_memory

PROJECT_ROOT = Path(__file__).parent.parent.parent
EXAMPLE_RESUME = PROJECT_ROOT / "data" / "example_resume.md"


@pytest.fixture(scope="session")
def jane_mv2_base(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Ingest the shipped example resume (Jane Chen) into a .mv2 once per session."""
    out = tmp_path_factory.mktemp("mv2") / "jane.mv2"
    ingest_memory(input_path=EXAMPLE_RESUME, output_path=out, verbose=False)
    return out


@pytest.fixture
def isolated_mv2(jane_mv2_base: Path, tmp_path: Path) -> Generator[str, None, None]:
    """Copy the session Jane .mv2 to an isolated temp path for exclusive access.

    memvid-core 2.0.139+ acquires an exclusive file lock on open.
    Each test gets its own copy so tests can run in parallel without
    lock contention.
    """
    dest = tmp_path / "test.mv2"
    shutil.copy2(jane_mv2_base, dest)
    yield str(dest)
    # Clean up any WAL files memvid creates alongside the copy
    for wal in tmp_path.glob("*.wal"):
        wal.unlink(missing_ok=True)
