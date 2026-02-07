"""Tests for query transformation module."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.query_transform import (
    transform_query_keywords,
    transform_query,
    KEYWORD_EXTRACTION_PROMPT,
)
from app.openrouter_client import LLMResponse


class TestTransformQueryKeywords:
    """Tests for transform_query_keywords function."""

    @pytest.mark.asyncio
    async def test_returns_original_when_openrouter_not_configured(self) -> None:
        """Test query transformation skips when OpenRouter not configured."""
        mock_client = MagicMock()
        mock_client.is_configured = False

        result = await transform_query_keywords(
            "What is your experience with Python?",
            mock_client,
        )

        assert result == "What is your experience with Python?"
        # Client should not be called
        assert not hasattr(mock_client, "chat") or not mock_client.chat.called

    @pytest.mark.asyncio
    async def test_short_query_passes_through_unchanged(self) -> None:
        """Test short queries (<=3 words) pass through unchanged."""
        mock_client = MagicMock()
        mock_client.is_configured = True

        # Test 1 word
        result = await transform_query_keywords("Python", mock_client)
        assert result == "Python"

        # Test 2 words
        result = await transform_query_keywords("Python experience", mock_client)
        assert result == "Python experience"

        # Test 3 words
        result = await transform_query_keywords("Python ML experience", mock_client)
        assert result == "Python ML experience"

        # Client should not be called for short queries
        assert not hasattr(mock_client, "chat") or not mock_client.chat.called

    @pytest.mark.asyncio
    async def test_successful_keyword_extraction(self) -> None:
        """Test successful keyword extraction from LLM."""
        mock_client = MagicMock()
        mock_client.is_configured = True

        # Mock LLM response with keywords
        mock_response = LLMResponse(
            content="python programming backend development django flask API REST",
            tokens_used=50,
            finish_reason="stop",
        )
        mock_client.chat = AsyncMock(return_value=mock_response)

        result = await transform_query_keywords(
            "What is your experience with Python backend development?",
            mock_client,
        )

        # Should return cleaned keywords (7 max)
        assert result == "python programming backend development django flask api"
        mock_client.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_keyword_deduplication_and_limiting(self) -> None:
        """Test keyword deduplication and 7-word limit."""
        mock_client = MagicMock()
        mock_client.is_configured = True

        # Mock response with duplicates and more than 7 words
        mock_response = LLMResponse(
            content="python Python PYTHON programming backend backend development api rest api testing deployment automation",
            tokens_used=50,
            finish_reason="stop",
        )
        mock_client.chat = AsyncMock(return_value=mock_response)

        result = await transform_query_keywords(
            "What is your experience with Python development?",
            mock_client,
        )

        # Should deduplicate and limit to 7 words
        words = result.split()
        assert len(words) == 7
        # All words should be unique
        assert len(words) == len(set(words))
        # Should be lowercase
        assert result == result.lower()

    @pytest.mark.asyncio
    async def test_fallback_when_llm_returns_empty_keywords(self) -> None:
        """Test fallback to original query when LLM returns empty/invalid keywords."""
        mock_client = MagicMock()
        mock_client.is_configured = True

        # Mock response with only short words that get filtered out
        mock_response = LLMResponse(
            content="a an in to at",
            tokens_used=50,
            finish_reason="stop",
        )
        mock_client.chat = AsyncMock(return_value=mock_response)

        question = "What is your experience with Python?"
        result = await transform_query_keywords(question, mock_client)

        # Should return original question when no valid keywords
        assert result == question

    @pytest.mark.asyncio
    async def test_fallback_when_llm_call_fails(self) -> None:
        """Test fallback to original query when LLM call raises exception."""
        mock_client = MagicMock()
        mock_client.is_configured = True

        # Mock chat to raise an exception
        mock_client.chat = AsyncMock(side_effect=Exception("API error"))

        question = "What is your experience with Python?"
        result = await transform_query_keywords(question, mock_client)

        # Should return original question on error
        assert result == question
        mock_client.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_punctuation_removal(self) -> None:
        """Test that punctuation is properly removed from keywords."""
        mock_client = MagicMock()
        mock_client.is_configured = True

        # Mock response with punctuation
        mock_response = LLMResponse(
            content="python, programming! backend? development: API.",
            tokens_used=50,
            finish_reason="stop",
        )
        mock_client.chat = AsyncMock(return_value=mock_response)

        result = await transform_query_keywords(
            "What is your experience with Python?",
            mock_client,
        )

        # Punctuation should be stripped
        assert result == "python programming backend development api"


class TestTransformQuery:
    """Tests for transform_query dispatcher function."""

    @pytest.mark.asyncio
    async def test_passthrough_strategy(self) -> None:
        """Test passthrough strategy returns original query."""
        mock_client = MagicMock()
        mock_client.is_configured = True

        question = "What is your experience with Python development?"
        result = await transform_query(question, mock_client, strategy="passthrough")

        # Should return original without calling LLM
        assert result == question
        assert not hasattr(mock_client, "chat") or not mock_client.chat.called

    @pytest.mark.asyncio
    async def test_keywords_strategy(self) -> None:
        """Test keywords strategy calls transform_query_keywords."""
        mock_client = MagicMock()
        mock_client.is_configured = True

        mock_response = LLMResponse(
            content="python programming backend development",
            tokens_used=50,
            finish_reason="stop",
        )
        mock_client.chat = AsyncMock(return_value=mock_response)

        result = await transform_query(
            "What is your experience with Python?",
            mock_client,
            strategy="keywords",
        )

        # Should use keyword extraction
        assert result == "python programming backend development"
        mock_client.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_unknown_strategy_fallback(self) -> None:
        """Test unknown strategy falls back to passthrough."""
        mock_client = MagicMock()
        mock_client.is_configured = True

        question = "What is your experience with Python?"
        result = await transform_query(question, mock_client, strategy="unknown_strategy")

        # Should return original without calling LLM
        assert result == question
        assert not hasattr(mock_client, "chat") or not mock_client.chat.called

    @pytest.mark.asyncio
    async def test_default_strategy_is_keywords(self) -> None:
        """Test that default strategy is keywords."""
        mock_client = MagicMock()
        mock_client.is_configured = True

        mock_response = LLMResponse(
            content="python programming backend",
            tokens_used=50,
            finish_reason="stop",
        )
        mock_client.chat = AsyncMock(return_value=mock_response)

        # Call without strategy parameter
        result = await transform_query(
            "What is your Python experience?",
            mock_client,
        )

        # Should use keyword extraction (default)
        assert result == "python programming backend"
        mock_client.chat.assert_called_once()


class TestKeywordExtractionPrompt:
    """Tests for KEYWORD_EXTRACTION_PROMPT template."""

    def test_prompt_template_formatting(self) -> None:
        """Test that prompt template can be formatted correctly."""
        question = "What is your experience with AI and ML?"
        prompt = KEYWORD_EXTRACTION_PROMPT.format(question=question)

        assert "Extract 5-10 search keywords" in prompt
        assert question in prompt
        assert "Keywords:" in prompt
        assert "AI artificial intelligence" in prompt  # Example in prompt
