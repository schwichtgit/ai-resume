"""Tests for configuration module."""

import os
from unittest.mock import patch

import pytest

from app.config import Settings, get_settings


class TestSettings:
    """Tests for Settings class."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        # Create settings with explicit defaults (ignoring env vars)
        settings = Settings(
            openrouter_api_key="",
            rate_limit_per_minute=10,  # Override test env var
        )

        assert settings.openrouter_base_url == "https://openrouter.ai/api/v1"
        assert settings.llm_model == "nvidia/nemotron-nano-2407-instruct"
        assert settings.llm_max_tokens == 1024
        assert settings.llm_temperature == 0.7
        assert settings.memvid_grpc_url == "localhost:50051"
        assert settings.memvid_timeout_seconds == 5.0
        assert settings.session_ttl == 1800
        assert settings.max_sessions == 1000
        assert settings.rate_limit_per_minute == 10
        assert settings.port == 3000
        assert settings.log_level == "INFO"
        assert settings.environment == "development"

    def test_is_development(self):
        """Test is_development property."""
        settings = Settings(environment="development")
        assert settings.is_development is True

        settings = Settings(environment="production")
        assert settings.is_development is False

    def test_has_openrouter_key_valid(self):
        """Test has_openrouter_key with valid key."""
        settings = Settings(openrouter_api_key="sk-or-v1-test123")
        assert settings.has_openrouter_key is True

    def test_has_openrouter_key_invalid(self):
        """Test has_openrouter_key with invalid key."""
        settings = Settings(openrouter_api_key="invalid-key")
        assert settings.has_openrouter_key is False

    def test_has_openrouter_key_empty(self):
        """Test has_openrouter_key with empty key."""
        settings = Settings(openrouter_api_key="")
        assert settings.has_openrouter_key is False

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-or-v1-envtest"})
    def test_load_from_env(self):
        """Test loading settings from environment variables."""
        # Clear the cache to force reload
        get_settings.cache_clear()
        settings = get_settings()
        assert settings.openrouter_api_key == "sk-or-v1-envtest"
        get_settings.cache_clear()

    def test_get_settings_caching(self):
        """Test that get_settings returns cached instance."""
        get_settings.cache_clear()
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2
        get_settings.cache_clear()
