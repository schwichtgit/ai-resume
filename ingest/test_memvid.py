#!/usr/bin/env python3
"""
Test script to validate memvid-sdk installation and demonstrate basic usage.

Run with: uv run python test_memvid.py
"""

import os
import tempfile
from pathlib import Path

import memvid_sdk


def test_sdk_info():
    """Print SDK build information."""
    print("=== memvid-sdk Info ===")
    info = memvid_sdk.info()
    for key, value in info.items():
        print(f"  {key}: {value}")
    print()


def test_create_and_query():
    """Test creating a memory file, adding content, and querying it."""
    print("=== Create & Query Test ===")

    # Create a temporary .mv2 file
    with tempfile.TemporaryDirectory() as tmpdir:
        mv2_path = os.path.join(tmpdir, "test.mv2")

        # Create memory
        print(f"Creating memory at: {mv2_path}")
        mem = memvid_sdk.create(mv2_path, kind="basic", enable_lex=True)

        # Add some test content
        test_documents = [
            {
                "title": "Python Experience",
                "text": "I have 10 years of experience with Python, including FastAPI, Django, and data science libraries like pandas and numpy.",
                "tags": ["python", "backend", "data-science"],
            },
            {
                "title": "Rust Experience",
                "text": "I have been learning Rust for 2 years, building high-performance services and CLI tools. I especially enjoy working with tokio for async programming.",
                "tags": ["rust", "systems", "performance"],
            },
            {
                "title": "Cloud Infrastructure",
                "text": "Extensive experience with AWS and GCP, including Kubernetes, Terraform, and CI/CD pipelines. Led migration of legacy systems to cloud-native architecture.",
                "tags": ["cloud", "aws", "kubernetes", "devops"],
            },
        ]

        print("Adding test documents...")
        for doc in test_documents:
            uri = mem.put(
                title=doc["title"],
                text=doc["text"],
                tags=doc["tags"],
            )
            print(f"  Added: {doc['title']} -> {uri}")

        # Close saves changes automatically (no explicit commit needed)
        # Get stats before closing
        print("\nGetting stats before close...")

        # Get stats
        stats = mem.stats()
        print(f"\nStats: {stats}")

        # Test search (find)
        print("\n--- Testing find() ---")
        query = "Python backend"
        result = mem.find(query, k=3)
        print(f"Query: '{query}'")
        print(f"Hits: {len(result.get('hits', []))}")
        for hit in result.get("hits", []):
            print(f"  - {hit.get('title', 'N/A')}: {hit.get('snippet', '')[:80]}...")

        # Test RAG (ask) - requires LLM API key, so we use context_only mode
        print("\n--- Testing ask() with context_only ---")
        question = "What programming languages do they know?"
        try:
            answer = mem.ask(question, k=3, context_only=True)
            print(f"Question: '{question}'")
            print(f"Context sources: {len(answer.get('sources', []))}")
            for src in answer.get("sources", []):
                print(f"  - {src.get('title', 'N/A')}")
        except Exception as e:
            print(f"  ask() failed (may require API key): {e}")

        # Close memory
        mem.close()
        print("\nMemory closed.")

        # Verify file was created
        if os.path.exists(mv2_path):
            size = os.path.getsize(mv2_path)
            print(f"\n.mv2 file created: {size:,} bytes")

    print("\nTest completed successfully!")


def test_open_existing():
    """Test opening an existing .mv2 file (if one exists)."""
    print("\n=== Open Existing Test ===")

    # Check for existing resume.mv2 in data/.memvid/
    project_root = Path(__file__).parent.parent
    mv2_path = project_root / "data" / ".memvid" / "resume.mv2"

    if mv2_path.exists():
        print(f"Found existing memory: {mv2_path}")
        # Use the new API (open() is deprecated)
        mem = memvid_sdk.use("basic", str(mv2_path))
        stats = mem.stats()
        print(f"Stats: {stats}")
        mem.close()
    else:
        print(f"No existing memory found at: {mv2_path}")
        print("Run ingest.py to create one from master_resume.md")


if __name__ == "__main__":
    test_sdk_info()
    test_create_and_query()
    test_open_existing()
