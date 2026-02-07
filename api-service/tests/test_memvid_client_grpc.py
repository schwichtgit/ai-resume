"""Tests for memvid gRPC client - gRPC-specific functionality."""

from collections.abc import Callable
from typing import Any

from ai_resume_api.config import Settings

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ai_resume_api.memvid_client import (
    MemvidClient,
    MemvidConnectionError,
    MemvidSearchError,
)


def create_mock_rpc_error(message: str) -> Exception:
    """Create a mock gRPC RpcError with a message."""
    import grpc

    class MockRpcError(grpc.RpcError):  # type: ignore[misc]
        def __init__(self, msg: str) -> None:
            self._msg = msg

        def __str__(self) -> str:
            return self._msg

    return MockRpcError(message)


def require_proto() -> Any:
    """Helper to skip tests if proto not available and import it."""
    try:
        from ai_resume_api.proto.memvid.v1 import memvid_pb2

        return memvid_pb2
    except ImportError:
        pytest.skip("gRPC proto not available")


def patch_grpc_available(memvid_pb2_module: Any) -> Any:
    """Context manager to patch GRPC_AVAILABLE and memvid_pb2."""
    return patch.multiple(
        "ai_resume_api.memvid_client",
        GRPC_AVAILABLE=True,
        memvid_pb2=memvid_pb2_module,
    )


class TestMemvidClientGrpcConnection:
    """Tests for gRPC connection handling."""

    @pytest.mark.asyncio
    async def test_connect_grpc_failure(self, mock_settings: Callable[..., Settings]) -> None:
        """Test connection failure when gRPC is unavailable."""
        mock_settings(mock_memvid_client="false")
        memvid_pb2 = require_proto()
        client = MemvidClient(grpc_url="invalid-host:99999")

        # Patch GRPC_AVAILABLE to simulate gRPC module available but connection fails
        with patch("ai_resume_api.memvid_client.GRPC_AVAILABLE", True):
            with patch("ai_resume_api.memvid_client.memvid_pb2", memvid_pb2, create=True):
                with patch("ai_resume_api.memvid_client.grpc.aio.insecure_channel") as mock_channel:
                    mock_channel.side_effect = Exception("Connection refused")

                    with pytest.raises(MemvidConnectionError) as exc_info:
                        await client.connect()
                    assert "Failed to connect" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_connect_grpc_not_available(self) -> None:
        """Test connect when gRPC protobuf not available."""
        client = MemvidClient(grpc_url="localhost:50051")

        with patch("ai_resume_api.memvid_client.GRPC_AVAILABLE", False):
            await client.connect()
            # Should not raise, just log that mock mode is used
            assert client._channel is None
            assert client._memvid_stub is None

    @pytest.mark.asyncio
    async def test_close_with_active_channel(self) -> None:
        """Test closing client with active gRPC channel."""
        client = MemvidClient(grpc_url="localhost:50051")

        # Mock an active channel
        mock_channel = AsyncMock()
        client._channel = mock_channel
        client._memvid_stub = MagicMock()
        client._health_stub = MagicMock()

        await client.close()

        mock_channel.close.assert_called_once()
        assert client._channel is None
        assert client._memvid_stub is None
        assert client._health_stub is None


class TestMemvidClientGrpcSearch:
    """Tests for gRPC search functionality."""

    @pytest.mark.asyncio
    async def test_search_grpc_error(self, mock_settings: Callable[..., Settings]) -> None:
        """Test search handles gRPC RPC errors."""
        memvid_pb2 = require_proto()
        mock_settings(mock_memvid_client="false")
        client = MemvidClient(grpc_url="localhost:50051")

        # Set up mock stub that raises RPC error
        with patch("ai_resume_api.memvid_client.GRPC_AVAILABLE", True):
            with patch("ai_resume_api.memvid_client.memvid_pb2", memvid_pb2, create=True):
                mock_stub = AsyncMock()
                mock_stub.Search.side_effect = create_mock_rpc_error("Search failed")
                client._memvid_stub = mock_stub

                with pytest.raises(MemvidSearchError) as exc_info:
                    await client.search(query="test query", top_k=5)
                assert "Search failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_without_connection_mock_disabled(
        self, mock_settings: Callable[..., Settings]
    ) -> None:
        """Test search fails when mock disabled and not connected."""
        mock_settings(mock_memvid_client="false")
        client = MemvidClient(grpc_url="localhost:50051")

        with patch("ai_resume_api.memvid_client.GRPC_AVAILABLE", False):
            with pytest.raises(MemvidConnectionError) as exc_info:
                await client.search(query="test", top_k=5)
            assert "MOCK_MEMVID_CLIENT=false" in str(exc_info.value)
            assert "gRPC connection unavailable" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_tag_filtering(self) -> None:
        """Test client-side tag filtering."""
        client = MemvidClient(grpc_url="localhost:50051")

        # Use mock search which has tags
        response = await client._mock_search(
            query="skills",
            top_k=10,
            snippet_chars=200,
            tags=["skills", "programming"],
        )

        # All returned hits should have both tags
        for hit in response.hits:
            assert "skills" in hit.tags
            assert "programming" in hit.tags

    @pytest.mark.asyncio
    async def test_search_tag_filtering_no_matches(self) -> None:
        """Test tag filtering when no hits match."""
        client = MemvidClient(grpc_url="localhost:50051")

        response = await client._mock_search(
            query="test",
            top_k=10,
            snippet_chars=200,
            tags=["nonexistent", "tags"],
        )

        # Should return empty results
        assert len(response.hits) == 0
        assert response.total_hits == 0

    @pytest.mark.asyncio
    async def test_search_with_grpc_stub_connected(self) -> None:
        """Test search with gRPC stub properly connected."""
        memvid_pb2 = require_proto()

        client = MemvidClient(grpc_url="localhost:50051")

        with patch("ai_resume_api.memvid_client.GRPC_AVAILABLE", True):
            with patch("ai_resume_api.memvid_client.memvid_pb2", memvid_pb2, create=True):
                # Create mock response
                mock_hit = MagicMock()
                mock_hit.title = "Test Result"
                mock_hit.score = 0.95
                mock_hit.snippet = "Test snippet"
                mock_hit.tags = ["test", "sample"]

                mock_response = MagicMock()
                mock_response.hits = [mock_hit]
                mock_response.took_ms = 5

                mock_stub = AsyncMock()
                mock_stub.Search.return_value = mock_response
                client._memvid_stub = mock_stub

                result = await client.search(query="test query", top_k=5)

                assert len(result.hits) == 1
                assert result.hits[0].title == "Test Result"
                assert result.hits[0].score == 0.95
                mock_stub.Search.assert_called_once()


class TestMemvidClientAsk:
    """Tests for Ask mode functionality."""

    @pytest.mark.asyncio
    async def test_ask_mode_mapping(self) -> None:
        """Test mode string mapping to proto enums."""
        memvid_pb2 = require_proto()
        client = MemvidClient(grpc_url="localhost:50051")

        with patch("ai_resume_api.memvid_client.GRPC_AVAILABLE", True):
            with patch("ai_resume_api.memvid_client.memvid_pb2", memvid_pb2, create=True):
                mock_response = MagicMock()
                mock_response.answer = "Test answer"
                mock_response.evidence = []
                mock_response.stats = MagicMock()
                mock_response.stats.candidates_retrieved = 10
                mock_response.stats.results_returned = 5
                mock_response.stats.retrieval_ms = 10
                mock_response.stats.reranking_ms = 5
                mock_response.stats.used_fallback = False

                mock_stub = AsyncMock()
                mock_stub.Ask.return_value = mock_response
                client._memvid_stub = mock_stub

                # Test hybrid mode
                await client.ask(question="test", mode="hybrid")
                call_args = mock_stub.Ask.call_args[0][0]
                assert call_args.mode == memvid_pb2.ASK_MODE_HYBRID

                # Test semantic mode
                await client.ask(question="test", mode="sem")
                call_args = mock_stub.Ask.call_args[0][0]
                assert call_args.mode == memvid_pb2.ASK_MODE_SEM

                # Test lexical mode
                await client.ask(question="test", mode="lex")
                call_args = mock_stub.Ask.call_args[0][0]
                assert call_args.mode == memvid_pb2.ASK_MODE_LEX

    @pytest.mark.asyncio
    async def test_ask_with_optional_params(self) -> None:
        """Test ask with all optional parameters."""
        memvid_pb2 = require_proto()
        client = MemvidClient(grpc_url="localhost:50051")

        with patch("ai_resume_api.memvid_client.GRPC_AVAILABLE", True):
            with patch("ai_resume_api.memvid_client.memvid_pb2", memvid_pb2, create=True):
                mock_response = MagicMock()
                mock_response.answer = "Test answer"
                mock_response.evidence = []
                mock_response.stats = MagicMock()
                mock_response.stats.candidates_retrieved = 10
                mock_response.stats.results_returned = 5
                mock_response.stats.retrieval_ms = 10
                mock_response.stats.reranking_ms = 5
                mock_response.stats.used_fallback = False

                mock_stub = AsyncMock()
                mock_stub.Ask.return_value = mock_response
                client._memvid_stub = mock_stub

                result = await client.ask(
                    question="test question",
                    use_llm=True,
                    top_k=10,
                    filters={"section": "experience"},
                    start=1000,
                    end=2000,
                    snippet_chars=300,
                    mode="sem",
                    uri="/document/test",
                    cursor="next_page_token",
                    as_of_frame=42,
                    as_of_ts=1234567890,
                    adaptive=True,
                )

                # Verify all params were passed
                call_args = mock_stub.Ask.call_args[0][0]
                assert call_args.question == "test question"
                assert call_args.use_llm is True
                assert call_args.top_k == 10
                assert call_args.filters == {"section": "experience"}
                assert call_args.start == 1000
                assert call_args.end == 2000
                assert call_args.snippet_chars == 300
                assert call_args.uri == "/document/test"
                assert call_args.cursor == "next_page_token"
                assert call_args.as_of_frame == 42
                assert call_args.as_of_ts == 1234567890
                assert call_args.adaptive is True

                # Verify response structure
                assert result["answer"] == "Test answer"
                assert "evidence" in result
                assert "stats" in result

    @pytest.mark.asyncio
    async def test_ask_without_connection_mock_disabled(
        self, mock_settings: Callable[..., Settings]
    ) -> None:
        """Test ask fails when mock disabled and not connected."""
        mock_settings(mock_memvid_client="false")
        client = MemvidClient(grpc_url="localhost:50051")

        with patch("ai_resume_api.memvid_client.GRPC_AVAILABLE", False):
            with pytest.raises(MemvidConnectionError) as exc_info:
                await client.ask(question="test", top_k=5)
            assert "MOCK_MEMVID_CLIENT=false" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_ask_grpc_error(self, mock_settings: Callable[..., Settings]) -> None:
        """Test ask handles gRPC RPC errors."""
        memvid_pb2 = require_proto()

        mock_settings(mock_memvid_client="false")
        client = MemvidClient(grpc_url="localhost:50051")

        with patch("ai_resume_api.memvid_client.GRPC_AVAILABLE", True):
            with patch("ai_resume_api.memvid_client.memvid_pb2", memvid_pb2, create=True):
                mock_stub = AsyncMock()
                mock_stub.Ask.side_effect = create_mock_rpc_error("Ask failed")
                client._memvid_stub = mock_stub

                with pytest.raises(MemvidSearchError) as exc_info:
                    await client.ask(question="test question", top_k=5)
                assert "Ask failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_mock_ask_mode_parameter(self) -> None:
        """Test that mock ask accepts mode parameter."""
        client = MemvidClient(grpc_url="localhost:50051")

        # Test different modes work with mock
        for mode in ["hybrid", "sem", "lex"]:
            result = await client._mock_ask(
                question=f"test {mode}",
                top_k=5,
                snippet_chars=200,
                mode=mode,
            )

            assert "answer" in result
            assert "evidence" in result
            assert "stats" in result
            assert len(result["evidence"]) > 0


class TestMemvidClientHealthCheck:
    """Tests for health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_grpc_error(self) -> None:
        """Test health check handles gRPC errors gracefully."""
        memvid_pb2 = require_proto()

        client = MemvidClient(grpc_url="localhost:50051")

        with patch("ai_resume_api.memvid_client.GRPC_AVAILABLE", True):
            with patch("ai_resume_api.memvid_client.memvid_pb2", memvid_pb2, create=True):
                mock_stub = AsyncMock()
                mock_stub.Check.side_effect = create_mock_rpc_error("Health check failed")
                client._health_stub = mock_stub

                response = await client.health_check()

                # Should return NOT_SERVING instead of raising
                assert response.status == "NOT_SERVING"
                assert response.frame_count == 0
                assert response.memvid_file == ""

    @pytest.mark.asyncio
    async def test_health_check_without_connection_mock_disabled(
        self, mock_settings: Callable[..., Settings]
    ) -> None:
        """Test health check fails when mock disabled and not connected."""
        mock_settings(mock_memvid_client="false")
        client = MemvidClient(grpc_url="localhost:50051")

        with patch("ai_resume_api.memvid_client.GRPC_AVAILABLE", False):
            with pytest.raises(MemvidConnectionError) as exc_info:
                await client.health_check()
            assert "MOCK_MEMVID_CLIENT=false" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_health_check_status_mapping(self) -> None:
        """Test health check status code mapping."""
        memvid_pb2 = require_proto()
        client = MemvidClient(grpc_url="localhost:50051")

        with patch("ai_resume_api.memvid_client.GRPC_AVAILABLE", True):
            with patch("ai_resume_api.memvid_client.memvid_pb2", memvid_pb2, create=True):
                mock_response = MagicMock()
                mock_response.frame_count = 100
                mock_response.memvid_file = "/path/to/resume.mv2"

                mock_stub = AsyncMock()
                client._health_stub = mock_stub

                # Test status mappings: 0=UNKNOWN, 1=SERVING, 2=NOT_SERVING
                for status_code, expected_status in [
                    (0, "UNKNOWN"),
                    (1, "SERVING"),
                    (2, "NOT_SERVING"),
                ]:
                    mock_response.status = status_code
                    mock_stub.Check.return_value = mock_response

                    result = await client.health_check()
                    assert result.status == expected_status
                    assert result.frame_count == 100


class TestMemvidClientGetState:
    """Tests for GetState functionality."""

    @pytest.mark.asyncio
    async def test_get_state_grpc_error(self) -> None:
        """Test get_state handles gRPC errors."""
        memvid_pb2 = require_proto()

        client = MemvidClient(grpc_url="localhost:50051")

        with patch("ai_resume_api.memvid_client.GRPC_AVAILABLE", True):
            with patch("ai_resume_api.memvid_client.memvid_pb2", memvid_pb2, create=True):
                mock_stub = AsyncMock()
                mock_stub.GetState.side_effect = create_mock_rpc_error("GetState failed")
                client._memvid_stub = mock_stub

                result = await client.get_state(entity="__profile__")

                # Should return None instead of raising
                assert result is None

    @pytest.mark.asyncio
    async def test_get_state_not_found(self) -> None:
        """Test get_state when entity not found."""
        memvid_pb2 = require_proto()
        client = MemvidClient(grpc_url="localhost:50051")

        with patch("ai_resume_api.memvid_client.GRPC_AVAILABLE", True):
            with patch("ai_resume_api.memvid_client.memvid_pb2", memvid_pb2, create=True):
                mock_response = MagicMock()
                mock_response.found = False

                mock_stub = AsyncMock()
                mock_stub.GetState.return_value = mock_response
                client._memvid_stub = mock_stub

                result = await client.get_state(entity="nonexistent")
                assert result is None

    @pytest.mark.asyncio
    async def test_get_state_without_connection_mock_disabled(
        self, mock_settings: Callable[..., Settings]
    ) -> None:
        """Test get_state fails when mock disabled and not connected."""
        mock_settings(mock_memvid_client="false")
        client = MemvidClient(grpc_url="localhost:50051")

        with patch("ai_resume_api.memvid_client.GRPC_AVAILABLE", False):
            with pytest.raises(MemvidConnectionError) as exc_info:
                await client.get_state(entity="__profile__")
            assert "MOCK_MEMVID_CLIENT=false" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_state_with_slot(self) -> None:
        """Test get_state with specific slot parameter."""
        memvid_pb2 = require_proto()
        client = MemvidClient(grpc_url="localhost:50051")

        with patch("ai_resume_api.memvid_client.GRPC_AVAILABLE", True):
            with patch("ai_resume_api.memvid_client.memvid_pb2", memvid_pb2, create=True):
                mock_response = MagicMock()
                mock_response.found = True
                mock_response.entity = "__profile__"
                mock_response.slots = {"data": '{"name": "Frank"}'}

                mock_stub = AsyncMock()
                mock_stub.GetState.return_value = mock_response
                client._memvid_stub = mock_stub

                result = await client.get_state(entity="__profile__", slot="data")

                assert result is not None
                assert result["found"] is True
                assert result["entity"] == "__profile__"
                assert "data" in result["slots"]

                # Verify slot was passed in request
                call_args = mock_stub.GetState.call_args[0][0]
                assert call_args.slot == "data"

    @pytest.mark.asyncio
    async def test_mock_get_state_profile(self) -> None:
        """Test mock get_state returns profile data."""
        client = MemvidClient(grpc_url="localhost:50051")

        result = await client._mock_get_state(entity="__profile__")

        assert result is not None
        assert result["found"] is True
        assert result["entity"] == "__profile__"
        assert "data" in result["slots"]

        # Parse the JSON data
        import json

        profile_data = json.loads(result["slots"]["data"])
        assert "name" in profile_data
        assert "title" in profile_data
        assert "experience" in profile_data

    @pytest.mark.asyncio
    async def test_mock_get_state_non_profile(self) -> None:
        """Test mock get_state returns None for non-profile entities."""
        client = MemvidClient(grpc_url="localhost:50051")

        result = await client._mock_get_state(entity="other_entity")
        assert result is None


class TestMemvidClientMetrics:
    """Tests for metrics and observability."""

    @pytest.mark.asyncio
    async def test_search_records_latency_metric(self) -> None:
        """Test that search records latency metrics."""
        memvid_pb2 = require_proto()

        client = MemvidClient(grpc_url="localhost:50051")

        # Use the public search method with mock mode enabled
        with patch("ai_resume_api.memvid_client.memvid_search_latency") as mock_histogram:
            with patch("ai_resume_api.memvid_client.GRPC_AVAILABLE", True):
                with patch("ai_resume_api.memvid_client.memvid_pb2", memvid_pb2, create=True):
                    # Create mock stub to avoid error path
                    mock_stub = AsyncMock()
                    mock_hit = MagicMock()
                    mock_hit.title = "Test"
                    mock_hit.score = 0.9
                    mock_hit.snippet = "Test"
                    mock_hit.tags = []
                    mock_response = MagicMock()
                    mock_response.hits = [mock_hit]
                    mock_response.took_ms = 5
                    mock_stub.Search.return_value = mock_response
                    client._memvid_stub = mock_stub

                    await client.search(query="test", top_k=5, snippet_chars=200)

                    # Verify metric was recorded
                    assert mock_histogram.observe.called

    @pytest.mark.asyncio
    async def test_search_error_records_latency_metric(
        self, mock_settings: Callable[..., Settings]
    ) -> None:
        """Test that failed search still records latency."""
        memvid_pb2 = require_proto()

        mock_settings(mock_memvid_client="false")
        client = MemvidClient(grpc_url="localhost:50051")

        with patch("ai_resume_api.memvid_client.GRPC_AVAILABLE", True):
            with patch("ai_resume_api.memvid_client.memvid_pb2", memvid_pb2, create=True):
                mock_stub = AsyncMock()
                mock_stub.Search.side_effect = create_mock_rpc_error("Error")
                client._memvid_stub = mock_stub

                with patch("ai_resume_api.memvid_client.memvid_search_latency") as mock_histogram:
                    with pytest.raises(MemvidSearchError):
                        await client.search(query="test", top_k=5)

                    # Verify metric was still recorded on error
                    assert mock_histogram.observe.called
