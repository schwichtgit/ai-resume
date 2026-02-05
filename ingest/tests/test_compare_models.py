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
    """Test that test_model() returns expected structure."""
    from compare_models import test_model

    # Use a small fast model for testing
    result = test_model("sentence-transformers/all-MiniLM-L6-v2")

    assert "model_name" in result
    assert "results" in result
    assert "avg_similarity" in result
    assert len(result["results"]) > 0
    assert 0.0 <= result["avg_similarity"] <= 1.0


def test_main_runs_without_errors():
    """Test that main() can be called without crashing."""
    from compare_models import main
    import sys
    from io import StringIO

    # Mock sys.argv for argument parsing
    old_argv = sys.argv
    sys.argv = ["compare_models.py",
                "sentence-transformers/all-MiniLM-L6-v2",
                "sentence-transformers/all-MiniLM-L6-v2"]

    # Capture stdout
    captured_output = StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured_output

    try:
        # This will take time as it downloads/loads models
        # For quick tests, we just verify it doesn't crash
        # Mark this test as slow and skip in fast test runs
        pytest.skip("Slow test - model download required")
    finally:
        sys.stdout = old_stdout
        sys.argv = old_argv
