"""Tests for OpenRouter LLM client."""

import json
from collections.abc import AsyncIterator, Callable
from typing import Any

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ai_resume_api.openrouter_client import (
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

    def test_init_default_values(self) -> None:
        """Test client initialization with defaults."""
        client = OpenRouterClient()
        assert client._model == "nvidia/nemotron-nano-9b-v2:free"
        assert client._max_tokens == 1024
        assert client._temperature == 0.7

    def test_init_custom_values(self) -> None:
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

    def test_is_configured_with_valid_key(self) -> None:
        """Test is_configured with valid API key."""
        client = OpenRouterClient(api_key="sk-or-v1-test123")
        assert client.is_configured is True

    def test_is_configured_with_invalid_key(self) -> None:
        """Test is_configured with invalid API key."""
        client = OpenRouterClient(api_key="invalid-key")
        assert client.is_configured is False

    def test_is_configured_with_empty_key(self) -> None:
        """Test is_configured with empty API key."""
        client = OpenRouterClient(api_key="")
        assert client.is_configured is False

    def test_build_messages(self) -> None:
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

    def test_build_messages_no_history(self) -> None:
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

    def test_llm_message(self) -> None:
        """Test LLMMessage dataclass."""
        msg = LLMMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_llm_response(self) -> None:
        """Test LLMResponse dataclass."""
        response = LLMResponse(
            content="Response text",
            tokens_used=50,
            finish_reason="stop",
        )
        assert response.content == "Response text"
        assert response.tokens_used == 50
        assert response.finish_reason == "stop"

    def test_streaming_chunk(self) -> None:
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

    def test_base_error(self) -> None:
        """Test base OpenRouterError."""
        error = OpenRouterError("Test error")
        assert str(error) == "Test error"

    def test_auth_error(self) -> None:
        """Test OpenRouterAuthError."""
        error = OpenRouterAuthError("Invalid key")
        assert str(error) == "Invalid key"
        assert isinstance(error, OpenRouterError)

    def test_rate_limit_error(self) -> None:
        """Test OpenRouterRateLimitError."""
        error = OpenRouterRateLimitError("Too many requests")
        assert str(error) == "Too many requests"
        assert isinstance(error, OpenRouterError)


class TestOpenRouterClientAsync:
    """Async tests for OpenRouterClient."""

    @pytest.mark.asyncio
    async def test_connect_and_close(self) -> None:
        """Test connect and close lifecycle."""
        client = OpenRouterClient(api_key="sk-test")
        await client.connect()
        assert client._client is not None
        await client.close()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Test async context manager."""
        async with OpenRouterClient(api_key="sk-test") as client:
            assert client._client is not None
        # Client should be closed after exiting context

    @pytest.mark.asyncio
    async def test_chat_without_connection(self) -> None:
        """Test that chat auto-connects."""
        client = OpenRouterClient(api_key="sk-test")
        # Mock the HTTP client to avoid actual API calls
        with patch.object(client, "_client") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Test"}, "finish_reason": "stop"}],
                "usage": {"total_tokens": 10},
            }
            mock_response.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)

            # This should work without explicit connect
            await client.chat(
                system_prompt="Be helpful",
                context="Context",
                user_message="Hi",
            )
            # Will auto-connect, but our mock won't actually work
            # This tests the code path


class TestOpenRouterHttpErrorHandling:
    """Tests for HTTP error handling."""

    def test_handle_http_error_auth(self) -> None:
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

    def test_handle_http_error_rate_limit(self) -> None:
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

    def test_handle_http_error_generic(self) -> None:
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

    def test_handle_http_error_json_parse_failure(self) -> None:
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

    def test_usage_defaults(self) -> None:
        """Test usage default values."""
        from ai_resume_api.openrouter_client import OpenRouterUsage

        usage = OpenRouterUsage()
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0

    def test_usage_with_values(self) -> None:
        """Test usage with custom values."""
        from ai_resume_api.openrouter_client import OpenRouterUsage

        usage = OpenRouterUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150


class TestGlobalClientFunctions:
    """Tests for global client functions."""

    @pytest.mark.asyncio
    async def test_get_openrouter_client_creates_singleton(self) -> None:
        """Test that get_openrouter_client creates a singleton."""
        from ai_resume_api.openrouter_client import (
            close_openrouter_client,
            get_openrouter_client,
        )

        # Reset global state
        import ai_resume_api.openrouter_client

        ai_resume_api.openrouter_client._openrouter_client = None

        client1 = await get_openrouter_client()
        client2 = await get_openrouter_client()
        assert client1 is client2

        # Clean up
        await close_openrouter_client()
        assert ai_resume_api.openrouter_client._openrouter_client is None

    @pytest.mark.asyncio
    async def test_close_openrouter_client_when_none(self) -> None:
        """Test closing when client is None."""
        import ai_resume_api.openrouter_client

        ai_resume_api.openrouter_client._openrouter_client = None

        # Should not raise
        from ai_resume_api.openrouter_client import close_openrouter_client

        await close_openrouter_client()


class TestOpenRouterMockModes:
    """Tests for mock mode functionality."""

    @pytest.mark.asyncio
    async def test_chat_with_mock_enabled(self, mock_settings: Callable[..., Any]) -> None:
        """Test chat() with mock mode enabled."""
        # Configure mock mode before creating client
        mock_settings(mock_openrouter="true", openrouter_api_key="")
        # Create client after settings are configured
        client = OpenRouterClient(api_key="")

        response = await client.chat(
            system_prompt="Be helpful",
            context="Resume content",
            user_message="What are your skills?",
        )

        assert response is not None
        assert isinstance(response, LLMResponse)
        assert "mock" in response.content.lower()
        assert response.tokens_used > 0
        assert response.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_chat_with_mock_disabled_no_api_key(
        self, mock_settings: Callable[..., Any]
    ) -> None:
        """Test chat() raises error when mock disabled but no API key."""
        mock_settings(mock_openrouter="false", openrouter_api_key="")
        client = OpenRouterClient(api_key="")

        with pytest.raises(OpenRouterAuthError) as exc_info:
            await client.chat(
                system_prompt="Be helpful",
                context="Resume content",
                user_message="What are your skills?",
            )
        assert "MOCK_OPENROUTER=false" in str(exc_info.value)
        assert "OPENROUTER_API_KEY" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_chat_stream_with_mock_enabled(self, mock_settings: Callable[..., Any]) -> None:
        """Test chat_stream() with mock mode enabled."""
        # Configure mock mode before creating client
        mock_settings(mock_openrouter="true", openrouter_api_key="")
        # Create client after settings are configured
        client = OpenRouterClient(api_key="")

        chunks = []
        async for chunk in client.chat_stream(
            system_prompt="Be helpful",
            context="Resume content",
            user_message="Tell me about yourself",
        ):
            chunks.append(chunk)

        assert len(chunks) > 0
        # Should have content chunks
        content_chunks = [c for c in chunks if c.content]
        assert len(content_chunks) > 0
        # Last chunk should have finish_reason
        assert chunks[-1].finish_reason == "stop"
        assert chunks[-1].tokens_used > 0

    @pytest.mark.asyncio
    async def test_chat_stream_with_mock_disabled_no_api_key(
        self, mock_settings: Callable[..., Any]
    ) -> None:
        """Test chat_stream() raises error when mock disabled but no API key."""
        mock_settings(mock_openrouter="false", openrouter_api_key="")
        client = OpenRouterClient(api_key="")

        with pytest.raises(OpenRouterAuthError) as exc_info:
            async for _ in client.chat_stream(
                system_prompt="Be helpful",
                context="Resume content",
                user_message="What are your skills?",
            ):
                pass
        assert "MOCK_OPENROUTER=false" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_mock_chat_response_format(self) -> None:
        """Test _mock_chat() generates proper responses."""
        client = OpenRouterClient(api_key="sk-test")

        response = await client._mock_chat("What are your skills?")

        assert isinstance(response, LLMResponse)
        assert "mock" in response.content.lower()
        assert "What are your skills?" in response.content or len(response.content) > 10
        assert response.tokens_used == 50
        assert response.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_mock_chat_stream_chunks(self) -> None:
        """Test _mock_chat_stream() generates proper chunks."""
        client = OpenRouterClient(api_key="sk-test")

        chunks = []
        async for chunk in client._mock_chat_stream("Tell me about yourself"):
            chunks.append(chunk)

        # Should have multiple chunks
        assert len(chunks) > 5
        # All but last should have content
        for chunk in chunks[:-1]:
            assert len(chunk.content) > 0
        # Last chunk should have finish_reason and token count
        assert chunks[-1].finish_reason == "stop"
        assert chunks[-1].tokens_used > 0


class TestOpenRouterStreamingSuccess:
    """Tests for successful streaming scenarios."""

    @pytest.mark.asyncio
    async def test_chat_stream_success_with_sse_parsing(self) -> None:
        """Test chat_stream() success with SSE parsing."""
        client = OpenRouterClient(api_key="sk-test-key")

        # Mock successful streaming response
        mock_lines = [
            "data: "
            + json.dumps(
                {
                    "choices": [{"delta": {"content": "Hello"}, "finish_reason": None}],
                }
            ),
            "data: "
            + json.dumps(
                {
                    "choices": [{"delta": {"content": " world"}, "finish_reason": None}],
                }
            ),
            "data: "
            + json.dumps(
                {"choices": [{"delta": {}, "finish_reason": "stop"}], "usage": {"total_tokens": 42}}
            ),
        ]

        async def mock_aiter_lines() -> AsyncIterator[str]:
            for line in mock_lines:
                yield line

        mock_response = MagicMock()
        mock_response.aiter_lines = mock_aiter_lines
        mock_response.raise_for_status = MagicMock()

        # Create proper async context manager
        class MockStreamContext:
            async def __aenter__(self) -> MagicMock:
                return mock_response

            async def __aexit__(self, *args: Any) -> None:
                return None

        mock_client = AsyncMock()
        mock_client.stream = MagicMock(return_value=MockStreamContext())

        client._client = mock_client

        chunks = []
        async for chunk in client.chat_stream(
            system_prompt="Be helpful",
            context="Context",
            user_message="Hi",
        ):
            chunks.append(chunk)

        assert len(chunks) == 3
        assert chunks[0].content == "Hello"
        assert chunks[1].content == " world"
        assert chunks[2].finish_reason == "stop"
        assert chunks[2].tokens_used == 42

    @pytest.mark.asyncio
    async def test_chat_stream_handles_done_event(self) -> None:
        """Test chat_stream() handles [DONE] event."""
        client = OpenRouterClient(api_key="sk-test-key")

        mock_lines = [
            "data: "
            + json.dumps(
                {
                    "choices": [{"delta": {"content": "Test"}, "finish_reason": None}],
                }
            ),
            "data: [DONE]",
        ]

        async def mock_aiter_lines() -> AsyncIterator[str]:
            for line in mock_lines:
                yield line

        mock_response = MagicMock()
        mock_response.aiter_lines = mock_aiter_lines
        mock_response.raise_for_status = MagicMock()

        # Create proper async context manager
        class MockStreamContext:
            async def __aenter__(self) -> MagicMock:
                return mock_response

            async def __aexit__(self, *args: Any) -> None:
                return None

        mock_client = AsyncMock()
        mock_client.stream = MagicMock(return_value=MockStreamContext())

        client._client = mock_client

        chunks = []
        async for chunk in client.chat_stream(
            system_prompt="Be helpful",
            context="Context",
            user_message="Hi",
        ):
            chunks.append(chunk)

        # Should get content chunk and DONE chunk
        assert len(chunks) == 2
        assert chunks[0].content == "Test"
        assert chunks[1].finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_chat_stream_handles_malformed_json(self) -> None:
        """Test chat_stream() handles malformed JSON chunks."""
        client = OpenRouterClient(api_key="sk-test-key")

        mock_lines = [
            "data: "
            + json.dumps(
                {
                    "choices": [{"delta": {"content": "Valid"}, "finish_reason": None}],
                }
            ),
            "data: {invalid json}",  # Malformed JSON
            "data: "
            + json.dumps(
                {
                    "choices": [{"delta": {"content": " content"}, "finish_reason": None}],
                }
            ),
            "data: [DONE]",
        ]

        async def mock_aiter_lines() -> AsyncIterator[str]:
            for line in mock_lines:
                yield line

        mock_response = MagicMock()
        mock_response.aiter_lines = mock_aiter_lines
        mock_response.raise_for_status = MagicMock()

        # Create proper async context manager
        class MockStreamContext:
            async def __aenter__(self) -> MagicMock:
                return mock_response

            async def __aexit__(self, *args: Any) -> None:
                return None

        mock_client = AsyncMock()
        mock_client.stream = MagicMock(return_value=MockStreamContext())

        client._client = mock_client

        chunks = []
        async for chunk in client.chat_stream(
            system_prompt="Be helpful",
            context="Context",
            user_message="Hi",
        ):
            chunks.append(chunk)

        # Should skip malformed chunk
        assert len(chunks) == 3
        assert chunks[0].content == "Valid"
        assert chunks[1].content == " content"

    @pytest.mark.asyncio
    async def test_chat_stream_handles_http_errors(self) -> None:
        """Test chat_stream() handles HTTP errors."""
        import httpx

        client = OpenRouterClient(api_key="sk-test-key")

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": {"message": "Server error"}}

        mock_http_error = httpx.HTTPStatusError(
            message="500 Internal Server Error",
            request=MagicMock(),
            response=mock_response,
        )

        # Create async context manager that raises on enter
        class MockStreamContext:
            async def __aenter__(self) -> MagicMock:
                raise mock_http_error

            async def __aexit__(self, *args: Any) -> None:
                return None

        mock_client = AsyncMock()
        mock_client.stream = MagicMock(return_value=MockStreamContext())

        client._client = mock_client

        with pytest.raises(OpenRouterError) as exc_info:
            async for _ in client.chat_stream(
                system_prompt="Be helpful",
                context="Context",
                user_message="Hi",
            ):
                pass
        assert "API error (500)" in str(exc_info.value)


class TestOpenRouterChatSuccess:
    """Tests for successful non-streaming chat."""

    @pytest.mark.asyncio
    async def test_chat_success_response(self) -> None:
        """Test chat() with successful response."""
        client = OpenRouterClient(api_key="sk-test-key")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "This is the response"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        client._client = mock_client

        response = await client.chat(
            system_prompt="Be helpful",
            context="Resume data",
            user_message="What are your skills?",
        )

        assert response.content == "This is the response"
        assert response.tokens_used == 30
        assert response.finish_reason == "stop"

        # Verify request was made correctly
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/chat/completions"
        payload = call_args[1]["json"]
        assert payload["model"] == "nvidia/nemotron-nano-9b-v2:free"
        assert payload["stream"] is False
