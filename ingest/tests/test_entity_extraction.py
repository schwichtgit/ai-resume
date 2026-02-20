#!/usr/bin/env python3
"""
Tests for entity type extraction (ontology stub).

Phase 7 stub: validates that extract_entity_types correctly tags chunks
with broad entity categories based on content patterns.

Run with:
    cd ingest
    source .venv/bin/activate
    uv run pytest tests/test_entity_extraction.py -v
"""

from ingest import extract_entity_types


class TestEntityExtraction:
    def test_detects_company(self) -> None:
        result = extract_entity_types("Worked at Acme Corp as a senior developer")
        assert "Company" in result

    def test_detects_role(self) -> None:
        result = extract_entity_types("Senior Software Engineer at a startup")
        assert "Role" in result

    def test_detects_skill(self) -> None:
        result = extract_entity_types("Built microservices with Python and Kubernetes")
        assert "Skill" in result

    def test_detects_achievement(self) -> None:
        result = extract_entity_types("Reduced API latency by 40% through caching")
        assert "Achievement" in result

    def test_detects_project(self) -> None:
        result = extract_entity_types("Built the data pipeline for analytics")
        assert "Project" in result

    def test_empty_text_returns_empty(self) -> None:
        result = extract_entity_types("")
        assert result == []

    def test_multiple_entity_types(self) -> None:
        result = extract_entity_types(
            "Senior Engineer at Acme Corp built a Python service that reduced costs by 30%"
        )
        assert "Role" in result
        assert "Company" in result
        assert "Skill" in result
        assert "Achievement" in result

    def test_company_keywords_case_insensitive(self) -> None:
        """Company keywords should match regardless of case."""
        assert "Company" in extract_entity_types("Working at BigTech Inc on infrastructure")
        assert "Company" in extract_entity_types("Joined Startup LLC in 2020")
        assert "Company" in extract_entity_types("Consulting for Siemens GmbH")
        assert "Company" in extract_entity_types("Partnered with Foo Ltd for delivery")

    def test_role_keywords_case_insensitive(self) -> None:
        """Role keywords should match regardless of case."""
        assert "Role" in extract_entity_types("Promoted to Director of Engineering")
        assert "Role" in extract_entity_types("Worked as a software architect")
        assert "Role" in extract_entity_types("Acting CTO for six months")

    def test_skill_detection_is_case_sensitive(self) -> None:
        """Skill detection uses case-sensitive matching for technology names."""
        assert "Skill" in extract_entity_types("Expert in Python and Docker")
        assert "Skill" not in extract_entity_types("used python scripting daily")

    def test_achievement_regex_patterns(self) -> None:
        """Achievement detection covers percentage, multiplier, and verb patterns."""
        assert "Achievement" in extract_entity_types("Achieved 10x throughput improvement")
        assert "Achievement" in extract_entity_types("Increased revenue by 25%")
        assert "Achievement" in extract_entity_types("Improved deployment frequency")
        assert "Achievement" in extract_entity_types("Grew the team from 3 to 12")
        assert "Achievement" in extract_entity_types("Scaled the platform to 1M users")

    def test_no_false_positives_on_plain_text(self) -> None:
        """Plain conversational text should not produce entity annotations."""
        result = extract_entity_types("Hello world, this is a simple sentence.")
        assert result == []
