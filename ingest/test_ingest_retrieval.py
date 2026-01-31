#!/usr/bin/env python3
"""
Integration test for ingest → retrieval pipeline.

This test validates that data ingested via ingest.py can be
successfully retrieved from the .mv2 file, catching issues like
search query mismatches that unit tests with mocks miss.
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path

import memvid_sdk


async def test_profile_metadata_retrieval():
    """Test that profile metadata can be retrieved after ingest."""
    print("\n🔍 Test: Profile Metadata Retrieval")

    # Use the example resume as input
    input_file = Path(__file__).parent.parent / "data" / "example_resume.md"

    # Create temporary output file
    with tempfile.NamedTemporaryFile(suffix=".mv2", delete=False) as tmp:
        output_file = tmp.name

    try:
        # Step 1: Run ingest
        print(f"  Ingesting: {input_file}")
        from ingest import main as ingest_main

        # Mock sys.argv for ingest
        import sys
        old_argv = sys.argv
        sys.argv = ["ingest.py", "--input", str(input_file), "--output", output_file, "--quiet"]

        try:
            ingest_main()
        finally:
            sys.argv = old_argv

        print(f"  ✅ Ingest complete: {output_file}")

        # Step 2: Open the .mv2 file
        print("  Opening .mv2 file...")
        memory = memvid_sdk.use("basic", output_file)
        stats = memory.stats()
        print(f"  ✅ Memory loaded: {stats.get('frame_count', 0)} frames")

        # Step 3: Retrieve profile using state() - O(1) memory card lookup
        # Profile is stored as memory card during ingest, not as a frame
        print("  Retrieving profile via state('__profile__')...")
        profile_state = memory.state("__profile__")

        if not profile_state or not profile_state.get("found"):
            print("  ❌ FAILED: Profile memory card not found")
            print("     Make sure ingest.py uses add_memory_cards() for profile storage")
            return False

        print(f"  ✅ Profile memory card found")

        # Step 4: Parse the profile JSON from memory card
        profile_json = profile_state.get("slots", {}).get("data", {}).get("value", "")

        if not profile_json:
            print("  ❌ FAILED: Retrieved result has no text content")
            return False

        try:
            profile = json.loads(profile_json)
        except json.JSONDecodeError as e:
            print(f"  ❌ FAILED: Could not parse profile JSON: {e}")
            print(f"      First 200 chars: {profile_json[:200]}")
            return False

        print("  ✅ Profile JSON parsed successfully")

        # Step 5: Validate required fields
        required_fields = [
            "name", "title", "email", "linkedin", "location", "status",
            "suggested_questions", "tags", "system_prompt",
            "experience", "skills", "fit_assessment_examples"
        ]

        missing = [f for f in required_fields if f not in profile]

        if missing:
            print(f"  ❌ FAILED: Missing required fields: {missing}")
            return False

        print(f"  ✅ All {len(required_fields)} required fields present")

        # Step 6: Validate data content
        print("  Validating profile content...")

        checks = {
            "name": profile.get("name"),
            "experience_count": len(profile.get("experience", [])),
            "fit_examples_count": len(profile.get("fit_assessment_examples", [])),
            "suggested_questions_count": len(profile.get("suggested_questions", [])),
        }

        print(f"    - Name: {checks['name']}")
        print(f"    - Experience entries: {checks['experience_count']}")
        print(f"    - Fit examples: {checks['fit_examples_count']}")
        print(f"    - Suggested questions: {checks['suggested_questions_count']}")

        if not checks["name"]:
            print("  ❌ FAILED: Profile has no name")
            return False

        if checks["experience_count"] == 0:
            print("  ⚠️  WARNING: No experience entries found")

        print("  ✅ Profile content validated")

        # Step 7: Test semantic search
        print("  Testing semantic search...")
        search_result = memory.find("Python programming experience", k=3)
        search_results = search_result.get("hits", [])
        print(f"  ✅ Semantic search returned {len(search_results)} results")

        return True

    finally:
        # Cleanup
        if os.path.exists(output_file):
            os.unlink(output_file)
            print(f"  🧹 Cleaned up: {output_file}")


async def test_experience_retrieval():
    """Test that experience entries can be retrieved."""
    print("\n🔍 Test: Experience Entry Retrieval")

    input_file = Path(__file__).parent.parent / "data" / "example_resume.md"

    with tempfile.NamedTemporaryFile(suffix=".mv2", delete=False) as tmp:
        output_file = tmp.name

    try:
        # Ingest
        import sys
        old_argv = sys.argv
        sys.argv = ["ingest.py", "--input", str(input_file), "--output", output_file, "--quiet"]

        try:
            from ingest import main as ingest_main
            ingest_main()
        finally:
            sys.argv = old_argv

        # Open and search
        memory = memvid_sdk.use("basic", output_file)

        # Search for experience-related content
        result = memory.find("Acme Corp engineering experience", k=5)
        results = result.get("hits", [])

        if not results:
            print("  ❌ FAILED: No experience results found")
            return False

        print(f"  ✅ Found {len(results)} experience-related results")

        # Verify at least one result mentions experience
        has_experience_content = any(
            "experience" in r["text"].lower() or
            "acme" in r["text"].lower()
            for r in results
        )

        if not has_experience_content:
            print("  ❌ FAILED: Results don't contain expected experience content")
            return False

        print("  ✅ Experience content verified in search results")
        return True

    finally:
        if os.path.exists(output_file):
            os.unlink(output_file)


async def test_fit_assessment_examples_retrieval():
    """Test that fit assessment examples can be retrieved."""
    print("\n🔍 Test: Fit Assessment Examples Retrieval")

    input_file = Path(__file__).parent.parent / "data" / "example_resume.md"

    with tempfile.NamedTemporaryFile(suffix=".mv2", delete=False) as tmp:
        output_file = tmp.name

    try:
        # Ingest
        import sys
        old_argv = sys.argv
        sys.argv = ["ingest.py", "--input", str(input_file), "--output", output_file, "--quiet"]

        try:
            from ingest import main as ingest_main
            ingest_main()
        finally:
            sys.argv = old_argv

        # Open and search
        memory = memvid_sdk.use("basic", output_file)

        # Search for fit assessment content
        result = memory.find("fit assessment examples VP Platform Engineering", k=5)
        results = result.get("hits", [])

        if not results:
            print("  ❌ FAILED: No fit assessment results found")
            return False

        print(f"  ✅ Found {len(results)} fit assessment-related results")
        return True

    finally:
        if os.path.exists(output_file):
            os.unlink(output_file)


async def main():
    """Run all ingest-retrieval integration tests."""
    print("=" * 60)
    print("Ingest → Retrieval Integration Tests")
    print("Validates that ingested data can be retrieved from .mv2")
    print("=" * 60)

    tests = [
        ("Profile Metadata Retrieval", test_profile_metadata_retrieval),
        ("Experience Retrieval", test_experience_retrieval),
        ("Fit Assessment Examples Retrieval", test_fit_assessment_examples_retrieval),
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            results[test_name] = await test_func()
        except Exception as e:
            print(f"\n  ❌ EXCEPTION in {test_name}: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = False

    # Summary
    print("\n" + "=" * 60)
    passed = sum(1 for v in results.values() if v)
    total = len(results)

    if passed == total:
        print(f"✅ SUCCESS: All {total} tests passed!")
        print("\nThe ingest → retrieval pipeline is working correctly.")
        print("Data can be successfully ingested and retrieved from .mv2 files.")
    else:
        print(f"❌ FAILED: {total - passed}/{total} tests failed")
        print("\nFailed tests:")
        for name, result in results.items():
            if not result:
                print(f"  - {name}")

    print("=" * 60)

    return 0 if passed == total else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
