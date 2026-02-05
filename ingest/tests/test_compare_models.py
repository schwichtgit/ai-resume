#!/usr/bin/env python3
"""Tests for compare_models.py"""

import numpy as np
import pytest


def test_cosine_similarity():
    """Test cosine similarity calculation."""
    from compare_models import cosine_similarity

    # Identical vectors = similarity 1.0
    a = np.array([1.0, 0.0, 0.0])
    b = np.array([1.0, 0.0, 0.0])
    assert abs(cosine_similarity(a, b) - 1.0) < 0.001

    # Orthogonal vectors = similarity 0.0
    a = np.array([1.0, 0.0, 0.0])
    b = np.array([0.0, 1.0, 0.0])
    assert abs(cosine_similarity(a, b) - 0.0) < 0.001

    # Opposite vectors = similarity -1.0
    a = np.array([1.0, 0.0, 0.0])
    b = np.array([-1.0, 0.0, 0.0])
    assert abs(cosine_similarity(a, b) - (-1.0)) < 0.001


@pytest.mark.slow
def test_test_model_returns_results():
    """
    Test that test_model() returns expected structure.

    This test downloads the embedding model (~130MB) on first run,
    so it's marked as slow. Run with: pytest -m slow
    """
    from compare_models import test_model

    # Use a small fast model for testing
    result = test_model("sentence-transformers/all-MiniLM-L6-v2")

    # Verify structure
    assert "model_name" in result
    assert result["model_name"] == "sentence-transformers/all-MiniLM-L6-v2"

    assert "results" in result
    assert isinstance(result["results"], list)
    assert len(result["results"]) > 0

    # Verify each query result has required fields
    for query_result in result["results"]:
        assert "query" in query_result
        assert "similarity" in query_result
        assert isinstance(query_result["similarity"], (float, np.floating))
        assert 0.0 <= query_result["similarity"] <= 1.0

    # Verify average similarity
    assert "avg_similarity" in result
    assert isinstance(result["avg_similarity"], (float, np.floating))
    assert 0.0 <= result["avg_similarity"] <= 1.0


@pytest.mark.slow
def test_main_runs_without_errors(monkeypatch, capsys):
    """
    Test that main() can be called without crashing.

    Uses pytest fixtures (monkeypatch, capsys) for clean mocking.
    Marked as slow due to model download. Run with: pytest -m slow
    """
    from compare_models import main
    import sys

    # Mock CLI arguments using monkeypatch (safe, auto-restored)
    test_args = [
        "compare_models.py",
        "sentence-transformers/all-MiniLM-L6-v2",
        "sentence-transformers/all-MiniLM-L6-v2"
    ]
    monkeypatch.setattr(sys, "argv", test_args)

    # Run main (capsys automatically captures stdout/stderr)
    main()

    # Verify output contains expected content
    captured = capsys.readouterr()

    assert "EMBEDDING MODEL COMPARISON" in captured.out
    assert "Average Similarity" in captured.out
    assert "sentence-transformers" in captured.out
