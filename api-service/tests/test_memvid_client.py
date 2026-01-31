"""Tests for memvid gRPC client."""

import pytest

from app.memvid_client import MemvidClient


class TestMemvidClient:
    """Tests for MemvidClient class."""

    @pytest.fixture
    def client(self):
        """Create a memvid client for testing."""
        return MemvidClient(grpc_url="localhost:50051")

    @pytest.mark.asyncio
    async def test_mock_search(self, client):
        """Test mock search functionality."""
        response = await client._mock_search(
            query="Python experience",
            top_k=3,
            snippet_chars=200,
        )

        assert response is not None
        assert len(response.hits) <= 3
        assert response.total_hits > 0
        assert response.took_ms >= 0

        for hit in response.hits:
            assert hit.title
            assert 0.0 <= hit.score <= 1.0
            assert hit.snippet

    @pytest.mark.asyncio
    async def test_mock_search_query_relevance(self, client):
        """Test that mock search boosts scores based on query."""
        # Search for something that matches tags
        response = await client._mock_search(
            query="leadership management",
            top_k=5,
            snippet_chars=200,
        )

        # Should find VP Engineering which has leadership and management tags
        titles = [hit.title for hit in response.hits]
        assert any("VP" in title or "leadership" in title.lower() for title in titles)

    @pytest.mark.asyncio
    async def test_mock_search_top_k(self, client):
        """Test that top_k limits results."""
        response = await client._mock_search(query="test", top_k=2, snippet_chars=200)
        assert len(response.hits) <= 2

    @pytest.mark.asyncio
    async def test_mock_search_snippet_chars(self, client):
        """Test that snippets are truncated."""
        response = await client._mock_search(query="test", top_k=5, snippet_chars=50)
        for hit in response.hits:
            assert len(hit.snippet) <= 50

    @pytest.mark.asyncio
    async def test_search_without_grpc(self, client):
        """Test search falls back to mock when gRPC not available."""
        # Without connecting, should use mock
        response = await client.search(query="Python", top_k=3)

        assert response is not None
        assert len(response.hits) > 0

    @pytest.mark.asyncio
    async def test_health_check_mock(self, client):
        """Test health check returns mock data when not connected."""
        response = await client.health_check()

        assert response.status == "SERVING"
        assert response.frame_count > 0
        assert "mock" in response.memvid_file

    @pytest.mark.asyncio
    async def test_is_healthy(self, client):
        """Test is_healthy method."""
        result = await client.is_healthy()
        assert result is True  # Mock always returns healthy

    @pytest.mark.asyncio
    async def test_connect_and_close(self, client):
        """Test connect and close lifecycle."""
        # Connect (will use mock mode if gRPC not available)
        await client.connect()
        # Close should not raise
        await client.close()

    @pytest.mark.asyncio
    async def test_search_scores_sorted(self, client):
        """Test that search results are sorted by score descending."""
        response = await client._mock_search(query="experience", top_k=5, snippet_chars=200)

        scores = [hit.score for hit in response.hits]
        assert scores == sorted(scores, reverse=True)


class TestMemvidClientErrors:
    """Tests for memvid client error classes."""

    def test_memvid_client_error(self):
        """Test base MemvidClientError."""
        from app.memvid_client import MemvidClientError

        error = MemvidClientError("Test error")
        assert str(error) == "Test error"

    def test_memvid_connection_error(self):
        """Test MemvidConnectionError."""
        from app.memvid_client import MemvidClientError, MemvidConnectionError

        error = MemvidConnectionError("Connection failed")
        assert str(error) == "Connection failed"
        assert isinstance(error, MemvidClientError)

    def test_memvid_search_error(self):
        """Test MemvidSearchError."""
        from app.memvid_client import MemvidClientError, MemvidSearchError

        error = MemvidSearchError("Search failed")
        assert str(error) == "Search failed"
        assert isinstance(error, MemvidClientError)


class TestMemvidClientIsHealthy:
    """Tests for is_healthy method edge cases."""

    @pytest.mark.asyncio
    async def test_is_healthy_returns_false_on_exception(self):
        """Test is_healthy returns False when health_check raises."""
        from unittest.mock import AsyncMock, patch

        client = MemvidClient(grpc_url="localhost:50051")

        with patch.object(client, "health_check", new_callable=AsyncMock) as mock_health:
            mock_health.side_effect = Exception("Network error")

            result = await client.is_healthy()
            assert result is False


class TestGlobalMemvidClientFunctions:
    """Tests for global memvid client functions."""

    @pytest.mark.asyncio
    async def test_get_memvid_client_creates_singleton(self):
        """Test that get_memvid_client creates a singleton."""
        import app.memvid_client
        from app.memvid_client import close_memvid_client, get_memvid_client

        # Reset global state
        app.memvid_client._memvid_client = None

        client1 = await get_memvid_client()
        client2 = await get_memvid_client()
        assert client1 is client2

        # Clean up
        await close_memvid_client()
        assert app.memvid_client._memvid_client is None

    @pytest.mark.asyncio
    async def test_close_memvid_client_when_none(self):
        """Test closing when client is None."""
        import app.memvid_client
        from app.memvid_client import close_memvid_client

        app.memvid_client._memvid_client = None

        # Should not raise
        await close_memvid_client()


class TestMemvidClientClose:
    """Tests for client close behavior."""

    @pytest.mark.asyncio
    async def test_close_clears_channel(self):
        """Test that close clears internal state."""
        client = MemvidClient(grpc_url="localhost:50051")
        await client.connect()

        # Mock channel to avoid real gRPC
        client._channel = None  # Already None in mock mode

        await client.close()
        assert client._channel is None
        assert client._memvid_stub is None
        assert client._health_stub is None
