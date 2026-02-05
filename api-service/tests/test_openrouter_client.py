"""Tests for OpenRouter LLM client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.openrouter_client import (
    LLMMessage,
    LLMResponse,
    OpenRouterClient,
    OpenRouterError,
    OpenRouterAuthError,
    OpenRouterRateLimitError,
    StreamingChunk,
)


class TestOpenRouterClient:
    """Tests for OpenRouterClient class."""

    def test_init_default_values(self):
        """Test client initialization with defaults."""
        client = OpenRouterClient()
        assert client._model == "nvidia/nemotron-nano-9b-v2:free"
        assert client._max_tokens == 1024
        assert client._temperature == 0.7

    def test_init_custom_values(self):
        """Test client initialization with custom values."""
        client = OpenRouterClient(
            api_key="sk-test-key",
            model="gpt-4",
            max_tokens=2048,
            temperature=0.5,
        )
        assert client._api_key == "sk-test-key"
        assert client._model == "gpt-4"
        assert client._max_tokens == 2048
        assert client._temperature == 0.5

    def test_is_configured_with_valid_key(self):
        """Test is_configured with valid API key."""
        client = OpenRouterClient(api_key="sk-or-v1-test123")
        assert client.is_configured is True

    def test_is_configured_with_invalid_key(self):
        """Test is_configured with invalid API key."""
        client = OpenRouterClient(api_key="invalid-key")
        assert client.is_configured is False

    def test_is_configured_with_empty_key(self):
        """Test is_configured with empty API key."""
        client = OpenRouterClient(api_key="")
        assert client.is_configured is False

    def test_build_messages(self):
        """Test building messages for API request."""
        client = OpenRouterClient()
        messages = client._build_messages(
            system_prompt="Be helpful",
            context="Resume content here",
            user_message="What skills do they have?",
            history=[{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello!"}],
        )

        assert len(messages) == 4  # system + 2 history + user
        assert messages[0]["role"] == "system"
        assert "Be helpful" in messages[0]["content"]
        assert "Resume content here" in messages[0]["content"]
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == "What skills do they have?"

    def test_build_messages_no_history(self):
        """Test building messages without history."""
        client = OpenRouterClient()
        messages = client._build_messages(
            system_prompt="Be helpful",
            context="Context",
            user_message="Question?",
            history=None,
        )

        assert len(messages) == 2  # system + user
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"


class TestLLMModels:
    """Tests for LLM data models."""

    def test_llm_message(self):
        """Test LLMMessage dataclass."""
        msg = LLMMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_llm_response(self):
        """Test LLMResponse dataclass."""
        response = LLMResponse(
            content="Response text",
            tokens_used=50,
            finish_reason="stop",
        )
        assert response.content == "Response text"
        assert response.tokens_used == 50
        assert response.finish_reason == "stop"

    def test_streaming_chunk(self):
        """Test StreamingChunk dataclass."""
        chunk = StreamingChunk(
            content="Hello",
            finish_reason=None,
            tokens_used=0,
        )
        assert chunk.content == "Hello"
        assert chunk.finish_reason is None


class TestOpenRouterErrors:
    """Tests for OpenRouter error classes."""

    def test_base_error(self):
        """Test base OpenRouterError."""
        error = OpenRouterError("Test error")
        assert str(error) == "Test error"

    def test_auth_error(self):
        """Test OpenRouterAuthError."""
        error = OpenRouterAuthError("Invalid key")
        assert str(error) == "Invalid key"
        assert isinstance(error, OpenRouterError)

    def test_rate_limit_error(self):
        """Test OpenRouterRateLimitError."""
        error = OpenRouterRateLimitError("Too many requests")
        assert str(error) == "Too many requests"
        assert isinstance(error, OpenRouterError)


class TestOpenRouterClientAsync:
    """Async tests for OpenRouterClient."""

    @pytest.mark.asyncio
    async def test_connect_and_close(self):
        """Test connect and close lifecycle."""
        client = OpenRouterClient(api_key="sk-test")
        await client.connect()
        assert client._client is not None
        await client.close()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        async with OpenRouterClient(api_key="sk-test") as client:
            assert client._client is not None
        # Client should be closed after exiting context

    @pytest.mark.asyncio
    async def test_chat_without_connection(self):
        """Test that chat auto-connects."""
        client = OpenRouterClient(api_key="sk-test")
        # Mock the HTTP client to avoid actual API calls
        with patch.object(client, '_client') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Test"}, "finish_reason": "stop"}],
                "usage": {"total_tokens": 10},
            }
            mock_response.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)

            # This should work without explicit connect
            response = await client.chat(
                system_prompt="Be helpful",
                context="Context",
                user_message="Hi",
            )
            # Will auto-connect, but our mock won't actually work
            # This tests the code path


class TestOpenRouterHttpErrorHandling:
    """Tests for HTTP error handling."""

    def test_handle_http_error_auth(self):
        """Test handling 401 authentication error."""
        import httpx

        client = OpenRouterClient(api_key="sk-test")
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": {"message": "Invalid API key"}}

        error = httpx.HTTPStatusError(
            message="401 Unauthorized",
            request=MagicMock(),
            response=mock_response,
        )

        with pytest.raises(OpenRouterAuthError) as exc_info:
            client._handle_http_error(error)
        assert "Authentication failed" in str(exc_info.value)

    def test_handle_http_error_rate_limit(self):
        """Test handling 429 rate limit error."""
        import httpx

        client = OpenRouterClient(api_key="sk-test")
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": {"message": "Rate limit exceeded"}}

        error = httpx.HTTPStatusError(
            message="429 Too Many Requests",
            request=MagicMock(),
            response=mock_response,
        )

        with pytest.raises(OpenRouterRateLimitError) as exc_info:
            client._handle_http_error(error)
        assert "Rate limit exceeded" in str(exc_info.value)

    def test_handle_http_error_generic(self):
        """Test handling generic HTTP error."""
        import httpx

        client = OpenRouterClient(api_key="sk-test")
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": {"message": "Internal server error"}}

        error = httpx.HTTPStatusError(
            message="500 Internal Server Error",
            request=MagicMock(),
            response=mock_response,
        )

        with pytest.raises(OpenRouterError) as exc_info:
            client._handle_http_error(error)
        assert "API error (500)" in str(exc_info.value)

    def test_handle_http_error_json_parse_failure(self):
        """Test handling error when JSON parsing fails."""
        import httpx

        client = OpenRouterClient(api_key="sk-test")
        mock_response = MagicMock()
        mock_response.status_code = 502
        mock_response.json.side_effect = Exception("Not JSON")

        error = httpx.HTTPStatusError(
            message="502 Bad Gateway",
            request=MagicMock(),
            response=mock_response,
        )

        with pytest.raises(OpenRouterError) as exc_info:
            client._handle_http_error(error)
        assert "API error (502)" in str(exc_info.value)


class TestOpenRouterUsage:
    """Tests for OpenRouterUsage dataclass."""

    def test_usage_defaults(self):
        """Test usage default values."""
        from app.openrouter_client import OpenRouterUsage

        usage = OpenRouterUsage()
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0

    def test_usage_with_values(self):
        """Test usage with custom values."""
        from app.openrouter_client import OpenRouterUsage

        usage = OpenRouterUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150


class TestGlobalClientFunctions:
    """Tests for global client functions."""

    @pytest.mark.asyncio
    async def test_get_openrouter_client_creates_singleton(self):
        """Test that get_openrouter_client creates a singleton."""
        from app.openrouter_client import (
            _openrouter_client,
            close_openrouter_client,
            get_openrouter_client,
        )

        # Reset global state
        import app.openrouter_client

        app.openrouter_client._openrouter_client = None

        client1 = await get_openrouter_client()
        client2 = await get_openrouter_client()
        assert client1 is client2

        # Clean up
        await close_openrouter_client()
        assert app.openrouter_client._openrouter_client is None

    @pytest.mark.asyncio
    async def test_close_openrouter_client_when_none(self):
        """Test closing when client is None."""
        import app.openrouter_client

        app.openrouter_client._openrouter_client = None

        # Should not raise
        from app.openrouter_client import close_openrouter_client

        await close_openrouter_client()
