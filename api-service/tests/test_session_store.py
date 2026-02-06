"""Tests for session store module."""

from uuid import uuid4

from app.models import Session
from app.session_store import SessionStore, get_session_store, reset_session_store


class TestSessionStore:
    """Tests for SessionStore class."""

    def setup_method(self):
        """Reset session store before each test."""
        reset_session_store()

    def test_create_store(self):
        """Test creating a session store with custom parameters."""
        store = SessionStore(ttl_seconds=60, max_sessions=10)
        assert store._ttl == 60
        assert store._max_sessions == 10

    def test_set_and_get_session(self):
        """Test storing and retrieving a session."""
        store = SessionStore()
        session = Session()
        store.set(session.id, session)

        retrieved = store.get(session.id)
        assert retrieved is not None
        assert retrieved.id == session.id

    def test_get_nonexistent_session(self):
        """Test getting a session that doesn't exist."""
        store = SessionStore()
        result = store.get(uuid4())
        assert result is None

    def test_get_or_create_new_session(self):
        """Test get_or_create creates new session when none exists."""
        store = SessionStore()
        session = store.get_or_create(None)

        assert session is not None
        assert session.id is not None
        assert store.count() == 1

    def test_get_or_create_existing_session(self):
        """Test get_or_create returns existing session."""
        store = SessionStore()
        session1 = store.get_or_create(None)
        session2 = store.get_or_create(session1.id)

        assert session1.id == session2.id
        assert store.count() == 1

    def test_get_or_create_missing_session_id(self):
        """Test get_or_create creates new session when ID not found."""
        store = SessionStore()
        missing_id = uuid4()
        session = store.get_or_create(missing_id)

        assert session is not None
        assert session.id != missing_id  # New session created
        assert store.count() == 1

    def test_delete_session(self):
        """Test deleting a session."""
        store = SessionStore()
        session = Session()
        store.set(session.id, session)

        assert store.delete(session.id) is True
        assert store.get(session.id) is None
        assert store.count() == 0

    def test_delete_nonexistent_session(self):
        """Test deleting a session that doesn't exist."""
        store = SessionStore()
        assert store.delete(uuid4()) is False

    def test_count(self):
        """Test counting sessions."""
        store = SessionStore()
        assert store.count() == 0

        store.get_or_create(None)
        assert store.count() == 1

        store.get_or_create(None)
        assert store.count() == 2

    def test_clear(self):
        """Test clearing all sessions."""
        store = SessionStore()
        store.get_or_create(None)
        store.get_or_create(None)
        assert store.count() == 2

        store.clear()
        assert store.count() == 0

    def test_get_stats(self):
        """Test getting store statistics."""
        store = SessionStore(ttl_seconds=120, max_sessions=50)
        store.get_or_create(None)

        stats = store.get_stats()
        assert stats["active_sessions"] == 1
        assert stats["max_sessions"] == 50
        assert stats["ttl_seconds"] == 120

    def test_cleanup_expired(self):
        """Test cleanup_expired method."""
        store = SessionStore()
        store.get_or_create(None)

        # This method triggers lazy expiration check
        expired = store.cleanup_expired()
        assert expired == 0


class TestGlobalSessionStore:
    """Tests for global session store functions."""

    def setup_method(self):
        """Reset session store before each test."""
        reset_session_store()

    def test_get_session_store(self):
        """Test getting global session store."""
        store1 = get_session_store()
        store2 = get_session_store()
        assert store1 is store2

    def test_reset_session_store(self):
        """Test resetting global session store."""
        store1 = get_session_store()
        store1.get_or_create(None)

        reset_session_store()
        store2 = get_session_store()

        assert store1 is not store2
        assert store2.count() == 0
