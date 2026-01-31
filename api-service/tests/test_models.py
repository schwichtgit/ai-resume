"""Tests for Pydantic models."""

from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChatStreamEvent,
    HealthResponse,
    MemvidSearchHit,
    MemvidSearchResponse,
    RetrievalChunk,
    Session,
    SuggestedQuestion,
)


class TestChatRequest:
    """Tests for ChatRequest model."""

    def test_valid_request(self):
        """Test creating a valid chat request."""
        request = ChatRequest(message="Hello, how are you?")
        assert request.message == "Hello, how are you?"
        assert request.session_id is None
        assert request.stream is True

    def test_with_session_id(self):
        """Test creating request with session ID."""
        session_id = uuid4()
        request = ChatRequest(message="Test", session_id=session_id)
        assert request.session_id == session_id

    def test_stream_false(self):
        """Test creating request with stream=False."""
        request = ChatRequest(message="Test", stream=False)
        assert request.stream is False

    def test_empty_message_fails(self):
        """Test that empty message fails validation."""
        with pytest.raises(ValidationError):
            ChatRequest(message="")

    def test_message_too_long(self):
        """Test that too long message fails validation."""
        with pytest.raises(ValidationError):
            ChatRequest(message="x" * 2001)


class TestChatMessage:
    """Tests for ChatMessage model."""

    def test_create_user_message(self):
        """Test creating a user message."""
        msg = ChatMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.timestamp is not None

    def test_create_assistant_message(self):
        """Test creating an assistant message."""
        msg = ChatMessage(role="assistant", content="Hi there!")
        assert msg.role == "assistant"

    def test_create_system_message(self):
        """Test creating a system message."""
        msg = ChatMessage(role="system", content="You are helpful.")
        assert msg.role == "system"


class TestChatStreamEvent:
    """Tests for ChatStreamEvent model."""

    def test_retrieval_event(self):
        """Test creating a retrieval event."""
        event = ChatStreamEvent(type="retrieval", chunks=5)
        assert event.type == "retrieval"
        assert event.chunks == 5

    def test_token_event(self):
        """Test creating a token event."""
        event = ChatStreamEvent(type="token", content="Hello")
        assert event.type == "token"
        assert event.content == "Hello"

    def test_metadata_event(self):
        """Test creating a metadata event."""
        event = ChatStreamEvent(type="metadata", tokens_used=100)
        assert event.type == "metadata"
        assert event.tokens_used == 100

    def test_error_event(self):
        """Test creating an error event."""
        event = ChatStreamEvent(type="error", error="Something went wrong")
        assert event.type == "error"
        assert event.error == "Something went wrong"

    def test_done_event(self):
        """Test creating a done event."""
        event = ChatStreamEvent(type="done")
        assert event.type == "done"


class TestChatResponse:
    """Tests for ChatResponse model."""

    def test_create_response(self):
        """Test creating a chat response."""
        response = ChatResponse(
            message="Hello!",
            chunks_retrieved=3,
            tokens_used=50,
        )
        assert response.message == "Hello!"
        assert response.chunks_retrieved == 3
        assert response.tokens_used == 50
        assert response.session_id is not None


class TestHealthResponse:
    """Tests for HealthResponse model."""

    def test_healthy_response(self):
        """Test creating a healthy response."""
        response = HealthResponse(
            status="healthy",
            memvid_connected=True,
            memvid_frame_count=42,
            active_sessions=5,
            version="1.0.0",
        )
        assert response.status == "healthy"
        assert response.memvid_connected is True
        assert response.memvid_frame_count == 42

    def test_degraded_response(self):
        """Test creating a degraded response."""
        response = HealthResponse(
            status="degraded",
            memvid_connected=False,
            active_sessions=0,
            version="1.0.0",
        )
        assert response.status == "degraded"
        assert response.memvid_frame_count is None


class TestSession:
    """Tests for Session model."""

    def test_create_session(self):
        """Test creating a session."""
        session = Session()
        assert session.id is not None
        assert session.messages == []
        assert session.created_at is not None

    def test_add_message(self):
        """Test adding messages to session."""
        session = Session()
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi!")

        assert len(session.messages) == 2
        assert session.messages[0].role == "user"
        assert session.messages[1].role == "assistant"

    def test_get_history_for_llm(self):
        """Test getting history formatted for LLM."""
        session = Session()
        session.add_message("system", "System prompt")
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi!")
        session.add_message("user", "How are you?")

        history = session.get_history_for_llm()

        # Should exclude system messages
        assert len(history) == 3
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"

    def test_get_history_for_llm_with_limit(self):
        """Test history limit."""
        session = Session()
        for i in range(30):
            session.add_message("user", f"Message {i}")

        history = session.get_history_for_llm(max_messages=10)
        assert len(history) == 10
        # Should be the last 10 messages
        assert history[0]["content"] == "Message 20"


class TestMemvidModels:
    """Tests for memvid-related models."""

    def test_search_hit(self):
        """Test creating a search hit."""
        hit = MemvidSearchHit(
            title="Test Section",
            score=0.95,
            snippet="This is a snippet.",
            tags=["test", "example"],
        )
        assert hit.title == "Test Section"
        assert hit.score == 0.95
        assert "test" in hit.tags

    def test_search_response(self):
        """Test creating a search response."""
        hits = [
            MemvidSearchHit(title="A", score=0.9, snippet="...", tags=[]),
            MemvidSearchHit(title="B", score=0.8, snippet="...", tags=[]),
        ]
        response = MemvidSearchResponse(hits=hits, total_hits=2, took_ms=5)
        assert len(response.hits) == 2
        assert response.took_ms == 5


class TestSuggestedQuestion:
    """Tests for SuggestedQuestion model."""

    def test_create_question(self):
        """Test creating a suggested question."""
        q = SuggestedQuestion(question="What skills do they have?", category="technical")
        assert q.question == "What skills do they have?"
        assert q.category == "technical"

    def test_question_without_category(self):
        """Test creating question without category."""
        q = SuggestedQuestion(question="General question")
        assert q.category is None
