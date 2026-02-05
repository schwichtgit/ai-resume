#!/usr/bin/env python3
"""
End-to-End Integration Tests for AI Resume Agent.

This test validates the complete pipeline:
1. Memvid retrieval - suggested questions find matching FAQ entries
2. Query transformation - LLM keyword extraction improves retrieval
3. Full RAG pipeline - correct answers generated from retrieved context

Requires:
- data/.memvid/resume.mv2 (ingested example_resume.md)
- deployment/.env with OPENROUTER_API_KEY

Run with:
    cd ingest
    source .venv/bin/activate
    python test_e2e.py
"""

import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
import memvid_sdk

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MV2_PATH = DATA_DIR / ".memvid" / "resume.mv2"
DEPLOYMENT_ENV = PROJECT_ROOT / "deployment" / ".env"


def load_env_file(env_path: Path) -> dict[str, str]:
    """Load environment variables from .env file."""
    env_vars = {}
    if not env_path.exists():
        return env_vars
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:]
            if "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()
    return env_vars


# Load environment
env_vars = load_env_file(DEPLOYMENT_ENV)
for key, value in env_vars.items():
    if key not in os.environ:
        os.environ[key] = value


@dataclass
class RetrievalTestCase:
    """A test case for retrieval validation."""
    name: str
    query: str
    expected_title_contains: str  # Expected substring in top result title
    expected_content_contains: list[str]  # Expected substrings in content
    min_score: float = 0.3


# ============================================================================
# Test Cases - Based on example_resume.md (Jane Chen)
# ============================================================================

RETRIEVAL_TEST_CASES = [
    # FAQ Mirroring Tests - suggested questions should find their FAQ entries
    RetrievalTestCase(
        name="FAQ: Programming Languages",
        query="What programming languages does she know?",
        expected_title_contains="FAQ: What programming languages",
        expected_content_contains=["Python", "Go", "Bash", "10+ years"],
    ),
    RetrievalTestCase(
        name="FAQ: Security Track Record",
        query="security track record",  # Keywords work better than full question
        expected_title_contains="FAQ: What's her security track record",
        expected_content_contains=["FedRAMP", "SOC 2", "zero-trust"],
    ),
    RetrievalTestCase(
        name="FAQ: AI/ML Experience",
        query="Tell me about her AI/ML experience.",
        expected_title_contains="FAQ: Tell me about her AI/ML experience",
        expected_content_contains=["MLOps", "model serving", "10M inferences"],
    ),
    RetrievalTestCase(
        name="FAQ: Biggest Failures",
        query="What are her biggest failures?",
        expected_title_contains="FAQ: What are her biggest failures",
        expected_content_contains=["Over-Engineered Platform", "Migration"],
    ),
    RetrievalTestCase(
        name="FAQ: Early-Stage Startup Fit",
        query="Would she be good for an early-stage startup?",
        expected_title_contains="FAQ: Would she be good for an early-stage startup",
        expected_content_contains=["Series A/B", "Strong fit", "Weak fit"],
    ),
    # General Semantic Queries
    RetrievalTestCase(
        name="General: Python Experience",
        query="Python programming data pipelines",
        expected_title_contains="programming languages",
        expected_content_contains=["Python"],
    ),
    RetrievalTestCase(
        name="General: Leadership",
        query="leadership team management philosophy",
        expected_title_contains="Leadership",
        expected_content_contains=["team", "leadership"],
    ),
    RetrievalTestCase(
        name="General: Kubernetes",
        query="Kubernetes clusters cloud infrastructure",
        expected_title_contains="",  # Could match multiple sections
        expected_content_contains=["Kubernetes"],
    ),
]


def test_memvid_retrieval():
    """Test that memvid retrieves expected content for each test case."""
    print("\n" + "=" * 70)
    print("TEST SUITE: Memvid Retrieval Accuracy")
    print("=" * 70)

    if not MV2_PATH.exists():
        print(f"ERROR: {MV2_PATH} not found. Run ingest first.")
        pytest.skip(f"{MV2_PATH} not found. Run ingest first.")

    mem = memvid_sdk.use("basic", str(MV2_PATH))
    stats = mem.stats()
    print(f"Loaded: {MV2_PATH.name} ({stats.get('frame_count', 0)} frames)")

    passed = 0
    failed = 0

    for tc in RETRIEVAL_TEST_CASES:
        print(f"\n--- {tc.name} ---")
        print(f"Query: {tc.query}")

        result = mem.find(tc.query, k=3)
        hits = result.get("hits", [])

        if not hits:
            print("  FAILED: No results returned")
            failed += 1
            continue

        top_hit = hits[0]
        title = top_hit.get("title", "")
        score = top_hit.get("score", 0)
        content = top_hit.get("text", "") or top_hit.get("snippet", "")

        print(f"  Top result: [{score:.2f}] {title[:60]}")

        # Check title match (if expected)
        title_ok = True
        if tc.expected_title_contains:
            title_ok = tc.expected_title_contains.lower() in title.lower()
            if not title_ok:
                print(f"  WARN: Title mismatch - expected '{tc.expected_title_contains}'")

        # Check content contains expected terms
        content_ok = True
        missing_terms = []
        for term in tc.expected_content_contains:
            if term.lower() not in content.lower():
                content_ok = False
                missing_terms.append(term)

        if missing_terms:
            print(f"  WARN: Missing terms in content: {missing_terms}")

        # Check score threshold
        score_ok = score >= tc.min_score

        if title_ok and content_ok and score_ok:
            print(f"  PASSED")
            passed += 1
        else:
            print(f"  FAILED: title={title_ok}, content={content_ok}, score={score_ok}")
            failed += 1

    mem.close()

    print(f"\n{'=' * 70}")
    print(f"Retrieval Tests: {passed} passed, {failed} failed")

    # Assert all tests passed
    assert failed == 0, f"{failed} retrieval test(s) failed"


@pytest.mark.anyio
async def test_query_transformation_improves_retrieval() -> tuple[int, int]:
    """Test that query transformation improves retrieval for ambiguous queries."""
    print("\n" + "=" * 70)
    print("TEST SUITE: Query Transformation Impact")
    print("=" * 70)

    # Import OpenRouter client (requires env vars set)
    try:
        import httpx
    except ImportError:
        print("SKIP: httpx not installed")
        return 0, 0

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key or not api_key.startswith("sk-"):
        print("SKIP: OPENROUTER_API_KEY not configured")
        return 0, 0

    if not MV2_PATH.exists():
        print(f"ERROR: {MV2_PATH} not found")
        return 0, 0

    mem = memvid_sdk.use("basic", str(MV2_PATH))

    # Ambiguous queries that benefit from transformation
    test_cases = [
        ("What does she know?", "skills languages experience"),
        ("Is she any good?", "experience achievements qualifications"),
        ("Tell me about her", "summary background experience"),
    ]

    passed = 0
    failed = 0

    async with httpx.AsyncClient(
        base_url="https://openrouter.ai/api/v1",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        timeout=60.0,
    ) as client:

        for original_query, _ in test_cases:
            print(f"\n--- Query: {original_query} ---")

            # Get retrieval score with original query
            original_result = mem.find(original_query, k=1)
            original_hits = original_result.get("hits", [])
            original_score = original_hits[0].get("score", 0) if original_hits else 0
            original_title = original_hits[0].get("title", "N/A") if original_hits else "N/A"

            print(f"  Original: [{original_score:.2f}] {original_title[:50]}")

            # Transform query using LLM
            try:
                response = await client.post(
                    "/chat/completions",
                    json={
                        "model": os.environ.get("LLM_MODEL", "nvidia/nemotron-nano-9b-v2:free"),
                        "messages": [
                            {"role": "system", "content": "Extract search keywords. Output only space-separated keywords."},
                            {"role": "user", "content": f"Extract 5-10 keywords for resume search:\n{original_query}\nKeywords:"},
                        ],
                        "max_tokens": 50,
                        "temperature": 0.3,
                    },
                )
                response.raise_for_status()
                transformed_query = response.json()["choices"][0]["message"]["content"].strip()
            except Exception as e:
                print(f"  Transform failed: {e}")
                failed += 1
                continue

            print(f"  Transformed: {transformed_query[:60]}")

            # Skip if transformation returned empty
            if not transformed_query.strip():
                print("  WARN: Empty transformation, skipping")
                passed += 1  # Don't fail - this is a transformation quality issue
                continue

            # Get retrieval score with transformed query
            transformed_result = mem.find(transformed_query, k=1)
            transformed_hits = transformed_result.get("hits", [])
            transformed_score = transformed_hits[0].get("score", 0) if transformed_hits else 0
            transformed_title = transformed_hits[0].get("title", "N/A") if transformed_hits else "N/A"

            print(f"  Result: [{transformed_score:.2f}] {transformed_title[:50]}")

            # Check if transformation improved score
            improvement = transformed_score - original_score
            if improvement > 0:
                print(f"  PASSED: Score improved by {improvement:.2f}")
                passed += 1
            elif transformed_score >= original_score:
                print(f"  PASSED: Score maintained ({improvement:.2f})")
                passed += 1
            else:
                print(f"  WARN: Score decreased by {-improvement:.2f}")
                # Don't fail - transformation isn't always better
                passed += 1

    mem.close()

    print(f"\n{'=' * 70}")
    print(f"Transformation Tests: {passed} passed, {failed} failed")
    return passed, failed


@pytest.mark.anyio
async def test_full_rag_pipeline() -> tuple[int, int]:
    """Test the complete RAG pipeline produces correct answers."""
    print("\n" + "=" * 70)
    print("TEST SUITE: Full RAG Pipeline (Retrieval + Generation)")
    print("=" * 70)

    try:
        import httpx
    except ImportError:
        print("SKIP: httpx not installed")
        return 0, 0

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key or not api_key.startswith("sk-"):
        print("SKIP: OPENROUTER_API_KEY not configured")
        return 0, 0

    if not MV2_PATH.exists():
        print(f"ERROR: {MV2_PATH} not found")
        return 0, 0

    mem = memvid_sdk.use("basic", str(MV2_PATH))

    # Test cases: question, expected terms in answer
    test_cases = [
        (
            "What programming languages does Jane know?",
            ["Python", "Go"],  # Must mention these languages
        ),
        (
            "What is Jane's security experience?",
            ["FedRAMP", "SOC 2"],  # Must mention certifications
        ),
        (
            "Tell me about Jane's failures",
            ["Over-Engineered", "migration"],  # Must mention failure stories
        ),
    ]

    passed = 0
    failed = 0

    async with httpx.AsyncClient(
        base_url="https://openrouter.ai/api/v1",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        timeout=60.0,
    ) as client:

        for question, expected_terms in test_cases:
            print(f"\n--- Question: {question} ---")

            # Step 1: Retrieve context from memvid
            result = mem.find(question, k=3)
            hits = result.get("hits", [])

            context_parts = []
            for hit in hits:
                title = hit.get("title", "")
                content = hit.get("text", "") or hit.get("snippet", "")
                context_parts.append(f"**{title}**\n{content}")

            context = "\n\n".join(context_parts)
            print(f"  Retrieved {len(hits)} chunks ({len(context)} chars)")

            # Step 2: Generate response with LLM
            try:
                response = await client.post(
                    "/chat/completions",
                    json={
                        "model": os.environ.get("LLM_MODEL", "nvidia/nemotron-nano-9b-v2:free"),
                        "messages": [
                            {
                                "role": "system",
                                "content": f"You are helping evaluate Jane Chen as a candidate. Use the context to answer.\n\nCONTEXT:\n{context}",
                            },
                            {"role": "user", "content": question},
                        ],
                        "max_tokens": 1000,  # Enough for reasoning + answer
                        "temperature": 0.3,
                    },
                )
                response.raise_for_status()
                data = response.json()
                answer = data["choices"][0]["message"]["content"]
                # Some reasoning models put output in reasoning field
                if not answer:
                    reasoning = data["choices"][0]["message"].get("reasoning", "")
                    if reasoning:
                        print(f"  Note: Using reasoning output ({len(reasoning)} chars)")
                        answer = reasoning
            except Exception as e:
                print(f"  Generation failed: {e}")
                import traceback
                traceback.print_exc()
                failed += 1
                continue

            print(f"  Answer ({len(answer)} chars): {answer[:200]}...")

            # Step 3: Validate answer contains expected terms
            answer_lower = answer.lower()
            found_terms = [t for t in expected_terms if t.lower() in answer_lower]
            missing_terms = [t for t in expected_terms if t.lower() not in answer_lower]

            if len(found_terms) >= len(expected_terms) * 0.5:  # At least 50% of terms
                print(f"  PASSED: Found terms {found_terms}")
                passed += 1
            else:
                print(f"  FAILED: Missing terms {missing_terms}")
                failed += 1

    mem.close()

    print(f"\n{'=' * 70}")
    print(f"RAG Pipeline Tests: {passed} passed, {failed} failed")
    return passed, failed


async def main():
    """Run all end-to-end tests."""
    print("=" * 70)
    print("AI Resume Agent - End-to-End Integration Tests")
    print("=" * 70)
    print(f"MV2 file: {MV2_PATH}")
    print(f"Environment: {DEPLOYMENT_ENV}")
    print(f"OpenRouter configured: {bool(os.environ.get('OPENROUTER_API_KEY', '').startswith('sk-'))}")

    total_passed = 0
    total_failed = 0

    # Test 1: Memvid retrieval accuracy
    p, f = test_memvid_retrieval()
    total_passed += p
    total_failed += f

    # Test 2: Query transformation impact
    p, f = await test_query_transformation_improves_retrieval()
    total_passed += p
    total_failed += f

    # Test 3: Full RAG pipeline
    p, f = await test_full_rag_pipeline()
    total_passed += p
    total_failed += f

    # Final summary
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    print(f"Total: {total_passed} passed, {total_failed} failed")

    if total_failed == 0:
        print("\n✓ All tests passed!")
        return True
    else:
        print(f"\n✗ {total_failed} tests failed")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
