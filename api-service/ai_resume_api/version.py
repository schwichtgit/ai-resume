"""Build-time version injection with dev fallback."""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_VERSION_FILE = Path("/app/VERSION")
_cached_version: dict | None = None


def get_version() -> dict[str, str]:
    """Read version info from /app/VERSION, with dev fallback.

    Returns dict with 'version' and 'commit' keys.
    Caches the result after first read.
    """
    global _cached_version
    if _cached_version is not None:
        return _cached_version

    try:
        data = json.loads(_VERSION_FILE.read_text())
        _cached_version = {
            "version": data.get("version", "dev"),
            "commit": data.get("commit", "unknown"),
        }
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        _cached_version = {"version": "dev", "commit": "unknown"}

    return _cached_version
