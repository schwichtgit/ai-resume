"""OpenRouter LLM client with streaming support."""

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import httpx
import structlog

from ai_resume_api.config import get_settings

logger = structlog.get_logger()


class OpenRouterError(Exception):
    """Base exception for OpenRouter client errors."""

    pass


class OpenRouterAuthError(OpenRouterError):
    """Raised when authentication fails."""

    pass


class OpenRouterRateLimitError(OpenRouterError):
    """Raised when rate limit is exceeded."""

    pass


@dataclass
class LLMMessage:
    """A message in the conversation."""

    role: str  # "system", "user", or "assistant"
    content: str


@dataclass
class LLMResponse:
    """Non-streaming response from the LLM."""

    content: str
    tokens_used: int
    finish_reason: str | None = None


@dataclass
class StreamingChunk:
    """A chunk from a streaming response."""

    content: str = ""
    finish_reason: str | None = None
    tokens_used: int = 0


@dataclass
class OpenRouterUsage:
    """Token usage information."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class OpenRouterClient:
    """Async client for OpenRouter API with streaming support."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ):
        """Initialize the OpenRouter client.

        Args:
            api_key: OpenRouter API key. Defaults to config value.
            base_url: API base URL. Defaults to config value.
            model: Model ID to use. Defaults to config value.
            max_tokens: Maximum tokens in response. Defaults to config value.
            temperature: Sampling temperature. Defaults to config value.
        """
        settings = get_settings()
        self._api_key = api_key or settings.openrouter_api_key
        self._base_url = base_url or settings.openrouter_base_url
        self._model = model or settings.llm_model
        self._max_tokens = max_tokens or settings.llm_max_tokens
        self._temperature = temperature or settings.llm_temperature
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "OpenRouterClient":
        """Enter async context."""
        await self.connect()
        return self

    async def __aexit__(self, _exc_type: Any, _exc_val: Any, _exc_tb: Any) -> None:
        """Exit async context."""
        await self.close()

    async def connect(self) -> None:
        """Create the HTTP client.

        In mock mode (MOCK_OPENROUTER=true), skips creating a real HTTP client
        since all requests will be served by mock handlers.
        """
        settings = get_settings()
        if settings.mock_openrouter:
            logger.info(
                "OpenRouter client in mock mode, skipping HTTP client creation",
                model=self._model,
            )
            return

        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://frank-resume.schwichtenberg.us",
                "X-Title": "AI Resume Chat",
            },
            timeout=httpx.Timeout(60.0, connect=10.0),
        )
        logger.info("OpenRouter client connected", model=self._model)

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("OpenRouter client closed")

    def _build_messages(
        self,
        system_prompt: str,
        context: str,
        user_message: str,
        history: list[dict[str, str]] | None = None,
    ) -> list[dict[str, str]]:
        """Build the messages array for the API request.

        Args:
            system_prompt: System instructions for the model.
            context: Retrieved context from memvid.
            user_message: Current user message.
            history: Previous conversation history.

        Returns:
            List of message dicts for the API.
        """
        messages = []

        # System message with context
        full_system = f"""{system_prompt}

---
CONTEXT FROM RESUME:
{context}
---

Use the context above to answer the user's question. \
If the context doesn't contain relevant information, say so honestly."""

        messages.append({"role": "system", "content": full_system})

        # Add conversation history
        if history:
            messages.extend(history)

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        return messages

    async def chat(
        self,
        system_prompt: str,
        context: str,
        user_message: str,
        history: list[dict[str, str]] | None = None,
    ) -> LLMResponse:
        """Send a chat completion request (non-streaming).

        Args:
            system_prompt: System instructions for the model.
            context: Retrieved context from memvid.
            user_message: Current user message.
            history: Previous conversation history.

        Returns:
            LLM response with content and token usage.

        Raises:
            OpenRouterError: If the request fails.
            OpenRouterAuthError: If MOCK_OPENROUTER=false but API key missing.
        """
        settings = get_settings()

        # Check mock policy - fail loudly if real implementation unavailable
        if not self.is_configured:
            if settings.mock_openrouter:
                logger.info("MOCK_OPENROUTER=true: Using mock LLM response")
                return await self._mock_chat(user_message)
            else:
                error_msg = (
                    "FATAL: OpenRouter API key not configured with MOCK_OPENROUTER=false. "
                    "Either set OPENROUTER_API_KEY or set MOCK_OPENROUTER=true for testing."
                )
                logger.error(error_msg)
                raise OpenRouterAuthError(error_msg)

        if not self._client:
            await self.connect()

        messages = self._build_messages(system_prompt, context, user_message, history)

        payload = {
            "model": self._model,
            "messages": messages,
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
            "stream": False,
        }

        try:
            response = await self._client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()

            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            tokens_used = usage.get("total_tokens", 0)
            finish_reason = data["choices"][0].get("finish_reason")

            logger.info(
                "LLM response received",
                tokens=tokens_used,
                finish_reason=finish_reason,
            )

            return LLMResponse(
                content=content,
                tokens_used=tokens_used,
                finish_reason=finish_reason,
            )

        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
            raise  # Re-raise after logging

    async def chat_stream(
        self,
        system_prompt: str,
        context: str,
        user_message: str,
        history: list[dict[str, str]] | None = None,
    ) -> AsyncIterator[StreamingChunk]:
        """Send a streaming chat completion request.

        Args:
            system_prompt: System instructions for the model.
            context: Retrieved context from memvid.
            user_message: Current user message.
            history: Previous conversation history.

        Yields:
            StreamingChunk objects with content and metadata.

        Raises:
            OpenRouterError: If the request fails.
            OpenRouterAuthError: If MOCK_OPENROUTER=false but API key missing.
        """
        settings = get_settings()

        # Check mock policy - fail loudly if real implementation unavailable
        if not self.is_configured:
            if settings.mock_openrouter:
                logger.info("MOCK_OPENROUTER=true: Using mock streaming LLM response")
                async for chunk in self._mock_chat_stream(user_message):
                    yield chunk
                return
            else:
                error_msg = (
                    "FATAL: OpenRouter API key not configured with MOCK_OPENROUTER=false. "
                    "Either set OPENROUTER_API_KEY or set MOCK_OPENROUTER=true for testing."
                )
                logger.error(error_msg)
                raise OpenRouterAuthError(error_msg)

        if not self._client:
            await self.connect()

        messages = self._build_messages(system_prompt, context, user_message, history)

        payload = {
            "model": self._model,
            "messages": messages,
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
            "stream": True,
        }

        total_tokens = 0

        try:
            async with self._client.stream(
                "POST",
                "/chat/completions",
                json=payload,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix

                        if data_str == "[DONE]":
                            yield StreamingChunk(
                                content="",
                                finish_reason="stop",
                                tokens_used=total_tokens,
                            )
                            break

                        try:
                            data = json.loads(data_str)
                            choice = data.get("choices", [{}])[0]
                            delta = choice.get("delta", {})
                            content = delta.get("content", "")
                            finish_reason = choice.get("finish_reason")

                            # Update usage if provided
                            if "usage" in data:
                                total_tokens = data["usage"].get("total_tokens", total_tokens)

                            if content or finish_reason:
                                yield StreamingChunk(
                                    content=content,
                                    finish_reason=finish_reason,
                                    tokens_used=total_tokens,
                                )

                        except json.JSONDecodeError:
                            logger.warning("Failed to parse streaming chunk", line=line)
                            continue

            logger.info("Streaming response completed", tokens=total_tokens)

        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
            raise

    def _handle_http_error(self, error: httpx.HTTPStatusError) -> None:
        """Handle HTTP errors from OpenRouter API."""
        status = error.response.status_code
        try:
            detail = error.response.json().get("error", {}).get("message", str(error))
        except Exception:
            detail = str(error)

        logger.error("OpenRouter API error", status=status, detail=detail)

        if status == 401:
            raise OpenRouterAuthError(f"Authentication failed: {detail}")
        elif status == 429:
            raise OpenRouterRateLimitError(f"Rate limit exceeded: {detail}")
        else:
            raise OpenRouterError(f"API error ({status}): {detail}")

    async def _mock_chat(self, user_message: str) -> LLMResponse:
        """Return mock LLM response for testing.

        Args:
            user_message: User's question (used to generate relevant mock response)

        Returns:
            Mock LLM response with simulated token count.
        """
        # Simple mock response based on query keywords
        mock_content = (
            "This is a mock LLM response (MOCK_OPENROUTER=true). "
            f"In production, this would be a real AI response to: '{user_message[:50]}...'. "
            "Set OPENROUTER_API_KEY to enable real LLM responses."
        )

        return LLMResponse(
            content=mock_content,
            tokens_used=50,  # Simulated token count
            finish_reason="stop",
        )

    async def _mock_chat_stream(self, user_message: str) -> AsyncIterator[StreamingChunk]:
        """Return mock streaming LLM response for testing.

        Args:
            user_message: User's question

        Yields:
            Mock streaming chunks simulating real LLM streaming.
        """
        import asyncio

        mock_words = [
            "This",
            "is",
            "a",
            "mock",
            "streaming",
            "response",
            "(MOCK_OPENROUTER=true).",
            "Set",
            "OPENROUTER_API_KEY",
            "to",
            "enable",
            "real",
            "LLM",
            "responses.",
        ]

        for word in mock_words:
            await asyncio.sleep(0.05)  # Simulate network latency
            yield StreamingChunk(content=word + " ")

        # Final chunk with finish reason
        yield StreamingChunk(content="", finish_reason="stop", tokens_used=len(mock_words))

    @property
    def is_configured(self) -> bool:
        """Check if the client is properly configured with an API key."""
        return bool(self._api_key and self._api_key.startswith("sk-"))


# Global client instance
_openrouter_client: OpenRouterClient | None = None


async def get_openrouter_client() -> OpenRouterClient:
    """Get or create the global OpenRouter client instance."""
    global _openrouter_client
    if _openrouter_client is None:
        _openrouter_client = OpenRouterClient()
        await _openrouter_client.connect()
    return _openrouter_client


async def close_openrouter_client() -> None:
    """Close the global OpenRouter client."""
    global _openrouter_client
    if _openrouter_client:
        await _openrouter_client.close()
        _openrouter_client = None


def reset_openrouter_client() -> None:
    """Reset the global OpenRouter client (for testing)."""
    global _openrouter_client
    _openrouter_client = None
