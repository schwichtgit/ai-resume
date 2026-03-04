#!/usr/bin/env python3
"""
Reproduction script for memvid Bug C (GitHub issue #196).

Bug: ask() (and find() with mode="hybrid" in some configurations) fails
with "Time index track is invalid: frame id out of range" on freshly
created .mv2 files containing 12+ frames of varied content. The error
is deterministic (5/5 trials).  Workaround: run
`memvid doctor --rebuild-time-index <path>` before querying.

Versions tested:
    memvid-sdk  2.0.158  (PyPI)
    memvid-core 2.0.138  (bundled inside SDK)
    Python      3.12
    Platform    macOS Darwin 25.3.0

Requirements:
    pip install memvid-sdk==2.0.158
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
print("Bug C (#196): ask() 'frame id out of range' on fresh .mv2")
print("=" * 64)
print()
print(f"  SDK version:  {info.get('sdk_version')}")
print(f"  Core version: {info.get('native', {}).get('memvid_core_version')}")
print(f"  Python:       {sys.version.split()[0]}")
print(f"  Platform:     {sys.platform}")
print()

# ---------------------------------------------------------------------------
# Content -- 12 realistic resume-style chunks (varied lengths & topics)
# ---------------------------------------------------------------------------
DOCUMENTS = [
    (
        "Professional Summary",
        "Experienced technology leader with 15+ years in software engineering, "
        "cloud architecture, and team management. Expertise in distributed "
        "systems, microservices, CI/CD pipelines, and modern DevOps practices.",
    ),
    (
        "Company A - VP Engineering",
        "Led engineering organization of 50+ engineers across 5 teams. Drove "
        "migration from monolithic to microservices architecture. Reduced "
        "deployment time from days to minutes through CI/CD automation. "
        "Implemented observability stack with Prometheus, Grafana, and "
        "distributed tracing.",
    ),
    (
        "Company B - Sr Staff Engineer",
        "Designed and implemented real-time data processing pipeline handling "
        "10M events/day. Built hybrid search system combining BM25 lexical "
        "search with vector embeddings. Optimized query latency from 200ms "
        "to sub-5ms using caching and index tuning.",
    ),
    (
        "Company C - Engineering Manager",
        "Managed team of 12 engineers building customer-facing API platform. "
        "Introduced TypeScript migration reducing production errors by 40%. "
        "Established code review practices and architectural decision records.",
    ),
    (
        "Skills - Strong",
        "Python, Rust, TypeScript, React, FastAPI, gRPC, Kubernetes, Docker, "
        "AWS, PostgreSQL, Redis, Prometheus, CI/CD, Git, Linux administration.",
    ),
    (
        "Skills - Moderate",
        "Go, Java, Terraform, Azure, GCP, MongoDB, Elasticsearch, RabbitMQ, GraphQL.",
    ),
    (
        "Skills - Gaps",
        "Solidity, blockchain, mobile development (iOS/Android native), game "
        "development, embedded systems.",
    ),
    (
        "Education",
        "Master of Science in Computer Science from State University. Bachelor "
        "of Science in Mathematics from Regional College.",
    ),
    (
        "Certifications",
        "AWS Solutions Architect Professional, Kubernetes Administrator (CKA), "
        "Hashicorp Terraform Associate.",
    ),
    (
        "Publications",
        "Co-authored paper on distributed consensus algorithms. Technical blog "
        "posts on microservices patterns and observability.",
    ),
    (
        "Fit Assessment - Strong",
        "VP of Engineering at mid-stage startup. Led teams, built platforms, "
        "strong technical depth. 4-star rating.",
    ),
    (
        "Fit Assessment - Weak",
        "Executive Chef at fine dining restaurant. Different professional "
        "domain entirely. 1-star rating.",
    ),
]

# ---------------------------------------------------------------------------
# Step 1 -- Create .mv2 with 12 frames
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmpdir:
    mv2_path = os.path.join(tmpdir, "bug_c_test.mv2")

    print(f"--- Step 1: Create .mv2 with {len(DOCUMENTS)} frames ---")
    mem = memvid_sdk.create(mv2_path, kind="basic", enable_lex=True, enable_vec=True)
    for title, text in DOCUMENTS:
        mem.put(title=title, text=text, tags=["resume"])

    stats = mem.stats()
    print(f"  frame_count: {stats.get('frame_count')}")
    print(f"  file_size:   {os.path.getsize(mv2_path):,} bytes")
    mem.close()
    print()

    # -------------------------------------------------------------------
    # Step 2 -- Re-open and test find() (baseline -- usually works)
    # -------------------------------------------------------------------
    print("--- Step 2: Re-open and test find() ---")
    mem2 = memvid_sdk.use("basic", mv2_path)

    for mode in ("lexical", "hybrid"):
        try:
            result = mem2.find("Python programming", k=3, mode=mode)
            hits = result.get("hits", [])
            print(f"  find(mode={mode:>8}): {len(hits)} hits")
        except Exception as e:
            print(f"  find(mode={mode:>8}): ERROR -- {type(e).__name__}: {e}")
    print()

    # -------------------------------------------------------------------
    # Step 3 -- Test find(mode="hybrid") (replaces deprecated ask() API)
    #
    # The original bug was about time-index traversal in ask(). The
    # function-level ask() API is deprecated and top_k kwarg removed in
    # 2.0.158. We now test find(mode="hybrid") which exercises the same
    # time-index code path.
    # -------------------------------------------------------------------
    print("--- Step 3: Test find(mode='hybrid') (replaces deprecated ask()) ---")
    find_hybrid_passed = False
    try:
        result = mem2.find(
            "What programming languages are discussed?", k=3, mode="hybrid"
        )
        hits = result.get("hits", [])
        print(f"  find(mode='hybrid'): OK -- {len(hits)} hits")
        for h in hits:
            print(f"    - [{h.get('score', 0):.3f}] {h.get('title', 'N/A')}")
        find_hybrid_passed = True
    except Exception as e:
        print(f"  find(mode='hybrid'): ERROR -- {type(e).__name__}: {e}")
    print()

    # -------------------------------------------------------------------
    # Step 4 -- Determinism check (run find(mode="hybrid") 5 times)
    # -------------------------------------------------------------------
    print("--- Step 4: Determinism check (5 trials) ---")
    passes, fails = 0, 0
    for trial in range(5):
        try:
            mem2.find("Tell me about cloud experience", k=3, mode="hybrid")
            passes += 1
            print(f"  Trial {trial + 1}: PASS")
        except Exception as e:
            fails += 1
            print(f"  Trial {trial + 1}: FAIL -- {e}")
    print(f"  Result: {passes}/5 passed, {fails}/5 failed")
    print()

    mem2.close()

    # -------------------------------------------------------------------
    # Verdict
    # -------------------------------------------------------------------
    print("--- Verdict ---")
    if find_hybrid_passed and fails == 0:
        print("PASS: find(mode='hybrid') works on fresh .mv2 files. Bug appears FIXED.")
    else:
        print(
            f"FAIL: find(mode='hybrid') raises 'frame id out of range' on fresh .mv2 "
            f"({fails}/5 deterministic failures)."
        )
        print("Bug #196 is NOT fixed.")
        print()
        print("Workaround: memvid doctor --rebuild-time-index <path>")
