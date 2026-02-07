"""In-memory session store with TTL-based expiration."""

import threading
from datetime import datetime, timezone
from typing import cast
from uuid import UUID

from cachetools import TTLCache

from ai_resume_api.config import get_settings
from ai_resume_api.models import Session


class SessionStore:
    """Thread-safe in-memory session store with automatic expiration."""

    def __init__(self, ttl_seconds: int | None = None, max_sessions: int | None = None):
        """Initialize the session store.

        Args:
            ttl_seconds: Time-to-live for sessions in seconds. Defaults to config value.
            max_sessions: Maximum number of sessions to store. Defaults to config value.
        """
        settings = get_settings()
        self._ttl = ttl_seconds or settings.session_ttl
        self._max_sessions = max_sessions or settings.max_sessions
        self._cache: TTLCache[UUID, Session] = TTLCache(
            maxsize=self._max_sessions,
            ttl=self._ttl,
        )
        self._lock = threading.Lock()

    def get(self, session_id: UUID) -> Session | None:
        """Get a session by ID, returning None if not found or expired."""
        with self._lock:
            result = self._cache.get(session_id)
            session = cast(Session, result) if result is not None else None
            if session:
                # Update last activity timestamp
                session.last_activity = datetime.now(timezone.utc)
            return session

    def get_or_create(self, session_id: UUID | None = None) -> Session:
        """Get an existing session or create a new one.

        Args:
            session_id: Optional session ID. If None or not found, creates new session.

        Returns:
            Existing or newly created session.
        """
        if session_id:
            session = self.get(session_id)
            if session:
                return session

        # Create new session
        session = Session()
        self.set(session.id, session)
        return session

    def set(self, session_id: UUID, session: Session) -> None:
        """Store or update a session."""
        with self._lock:
            self._cache[session_id] = session

    def delete(self, session_id: UUID) -> bool:
        """Delete a session by ID.

        Returns:
            True if session was deleted, False if not found.
        """
        with self._lock:
            if session_id in self._cache:
                del self._cache[session_id]
                return True
            return False

    def count(self) -> int:
        """Get the number of active sessions."""
        with self._lock:
            return len(self._cache)

    def clear(self) -> None:
        """Clear all sessions."""
        with self._lock:
            self._cache.clear()

    def cleanup_expired(self) -> int:
        """Manually trigger cleanup of expired sessions.

        Note: TTLCache handles expiration automatically, but this can be called
        to force immediate cleanup if needed.

        Returns:
            Number of sessions that were expired (always 0 for TTLCache as it
            handles expiration lazily).
        """
        with self._lock:
            # TTLCache expires items lazily, so we just need to access it
            # to trigger cleanup. We'll iterate to force expiration check.
            _ = list(self._cache.keys())
            return 0

    def get_stats(self) -> dict:
        """Get statistics about the session store."""
        with self._lock:
            return {
                "active_sessions": len(self._cache),
                "max_sessions": self._max_sessions,
                "ttl_seconds": self._ttl,
            }


# Global session store instance
_session_store: SessionStore | None = None


def get_session_store() -> SessionStore:
    """Get the global session store instance."""
    global _session_store
    if _session_store is None:
        _session_store = SessionStore()
    return _session_store


def reset_session_store() -> None:
    """Reset the global session store (useful for testing)."""
    global _session_store
    _session_store = None
