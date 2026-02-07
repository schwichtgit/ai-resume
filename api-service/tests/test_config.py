"""Tests for configuration module."""

import os
from unittest.mock import patch

import pytest

from app.config import Settings, get_settings


class TestSettings:
    """Tests for Settings class."""

    def test_default_values(self) -> None:
        """Test that default values are set correctly."""
        # Create settings with explicit defaults (ignoring env vars)
        settings = Settings(
            openrouter_api_key="",
            rate_limit_per_minute=10,  # Override test env var
        )

        assert settings.openrouter_base_url == "https://openrouter.ai/api/v1"
        assert settings.llm_model == "nvidia/nemotron-nano-9b-v2:free"
        assert settings.llm_max_tokens == 1024
        assert settings.llm_temperature == 0.7
        assert settings.memvid_timeout_seconds == 5.0
        assert settings.session_ttl == 1800
        assert settings.max_sessions == 1000
        assert settings.rate_limit_per_minute == 10
        assert settings.port == 3000
        assert settings.log_level == "INFO"
        assert settings.environment == "development"

    def test_is_development(self) -> None:
        """Test is_development property."""
        settings = Settings(environment="development")
        assert settings.is_development is True

        settings = Settings(environment="production")
        assert settings.is_development is False

    def test_has_openrouter_key_valid(self) -> None:
        """Test has_openrouter_key with valid key."""
        settings = Settings(openrouter_api_key="sk-or-v1-test123")
        assert settings.has_openrouter_key is True

    def test_has_openrouter_key_invalid(self) -> None:
        """Test has_openrouter_key with invalid key."""
        settings = Settings(openrouter_api_key="invalid-key")
        assert settings.has_openrouter_key is False

    def test_has_openrouter_key_empty(self) -> None:
        """Test has_openrouter_key with empty key."""
        settings = Settings(openrouter_api_key="")
        assert settings.has_openrouter_key is False

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-or-v1-envtest"})
    def test_load_from_env(self) -> None:
        """Test loading settings from environment variables."""
        # Clear the cache to force reload
        get_settings.cache_clear()
        settings = get_settings()
        assert settings.openrouter_api_key == "sk-or-v1-envtest"
        get_settings.cache_clear()

    def test_get_settings_caching(self) -> None:
        """Test that get_settings returns cached instance."""
        get_settings.cache_clear()
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2
        get_settings.cache_clear()

    @patch.dict(os.environ, {"MEMVID_GRPC_URL": "memvid-service:50051"})
    def test_memvid_grpc_url_from_env(self) -> None:
        """Test memvid_grpc_url property with MEMVID_GRPC_URL env override."""
        settings = Settings()
        assert settings.memvid_grpc_url == "memvid-service:50051"

    def test_memvid_grpc_url_from_host_port(self) -> None:
        """Test memvid_grpc_url constructed from host:port."""
        settings = Settings(
            memvid_grpc_host="memvid-server",
            memvid_grpc_port=9090,
        )
        # Clear env var to ensure we're testing host:port construction
        with patch.dict(os.environ, {}, clear=False):
            if "MEMVID_GRPC_URL" in os.environ:
                del os.environ["MEMVID_GRPC_URL"]
            assert settings.memvid_grpc_url == "memvid-server:9090"

    def test_memvid_grpc_url_default(self) -> None:
        """Test memvid_grpc_url uses default localhost:50051."""
        settings = Settings()
        # Without env override, should use host:port from settings
        with patch.dict(os.environ, {}, clear=False):
            if "MEMVID_GRPC_URL" in os.environ:
                del os.environ["MEMVID_GRPC_URL"]
            assert settings.memvid_grpc_url == "localhost:50051"

    @pytest.mark.asyncio
    async def test_load_profile_from_memvid_success(self) -> None:
        """Test load_profile_from_memvid loads profile successfully."""
        from unittest.mock import AsyncMock, MagicMock, patch
        import json

        settings = Settings()

        # Mock profile data
        mock_profile = {
            "name": "Test Candidate",
            "title": "Senior Developer",
            "email": "test@example.com",
        }

        # Mock get_state response
        mock_state = {
            "found": True,
            "entity": "__profile__",
            "slots": {"data": json.dumps(mock_profile)},
        }

        # Mock the memvid client
        mock_client = MagicMock()
        mock_client.get_state = AsyncMock(return_value=mock_state)

        with patch(
            "ai_resume_api.memvid_client.get_memvid_client", AsyncMock(return_value=mock_client)
        ):
            profile = await settings.load_profile_from_memvid()

        assert profile is not None
        assert profile["name"] == "Test Candidate"
        assert profile["title"] == "Senior Developer"
        mock_client.get_state.assert_called_once_with("__profile__")

    @pytest.mark.asyncio
    async def test_load_profile_from_memvid_not_found(self) -> None:
        """Test load_profile_from_memvid when profile not found."""
        from unittest.mock import AsyncMock, MagicMock, patch

        settings = Settings()

        # Mock get_state response - not found
        mock_state = {"found": False}

        mock_client = MagicMock()
        mock_client.get_state = AsyncMock(return_value=mock_state)

        with patch(
            "ai_resume_api.memvid_client.get_memvid_client", AsyncMock(return_value=mock_client)
        ):
            profile = await settings.load_profile_from_memvid()

        assert profile is None
        mock_client.get_state.assert_called_once_with("__profile__")

    @pytest.mark.asyncio
    async def test_load_profile_from_memvid_json_decode_error(self) -> None:
        """Test load_profile_from_memvid handles JSON decode errors."""
        from unittest.mock import AsyncMock, MagicMock, patch

        settings = Settings()

        # Mock get_state with invalid JSON
        mock_state = {
            "found": True,
            "entity": "__profile__",
            "slots": {"data": "invalid json {{{"},
        }

        mock_client = MagicMock()
        mock_client.get_state = AsyncMock(return_value=mock_state)

        with patch(
            "ai_resume_api.memvid_client.get_memvid_client", AsyncMock(return_value=mock_client)
        ):
            profile = await settings.load_profile_from_memvid()

        assert profile is None

    @pytest.mark.asyncio
    async def test_load_profile_from_memvid_exception(self) -> None:
        """Test load_profile_from_memvid handles exceptions gracefully."""
        from unittest.mock import AsyncMock, patch

        settings = Settings()

        # Mock get_memvid_client to raise an exception
        with patch(
            "ai_resume_api.memvid_client.get_memvid_client",
            AsyncMock(side_effect=Exception("Connection error")),
        ):
            profile = await settings.load_profile_from_memvid()

        assert profile is None

    @pytest.mark.asyncio
    async def test_load_profile_from_memvid_empty_data_slot(self) -> None:
        """Test load_profile_from_memvid when data slot is empty."""
        from unittest.mock import AsyncMock, MagicMock, patch

        settings = Settings()

        # Mock get_state with empty data slot
        mock_state = {
            "found": True,
            "entity": "__profile__",
            "slots": {},  # No 'data' key
        }

        mock_client = MagicMock()
        mock_client.get_state = AsyncMock(return_value=mock_state)

        with patch(
            "ai_resume_api.memvid_client.get_memvid_client", AsyncMock(return_value=mock_client)
        ):
            profile = await settings.load_profile_from_memvid()

        assert profile is None

    def test_load_profile_returns_none_for_missing_file(self) -> None:
        """Test load_profile returns None when profile.json doesn't exist."""
        settings = Settings(profile_json_path="/nonexistent/profile.json")

        profile = settings.load_profile()

        assert profile is None

    def test_load_profile_handles_invalid_json(self) -> None:
        """Test load_profile handles invalid JSON gracefully."""
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            f.write("invalid json {{{")
            temp_path = f.name

        try:
            settings = Settings(profile_json_path=temp_path)
            profile = settings.load_profile()
            assert profile is None
        finally:
            os.unlink(temp_path)

    def test_get_system_prompt_from_profile_injects_ground_facts(self) -> None:
        """Test get_system_prompt_from_profile injects ground facts."""
        import tempfile
        import json

        mock_profile = {
            "name": "Jane Doe",
            "title": "Senior Python Developer",
            "system_prompt": "You are an AI assistant representing a job candidate.",
            "experience": [
                {"company": "Google", "role": "Engineer"},
                {"company": "Meta", "role": "Senior Engineer"},
                {"company": "Apple", "role": "Staff Engineer"},
            ],
        }

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".json", encoding="utf-8"
        ) as f:
            json.dump(mock_profile, f)
            temp_path = f.name

        try:
            settings = Settings(profile_json_path=temp_path)
            system_prompt = settings.get_system_prompt_from_profile()

            # Should inject ground facts
            assert "GROUND FACTS" in system_prompt
            assert "Jane Doe" in system_prompt
            assert "Senior Python Developer" in system_prompt
            assert "Google" in system_prompt
            # Should only include first 3 companies
            assert "Meta" in system_prompt
            assert "Apple" in system_prompt
        finally:
            os.unlink(temp_path)

    def test_get_system_prompt_from_profile_fallback(self) -> None:
        """Test get_system_prompt_from_profile uses fallback when no profile."""
        settings = Settings(profile_json_path="/nonexistent/profile.json")

        system_prompt = settings.get_system_prompt_from_profile()

        # Should return default system prompt
        assert system_prompt == settings.system_prompt
        assert "You are an AI assistant representing a job candidate" in system_prompt

    def test_get_system_prompt_from_profile_with_existing_ground_facts(self) -> None:
        """Test get_system_prompt doesn't duplicate GROUND FACTS."""
        import tempfile
        import json

        mock_profile = {
            "name": "John Smith",
            "title": "DevOps Engineer",
            "system_prompt": "You are an assistant.\n\nGROUND FACTS (NEVER VIOLATE THESE):\n- Existing fact",
            "experience": [],
        }

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".json", encoding="utf-8"
        ) as f:
            json.dump(mock_profile, f)
            temp_path = f.name

        try:
            settings = Settings(profile_json_path=temp_path)
            system_prompt = settings.get_system_prompt_from_profile()

            # Should not duplicate GROUND FACTS
            assert system_prompt.count("GROUND FACTS") == 1
        finally:
            os.unlink(temp_path)
