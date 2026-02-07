"""gRPC client for the Rust memvid service."""

import asyncio
import time
from typing import Any, cast

import grpc
import structlog
from prometheus_client import Histogram

from ai_resume_api.config import get_settings
from ai_resume_api.models import MemvidHealthResponse, MemvidSearchHit, MemvidSearchResponse
from ai_resume_api.observability import get_trace_id

logger = structlog.get_logger()

# Memvid retrieval latency histogram
# Handle re-registration during test collection
try:
    memvid_search_latency = Histogram(
        "memvid_search_latency_seconds",
        "Memvid search latency in seconds",
        buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
    )
except ValueError:
    # Metric already registered (during test collection)
    from prometheus_client import REGISTRY

    memvid_search_latency = cast(
        Histogram, REGISTRY._names_to_collectors.get("memvid_search_latency_seconds")
    )

# Try to import generated protobuf code
# If not available, we'll use a mock client
try:
    from ai_resume_api.proto.memvid.v1 import memvid_pb2, memvid_pb2_grpc

    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False
    logger.warning("gRPC protobuf stubs not found, using mock client")


class MemvidClientError(Exception):
    """Base exception for memvid client errors."""

    pass


class MemvidConnectionError(MemvidClientError):
    """Raised when unable to connect to memvid service."""

    pass


class MemvidSearchError(MemvidClientError):
    """Raised when search operation fails."""

    pass


class MemvidClient:
    """Async gRPC client for the Rust memvid service."""

    def __init__(self, grpc_url: str | None = None, timeout: float | None = None):
        """Initialize the memvid client.

        Args:
            grpc_url: gRPC server URL (host:port). Defaults to config value.
            timeout: Request timeout in seconds. Defaults to config value.
        """
        settings = get_settings()
        self._grpc_url = grpc_url or settings.memvid_grpc_url
        self._timeout = timeout or settings.memvid_timeout_seconds
        self._channel: Any = None
        self._memvid_stub: Any = None
        self._health_stub: Any = None

    async def connect(self) -> None:
        """Establish connection to the memvid gRPC service."""
        settings = get_settings()
        if settings.mock_memvid_client:
            logger.info("MOCK_MEMVID_CLIENT=true: Skipping gRPC connection")
            return

        if not GRPC_AVAILABLE:
            logger.info("gRPC not available, using mock mode")
            return

        try:
            self._channel = grpc.aio.insecure_channel(self._grpc_url)
            self._memvid_stub = memvid_pb2_grpc.MemvidServiceStub(self._channel)  # type: ignore[no-untyped-call]
            self._health_stub = memvid_pb2_grpc.HealthStub(self._channel)  # type: ignore[no-untyped-call]
            logger.info("Connected to memvid service", url=self._grpc_url)
        except Exception as e:
            logger.error("Failed to connect to memvid service", error=str(e), url=self._grpc_url)
            raise MemvidConnectionError(f"Failed to connect: {e}") from e

    async def close(self) -> None:
        """Close the gRPC connection."""
        if self._channel:
            await self._channel.close()
            self._channel = None
            self._memvid_stub = None
            self._health_stub = None
            logger.info("Closed memvid connection")

    async def search(
        self,
        query: str,
        top_k: int = 5,
        snippet_chars: int = 200,
        tags: list[str] | None = None,
    ) -> MemvidSearchResponse:
        """Search the memvid index.

        Args:
            query: Natural language search query.
            top_k: Maximum number of results to return.
            snippet_chars: Maximum characters per snippet.
            tags: Optional list of tags to filter by (exact match).

        Returns:
            Search response with hits and metadata.

        Raises:
            MemvidSearchError: If search fails.
            MemvidConnectionError: If MOCK_MEMVID_CLIENT=false but gRPC unavailable.
        """
        start_time = time.time()
        trace_id = get_trace_id()
        settings = get_settings()

        # Check mock policy - fail loudly if real implementation unavailable
        if not GRPC_AVAILABLE or self._memvid_stub is None:
            if settings.mock_memvid_client:
                logger.info("MOCK_MEMVID_CLIENT=true: Using mock gRPC client")
                return await self._mock_search(query, top_k, snippet_chars, tags)
            else:
                error_msg = (
                    "FATAL: gRPC connection unavailable with MOCK_MEMVID_CLIENT=false. "
                    "Either start the memvid service or set MOCK_MEMVID_CLIENT=true for testing."
                )
                logger.error(
                    error_msg,
                    grpc_available=GRPC_AVAILABLE,
                    stub_connected=self._memvid_stub is not None,
                )
                raise MemvidConnectionError(error_msg)

        try:
            request = memvid_pb2.SearchRequest(
                query=query,
                top_k=top_k,
                snippet_chars=snippet_chars,
            )
            response = await self._memvid_stub.Search(
                request,
                timeout=self._timeout,
            )

            hits = [
                MemvidSearchHit(
                    title=hit.title,
                    score=hit.score,
                    snippet=hit.snippet,
                    tags=list(hit.tags),
                )
                for hit in response.hits
            ]

            # Client-side filtering by tags if specified
            # (gRPC proto doesn't support tag filtering yet)
            if tags:
                filtered_hits = []
                for hit in hits:
                    # Match if ALL requested tags are present in hit's tags
                    if all(tag in hit.tags for tag in tags):
                        filtered_hits.append(hit)
                hits = filtered_hits

            # Record metrics and log
            latency = time.time() - start_time
            memvid_search_latency.observe(latency)
            logger.info(
                "memvid_search",
                trace_id=trace_id,
                query_preview=query[:50],
                top_k=top_k,
                hits=len(hits),
                latency_ms=int(latency * 1000),
            )

            return MemvidSearchResponse(
                hits=hits,
                total_hits=len(hits),  # Update total after filtering
                took_ms=response.took_ms,
            )
        except grpc.RpcError as e:
            latency = time.time() - start_time
            memvid_search_latency.observe(latency)
            logger.error(
                "memvid_search_error",
                trace_id=trace_id,
                query_preview=query[:50],
                error=str(e),
                latency_ms=int(latency * 1000),
            )
            raise MemvidSearchError(f"Search failed: {e}") from e

    async def ask(
        self,
        question: str,
        use_llm: bool = False,
        top_k: int = 5,
        filters: dict[str, str] | None = None,
        start: int = 0,
        end: int = 0,
        snippet_chars: int = 200,
        mode: str = "hybrid",
        uri: str | None = None,
        cursor: str | None = None,
        as_of_frame: int | None = None,
        as_of_ts: int | None = None,
        adaptive: bool | None = None,
    ) -> dict[str, Any]:
        """Ask a question using memvid's Ask mode with re-ranking.

        Args:
            question: The question to ask.
            use_llm: Whether to use LLM for answer synthesis (not implemented yet).
            top_k: Maximum number of results to return.
            filters: Metadata filters (e.g., {"section": "experience"}).
            start: Temporal filter start (Unix timestamp).
            end: Temporal filter end (Unix timestamp).
            snippet_chars: Maximum characters per snippet.
            mode: Search mode - "hybrid" (default), "sem" (semantic), or "lex" (lexical).
            uri: Optional URI to scope search to specific document.
            cursor: Pagination cursor for retrieving next page.
            as_of_frame: View data as of specific frame ID (time-travel query).
            as_of_ts: View data as of specific timestamp (time-travel query).
            adaptive: Enable adaptive retrieval for better results.

        Returns:
            Dict with answer, evidence, and stats.
            Structure: {
                "answer": "...",
                "evidence": [{"title": "...", "score": 0.9, "snippet": "...", "tags": []}],
                "stats": {"candidates_retrieved": 10, "results_returned": 5, ...}
            }

        Raises:
            MemvidSearchError: If ask operation fails.
            MemvidConnectionError: If MOCK_MEMVID_CLIENT=false but gRPC unavailable.
        """
        start_time = time.time()
        trace_id = get_trace_id()
        settings = get_settings()

        # Check mock policy
        if not GRPC_AVAILABLE or self._memvid_stub is None:
            if settings.mock_memvid_client:
                logger.info("MOCK_MEMVID_CLIENT=true: Using mock Ask")
                return await self._mock_ask(question, top_k, snippet_chars, mode)
            else:
                error_msg = (
                    "FATAL: gRPC connection unavailable with MOCK_MEMVID_CLIENT=false. "
                    "Either start the memvid service or set MOCK_MEMVID_CLIENT=true for testing."
                )
                logger.error(
                    error_msg,
                    grpc_available=GRPC_AVAILABLE,
                    stub_connected=self._memvid_stub is not None,
                )
                raise MemvidConnectionError(error_msg)

        try:
            # Map mode string to proto enum
            mode_map = {
                "hybrid": memvid_pb2.ASK_MODE_HYBRID,
                "sem": memvid_pb2.ASK_MODE_SEM,
                "lex": memvid_pb2.ASK_MODE_LEX,
            }
            proto_mode = mode_map.get(mode.lower(), memvid_pb2.ASK_MODE_HYBRID)

            # Build base request
            request_args = {
                "question": question,
                "use_llm": use_llm,
                "top_k": top_k,
                "filters": filters or {},
                "start": start,
                "end": end,
                "snippet_chars": snippet_chars,
                "mode": proto_mode,
            }

            # Add optional fields if provided
            if uri is not None:
                request_args["uri"] = uri
            if cursor is not None:
                request_args["cursor"] = cursor
            if as_of_frame is not None:
                request_args["as_of_frame"] = as_of_frame
            if as_of_ts is not None:
                request_args["as_of_ts"] = as_of_ts
            if adaptive is not None:
                request_args["adaptive"] = adaptive

            request = memvid_pb2.AskRequest(**request_args)  # type: ignore[arg-type]
            response = await self._memvid_stub.Ask(
                request,
                timeout=self._timeout,
            )

            # Convert proto response to dict
            evidence = [
                {
                    "title": hit.title,
                    "score": hit.score,
                    "snippet": hit.snippet,
                    "tags": list(hit.tags),
                }
                for hit in response.evidence
            ]

            stats = {
                "candidates_retrieved": response.stats.candidates_retrieved
                if response.stats
                else 0,
                "results_returned": response.stats.results_returned
                if response.stats
                else len(evidence),
                "retrieval_ms": response.stats.retrieval_ms if response.stats else 0,
                "reranking_ms": response.stats.reranking_ms if response.stats else 0,
                "used_fallback": response.stats.used_fallback if response.stats else False,
            }

            # Record metrics and log
            latency = time.time() - start_time
            logger.info(
                "memvid_ask",
                trace_id=trace_id,
                question_preview=question[:50],
                mode=mode,
                top_k=top_k,
                evidence_count=len(evidence),
                latency_ms=int(latency * 1000),
            )

            return {
                "answer": response.answer,
                "evidence": evidence,
                "stats": stats,
            }
        except grpc.RpcError as e:
            latency = time.time() - start_time
            logger.error(
                "memvid_ask_error",
                trace_id=trace_id,
                question_preview=question[:50],
                error=str(e),
                latency_ms=int(latency * 1000),
            )
            raise MemvidSearchError(f"Ask failed: {e}") from e

    async def health_check(self) -> MemvidHealthResponse:
        """Check health of the memvid service.

        Returns:
            Health response with status and metadata.

        Raises:
            MemvidConnectionError: If MOCK_MEMVID_CLIENT=false but gRPC unavailable.
        """
        settings = get_settings()

        if not GRPC_AVAILABLE or self._health_stub is None:
            if settings.mock_memvid_client:
                return MemvidHealthResponse(
                    status="SERVING",
                    frame_count=42,
                    memvid_file="mock://sample-resume.mv2",
                )
            else:
                error_msg = "gRPC health check unavailable with MOCK_MEMVID_CLIENT=false"
                logger.error(error_msg)
                raise MemvidConnectionError(error_msg)

        try:
            request = memvid_pb2.HealthCheckRequest()
            response = await self._health_stub.Check(
                request,
                timeout=self._timeout,
            )

            status_map = {0: "UNKNOWN", 1: "SERVING", 2: "NOT_SERVING"}
            status_str = status_map.get(response.status, "UNKNOWN")
            return MemvidHealthResponse(
                status=cast(str, status_str),  # type: ignore[arg-type]
                frame_count=response.frame_count,
                memvid_file=response.memvid_file,
            )
        except grpc.RpcError as e:
            logger.error("Memvid health check failed", error=str(e))
            return MemvidHealthResponse(
                status="NOT_SERVING",
                frame_count=0,
                memvid_file="",
            )

    async def is_healthy(self) -> bool:
        """Check if the memvid service is healthy."""
        try:
            response = await self.health_check()
            return response.status == "SERVING"
        except Exception:
            return False

    async def get_state(self, entity: str, slot: str | None = None) -> dict | None:
        """Get memory card state for an entity.

        This provides O(1) lookup for profile/metadata without search truncation.

        Args:
            entity: Entity name (e.g., "__profile__").
            slot: Optional specific slot to retrieve.

        Returns:
            Dict with entity state if found, None otherwise.
            Structure: {"found": True, "entity": "...", "slots": {"data": "..."}}

        Raises:
            MemvidConnectionError: If MOCK_MEMVID_CLIENT=false but gRPC unavailable.
        """
        settings = get_settings()

        if not GRPC_AVAILABLE or self._memvid_stub is None:
            if settings.mock_memvid_client:
                # Mock response for testing without gRPC
                if entity == "__profile__":
                    return await self._mock_get_state(entity)
                return None
            else:
                error_msg = "gRPC get_state unavailable with MOCK_MEMVID_CLIENT=false"
                logger.error(error_msg, entity=entity)
                raise MemvidConnectionError(error_msg)

        try:
            request = memvid_pb2.GetStateRequest(
                entity=entity,
                slot=slot or "",
            )
            response = await self._memvid_stub.GetState(
                request,
                timeout=self._timeout,
            )

            if not response.found:
                return None

            return {
                "found": response.found,
                "entity": response.entity,
                "slots": dict(response.slots),
            }
        except grpc.RpcError as e:
            logger.error("Memvid get_state failed", error=str(e), entity=entity)
            return None

    async def _mock_get_state(self, entity: str) -> dict | None:
        """Return mock state for testing without gRPC connection."""
        if entity != "__profile__":
            return None

        # Return mock profile data
        import json

        mock_profile = {
            "name": "Frank Schwichtenberg",
            "title": "Senior Engineering Manager",
            "email": "frank@example.com",
            "linkedin": "https://linkedin.com/in/franksch",
            "location": "San Francisco, CA",
            "status": "Open to opportunities",
            "suggested_questions": [
                "Tell me about your engineering leadership experience",
                "What's your approach to building high-performing teams?",
            ],
            "tags": ["engineering", "leadership", "platform"],
            "system_prompt": "You are an AI representing Frank's resume...",
            "experience": [
                {"company": "Siemens", "role": "Engineering Manager", "period": "2020-2024"}
            ],
            "skills": {"strong": ["Python", "Rust"], "moderate": ["Go"], "gaps": []},
            "fit_assessment_examples": [],
        }

        return {
            "found": True,
            "entity": entity,
            "slots": {"data": json.dumps(mock_profile)},
        }

    async def _mock_search(
        self,
        query: str,
        top_k: int,
        snippet_chars: int,
        tags: list[str] | None = None,
    ) -> MemvidSearchResponse:
        """Return mock search results for testing without gRPC connection."""
        # Simulate network latency
        await asyncio.sleep(0.002)

        query_lower = query.lower()

        # Mock data based on query
        mock_hits = [
            MemvidSearchHit(
                title="Senior Engineering Manager at Siemens",
                score=0.95,
                snippet="Led cross-functional team of 12 engineers building industrial IoT platform. "
                "Implemented CI/CD pipelines reducing deployment time by 60%.",
                tags=["experience", "leadership", "siemens"],
            ),
            MemvidSearchHit(
                title="Technical Skills - Programming Languages",
                score=0.88,
                snippet="Proficient in Rust, Python, TypeScript, Go. Experience with systems "
                "programming, web services, and ML pipelines.",
                tags=["skills", "programming", "languages"],
            ),
            MemvidSearchHit(
                title="GenAI and Machine Learning Experience",
                score=0.92,
                snippet="Built RAG systems using vector databases and LLM APIs. Implemented "
                "semantic search with memvid for resume applications.",
                tags=["skills", "ai", "ml", "genai"],
            ),
            MemvidSearchHit(
                title="Security Engineering Background",
                score=0.85,
                snippet="Implemented zero-trust architecture for industrial control systems. "
                "Led security audits and penetration testing initiatives.",
                tags=["experience", "security", "architecture"],
            ),
            MemvidSearchHit(
                title="VP Engineering Qualifications",
                score=0.90,
                snippet="10+ years of engineering leadership experience. Built and scaled "
                "teams from 5 to 50+ engineers.",
                tags=["leadership", "management", "executive"],
            ),
        ]

        # Boost scores based on query relevance
        scored_hits = []
        for hit in mock_hits:
            score = hit.score
            for tag in hit.tags:
                if tag in query_lower:
                    score = min(score + 0.05, 1.0)
            if any(word in hit.snippet.lower() for word in query_lower.split()):
                score = min(score + 0.03, 1.0)
            scored_hits.append(
                MemvidSearchHit(
                    title=hit.title,
                    score=score,
                    snippet=hit.snippet[:snippet_chars],
                    tags=hit.tags,
                )
            )

        # Sort by score and limit
        scored_hits.sort(key=lambda x: x.score, reverse=True)
        hits = scored_hits[:top_k]

        # Client-side filtering by tags if specified
        if tags:
            filtered_hits = []
            for hit in hits:
                # Match if ALL requested tags are present in hit's tags
                if all(tag in hit.tags for tag in tags):
                    filtered_hits.append(hit)
            hits = filtered_hits

        return MemvidSearchResponse(
            hits=hits,
            total_hits=len(hits),
            took_ms=2,
        )

    async def _mock_ask(
        self,
        question: str,
        top_k: int,
        snippet_chars: int,
        mode: str,
    ) -> dict[str, Any]:
        """Return mock ask results for testing without gRPC connection."""
        # Simulate network latency
        await asyncio.sleep(0.005)

        # Reuse mock search to get evidence
        search_response = await self._mock_search(question, top_k, snippet_chars, None)

        # Convert hits to evidence format
        evidence = [
            {
                "title": hit.title,
                "score": hit.score,
                "snippet": hit.snippet,
                "tags": hit.tags,
            }
            for hit in search_response.hits
        ]

        # Generate mock answer (concatenate snippets)
        answer = "\n\n".join([f"**{e['title']}**\n{e['snippet']}" for e in evidence])

        return {
            "answer": answer,
            "evidence": evidence,
            "stats": {
                "candidates_retrieved": len(evidence),
                "results_returned": len(evidence),
                "retrieval_ms": 5,
                "reranking_ms": 0,
                "used_fallback": False,
            },
        }


# Global client instance
_memvid_client: MemvidClient | None = None


async def get_memvid_client() -> MemvidClient:
    """Get or create the global memvid client instance."""
    global _memvid_client
    if _memvid_client is None:
        _memvid_client = MemvidClient()
        await _memvid_client.connect()
    return _memvid_client


async def close_memvid_client() -> None:
    """Close the global memvid client."""
    global _memvid_client
    if _memvid_client:
        await _memvid_client.close()
        _memvid_client = None


def reset_memvid_client() -> None:
    """Reset the global memvid client (for testing)."""
    global _memvid_client
    _memvid_client = None
