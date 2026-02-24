"""Tests for version injection (FUNC-081)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

import ai_resume_api.version as version_mod
from app.main import app
from app.session_store import reset_session_store


MOCK_PROFILE = {
    "name": "Test User",
    "title": "Test Title",
    "email": "test@example.com",
    "linkedin": "https://linkedin.com/in/test",
    "location": "Test Location",
    "status": "Available",
    "suggested_questions": ["What experience do they have?"],
    "tags": ["engineering"],
    "experience": [],
    "skills": {"strong": ["Python"], "moderate": [], "gaps": []},
    "fit_assessment_examples": [],
}


def _mock_version_file(
    read_text_rv: str | None = None, read_text_se: type[Exception] | None = None
) -> MagicMock:
    """Create a mock Path object for _VERSION_FILE."""
    mock_path = MagicMock()
    if read_text_se is not None:
        mock_path.read_text.side_effect = read_text_se
    else:
        mock_path.read_text.return_value = read_text_rv
    return mock_path


class TestGetVersion:
    """Unit tests for get_version()."""

    def setup_method(self) -> None:
        """Reset version cache before each test."""
        version_mod._cached_version = None

    def test_get_version_reads_file(self) -> None:
        """get_version returns parsed JSON when VERSION file exists."""
        fake_json = json.dumps({"version": "1.2.3", "commit": "abc123"})
        with patch(
            "ai_resume_api.version._VERSION_FILE", _mock_version_file(read_text_rv=fake_json)
        ):
            result = version_mod.get_version()

        assert result == {"version": "1.2.3", "commit": "abc123"}

    def test_get_version_file_not_found(self) -> None:
        """get_version returns dev fallback when VERSION file is missing."""
        with patch(
            "ai_resume_api.version._VERSION_FILE",
            _mock_version_file(read_text_se=FileNotFoundError),
        ):
            result = version_mod.get_version()

        assert result == {"version": "dev", "commit": "unknown"}

    def test_get_version_invalid_json(self) -> None:
        """get_version returns dev fallback when VERSION file has invalid JSON."""
        with patch(
            "ai_resume_api.version._VERSION_FILE", _mock_version_file(read_text_rv="not json")
        ):
            result = version_mod.get_version()

        assert result == {"version": "dev", "commit": "unknown"}

    def test_get_version_caches_result(self) -> None:
        """get_version reads the file only once, then returns cached result."""
        fake_json = json.dumps({"version": "2.0.0", "commit": "def456"})
        mock_file = _mock_version_file(read_text_rv=fake_json)
        with patch("ai_resume_api.version._VERSION_FILE", mock_file):
            version_mod.get_version()
            version_mod.get_version()

        mock_file.read_text.assert_called_once()

    def test_get_version_partial_json(self) -> None:
        """get_version defaults commit to 'unknown' when key is missing."""
        fake_json = json.dumps({"version": "1.0.0"})
        with patch(
            "ai_resume_api.version._VERSION_FILE", _mock_version_file(read_text_rv=fake_json)
        ):
            result = version_mod.get_version()

        assert result == {"version": "1.0.0", "commit": "unknown"}


class TestVersionEndpoint:
    """Integration tests for GET /api/v1/version."""

    def test_version_endpoint_returns_version(self) -> None:
        """GET /api/v1/version returns 200 with version and commit keys."""
        reset_session_store()

        with (
            patch("app.main.get_memvid_client") as mock_get_memvid,
            patch("app.main.get_openrouter_client") as mock_get_or,
            patch("app.config.get_settings") as mock_get_settings,
        ):
            mock_settings = AsyncMock()
            mock_settings.load_profile_from_memvid = AsyncMock(return_value=MOCK_PROFILE)
            mock_settings.load_profile = lambda: MOCK_PROFILE
            mock_settings.rate_limit_per_minute = 1000
            mock_get_settings.return_value = mock_settings

            mock_memvid = AsyncMock()
            mock_get_memvid.return_value = mock_memvid

            mock_or = AsyncMock()
            mock_get_or.return_value = mock_or

            with TestClient(app) as client:
                response = client.get("/api/v1/version")

            assert response.status_code == 200
            data = response.json()
            assert "version" in data
            assert "commit" in data

        reset_session_store()

    def test_version_endpoint_rate_limited(self) -> None:
        """GET /api/v1/version returns 429 when rate limit is exceeded."""
        reset_session_store()

        with (
            patch("app.main.get_memvid_client") as mock_get_memvid,
            patch("app.main.get_openrouter_client") as mock_get_or,
            patch("app.config.get_settings") as mock_get_settings,
            patch("app.main.get_settings") as mock_main_get_settings,
        ):
            mock_settings = AsyncMock()
            mock_settings.load_profile_from_memvid = AsyncMock(return_value=MOCK_PROFILE)
            mock_settings.load_profile = lambda: MOCK_PROFILE
            mock_settings.rate_limit_per_minute = 2
            mock_get_settings.return_value = mock_settings
            mock_main_get_settings.return_value = mock_settings

            mock_memvid = AsyncMock()
            mock_get_memvid.return_value = mock_memvid

            mock_or = AsyncMock()
            mock_get_or.return_value = mock_or

            from app.main import limiter

            limiter.reset()

            with TestClient(app, raise_server_exceptions=False) as client:
                # Send 2 requests (should succeed under limit of 2/minute)
                for i in range(2):
                    resp = client.get("/api/v1/version")
                    assert resp.status_code == 200, f"Request {i} failed with {resp.status_code}"

                # 3rd request should be rate limited
                resp = client.get("/api/v1/version")
                assert resp.status_code == 429

        reset_session_store()
