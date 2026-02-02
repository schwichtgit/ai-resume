"""Pydantic models for API requests and responses."""

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

# =============================================================================
# Chat API Models
# =============================================================================


class ChatRequest(BaseModel):
    """Request body for the chat endpoint."""

    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    session_id: UUID | None = Field(default=None, description="Session ID for conversation history")
    stream: bool = Field(default=True, description="Whether to stream the response")


class ChatMessage(BaseModel):
    """A single message in the conversation history."""

    role: Literal["user", "assistant", "system"] = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RetrievalChunk(BaseModel):
    """A chunk retrieved from memvid."""

    title: str = Field(..., description="Title of the matched section")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    snippet: str = Field(..., description="Text snippet")
    tags: list[str] = Field(default_factory=list, description="Associated tags")


class ChatStreamEvent(BaseModel):
    """Server-sent event for streaming chat responses."""

    type: Literal["retrieval", "token", "metadata", "error", "done"]
    content: str | None = None
    chunks: int | None = None
    tokens_used: int | None = None
    error: str | None = None


class ChatResponse(BaseModel):
    """Non-streaming chat response."""

    session_id: UUID = Field(default_factory=uuid4)
    message: str = Field(..., description="Assistant response")
    chunks_retrieved: int = Field(..., description="Number of context chunks used")
    tokens_used: int = Field(..., description="Total tokens used")


# =============================================================================
# Health API Models
# =============================================================================


class HealthResponse(BaseModel):
    """Response for health check endpoint."""

    status: Literal["healthy", "degraded", "unhealthy"] = Field(..., description="Service status")
    memvid_connected: bool = Field(..., description="Memvid gRPC connection status")
    memvid_frame_count: int | None = Field(None, description="Number of frames in memvid index")
    active_sessions: int = Field(..., description="Number of active sessions")
    version: str = Field(..., description="API version")


# =============================================================================
# Config API Models
# =============================================================================


class SuggestedQuestion(BaseModel):
    """A suggested question for the chat interface."""

    question: str = Field(..., description="The question text")
    category: str | None = Field(None, description="Question category")


class SuggestedQuestionsResponse(BaseModel):
    """Response for suggested questions endpoint."""

    questions: list[SuggestedQuestion] = Field(..., description="List of suggested questions")


class AIContext(BaseModel):
    """AI context for an experience entry."""

    situation: str = Field(default="", description="Situation/context")
    approach: str = Field(default="", description="Approach taken")
    technical_work: str = Field(default="", description="Technical work performed")
    lessons_learned: str = Field(default="", description="Lessons learned")


class Experience(BaseModel):
    """A single experience entry."""

    company: str = Field(..., description="Company name")
    role: str = Field(..., description="Role/title")
    period: str = Field(..., description="Time period")
    location: str = Field(default="", description="Location")
    tags: list[str] = Field(default_factory=list, description="Tags for this experience")
    highlights: list[str] = Field(default_factory=list, description="Key achievements")
    ai_context: AIContext = Field(default_factory=AIContext, description="AI context")


class Skills(BaseModel):
    """Skills categorization."""

    strong: list[str] = Field(default_factory=list, description="Strong skills")
    moderate: list[str] = Field(default_factory=list, description="Moderate skills")
    gaps: list[str] = Field(default_factory=list, description="Known gaps")


class FitAssessmentExample(BaseModel):
    """Pre-analyzed fit assessment example."""

    title: str = Field(..., description="Example title (e.g., 'Strong Fit — VP Engineering')")
    fit_level: str = Field(..., description="Fit level: strong_fit, moderate_fit, weak_fit")
    role: str = Field(..., description="Role title")
    job_description: str = Field(..., description="Full job description text")
    verdict: str = Field(..., description="Assessment verdict with rating")
    key_matches: str = Field(..., description="Key matching qualifications")
    gaps: str = Field(..., description="Identified gaps or limitations")
    recommendation: str = Field(..., description="Final recommendation")


class AssessFitRequest(BaseModel):
    """Request for real-time fit assessment."""

    job_description: str = Field(
        ..., description="Job description to assess fit against", min_length=50
    )


class AssessFitResponse(BaseModel):
    """Response for real-time fit assessment."""

    verdict: str = Field(..., description="Overall fit assessment with rating")
    key_matches: list[str] = Field(..., description="Key matching qualifications")
    gaps: list[str] = Field(..., description="Identified gaps or limitations")
    recommendation: str = Field(..., description="Final recommendation")
    chunks_retrieved: int = Field(..., description="Number of context chunks used")
    tokens_used: int = Field(..., description="Tokens used in LLM call")


class ProfileResponse(BaseModel):
    """Response for profile endpoint."""

    name: str = Field(..., description="Candidate name")
    title: str = Field(..., description="Current title")
    email: str = Field(..., description="Email address")
    linkedin: str = Field(..., description="LinkedIn URL")
    location: str = Field(..., description="Location")
    status: str = Field(..., description="Current status (availability)")
    suggested_questions: list[str] = Field(default_factory=list, description="Suggested questions")
    tags: list[str] = Field(default_factory=list, description="Profile tags")
    experience: list[Experience] = Field(default_factory=list, description="Work experience")
    skills: Skills = Field(default_factory=Skills, description="Skills assessment")
    fit_assessment_examples: list[FitAssessmentExample] = Field(
        default_factory=list, description="Pre-analyzed fit assessment examples"
    )


# =============================================================================
# Memvid Client Models (internal)
# =============================================================================


class MemvidSearchRequest(BaseModel):
    """Request to memvid search service."""

    query: str
    top_k: int = 5
    snippet_chars: int = 200


class MemvidSearchHit(BaseModel):
    """A single search hit from memvid."""

    title: str
    score: float
    snippet: str
    tags: list[str] = Field(default_factory=list)


class MemvidSearchResponse(BaseModel):
    """Response from memvid search service."""

    hits: list[MemvidSearchHit]
    total_hits: int
    took_ms: int


class MemvidHealthResponse(BaseModel):
    """Response from memvid health check."""

    status: Literal["SERVING", "NOT_SERVING", "UNKNOWN"]
    frame_count: int
    memvid_file: str


# =============================================================================
# Session Models (internal)
# =============================================================================


class Session(BaseModel):
    """A chat session with conversation history."""

    id: UUID = Field(default_factory=uuid4)
    messages: list[ChatMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def add_message(self, role: Literal["user", "assistant", "system"], content: str) -> None:
        """Add a message to the session history."""
        self.messages.append(ChatMessage(role=role, content=content))
        self.last_activity = datetime.now(timezone.utc)

    def get_history_for_llm(self, max_messages: int = 20) -> list[dict[str, str]]:
        """Get conversation history formatted for LLM API."""
        # Take last N messages, excluding system messages
        recent = [m for m in self.messages if m.role != "system"][-max_messages:]
        return [{"role": m.role, "content": m.content} for m in recent]
