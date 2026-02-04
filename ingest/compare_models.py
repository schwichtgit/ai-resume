#!/usr/bin/env python3
"""Compare MPNet vs BGE-small for AI/ML query retrieval."""

from sentence_transformers import SentenceTransformer
import numpy as np

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def test_model(model_name):
    """Test a model's ability to match AI queries with AI content."""
    print(f"\n{'='*80}")
    print(f"Model: {model_name}")
    print(f"{'='*80}")

    model = SentenceTransformer(model_name)

    # Critical test case: full term vs acronym
    query = "artificial intelligence experience"
    content = "AI/ML infrastructure"

    q_emb = model.encode([query])[0]
    c_emb = model.encode([content])[0]

    sim = cosine_similarity(q_emb, c_emb)

    print(f"\nQuery:   '{query}'")
    print(f"Content: '{content}'")
    print(f"Similarity: {sim:.4f}")
    print(f"Status: {'✅ PASS (>0.4)' if sim >= 0.4 else '❌ FAIL (<0.4)'}")

    return sim

if __name__ == "__main__":
    mpnet_score = test_model("all-mpnet-base-v2")
    bge_score = test_model("BAAI/bge-small-en-v1.5")

    print(f"\n{'='*80}")
    print("COMPARISON")
    print(f"{'='*80}")
    print(f"MPNet:     {mpnet_score:.4f}")
    print(f"BGE-small: {bge_score:.4f}")
    print(f"Improvement: {((bge_score - mpnet_score) / mpnet_score * 100):.1f}%")

    if bge_score > mpnet_score:
        print("\n✅ BGE is BETTER for this use case!")
    else:
        print("\n⚠️  MPNet performed better (unexpected)")
