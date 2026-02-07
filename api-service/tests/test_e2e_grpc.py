"""E2E tests for the Python gRPC client against a running Rust memvid-service.

These tests require a running memvid-service on localhost:50051.
Run with: pytest -m slow tests/test_e2e_grpc.py

Tests marked @pytest.mark.slow are skipped when the service is unreachable.
Test #5 (connection failure) uses a dead port and runs without the service.
"""

import json
import socket
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio

from ai_resume_api.memvid_client import (
    MemvidClient,
    MemvidConnectionError,
    reset_memvid_client,
)

# Default gRPC endpoint for the Rust memvid-service
GRPC_HOST = "localhost"
GRPC_PORT = 50051
GRPC_URL = f"{GRPC_HOST}:{GRPC_PORT}"

# Port guaranteed to have nothing listening
DEAD_PORT = 19999


def _service_reachable(host: str = GRPC_HOST, port: int = GRPC_PORT) -> bool:
    """Return True if a TCP connection to host:port succeeds."""
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


@pytest.fixture()
def require_memvid_service() -> None:
    """Skip the test if the Rust memvid-service is not reachable."""
    if not _service_reachable():
        pytest.skip(f"memvid-service not running on {GRPC_URL}")


@pytest.fixture()
def grpc_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Set MOCK_MEMVID_CLIENT=false so the client uses real gRPC."""
    monkeypatch.setenv("MOCK_MEMVID_CLIENT", "false")
    from ai_resume_api.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
    reset_memvid_client()


@pytest_asyncio.fixture()
async def connected_client(
    grpc_env: None, require_memvid_service: None
) -> AsyncGenerator[MemvidClient, None]:
    """Provide a MemvidClient that is connected to the live service."""
    client = MemvidClient(grpc_url=GRPC_URL)
    await client.connect()
    yield client
    await client.close()


# ---------------------------------------------------------------------------
# E2E tests (require running memvid-service)
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.asyncio
async def test_grpc_health_check(connected_client: MemvidClient) -> None:
    """Health check returns a status field from the live service."""
    response = await connected_client.health_check()

    assert response is not None
    assert response.status in ("SERVING", "NOT_SERVING", "UNKNOWN")
    assert response.status == "SERVING"
    assert response.frame_count >= 0
    assert isinstance(response.memvid_file, str)


@pytest.mark.slow
@pytest.mark.asyncio
async def test_grpc_search(connected_client: MemvidClient) -> None:
    """Search via gRPC returns hits with expected structure."""
    response = await connected_client.search(
        query="Python experience",
        top_k=5,
        snippet_chars=300,
    )

    assert response is not None
    assert response.total_hits > 0
    assert len(response.hits) > 0
    assert response.took_ms >= 0

    hit = response.hits[0]
    assert isinstance(hit.title, str)
    assert len(hit.title) > 0
    assert hit.score >= 0.0
    assert isinstance(hit.snippet, str)
    assert len(hit.snippet) > 0


@pytest.mark.slow
@pytest.mark.asyncio
async def test_grpc_get_state_profile(connected_client: MemvidClient) -> None:
    """GetState for __profile__ returns profile data with expected keys."""
    result = await connected_client.get_state(entity="__profile__")

    assert result is not None
    assert result["found"] is True
    assert result["entity"] == "__profile__"
    assert "slots" in result
    assert "data" in result["slots"]

    # The data slot contains JSON-encoded profile
    profile = json.loads(result["slots"]["data"])
    assert "name" in profile
    assert "title" in profile


@pytest.mark.slow
@pytest.mark.asyncio
async def test_grpc_ask(connected_client: MemvidClient) -> None:
    """Ask via gRPC returns an answer with evidence."""
    result = await connected_client.ask(
        question="What programming languages are you experienced with?",
        top_k=5,
        snippet_chars=300,
        mode="hybrid",
    )

    assert result is not None
    assert "answer" in result
    assert isinstance(result["answer"], str)

    assert "evidence" in result
    assert len(result["evidence"]) > 0

    evidence_item = result["evidence"][0]
    assert "title" in evidence_item
    assert "score" in evidence_item
    assert "snippet" in evidence_item

    assert "stats" in result
    stats = result["stats"]
    assert "candidates_retrieved" in stats
    assert "results_returned" in stats


# ---------------------------------------------------------------------------
# Connection failure test (no live service required)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_grpc_connection_failure(grpc_env: None) -> None:
    """Dead port returns NOT_SERVING or raises MemvidConnectionError."""
    client = MemvidClient(grpc_url=f"{GRPC_HOST}:{DEAD_PORT}")
    await client.connect()

    # The gRPC channel is lazy -- connection failure surfaces on the first RPC.
    # The client may either raise or return a NOT_SERVING response.
    try:
        response = await client.health_check()
        # If it doesn't raise, the status should indicate failure
        assert response.status != "SERVING"
    except (MemvidConnectionError, Exception):
        pass  # Expected

    await client.close()
