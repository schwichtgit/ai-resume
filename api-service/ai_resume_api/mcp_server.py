"""MCP server with Streamable HTTP transport for AI Resume tools and resources."""

import json
import time
from collections import defaultdict
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Request
from fastmcp import FastMCP

from ai_resume_api.config import get_settings
from ai_resume_api.guardrails import check_input, check_output
from ai_resume_api.memvid_client import get_memvid_client
from ai_resume_api.openrouter_client import get_openrouter_client
from ai_resume_api.otel import get_tracer

logger = structlog.get_logger(__name__)

# =============================================================================
# Rate Limiting (programmatic, 60/min per IP)
# =============================================================================

_rate_limit_store: dict[str, list[float]] = defaultdict(list)
MCP_RATE_LIMIT = 60  # requests per minute


def _check_rate_limit(client_ip: str) -> bool:
    """Check if client IP is within rate limit. Returns True if allowed."""
    now = time.time()
    window_start = now - 60
    timestamps = _rate_limit_store[client_ip]
    # Prune old entries
    _rate_limit_store[client_ip] = [t for t in timestamps if t > window_start]
    if len(_rate_limit_store[client_ip]) >= MCP_RATE_LIMIT:
        return False
    _rate_limit_store[client_ip].append(now)
    return True


# =============================================================================
# MCP Server Instance
# =============================================================================

mcp = FastMCP(
    "AI Resume",
    instructions=(
        "AI-powered resume query tools. Use ask_question to chat about the "
        "candidate's experience. Use assess_fit to evaluate job fit."
    ),
)

# =============================================================================
# MCP Tools (stateless, no session)
# =============================================================================


@mcp.tool()
async def ask_question(question: str) -> str:
    """Ask a question about the candidate's professional experience, skills, and background.

    Returns an AI-generated answer based on semantic search of the candidate's resume.
    """
    tracer = get_tracer()

    # Rate limit check (placeholder IP -- FastMCP doesn't expose client IP easily)
    if not _check_rate_limit("mcp-client"):
        return "Rate limit exceeded. Please wait a moment before trying again."

    settings = get_settings()

    # Input guardrail
    with tracer.start_as_current_span("guardrail.check_input") as guard_span:
        guard_span.set_attribute("message.length", len(question))
        profile = await settings.load_profile_from_memvid() or settings.load_profile()
        profile_name = profile.get("name") if profile else None
        suggested_questions = profile.get("suggested_questions", []) if profile else []
        is_safe, blocked_response = check_input(question, profile_name, suggested_questions)
        guard_span.set_attribute("guardrail.passed", is_safe)
    if not is_safe:
        return blocked_response

    # Semantic search via memvid
    with tracer.start_as_current_span("memvid.search") as search_span:
        search_span.set_attribute("search.query_length", len(question))
        search_span.set_attribute("search.top_k", 5)
        search_span.set_attribute("search.mode", "hybrid")

        memvid_client = await get_memvid_client()
        try:
            ask_response = await memvid_client.ask(
                question=question,
                use_llm=False,
                top_k=5,
                snippet_chars=300,
                mode="hybrid",
            )
        except Exception as e:
            logger.error("MCP ask_question memvid error", error=str(e))
            return "Unable to search resume data at this time."

        context = ask_response.get("answer", "")
        chunks = ask_response.get("stats", {}).get("results_returned", 0)
        search_span.set_attribute("search.chunks_retrieved", chunks)

    if chunks == 0:
        return "I don't have specific information about that in the resume data."

    # Get system prompt (sync method -- uses fallback profile.json)
    system_prompt = settings.get_system_prompt_from_profile() or settings.system_prompt

    # LLM call (non-streaming, stateless -- no history)
    with tracer.start_as_current_span("llm.openrouter_call") as llm_span:
        llm_span.set_attribute("llm.model", settings.llm_model)
        llm_span.set_attribute("llm.stream", False)
        llm_span.set_attribute("llm.context_chunks", chunks)

        openrouter_client = await get_openrouter_client()
        try:
            response = await openrouter_client.chat(
                system_prompt=system_prompt,
                context=context,
                user_message=question,
                history=[],
            )
        except Exception as e:
            logger.error("MCP ask_question LLM error", error=str(e))
            return "Unable to generate a response at this time."

        llm_span.set_attribute("llm.tokens_used", response.tokens_used)

    # Output guardrail
    with tracer.start_as_current_span("guardrail.check_output"):
        safe_content = check_output(response.content)
    return safe_content


@mcp.tool()
async def assess_fit(job_description: str) -> str:
    """Evaluate how well the candidate fits a job description.

    Provide the full job description text. Returns a structured assessment with
    verdict, key matches, gaps, and recommendation.
    """
    tracer = get_tracer()

    # Rate limit check
    if not _check_rate_limit("mcp-client"):
        return "Rate limit exceeded. Please wait a moment before trying again."

    # Search memvid for relevant context
    with tracer.start_as_current_span("memvid.search") as search_span:
        search_span.set_attribute("search.query_length", len(job_description))
        search_span.set_attribute("search.top_k", 10)
        search_span.set_attribute("search.mode", "hybrid")

        memvid_client = await get_memvid_client()
        try:
            ask_response = await memvid_client.ask(
                question=(
                    "What relevant experience, skills, and qualifications does the "
                    f"candidate have for this role? {job_description[:300]}"
                ),
                use_llm=False,
                top_k=10,
                snippet_chars=500,
                mode="hybrid",
            )
        except Exception as e:
            logger.error("MCP assess_fit memvid error", error=str(e))
            return "Unable to search resume data at this time."

        context = ask_response.get("answer", "")
        chunks = ask_response.get("stats", {}).get("results_returned", 0)
        search_span.set_attribute("search.chunks_retrieved", chunks)

    if chunks == 0:
        return "Unable to find relevant resume data for this assessment."

    # Role classification for assessor persona
    from ai_resume_api.role_classifier import classify_job_description

    classification = classify_job_description(job_description)
    role_info = (
        classification
        if isinstance(classification, dict)
        else {"persona": "You are a technical recruiter evaluating candidate fit."}
    )

    # Build assessment prompt (simplified version of main.py's assess_fit)
    fit_assessment_prompt = f"""Evaluate the following job description against the candidate's background.

JOB DESCRIPTION:
{job_description}

CANDIDATE CONTEXT:
{context}

Provide your assessment in this exact format:
VERDICT: [Strong Fit / Moderate Fit / Weak Fit]
KEY MATCHES:
- [match 1]
- [match 2]
- [match 3]
GAPS:
- [gap 1]
- [gap 2]
RECOMMENDATION:
[Your recommendation paragraph]"""

    with tracer.start_as_current_span("llm.openrouter_call") as llm_span:
        llm_span.set_attribute("llm.model", get_settings().llm_model)
        llm_span.set_attribute("llm.stream", False)
        llm_span.set_attribute("llm.context_chunks", chunks)

        openrouter_client = await get_openrouter_client()
        try:
            response = await openrouter_client.chat(
                system_prompt=role_info.get(
                    "persona", "You are a technical recruiter evaluating candidate fit."
                ),
                context="",
                user_message=fit_assessment_prompt,
                history=[],
                max_tokens=2048,
            )
        except Exception as e:
            logger.error("MCP assess_fit LLM error", error=str(e))
            return "Unable to generate fit assessment at this time."

        llm_span.set_attribute("llm.tokens_used", response.tokens_used)

    with tracer.start_as_current_span("guardrail.check_output"):
        return check_output(response.content)


# =============================================================================
# MCP Resources
# =============================================================================


@mcp.resource("profile://current")
async def get_profile_resource() -> str:
    """Current candidate profile including experience, skills, and background."""
    settings = get_settings()
    profile = await settings.load_profile_from_memvid() or settings.load_profile()
    if not profile:
        return json.dumps({"error": "Profile not available"})
    return json.dumps(profile, default=str)


@mcp.resource("questions://suggested")
async def get_suggested_questions_resource() -> str:
    """Suggested questions to ask about the candidate."""
    settings = get_settings()
    profile = await settings.load_profile_from_memvid() or settings.load_profile()
    if not profile:
        return json.dumps({"questions": []})
    questions = profile.get("suggested_questions", [])
    return json.dumps({"questions": questions})


# =============================================================================
# create_mcp_app() factory
# =============================================================================


def create_mcp_app() -> Any:
    """Create the MCP ASGI app with Streamable HTTP transport.

    Uses stateless mode (no server-side session persistence).
    Each MCP tool invocation is independent.

    Mounted at /mcp in main app; internal path is "/" so the
    endpoint responds at /mcp/ (Starlette strips the mount prefix).
    A redirect middleware handles /mcp -> /mcp/ transparently.
    """
    return mcp.http_app(
        path="/",
        transport="streamable-http",
        stateless_http=True,
    )


# =============================================================================
# Config Endpoints (FastAPI Router)
# =============================================================================

mcp_config_router = APIRouter(prefix="/api/v1/mcp", tags=["mcp-config"])

# Supported MCP clients
MCP_CLIENTS = [
    {"id": "claude-desktop", "label": "Claude Desktop"},
    {"id": "claude-code", "label": "Claude Code"},
    {"id": "claude-web", "label": "Claude Web"},
    {"id": "cursor", "label": "Cursor"},
]


def _derive_base_url(request: Request) -> str:
    """Derive the public base URL from forwarded headers or request."""
    proto = request.headers.get("x-forwarded-proto", "https")
    host = request.headers.get("x-forwarded-host", request.headers.get("host", "localhost"))
    return f"{proto}://{host}"


def _get_config_template(client_id: str, base_url: str, profile_name: str) -> dict | None:
    """Return MCP config template for a given client."""
    mcp_url = f"{base_url}/mcp"
    server_name = profile_name.lower().replace(" ", "-") + "-resume"

    templates = {
        "claude-desktop": {
            "label": "Claude Desktop",
            "instructions": (
                "Claude Desktop does not support remote URLs directly. "
                "Add this to claude_desktop_config.json "
                "(Settings > Developer > Edit Config):"
            ),
            "config": {
                "mcpServers": {
                    server_name: {
                        "command": "npx",
                        "args": ["-y", "mcp-remote", mcp_url],
                    }
                }
            },
        },
        "claude-code": {
            "label": "Claude Code",
            "instructions": "Run this command in your terminal:",
            "config": {
                "command": (f"claude mcp add --transport http {server_name} {mcp_url}"),
            },
        },
        "claude-web": {
            "label": "Claude Web",
            "instructions": (
                "Add this MCP server URL in Claude.ai (Settings > Integrations > Add MCP Server):"
            ),
            "config": {
                "url": mcp_url,
            },
        },
        "cursor": {
            "label": "Cursor",
            "instructions": "Add this to your Cursor MCP settings (.cursor/mcp.json):",
            "config": {
                "mcpServers": {
                    server_name: {
                        "url": mcp_url,
                    }
                }
            },
        },
    }

    return templates.get(client_id)


@mcp_config_router.get("/clients")
async def list_mcp_clients() -> list[dict]:
    """List supported MCP client configurations."""
    return MCP_CLIENTS


@mcp_config_router.get("/config/{client_id}")
async def get_mcp_config(client_id: str, request: Request, origin: str | None = None) -> dict:
    """Get MCP configuration template for a specific client."""
    settings = get_settings()
    profile = await settings.load_profile_from_memvid() or settings.load_profile()
    profile_name = profile.get("name", "candidate") if profile else "candidate"

    base_url = origin if origin else _derive_base_url(request)
    template = _get_config_template(client_id, base_url, profile_name)

    if template is None:
        raise HTTPException(
            status_code=404,
            detail=f"MCP config for '{client_id}' is not available at this time",
        )

    return template
