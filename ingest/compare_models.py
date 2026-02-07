#!/usr/bin/env python3
"""
Compare embedding models for semantic similarity.

Usage:
    python compare_models.py [MODEL1] [MODEL2]

    If no models specified, compares:
    - all-MiniLM-L6-v2 (default, fast)
    - BAAI/bge-small-en-v1.5 (current)
"""

import argparse
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer


def cosine_similarity(a: Any, b: Any) -> float:
    """Calculate cosine similarity between two vectors."""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def test_model(model_name: str) -> dict[str, Any]:
    """Test a single model on sample queries."""
    print(f"\n{'=' * 60}")
    print(f"Testing: {model_name}")
    print("=" * 60)

    model = SentenceTransformer(model_name)

    # Sample queries
    queries = [
        "What cloud platforms has she used?",
        "Tell me about her leadership experience",
        "What programming languages does she know?",
    ]

    # Sample context from resume
    context = """
    Led platform engineering teams at scale, managing AWS and GCP infrastructure.
    Proficient in Python, Go, Rust. 10+ years building distributed systems.
    """

    context_embedding = model.encode(context)
    results = []

    for query in queries:
        query_embedding = model.encode(query)
        similarity = cosine_similarity(query_embedding, context_embedding)
        results.append({"query": query, "similarity": similarity})
        print(f"Query: {query}")
        print(f"  Similarity: {similarity:.4f}\n")

    avg_similarity = np.mean([r["similarity"] for r in results])

    return {"model_name": model_name, "results": results, "avg_similarity": avg_similarity}


def main() -> None:
    """Main comparison script."""
    parser = argparse.ArgumentParser(
        description="Compare two embedding models for semantic similarity"
    )
    parser.add_argument(
        "model1",
        nargs="?",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="First model name (default: all-MiniLM-L6-v2)",
    )
    parser.add_argument(
        "model2",
        nargs="?",
        default="BAAI/bge-small-en-v1.5",
        help="Second model name (default: BAAI/bge-small-en-v1.5)",
    )

    args = parser.parse_args()

    print("EMBEDDING MODEL COMPARISON")
    print("=" * 60)

    # Test both models
    result1 = test_model(args.model1)
    result2 = test_model(args.model2)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"\n{result1['model_name']}")
    print(f"  Average Similarity: {result1['avg_similarity']:.4f}")
    print(f"\n{result2['model_name']}")
    print(f"  Average Similarity: {result2['avg_similarity']:.4f}")

    if result2["avg_similarity"] > result1["avg_similarity"]:
        diff = result2["avg_similarity"] - result1["avg_similarity"]
        print(f"\n✓ {result2['model_name']} is better by {diff:.4f}")
    elif result1["avg_similarity"] > result2["avg_similarity"]:
        diff = result1["avg_similarity"] - result2["avg_similarity"]
        print(f"\n✓ {result1['model_name']} is better by {diff:.4f}")
    else:
        print("\n= Models perform equally")


if __name__ == "__main__":
    main()
