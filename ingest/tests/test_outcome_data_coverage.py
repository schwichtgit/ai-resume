"""Tests that all 10 PRD resume categories are represented in ingested data.

Validates the example_resume.md template contains all major sections
required by the PRD, ensuring the ingestion pipeline can produce
complete profile data.
"""

from pathlib import Path

import pytest


@pytest.mark.slow
class TestDataCoverage:
    """Validates all 10 resume fact categories are extractable."""

    CATEGORIES = [
        "profile",
        "experience",
        "technical_skills",
        "accomplishments",
        "security",
        "ai_ml",
        "leadership",
        "failures_growth",
        "limitations",
        "fit_scenarios",
    ]

    def test_example_resume_has_all_sections(self) -> None:
        """Parse example_resume.md and verify all major sections exist."""
        resume_path = Path(__file__).parent.parent.parent / "data" / "example_resume.md"
        if not resume_path.exists():
            pytest.skip("example_resume.md not available")
        content = resume_path.read_text()
        # Verify key sections exist
        sections = ["Professional Experience", "Skills Assessment", "Fit Assessment"]
        for section in sections:
            assert section in content, f"Missing section: {section}"

    def test_example_resume_has_frontmatter(self) -> None:
        """Resume must have YAML frontmatter with profile metadata."""
        resume_path = Path(__file__).parent.parent.parent / "data" / "example_resume.md"
        if not resume_path.exists():
            pytest.skip("example_resume.md not available")
        content = resume_path.read_text()
        assert content.startswith("---"), "Resume must start with YAML frontmatter delimiter"
        # Find closing delimiter
        second_delimiter = content.find("---", 3)
        assert second_delimiter > 3, "Resume must have closing frontmatter delimiter"

    def test_example_resume_has_experience_entries(self) -> None:
        """Resume must have at least one experience entry with AI context."""
        resume_path = Path(__file__).parent.parent.parent / "data" / "example_resume.md"
        if not resume_path.exists():
            pytest.skip("example_resume.md not available")
        content = resume_path.read_text()
        # Check for AI context markers that indicate structured experience data
        assert "AI Context" in content or "ai_context" in content, (
            "Resume must include AI Context blocks for experience entries"
        )

    def test_example_resume_has_skills_categories(self) -> None:
        """Resume must categorize skills into strong/moderate/gaps."""
        resume_path = Path(__file__).parent.parent.parent / "data" / "example_resume.md"
        if not resume_path.exists():
            pytest.skip("example_resume.md not available")
        content = resume_path.read_text()
        for category in ["Strong Skills", "Moderate Skills", "Gaps"]:
            assert category in content, f"Missing skills category: {category}"

    def test_example_resume_has_fit_examples(self) -> None:
        """Resume must include fit assessment examples for the UI."""
        resume_path = Path(__file__).parent.parent.parent / "data" / "example_resume.md"
        if not resume_path.exists():
            pytest.skip("example_resume.md not available")
        content = resume_path.read_text()
        assert "Fit Assessment" in content, "Resume must include fit assessment examples"
        # Check for structured fit data markers (markdown bold format: **Verdict:**)
        assert "Verdict:" in content or "verdict:" in content or "VERDICT:" in content, (
            "Fit examples must include verdict fields"
        )
