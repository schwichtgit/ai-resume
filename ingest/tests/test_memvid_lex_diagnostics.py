#!/usr/bin/env python3
"""
Memvid Lexical Index Diagnostics

Tests memvid-sdk for lexical (BM25) and vector (semantic) index functionality.
Used to investigate index disabled issue on macOS.

Run with:
    source ingest/.venv/bin/activate
    python ingest/test_memvid_lex_diagnostics.py
"""

import json
import sys
from pathlib import Path

import pytest
import memvid_sdk


@pytest.mark.slow
def test_index_status(isolated_mv2: str) -> None:
    """Check if indexes are enabled/disabled in the .mv2 file."""
    print("=" * 70)
    print("MEMVID LEX INDEX DIAGNOSTICS")
    print("=" * 70)
    print()

    mv2_path = Path(isolated_mv2)
    print(f"📁 Testing: {mv2_path}")
    print(f"📊 Size: {mv2_path.stat().st_size:,} bytes")
    print()

    mem = memvid_sdk.use("basic", isolated_mv2)
    stats = mem.stats()

    # Index Status Report
    print("INDEX STATUS REPORT")
    print("-" * 70)

    lex_storage = stats.get("has_lex_index", False)
    lex_enabled = stats.get("lex_enabled", False)
    lex_bytes = stats.get("lex_index_bytes", 0)

    vec_storage = stats.get("has_vec_index", False)
    vec_enabled = stats.get("vec_enabled", False)
    vec_bytes = stats.get("vec_index_bytes", 0)

    print("\n📑 LEXICAL INDEX (BM25)")
    print(f"   Storage present: {'✓ YES' if lex_storage else '✗ NO'} ({lex_bytes:,} bytes)")
    print(f"   Enabled at runtime: {'✓ YES' if lex_enabled else '✗ NO'}")
    print(f"   Status: {'🟢 OK' if lex_storage and lex_enabled else '🔴 BROKEN'}")

    print("\n📊 VECTOR INDEX (Semantic)")
    print(f"   Storage present: {'✓ YES' if vec_storage else '✗ NO'} ({vec_bytes:,} bytes)")
    print(f"   Enabled at runtime: {'✓ YES' if vec_enabled else '✗ NO'}")
    print(f"   Status: {'🟢 OK' if vec_storage and vec_enabled else '🔴 BROKEN'}")

    # Frame Count
    frame_count = stats.get("frame_count", 0)
    print(f"\n📄 FRAMES: {frame_count}")

    # Embedding Model
    embed_info = stats.get("embedding_identity_summary", {})
    if embed_info:
        identity = embed_info.get("identity", {})
        print("\n🔧 EMBEDDING MODEL")
        print(f"   Provider: {identity.get('provider', 'N/A')}")
        print(f"   Model: {identity.get('model', 'N/A')}")
        print(f"   Dimension: {identity.get('dimension', 'N/A')}")

    print()
    print("=" * 70)
    print("QUERY TESTS")
    print("=" * 70)

    # Test Query Results (reuse same instance)
    test_queries = [
        ("What cloud platforms has she used?", "semantic"),
        ("Python Go Rust", "lexical"),
        ("leadership team building", "hybrid"),
    ]

    query_results = []
    for query, mode in test_queries:
        print(f"\n🔍 Query: '{query}' ({mode})")
        try:
            result = mem.find(query, k=3, mode=mode)
            hits = result.get("hits", [])
            print(f"   ✓ Success: {len(hits)} hits")
            query_results.append(True)
            if hits:
                for i, hit in enumerate(hits[:2], 1):
                    print(f"     {i}. [{hit.get('score', 0):.3f}] {hit.get('title', 'N/A')}")
        except Exception as e:
            print(f"   ✗ Failed: {type(e).__name__}: {str(e)[:60]}")
            query_results.append(False)

    # Close the first instance before opening another
    mem.close()

    # Profile State Test
    print("\n" + "=" * 70)
    print("PROFILE STATE TEST (O(1) LOOKUP)")
    print("=" * 70)
    mem = memvid_sdk.use("basic", isolated_mv2)
    profile_found = False
    try:
        state = mem.state("__profile__")
        if state and state.get("found"):
            print("\n✓ Profile state found")
            slots = state.get("slots", {})
            if "data" in slots:
                profile_json = slots["data"].get("value")
                profile = json.loads(profile_json)
                print(f"   Name: {profile.get('name', 'N/A')}")
                print(f"   Title: {profile.get('title', 'N/A')}")
                print(f"   Email: {profile.get('email', 'N/A')}")
                profile_found = True
        else:
            print("✗ Profile state NOT found")
    except Exception as e:
        print(f"✗ Error retrieving profile: {e}")
    finally:
        mem.close()

    # Summary
    print()
    print("=" * 70)
    print("DIAGNOSIS")
    print("=" * 70)

    if lex_storage and not lex_enabled:
        print("\n⚠️  CRITICAL ISSUE:")
        print("    Lexical index DATA exists but is DISABLED at runtime")
        print("    This is the SDK/Core serialization compatibility issue")
        print()
        print("    Workaround: Use O(1) profile state lookup (works fine)")
        print("    Fix: Upgrade to memvid-sdk v2.0.136+ when released")

    if vec_storage and not vec_enabled:
        print("\n⚠️  VECTOR INDEX DISABLED")
        print("    Vector index DATA exists but is DISABLED at runtime")

    if lex_storage and lex_enabled and vec_storage and vec_enabled:
        print("\n✓ All indexes functioning correctly")

    # Assert that profile lookup works (critical functionality)
    # Note: Query failures due to disabled indexes are documented issues, not test failures
    assert profile_found, "Profile state lookup failed"

    # Optionally verify at least some queries work (lexical should work even if vector doesn't)
    at_least_one_query_worked = any(query_results)
    if not at_least_one_query_worked:
        pytest.fail("All query modes failed, expected at least lexical to work")


if __name__ == "__main__":
    test_index_status(str(Path(__file__).parent.parent.parent / "data/.memvid/resume.mv2"))
    sys.exit(0)
