#!/usr/bin/env python3
"""
Test embedding similarity between queries and resume content.
Validates that semantic search should find "AI" when querying "artificial intelligence".
"""

from sentence_transformers import SentenceTransformer
import numpy as np

# Use the same model as ingest
MODEL = "all-mpnet-base-v2"


def cosine_similarity(a, b):
    """Calculate cosine similarity between two vectors."""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def test_embeddings():
    """Test if model understands AI = Artificial Intelligence."""
    print(f"Loading model: {MODEL}")
    model = SentenceTransformer(MODEL)

    # Test cases
    queries = [
        "artificial intelligence",
        "machine learning",
        "AI ML experience",
    ]

    resume_snippets = [
        "AI/ML infrastructure (model serving platforms handling 10M+ inferences/day)",
        "Building AI infrastructure at scale",
        "Go programming for Kubernetes operators",
        "Python for data pipelines and MLOps",
    ]

    print("\n" + "=" * 80)
    print("SIMILARITY MATRIX")
    print("=" * 80)

    # Compute embeddings
    query_embeddings = model.encode(queries)
    snippet_embeddings = model.encode(resume_snippets)

    # Print results
    print(f"\n{'Query':<30} | {'Resume Snippet':<50} | Similarity")
    print("-" * 100)

    for i, query in enumerate(queries):
        for j, snippet in enumerate(resume_snippets):
            sim = cosine_similarity(query_embeddings[i], snippet_embeddings[j])
            marker = " ⭐" if sim > 0.5 else ""
            print(f"{query:<30} | {snippet[:48]:<50} | {sim:.4f}{marker}")
        print()

    print("\n" + "=" * 80)
    print("ANALYSIS")
    print("=" * 80)

    # Test specific case: "artificial intelligence" vs "AI/ML infrastructure"
    ai_query_emb = model.encode(["artificial intelligence"])[0]
    ai_resume_emb = model.encode(["AI/ML infrastructure"])[0]
    sim = cosine_similarity(ai_query_emb, ai_resume_emb)

    print("\nQuery: 'artificial intelligence'")
    print("Resume: 'AI/ML infrastructure'")
    print(f"Similarity: {sim:.4f}")

    if sim > 0.5:
        print("✅ PASS: Semantic search SHOULD find this content!")
    elif sim > 0.3:
        print("⚠️  MARGINAL: Might work depending on threshold")
    else:
        print("❌ FAIL: Model doesn't understand the relationship")

    print("\nRecommended min-relevancy: 0.4 (from memvid stats)")
    print(f"This similarity: {sim:.4f}")
    print(f"Above threshold: {'✅ YES' if sim >= 0.4 else '❌ NO'}")


if __name__ == "__main__":
    test_embeddings()
