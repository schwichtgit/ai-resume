"""FastAPI application entrypoint for AI Resume API."""

import json
import time
from asyncio import CancelledError
from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from ai_resume_api import __version__
from ai_resume_api.config import get_settings
from ai_resume_api.memvid_client import (
    MemvidConnectionError,
    MemvidSearchError,
    close_memvid_client,
    get_memvid_client,
)
from ai_resume_api.observability import (
    generate_trace_id,
    get_trace_id,
    set_trace_id,
    log_llm_request,
    log_llm_response,
)
from ai_resume_api.guardrails import check_input, check_output
from ai_resume_api.models import (
    AssessFitRequest,
    AssessFitResponse,
    ChatRequest,
    ChatResponse,
    ChatStreamEvent,
    Experience,
    FitAssessmentExample,
    HealthResponse,
    ProfileResponse,
    Skills,
    SuggestedQuestion,
    SuggestedQuestionsResponse,
)
from ai_resume_api.openrouter_client import (
    OpenRouterAuthError,
    OpenRouterError,
    close_openrouter_client,
    get_openrouter_client,
)
from ai_resume_api.query_transform import transform_query
from ai_resume_api.session_store import get_session_store

# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
settings = get_settings()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler for startup/shutdown."""
    logger.info("Starting AI Resume API", version=__version__)

    # Initialize clients on startup
    try:
        await get_memvid_client()
        logger.info("Memvid client initialized")
    except Exception as e:
        logger.error("Failed to initialize memvid client", error=str(e))

    try:
        await get_openrouter_client()
        logger.info("OpenRouter client initialized")
    except Exception as e:
        logger.warning("Failed to initialize OpenRouter client", error=str(e))

    yield

    # Cleanup on shutdown
    logger.info("Shutting down AI Resume API")
    await close_memvid_client()
    await close_openrouter_client()


# Create FastAPI app
app = FastAPI(
    title="AI Resume API",
    description="AI-powered resume chat API with semantic search",
    version=__version__,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Trace ID middleware for request correlation
@app.middleware("http")
async def trace_id_middleware(request: Request, call_next):
    """Add trace ID to every request for log correlation."""
    # Get trace ID from header or generate new one
    trace_id = request.headers.get("X-Trace-ID", generate_trace_id())
    set_trace_id(trace_id)

    # Bind trace ID to structlog context for all logs in this request
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(trace_id=trace_id)

    response = await call_next(request)

    # Add trace ID to response headers for client correlation
    response.headers["X-Trace-ID"] = trace_id
    return response


# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add Prometheus metrics
Instrumentator().instrument(app).expose(app)


# =============================================================================
# Health Endpoints
# =============================================================================


@app.get("/health", response_model=HealthResponse)
@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check the health of the API and its dependencies."""
    session_store = get_session_store()

    # Check memvid connection
    try:
        memvid_client = await get_memvid_client()
        memvid_health = await memvid_client.health_check()
        memvid_connected = memvid_health.status == "SERVING"
        frame_count = memvid_health.frame_count
    except Exception:
        memvid_connected = False
        frame_count = None

    # Determine overall status
    if memvid_connected:
        status = "healthy"
    else:
        status = "degraded"

    return HealthResponse(
        status=status,
        memvid_connected=memvid_connected,
        memvid_frame_count=frame_count,
        active_sessions=session_store.count(),
        version=__version__,
    )


# =============================================================================
# Chat Endpoints
# =============================================================================


@app.post("/api/v1/chat")
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def chat(request: Request, chat_request: ChatRequest):
    """
    Chat endpoint with optional streaming.

    - **message**: The user's message
    - **session_id**: Optional session ID for conversation history
    - **stream**: Whether to stream the response (default: true)
    """
    print("🚨 CHAT ENDPOINT CALLED - START OF FUNCTION", flush=True)
    session_store = get_session_store()
    session = session_store.get_or_create(chat_request.session_id)

    logger.info(
        "Chat request received",
        session_id=str(session.id),
        message_length=len(chat_request.message),
        stream=chat_request.stream,
    )

    # Load profile data for guardrail response (lightweight, from memvid metadata)
    try:
        profile = await settings.load_profile_from_memvid()
        if not profile:
            profile = settings.load_profile()
        profile_name = profile.get("name") if profile else None
        suggested_questions = profile.get("suggested_questions", []) if profile else []
    except Exception as e:
        logger.warning("Failed to load profile for guardrails", error=str(e))
        profile_name = None
        suggested_questions = []

    # Input guardrail: Check for prompt injection attempts
    is_safe, blocked_response = check_input(
        chat_request.message,
        profile_name=profile_name,
        suggested_questions=suggested_questions,
    )
    if not is_safe:
        logger.warning(
            "Chat blocked by guardrail",
            session_id=str(session.id),
            message_preview=chat_request.message[:50],
        )
        # Add blocked message to session
        session.add_message("user", chat_request.message)
        session.add_message("assistant", blocked_response)
        session_store.set(session.id, session)

        # Return blocked response with streaming support
        if chat_request.stream:
            return StreamingResponse(
                _mock_stream_response(blocked_response, chunks_retrieved=0),
                media_type="text/event-stream",
            )
        else:
            return ChatResponse(
                session_id=session.id,
                message=blocked_response,
                chunks_retrieved=0,
                tokens_used=0,
            )

    # Get OpenRouter client for query transformation
    openrouter_client = await get_openrouter_client()

    # Transform query for better retrieval
    # TEMPORARILY DISABLED: Query transformation was expanding "AI" to "artificial intelligence"
    # which doesn't match "AI/ML" content. Need to improve transformation logic.
    # TODO: Re-enable with better keyword extraction that preserves acronyms
    transformed_query = chat_request.message
    # try:
    #     transformed_query = await transform_query(
    #         question=chat_request.message,
    #         openrouter_client=openrouter_client,
    #         strategy="keywords",
    #     )
    #     logger.info(
    #         "Query transformed",
    #         original=chat_request.message[:50],
    #         transformed=transformed_query[:100],
    #     )
    # except Exception as e:
    #     logger.warning("Query transformation failed", error=str(e))
    #     transformed_query = chat_request.message

    # Get context from memvid using transformed query
    try:
        memvid_client = await get_memvid_client()
        search_response = await memvid_client.search(
            query=transformed_query,  # Use transformed query for search
            top_k=5,
            snippet_chars=300,
        )
        context = "\n\n".join(f"**{hit.title}**\n{hit.snippet}" for hit in search_response.hits)
        chunks_retrieved = len(search_response.hits)

        if chunks_retrieved == 0:
            logger.info(
                "Memvid search returned no results",
                query_preview=transformed_query[:50],
            )
            # Return early - don't let LLM hallucinate without context
            no_results_msg = (
                "I couldn't find relevant information to answer that question. "
                "This could mean:\n"
                "- The information isn't in the resume\n"
                "- The question uses different terminology than the resume\n"
                "- Try rephrasing with more specific terms or asking about a different topic"
            )
            session.add_message("assistant", no_results_msg)
            session_store.set(session.id, session)

            return ChatResponse(
                session_id=session.id,
                message=no_results_msg,
                chunks_retrieved=0,
                tokens_used=0,
            )

    except MemvidConnectionError as e:
        logger.error("Memvid service unavailable", error=str(e))
        raise HTTPException(
            status_code=503,
            detail="Search service unavailable. Please try again later.",
        )
    except MemvidSearchError as e:
        logger.error("Memvid search failed", error=str(e))
        raise HTTPException(
            status_code=502,
            detail="Search service error. Please try again later.",
        )

    # Get conversation history
    history = session.get_history_for_llm(settings.max_history_messages)

    # Add user message to session
    session.add_message("user", chat_request.message)

    # Stream response
    if chat_request.stream:
        return StreamingResponse(
            _stream_chat_response(
                openrouter_client,
                context,
                chat_request.message,
                history,
                session,
                session_store,
                chunks_retrieved,
            ),
            media_type="text/event-stream",
        )
    else:
        # Non-streaming response with LLM logging
        system_prompt = settings.get_system_prompt_from_profile()
        request_log = log_llm_request(
            model=settings.llm_model,
            stream=False,
            system_prompt=system_prompt,
            context=context,
            context_chunks=chunks_retrieved,
            user_message=chat_request.message,
            history=history,
        )

        logger.info("🔴 ABOUT TO CALL OPENROUTER - THIS IS THE NEW CODE PATH")
        try:
            response = await openrouter_client.chat(
                system_prompt=system_prompt,
                context=context,
                user_message=chat_request.message,
                history=history,
            )

            # Output guardrail: Filter any internal structure leakage
            safe_content = check_output(response.content)

            session.add_message("assistant", safe_content)
            session_store.set(session.id, session)

            log_llm_response(
                request_log=request_log,
                tokens_total=response.tokens_used,
                finish_reason=response.finish_reason or "stop",
            )

            return ChatResponse(
                session_id=session.id,
                message=safe_content,
                chunks_retrieved=chunks_retrieved,
                tokens_used=response.tokens_used,
            )
        except OpenRouterAuthError as e:
            log_llm_response(
                request_log=request_log,
                error=str(e),
            )
            raise HTTPException(
                status_code=503,
                detail="AI service not configured. Please contact the administrator.",
            )
        except OpenRouterError as e:
            log_llm_response(
                request_log=request_log,
                error=str(e),
            )
            raise HTTPException(status_code=502, detail=str(e))


async def _stream_chat_response(
    openrouter_client,
    context: str,
    user_message: str,
    history: list,
    session,
    session_store,
    chunks_retrieved: int,
) -> AsyncIterator[str]:
    """Generate streaming SSE response with proper cancellation handling."""
    # Log LLM request for observability
    system_prompt = settings.get_system_prompt_from_profile()
    request_log = log_llm_request(
        model=settings.llm_model,
        stream=True,
        system_prompt=system_prompt,
        context=context,
        context_chunks=chunks_retrieved,
        user_message=user_message,
        history=history,
    )

    # Send retrieval info
    event = ChatStreamEvent(type="retrieval", chunks=chunks_retrieved)
    yield f"data: {event.model_dump_json()}\n\n"

    full_response = ""
    tokens_used = 0
    finish_reason = "unknown"

    try:
        async for chunk in openrouter_client.chat_stream(
            system_prompt=system_prompt,
            context=context,
            user_message=user_message,
            history=history,
        ):
            if chunk.content:
                full_response += chunk.content
                event = ChatStreamEvent(type="token", content=chunk.content)
                yield f"data: {event.model_dump_json()}\n\n"

            if chunk.tokens_used:
                tokens_used = chunk.tokens_used

            if chunk.finish_reason:
                finish_reason = chunk.finish_reason
                break

        # Save response to session
        session.add_message("assistant", full_response)
        session_store.set(session.id, session)

        # Log LLM response with metrics
        log_llm_response(
            request_log=request_log,
            tokens_total=tokens_used,
            finish_reason=finish_reason,
        )

        # Send stats event with comprehensive metrics (include trace_id)
        stats_data = {
            "chunks_retrieved": chunks_retrieved,
            "tokens_used": tokens_used,
            "elapsed_seconds": round((time.time() - request_log.timestamp), 2),
            "trace_id": get_trace_id(),
        }
        yield f"event: stats\ndata: {json.dumps(stats_data)}\n\n"

        # Send completion event
        yield "event: end\ndata: [DONE]\n\n"

    except CancelledError:
        log_llm_response(
            request_log=request_log,
            error="cancelled_by_client",
        )
        raise

    except OpenRouterAuthError as e:
        log_llm_response(
            request_log=request_log,
            error=str(e),
        )
        event = ChatStreamEvent(
            type="error",
            error="AI service not configured. Please contact the administrator.",
        )
        yield f"data: {event.model_dump_json()}\n\n"

    except OpenRouterError as e:
        log_llm_response(
            request_log=request_log,
            error=str(e),
        )
        event = ChatStreamEvent(type="error", error=str(e))
        yield f"data: {event.model_dump_json()}\n\n"


async def _mock_stream_response(
    response: str,
    chunks_retrieved: int,
) -> AsyncIterator[str]:
    """Generate mock streaming response when OpenRouter not configured."""
    import asyncio
    import random

    start_time = time.monotonic()

    # Send retrieval info
    event = ChatStreamEvent(type="retrieval", chunks=chunks_retrieved)
    yield f"data: {event.model_dump_json()}\n\n"

    # Stream words with realistic delays
    words = response.split()
    total_tokens = len(words)

    for i, word in enumerate(words):
        # Random delay for realism (50-150ms)
        await asyncio.sleep(random.uniform(0.05, 0.15))

        content = word + (" " if i < len(words) - 1 else "")
        event = ChatStreamEvent(type="token", content=content)
        yield f"data: {event.model_dump_json()}\n\n"

    # Calculate elapsed time
    elapsed = round(time.monotonic() - start_time, 2)

    # Send stats event matching real implementation
    stats_data = {
        "chunks_retrieved": chunks_retrieved,
        "tokens_used": total_tokens,
        "elapsed_seconds": elapsed,
        "mode": "mock",
    }
    yield f"event: stats\ndata: {json.dumps(stats_data)}\n\n"

    # Send completion event
    yield "event: end\ndata: [DONE]\n\n"


def _generate_mock_response(message: str, context: str) -> str:
    """Generate a mock response when OpenRouter is not configured."""
    if not context:
        return (
            "I don't have enough context to answer that question. "
            "Please try asking about specific skills, experience, or qualifications."
        )

    return (
        f"Based on the resume context, here's what I found relevant to your question:\n\n"
        f"{context[:500]}...\n\n"
        f"(Note: This is a mock response. Configure OPENROUTER_API_KEY for real AI responses.)"
    )


# =============================================================================
# Config Endpoints
# =============================================================================


@app.get("/api/v1/profile", response_model=ProfileResponse)
async def get_profile() -> ProfileResponse:
    """Get profile metadata from memvid."""
    # Try loading from memvid first
    profile = await settings.load_profile_from_memvid()

    # Fallback to profile.json for backward compatibility
    if not profile:
        profile = settings.load_profile()

    if not profile:
        # Return empty/default profile if not found
        raise HTTPException(
            status_code=404,
            detail="Profile data not found. Run ingest to create .mv2 file.",
        )

    # Parse experience entries
    experience_data = profile.get("experience", [])
    experience = [Experience(**exp) for exp in experience_data]

    # Parse skills
    skills_data = profile.get("skills", {})
    skills = Skills(**skills_data)

    # Parse fit assessment examples
    fit_examples_data = profile.get("fit_assessment_examples", [])
    fit_examples = [FitAssessmentExample(**example) for example in fit_examples_data]

    return ProfileResponse(
        name=profile.get("name", ""),
        title=profile.get("title", ""),
        email=profile.get("email", ""),
        linkedin=profile.get("linkedin", ""),
        location=profile.get("location", ""),
        status=profile.get("status", ""),
        suggested_questions=profile.get("suggested_questions", []),
        tags=profile.get("tags", []),
        experience=experience,
        skills=skills,
        fit_assessment_examples=fit_examples,
    )


@app.get("/api/v1/suggested-questions", response_model=SuggestedQuestionsResponse)
async def get_suggested_questions() -> SuggestedQuestionsResponse:
    """Get suggested questions from profile (memvid or fallback file)."""
    # Try loading from memvid first
    profile = await settings.load_profile_from_memvid()

    # Fallback to profile.json for backward compatibility
    if not profile:
        profile = settings.load_profile()

    if not profile or not profile.get("suggested_questions"):
        raise HTTPException(
            status_code=404,
            detail="Profile data not found. Run ingest to create .mv2 file.",
        )

    questions = [
        SuggestedQuestion(question=q, category="general") for q in profile["suggested_questions"]
    ]
    return SuggestedQuestionsResponse(questions=questions)


@app.post("/api/v1/assess-fit", response_model=AssessFitResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def assess_fit(request: Request, assess_request: AssessFitRequest) -> AssessFitResponse:
    """
    Assess candidate fit for a given job description using AI.

    - **job_description**: The job description to assess fit against (min 50 chars)

    Returns:
    - **verdict**: Overall fit assessment with rating (e.g., "⭐⭐⭐⭐ Strong fit")
    - **key_matches**: List of matching qualifications
    - **gaps**: List of identified gaps or limitations
    - **recommendation**: Final recommendation text
    - **chunks_retrieved**: Number of context chunks retrieved from memvid
    - **tokens_used**: Tokens used in LLM call
    """
    logger.info(
        "Fit assessment request",
        job_description_length=len(assess_request.job_description),
    )

    # Get OpenRouter client
    openrouter_client = await get_openrouter_client()

    # Query memvid for relevant context about candidate
    # Search for: experience, skills, failures, fit assessment guidance
    try:
        memvid_client = await get_memvid_client()
        search_response = await memvid_client.search(
            query=f"relevant experience and skills for role fit assessment: {assess_request.job_description[:200]}",
            top_k=10,
            snippet_chars=500,
        )
        context = "\n\n".join(f"**{hit.title}**\n{hit.snippet}" for hit in search_response.hits)
        chunks_retrieved = len(search_response.hits)

        if chunks_retrieved == 0:
            logger.warning(
                "Memvid search returned no results for fit assessment",
                job_description_preview=assess_request.job_description[:100],
            )
            # Continue with empty context - assessment will be limited

    except MemvidConnectionError as e:
        logger.error("Memvid service unavailable for fit assessment", error=str(e))
        raise HTTPException(
            status_code=503,
            detail="Search service unavailable. Please try again later.",
        )
    except MemvidSearchError as e:
        logger.error("Memvid search failed for fit assessment", error=str(e))
        raise HTTPException(
            status_code=502,
            detail="Search service error. Please try again later.",
        )

    # Build fit assessment prompt
    fit_assessment_prompt = f"""Analyze the candidate's fit for this job description and provide an honest, structured assessment.

JOB DESCRIPTION:
{assess_request.job_description}

CANDIDATE CONTEXT:
{context}

Provide a structured assessment with:

1. **VERDICT**: Rate the fit with stars (⭐ to ⭐⭐⭐⭐⭐) and brief summary (e.g., "⭐⭐⭐⭐ Strong fit - Excellent match for AI infrastructure role")

2. **KEY MATCHES**: List 3-5 specific qualifications from the candidate's background that match the role requirements. Be specific with examples and metrics.

3. **GAPS**: List 2-4 honest gaps or limitations where the candidate may not be a perfect match. Be direct and factual.

4. **RECOMMENDATION**: Provide a balanced final recommendation (2-3 sentences) addressing whether the candidate should be considered and any important caveats.

Be honest and direct. Do not oversell. Hiring managers value credibility over enthusiasm.

Format your response exactly as:

VERDICT: [stars and summary]

KEY MATCHES:
- [match 1]
- [match 2]
- [match 3]

GAPS:
- [gap 1]
- [gap 2]

RECOMMENDATION: [recommendation text]
"""

    # Call OpenRouter LLM
    try:
        response = await openrouter_client.chat(
            system_prompt="You are an expert technical recruiter providing honest, data-driven fit assessments for engineering leadership roles.",
            context="",  # Context already in user message
            user_message=fit_assessment_prompt,
            history=[],
        )

        # Parse structured response
        content = response.content
        tokens_used = response.tokens_used

        # Extract sections using simple parsing
        verdict = ""
        key_matches = []
        gaps = []
        recommendation = ""

        current_section = None
        for line in content.split("\n"):
            line = line.strip()

            if line.startswith("VERDICT:"):
                verdict = line.replace("VERDICT:", "").strip()
                current_section = "verdict"
            elif line.startswith("KEY MATCHES:"):
                current_section = "matches"
            elif line.startswith("GAPS:"):
                current_section = "gaps"
            elif line.startswith("RECOMMENDATION:"):
                recommendation_text = line.replace("RECOMMENDATION:", "").strip()
                if recommendation_text:
                    recommendation = recommendation_text
                current_section = "recommendation"
            elif line.startswith("- ") and current_section == "matches":
                key_matches.append(line[2:].strip())
            elif line.startswith("- ") and current_section == "gaps":
                gaps.append(line[2:].strip())
            elif current_section == "recommendation" and line:
                if recommendation:
                    recommendation += " " + line
                else:
                    recommendation = line

        # Fallback if parsing fails
        if not verdict:
            verdict = "Unable to parse assessment"
        if not key_matches:
            key_matches = ["See full assessment in raw response"]
        if not gaps:
            gaps = ["See full assessment in raw response"]
        if not recommendation:
            recommendation = content[:500]  # Use first 500 chars as fallback

        logger.info(
            "Fit assessment completed",
            chunks_retrieved=chunks_retrieved,
            tokens_used=tokens_used,
            verdict=verdict,
        )

        return AssessFitResponse(
            verdict=verdict,
            key_matches=key_matches,
            gaps=gaps,
            recommendation=recommendation,
            chunks_retrieved=chunks_retrieved,
            tokens_used=tokens_used,
        )

    except OpenRouterAuthError as e:
        logger.error("OpenRouter not configured for fit assessment", error=str(e))
        raise HTTPException(
            status_code=503,
            detail="AI service not configured. Please contact the administrator.",
        )
    except OpenRouterError as e:
        logger.error("OpenRouter error during fit assessment", error=str(e))
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")


# =============================================================================
# Entry point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
    )
