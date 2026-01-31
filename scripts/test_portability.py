#!/usr/bin/env python3
"""
Portability Test - Validates data-driven architecture

This script tests that the AI Resume system can work with ONLY the .mv2 file,
without needing profile.json or any hardcoded data.

Tests:
1. .mv2 file exists and can be loaded
2. Profile metadata can be extracted from memvid
3. Required profile fields are present (name, title, email, etc.)
4. Experience entries are present and properly structured
5. Skills data is present (strong, moderate, gaps)
6. Fit assessment examples are present
7. Suggested questions are present
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_memvid_loading():
    """Test that .mv2 file can be loaded."""
    print("\n🔍 Test 1: Loading .mv2 file...")

    try:
        # Import dynamically to handle path issues
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "memvid_client",
            Path(__file__).parent.parent / "api-service" / "ai_resume_api" / "memvid_client.py"
        )
        memvid_client = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(memvid_client)

        client = await memvid_client.get_memvid_client()
        health = await client.health_check()

        assert health.status == "SERVING", f"Memvid not serving: {health.status}"
        assert health.frame_count > 0, f"No frames loaded: {health.frame_count}"

        print(f"✅ Memvid loaded: {health.frame_count} frames")
        return True
    except Exception as e:
        print(f"❌ Failed to load memvid: {e}")
        return False


async def test_profile_extraction():
    """Test that profile can be extracted from memvid."""
    print("\n🔍 Test 2: Extracting profile from memvid...")

    try:
        # Import dynamically to handle path issues
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "config",
            Path(__file__).parent.parent / "api-service" / "ai_resume_api" / "config.py"
        )
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)

        settings = config_module.get_settings()
        profile = await settings.load_profile_from_memvid()

        assert profile is not None, "Profile not found in memvid"
        print(f"✅ Profile extracted: {len(json.dumps(profile))} bytes")
        return profile
    except Exception as e:
        print(f"❌ Failed to extract profile: {e}")
        return None


def test_profile_structure(profile: dict):
    """Test that profile has required fields."""
    print("\n🔍 Test 3: Validating profile structure...")

    required_fields = [
        "name",
        "title",
        "email",
        "linkedin",
        "location",
        "status",
        "suggested_questions",
        "tags",
        "system_prompt",
        "experience",
        "skills",
        "fit_assessment_examples",
    ]

    missing_fields = [field for field in required_fields if field not in profile]

    if missing_fields:
        print(f"❌ Missing fields: {missing_fields}")
        return False

    print(f"✅ All required fields present: {len(required_fields)} fields")
    return True


def test_profile_content(profile: dict):
    """Test that profile has actual content (not empty)."""
    print("\n🔍 Test 4: Validating profile content...")

    checks = {
        "name": profile.get("name"),
        "title": profile.get("title"),
        "email": profile.get("email"),
        "suggested_questions": len(profile.get("suggested_questions", [])),
        "tags": len(profile.get("tags", [])),
        "experience_entries": len(profile.get("experience", [])),
        "system_prompt_length": len(profile.get("system_prompt", "")),
    }

    failed = []
    for key, value in checks.items():
        if not value or (isinstance(value, (int, list)) and value == 0):
            failed.append(key)

    if failed:
        print(f"❌ Empty fields: {failed}")
        return False

    print("✅ Profile content valid:")
    for key, value in checks.items():
        print(f"   - {key}: {value}")

    return True


def test_experience_structure(profile: dict):
    """Test that experience entries have required structure."""
    print("\n🔍 Test 5: Validating experience entries...")

    experience = profile.get("experience", [])

    if not experience:
        print("❌ No experience entries found")
        return False

    required_experience_fields = [
        "company",
        "role",
        "period",
        "location",
        "tags",
        "highlights",
        "ai_context",
    ]

    for i, exp in enumerate(experience):
        missing = [field for field in required_experience_fields if field not in exp]
        if missing:
            print(f"❌ Experience {i} missing fields: {missing}")
            return False

        # Check ai_context structure
        ai_context = exp.get("ai_context", {})
        required_ai_fields = ["situation", "approach", "technical_work", "lessons_learned"]
        missing_ai = [field for field in required_ai_fields if field not in ai_context]
        if missing_ai:
            print(f"❌ Experience {i} ai_context missing fields: {missing_ai}")
            return False

    print(f"✅ {len(experience)} experience entries validated")
    return True


def test_skills_structure(profile: dict):
    """Test that skills data has required structure."""
    print("\n🔍 Test 6: Validating skills data...")

    skills = profile.get("skills", {})
    required_skill_categories = ["strong", "moderate", "gaps"]

    for category in required_skill_categories:
        if category not in skills:
            print(f"❌ Missing skills category: {category}")
            return False

        if not isinstance(skills[category], list):
            print(f"❌ Skills {category} is not a list")
            return False

    total_skills = sum(len(skills[cat]) for cat in required_skill_categories)
    print(f"✅ Skills validated: {total_skills} total skills")
    print(f"   - Strong: {len(skills['strong'])}")
    print(f"   - Moderate: {len(skills['moderate'])}")
    print(f"   - Gaps: {len(skills['gaps'])}")

    return True


def test_fit_assessment_examples(profile: dict):
    """Test that fit assessment examples are present and structured correctly."""
    print("\n🔍 Test 7: Validating fit assessment examples...")

    examples = profile.get("fit_assessment_examples", [])

    if not examples:
        print("⚠️  No fit assessment examples found (optional but recommended)")
        return True  # Not required, just recommended

    required_example_fields = [
        "title",
        "fit_level",
        "role",
        "job_description",
        "verdict",
        "key_matches",
        "gaps",
        "recommendation",
    ]

    for i, example in enumerate(examples):
        missing = [field for field in required_example_fields if field not in example]
        if missing:
            print(f"❌ Example {i} missing fields: {missing}")
            return False

    print(f"✅ {len(examples)} fit assessment examples validated")
    return True


async def main():
    """Run all portability tests."""
    print("="* 60)
    print("AI Resume Portability Test")
    print("Testing data-driven architecture (Phase 4 validation)")
    print("=" * 60)

    # Test 1: Load memvid
    if not await test_memvid_loading():
        print("\n❌ FAILED: Cannot load .mv2 file")
        sys.exit(1)

    # Test 2: Extract profile
    profile = await test_profile_extraction()
    if not profile:
        print("\n❌ FAILED: Cannot extract profile from memvid")
        sys.exit(1)

    # Test 3-7: Validate profile structure and content
    tests = [
        ("Profile structure", test_profile_structure, profile),
        ("Profile content", test_profile_content, profile),
        ("Experience entries", test_experience_structure, profile),
        ("Skills data", test_skills_structure, profile),
        ("Fit assessment examples", test_fit_assessment_examples, profile),
    ]

    failed_tests = []
    for test_name, test_func, *args in tests:
        if not test_func(*args):
            failed_tests.append(test_name)

    # Summary
    print("\n" + "=" * 60)
    if failed_tests:
        print(f"❌ FAILED: {len(failed_tests)} tests failed:")
        for test in failed_tests:
            print(f"   - {test}")
        print("=" * 60)
        sys.exit(1)
    else:
        print("✅ SUCCESS: All portability tests passed!")
        print("\nThe system is fully data-driven and portable.")
        print("Only the .mv2 file is needed for deployment.")
        print("=" * 60)
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
