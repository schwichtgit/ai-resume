"""Pytest configuration and fixtures."""

import os

import pytest

# Set test environment variables before importing app modules
os.environ.setdefault("OPENROUTER_API_KEY", "")
os.environ.setdefault("ENVIRONMENT", "development")
# Increase rate limit for testing
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "1000")


@pytest.fixture(autouse=True)
def reset_caches():
    """Reset cached settings and stores before each test."""
    from app.config import get_settings
    from app.session_store import reset_session_store

    get_settings.cache_clear()
    reset_session_store()

    # Reset rate limiter storage
    try:
        from app.main import limiter

        if hasattr(limiter, "_storage") and limiter._storage:
            limiter._storage.reset()
    except (ImportError, AttributeError):
        pass

    yield
    get_settings.cache_clear()
    reset_session_store()


@pytest.fixture
def mock_settings(monkeypatch):
    """Fixture to set test settings."""

    def _mock_settings(**kwargs):
        for key, value in kwargs.items():
            monkeypatch.setenv(key.upper(), str(value))
        from app.config import get_settings

        get_settings.cache_clear()
        return get_settings()

    return _mock_settings
