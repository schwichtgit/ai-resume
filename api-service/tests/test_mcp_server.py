"""Tests for MCP server module."""

import inspect
from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import ai_resume_api.mcp_server as mcp_server
from ai_resume_api.mcp_server import (
    _check_rate_limit,
    _derive_base_url,
    _get_config_template,
    mcp_config_router,
)
from app.main import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MOCK_PROFILE = {
    "name": "John Doe",
    "title": "Senior Engineer",
    "email": "john@example.com",
    "suggested_questions": ["Tell me about your experience"],
}


@pytest.fixture(autouse=True)
def _reset_rate_limit_store() -> None:
    """Clear MCP rate limit store before each test."""
    mcp_server._rate_limit_store.clear()


@pytest.fixture
def mcp_config_client() -> TestClient:
    """TestClient for MCP config router only (isolated from main app)."""
    test_app = FastAPI()
    test_app.include_router(mcp_config_router)
    return TestClient(test_app)


@pytest.fixture
def mock_profile_for_mcp() -> Generator[AsyncMock, None, None]:
    """Mock get_settings inside mcp_server to return a profile."""
    mock_settings = MagicMock()
    mock_settings.load_profile_from_memvid = AsyncMock(return_value=MOCK_PROFILE)
    mock_settings.load_profile.return_value = MOCK_PROFILE

    with patch("ai_resume_api.mcp_server.get_settings", return_value=mock_settings):
        yield mock_settings


# ---------------------------------------------------------------------------
# Unit Tests: _check_rate_limit
# ---------------------------------------------------------------------------


class TestCheckRateLimit:
    """Tests for the _check_rate_limit function."""

    def test_allows_under_limit(self) -> None:
        """Calls under the limit should all be allowed."""
        for _ in range(5):
            assert _check_rate_limit("test-ip") is True

    def test_blocks_over_limit(self) -> None:
        """The 61st call within the window should be blocked."""
        for i in range(mcp_server.MCP_RATE_LIMIT):
            result = _check_rate_limit("flood-ip")
            assert result is True, f"Call {i + 1} should be allowed"

        # 61st call should be blocked
        assert _check_rate_limit("flood-ip") is False

    def test_different_ips_independent(self) -> None:
        """Rate limits are tracked per IP."""
        for _ in range(mcp_server.MCP_RATE_LIMIT):
            _check_rate_limit("ip-a")

        # ip-a is exhausted
        assert _check_rate_limit("ip-a") is False
        # ip-b should still be allowed
        assert _check_rate_limit("ip-b") is True


# ---------------------------------------------------------------------------
# Unit Tests: _derive_base_url
# ---------------------------------------------------------------------------


class TestDeriveBaseUrl:
    """Tests for the _derive_base_url function."""

    def test_from_forwarded_headers(self) -> None:
        """Should use x-forwarded-proto and x-forwarded-host when present."""
        request = MagicMock()
        request.headers = {
            "x-forwarded-proto": "https",
            "x-forwarded-host": "example.com",
        }

        result = _derive_base_url(request)
        assert result == "https://example.com"

    def test_fallback_to_host(self) -> None:
        """Should fall back to host header when forwarded headers are absent."""
        request = MagicMock()
        request.headers = {"host": "localhost:3000"}

        result = _derive_base_url(request)
        assert result == "https://localhost:3000"

    def test_fallback_to_localhost(self) -> None:
        """Should default to https://localhost when no headers present."""
        request = MagicMock()
        request.headers = {}

        result = _derive_base_url(request)
        assert result == "https://localhost"


# ---------------------------------------------------------------------------
# Unit Tests: _get_config_template
# ---------------------------------------------------------------------------


class TestGetConfigTemplate:
    """Tests for the _get_config_template function."""

    def test_claude_desktop(self) -> None:
        """Should return config with mcpServers containing the MCP URL."""
        template = _get_config_template("claude-desktop", "https://example.com", "John Doe")

        assert template is not None
        assert template["label"] == "Claude Desktop"
        assert "instructions" in template
        config = template["config"]
        assert "mcpServers" in config
        server_name = "john-doe-resume"
        assert server_name in config["mcpServers"]
        assert config["mcpServers"][server_name]["url"] == "https://example.com/mcp"

    def test_claude_web(self) -> None:
        """Should return a flat URL config for Claude Web."""
        template = _get_config_template("claude-web", "https://example.com", "John Doe")

        assert template is not None
        assert template["label"] == "Claude Web"
        assert template["config"]["url"] == "https://example.com/mcp"

    def test_cursor(self) -> None:
        """Should return config with mcpServers for Cursor."""
        template = _get_config_template("cursor", "https://example.com", "John Doe")

        assert template is not None
        assert template["label"] == "Cursor"
        assert "mcpServers" in template["config"]

    def test_unknown_client_returns_none(self) -> None:
        """Unknown client ID should return None."""
        result = _get_config_template("unknown-client", "https://example.com", "John Doe")
        assert result is None

    def test_server_name_derived_from_profile_name(self) -> None:
        """Server name should be lowercase-hyphenated profile name + '-resume'."""
        template = _get_config_template("claude-desktop", "https://example.com", "Jane Smith")

        assert template is not None
        assert "jane-smith-resume" in template["config"]["mcpServers"]


# ---------------------------------------------------------------------------
# Unit Tests: Statelessness check
# ---------------------------------------------------------------------------


class TestMcpToolsStateless:
    """Verify MCP tools do not reference session state."""

    def test_no_session_store_references(self) -> None:
        """MCP server module should not reference session_store or session_id."""
        source = inspect.getsource(mcp_server)
        assert "session_store" not in source, (
            "mcp_server.py references session_store -- MCP tools must be stateless"
        )
        assert "session_id" not in source, (
            "mcp_server.py references session_id -- MCP tools must be stateless"
        )


# ---------------------------------------------------------------------------
# Integration Tests: Config Endpoints (isolated router)
# ---------------------------------------------------------------------------


class TestListMcpClients:
    """Tests for GET /api/v1/mcp/clients."""

    def test_returns_client_list(self, mcp_config_client: TestClient) -> None:
        """Should return the list of supported MCP clients."""
        response = mcp_config_client.get("/api/v1/mcp/clients")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3

        ids = {item["id"] for item in data}
        assert ids == {"claude-desktop", "claude-web", "cursor"}

        for item in data:
            assert "id" in item
            assert "label" in item


class TestGetMcpConfig:
    """Tests for GET /api/v1/mcp/config/{client_id}."""

    def test_claude_desktop_config(
        self,
        mcp_config_client: TestClient,
        mock_profile_for_mcp: Any,
    ) -> None:
        """Should return config for claude-desktop with correct structure."""
        response = mcp_config_client.get(
            "/api/v1/mcp/config/claude-desktop",
            headers={
                "x-forwarded-proto": "https",
                "x-forwarded-host": "example.com",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "config" in data
        assert "instructions" in data
        assert "label" in data

    def test_unknown_client_returns_404(
        self,
        mcp_config_client: TestClient,
        mock_profile_for_mcp: Any,
    ) -> None:
        """Unknown client ID should return 404."""
        response = mcp_config_client.get("/api/v1/mcp/config/unknown")
        assert response.status_code == 404

    def test_config_url_contains_mcp_path(
        self,
        mcp_config_client: TestClient,
        mock_profile_for_mcp: Any,
    ) -> None:
        """The URL in the config should end with /mcp."""
        response = mcp_config_client.get(
            "/api/v1/mcp/config/claude-desktop",
            headers={
                "x-forwarded-proto": "https",
                "x-forwarded-host": "resume.example.com",
            },
        )

        assert response.status_code == 200
        data = response.json()
        config = data["config"]
        # claude-desktop has mcpServers -> server_name -> url
        server_configs = config.get("mcpServers", {})
        urls = [v["url"] for v in server_configs.values()]
        assert len(urls) == 1
        assert urls[0] == "https://resume.example.com/mcp"

    def test_config_uses_profile_name_for_server_key(
        self,
        mcp_config_client: TestClient,
        mock_profile_for_mcp: Any,
    ) -> None:
        """Server key in mcpServers should be derived from profile name."""
        response = mcp_config_client.get(
            "/api/v1/mcp/config/claude-desktop",
            headers={"x-forwarded-host": "example.com"},
        )

        assert response.status_code == 200
        data = response.json()
        servers = data["config"]["mcpServers"]
        assert "john-doe-resume" in servers

    def test_fallback_profile_name(
        self,
        mcp_config_client: TestClient,
    ) -> None:
        """When profile is None, server name uses 'candidate'."""
        mock_settings = MagicMock()
        mock_settings.load_profile_from_memvid = AsyncMock(return_value=None)
        mock_settings.load_profile.return_value = None

        with patch("ai_resume_api.mcp_server.get_settings", return_value=mock_settings):
            response = mcp_config_client.get(
                "/api/v1/mcp/config/claude-desktop",
                headers={"x-forwarded-host": "example.com"},
            )

        assert response.status_code == 200
        data = response.json()
        servers = data["config"]["mcpServers"]
        assert "candidate-resume" in servers


# ---------------------------------------------------------------------------
# Integration Test: MCP disabled in main app
# ---------------------------------------------------------------------------


class TestMcpDisabledInMainApp:
    """Verify that MCP config endpoints return 404 when mcp_enabled=False."""

    @pytest.fixture
    def client(self) -> Generator[TestClient, None, None]:
        """Default test client (mcp_enabled=False by default)."""
        with TestClient(app) as c:
            yield c

    def test_mcp_clients_404_when_disabled(self, client: TestClient) -> None:
        """GET /api/v1/mcp/clients should 404 when MCP is disabled."""
        response = client.get("/api/v1/mcp/clients")
        assert response.status_code == 404

    def test_mcp_config_404_when_disabled(self, client: TestClient) -> None:
        """GET /api/v1/mcp/config/claude-desktop should 404 when MCP is disabled."""
        response = client.get("/api/v1/mcp/config/claude-desktop")
        assert response.status_code == 404
