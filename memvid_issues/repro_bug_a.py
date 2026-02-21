#!/usr/bin/env python3
"""
Reproduction script for memvid Bug A (GitHub issue #194).

Bug: After creating an .mv2 file with enable_lex=True and enable_vec=True,
closing it, and re-opening with memvid_sdk.use(), the stats report
lex_enabled=None and vec_enabled=None. Semantic search raises
VecIndexDisabledError (MV011), and hybrid mode silently degrades to
lexical-only.

Versions tested:
    memvid-sdk  2.0.157  (PyPI)
    memvid-core 2.0.137  (bundled inside SDK)
    Python      3.12
    Platform    macOS Darwin 25.3.0

Requirements:
    pip install memvid-sdk==2.0.157
"""
import os
import sys
import tempfile

import memvid_sdk

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
info = memvid_sdk.info()
print("=" * 64)
print("Bug A (#194): vec_enabled/lex_enabled reset to None on re-open")
print("=" * 64)
print()
print(f"  SDK version:  {info.get('sdk_version')}")
print(f"  Core version: {info.get('native', {}).get('memvid_core_version')}")
print(f"  Python:       {sys.version.split()[0]}")
print(f"  Platform:     {sys.platform}")
print()

# ---------------------------------------------------------------------------
# Step 1 -- Create a fresh .mv2 with lex + vec explicitly enabled
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmpdir:
    mv2_path = os.path.join(tmpdir, "bug_a_test.mv2")

    print("--- Step 1: Create .mv2 (enable_lex=True, enable_vec=True) ---")
    mem = memvid_sdk.create(
        mv2_path, kind="basic", enable_lex=True, enable_vec=True
    )
    mem.put(
        title="Python Programming",
        text="Python is a high-level language used for web dev and data science.",
        tags=["lang"],
    )
    mem.put(
        title="Rust Systems",
        text="Rust is a systems language focused on safety, speed, and concurrency.",
        tags=["lang"],
    )
    mem.put(
        title="TypeScript Frontend",
        text="TypeScript adds static typing to JavaScript for large-scale apps.",
        tags=["lang"],
    )

    stats = mem.stats()
    print(f"  frame_count:   {stats.get('frame_count')}")
    print(f"  lex_enabled:   {stats.get('lex_enabled')}")
    print(f"  vec_enabled:   {stats.get('vec_enabled')}")
    print(f"  has_lex_index: {stats.get('has_lex_index')}")
    print(f"  has_vec_index: {stats.get('has_vec_index')}")
    print(f"  file_size:     {os.path.getsize(mv2_path):,} bytes")
    print()
    mem.close()

    # -------------------------------------------------------------------
    # Step 2 -- Re-open the same file
    # -------------------------------------------------------------------
    print("--- Step 2: Re-open with memvid_sdk.use() ---")
    mem2 = memvid_sdk.use("basic", mv2_path)
    stats2 = mem2.stats()
    print(f"  frame_count:   {stats2.get('frame_count')}")
    print(f"  lex_enabled:   {stats2.get('lex_enabled')}")
    print(f"  vec_enabled:   {stats2.get('vec_enabled')}")
    print(f"  has_lex_index: {stats2.get('has_lex_index')}")
    print(f"  has_vec_index: {stats2.get('has_vec_index')}")
    print()

    # -------------------------------------------------------------------
    # Step 3 -- Attempt all three find() modes
    # -------------------------------------------------------------------
    print("--- Step 3: find() in all modes ---")
    for mode in ("lexical", "semantic", "hybrid"):
        try:
            result = mem2.find("Python programming", k=2, mode=mode)
            hits = result.get("hits", [])
            print(f"  find(mode={mode:>8}): {len(hits)} hits")
            for h in hits:
                print(f"    - [{h.get('score', 0):.3f}] {h.get('title', 'N/A')}")
        except Exception as e:
            print(f"  find(mode={mode:>8}): ERROR -- {type(e).__name__}: {e}")
    print()

    # -------------------------------------------------------------------
    # Verdict
    # -------------------------------------------------------------------
    print("--- Verdict ---")
    lex_ok = stats2.get("lex_enabled") is True
    vec_ok = stats2.get("vec_enabled") is True

    if lex_ok and vec_ok:
        print("PASS: lex_enabled and vec_enabled are both True after re-open.")
        print("Bug appears FIXED.")
    else:
        print(
            f"FAIL: lex_enabled={stats2.get('lex_enabled')}, "
            f"vec_enabled={stats2.get('vec_enabled')} after re-open."
        )
        if stats2.get("has_lex_index") or stats2.get("has_vec_index"):
            print(
                "  Index data IS present in the file, but the enabled flags "
                "are not restored on re-open."
            )
        print("Bug #194 is NOT fixed.")

    mem2.close()
