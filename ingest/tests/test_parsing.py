#!/usr/bin/env python3
"""
Unit tests for parsing functions in ingest.py.

Tests individual parsing functions with focused test cases:
- Frontmatter parsing
- Section extraction
- Experience parsing
- Skills parsing
- FAQ parsing
- Fit assessment parsing
- Utility functions

Run with:
    cd ingest
    source .venv/bin/activate
    uv run pytest test_parsing.py -v
"""

import textwrap

from ingest import (
    extract_experience_chunks,
    extract_failure_chunks,
    extract_faq_chunks,
    extract_keywords_from_content,
    extract_sections,
    extract_tags_from_content,
    get_current_timestamp,
    parse_experience_entry,
    parse_fit_assessment_examples,
    parse_frontmatter,
    parse_skills_section,
)


# ============================================================================
# Frontmatter Parsing Tests (6 tests)
# ============================================================================


def test_parse_frontmatter_basic():
    """Test parsing basic YAML frontmatter with simple key-value pairs."""
    content = textwrap.dedent("""
        ---
        name: Jane Doe
        title: Software Engineer
        email: jane@example.com
        ---

        Body content here.
    """).strip()

    frontmatter, body = parse_frontmatter(content)

    assert frontmatter["name"] == "Jane Doe"
    assert frontmatter["title"] == "Software Engineer"
    assert frontmatter["email"] == "jane@example.com"
    assert "Body content here." in body


def test_parse_frontmatter_with_list():
    """Test parsing frontmatter with list values."""
    content = textwrap.dedent("""
        ---
        name: John Smith
        tags:
          - python
          - golang
          - devops
        ---

        Content.
    """).strip()

    frontmatter, body = parse_frontmatter(content)

    assert frontmatter["name"] == "John Smith"
    assert "tags" in frontmatter
    assert isinstance(frontmatter["tags"], list)
    assert "python" in frontmatter["tags"]
    assert "golang" in frontmatter["tags"]
    assert "devops" in frontmatter["tags"]


def test_parse_frontmatter_with_multiline_string():
    """Test parsing frontmatter with multiline string (| syntax)."""
    content = textwrap.dedent("""
        ---
        name: Alice
        system_prompt: |
          You are a helpful assistant.
          Answer questions accurately.
        email: alice@test.com
        ---

        Body.
    """).strip()

    frontmatter, body = parse_frontmatter(content)

    assert frontmatter["name"] == "Alice"
    assert "system_prompt" in frontmatter
    assert "helpful assistant" in frontmatter["system_prompt"]
    assert "accurately" in frontmatter["system_prompt"]
    assert frontmatter["email"] == "alice@test.com"


def test_parse_frontmatter_empty():
    """Test parsing content with no frontmatter."""
    content = "No frontmatter here.\n\nJust body content."

    frontmatter, body = parse_frontmatter(content)

    assert frontmatter == {}
    assert body == content


def test_parse_frontmatter_empty_values():
    """Test parsing frontmatter with empty list placeholders."""
    content = textwrap.dedent("""
        ---
        name: Bob
        tags:
        location: Remote
        ---

        Body.
    """).strip()

    frontmatter, body = parse_frontmatter(content)

    assert frontmatter["name"] == "Bob"
    assert frontmatter["location"] == "Remote"


def test_parse_frontmatter_quoted_strings():
    """Test parsing frontmatter with quoted string values."""
    content = textwrap.dedent("""
        ---
        name: Charlie
        tags:
          - "machine-learning"
          - 'data-science'
          - AI/ML
        ---

        Body.
    """).strip()

    frontmatter, body = parse_frontmatter(content)

    assert frontmatter["name"] == "Charlie"
    assert "machine-learning" in frontmatter["tags"]
    assert "data-science" in frontmatter["tags"]
    assert "AI/ML" in frontmatter["tags"]


# ============================================================================
# Section Extraction Tests (5 tests)
# ============================================================================


def test_extract_sections_basic():
    """Test extracting basic sections from markdown."""
    content = textwrap.dedent("""
        ## Introduction

        This is the introduction.

        ## Skills

        Python, Go, Rust.

        ## Experience

        Work history here.
    """).strip()

    sections = extract_sections(content)

    assert len(sections) == 3
    assert sections[0]["title"] == "Introduction"
    assert "introduction" in sections[0]["content"]
    assert sections[1]["title"] == "Skills"
    assert "Python" in sections[1]["content"]
    assert sections[2]["title"] == "Experience"


def test_extract_sections_with_subsections():
    """Test extracting sections that contain ### subsections."""
    content = textwrap.dedent("""
        ## Professional Experience

        ### Acme Corp
        **Role:** Engineer

        ### TechCo
        **Role:** Lead
    """).strip()

    sections = extract_sections(content)

    assert len(sections) == 1
    assert sections[0]["title"] == "Professional Experience"
    assert "### Acme Corp" in sections[0]["content"]
    assert "### TechCo" in sections[0]["content"]


def test_extract_sections_empty_content():
    """Test extracting sections from empty or no-section content."""
    content = "Just some text without sections."

    sections = extract_sections(content)

    assert len(sections) == 0


def test_extract_sections_single_section():
    """Test extracting a single section."""
    content = textwrap.dedent("""
        ## Summary

        A brief overview of my background.
    """).strip()

    sections = extract_sections(content)

    assert len(sections) == 1
    assert sections[0]["title"] == "Summary"
    assert "overview" in sections[0]["content"]


def test_extract_sections_whitespace_handling():
    """Test that sections properly handle whitespace and blank lines."""
    content = textwrap.dedent("""
        ## Section One

        Line 1.

        Line 2.

        ## Section Two

        Content here.
    """).strip()

    sections = extract_sections(content)

    assert len(sections) == 2
    assert "Line 1" in sections[0]["content"]
    assert "Line 2" in sections[0]["content"]


# ============================================================================
# Experience Parsing Tests (6 tests)
# ============================================================================


def test_extract_experience_chunks_basic():
    """Test extracting experience chunks from Professional Experience section."""
    content = textwrap.dedent("""
        ### Acme Corporation
        **Role:** Senior Engineer

        ### TechCo Inc
        **Role:** Staff Engineer
    """).strip()

    chunks = extract_experience_chunks(content)

    assert len(chunks) == 2
    assert chunks[0]["title"] == "Acme Corporation"
    assert "Senior Engineer" in chunks[0]["content"]
    assert chunks[1]["title"] == "TechCo Inc"
    assert "Staff Engineer" in chunks[1]["content"]


def test_parse_experience_entry_basic():
    """Test parsing a basic experience entry."""
    content = textwrap.dedent("""
        **Role:** Software Engineer
        **Period:** Jan 2020 - Dec 2022
        **Location:** San Francisco, CA
        **Tags:** python, kubernetes, aws
    """).strip()

    entry = parse_experience_entry(content)

    assert entry["role"] == "Software Engineer"
    assert entry["period"] == "Jan 2020 - Dec 2022"
    assert entry["location"] == "San Francisco, CA"
    assert "python" in entry["tags"]
    assert "kubernetes" in entry["tags"]


def test_parse_experience_entry_with_highlights():
    """Test parsing experience entry with highlight bullets."""
    content = textwrap.dedent("""
        **Role:** Lead Engineer
        **Period:** 2023 - Present

        - **Achievement 1:** Built scalable system
        - **Achievement 2:** Led team of 5 engineers
    """).strip()

    entry = parse_experience_entry(content)

    assert entry["role"] == "Lead Engineer"
    assert len(entry["highlights"]) == 2
    assert "Built scalable system" in entry["highlights"][0]
    assert "Led team" in entry["highlights"][1]


def test_parse_experience_entry_with_ai_context():
    """Test parsing experience entry with AI Context section."""
    content = textwrap.dedent("""
        **Role:** Principal Engineer
        **Period:** 2021 - 2023

        **AI Context:**
        - **Situation:** Company needed to scale infrastructure
        - **Approach:** Designed microservices architecture
        - **Technical Work:** Implemented using Kubernetes and Go
        - **Lessons Learned:** Communication is key in large migrations
    """).strip()

    entry = parse_experience_entry(content)

    assert entry["role"] == "Principal Engineer"
    assert "ai_context" in entry
    assert "scale infrastructure" in entry["ai_context"]["situation"]
    assert "microservices" in entry["ai_context"]["approach"]
    assert "Kubernetes" in entry["ai_context"]["technical_work"]
    assert "Communication" in entry["ai_context"]["lessons_learned"]


def test_parse_experience_entry_minimal():
    """Test parsing experience entry with minimal fields."""
    content = "**Role:** Developer"

    entry = parse_experience_entry(content)

    assert entry["role"] == "Developer"
    assert entry["period"] == ""
    assert entry["location"] == ""
    assert len(entry["tags"]) == 0


def test_extract_experience_chunks_empty():
    """Test extracting experience chunks from empty content."""
    content = ""

    chunks = extract_experience_chunks(content)

    assert len(chunks) == 0


# ============================================================================
# Skills Parsing Tests (4 tests)
# ============================================================================


def test_parse_skills_section_complete():
    """Test parsing complete skills section with all categories."""
    content = textwrap.dedent("""
        ### Strong Skills
        - **Python:** 10+ years experience
        - **Kubernetes:** Production deployments

        ### Moderate Skills
        - **React:** Several projects
        - **TypeScript:** Growing proficiency

        ### Gaps
        - **Rust:** Limited experience
        - **Machine Learning:** Theoretical knowledge only
    """).strip()

    skills = parse_skills_section(content)

    assert len(skills["strong"]) == 2
    assert "Python" in skills["strong"]
    assert "Kubernetes" in skills["strong"]
    assert len(skills["moderate"]) == 2
    assert "React" in skills["moderate"]
    assert len(skills["gaps"]) == 2
    assert "Rust" in skills["gaps"]


def test_parse_skills_section_strong_only():
    """Test parsing skills section with only strong skills."""
    content = textwrap.dedent("""
        ### Strong Skills
        - **Go:** Expert level
        - **Docker:** Daily use
    """).strip()

    skills = parse_skills_section(content)

    assert len(skills["strong"]) == 2
    assert "Go" in skills["strong"]
    assert "Docker" in skills["strong"]
    assert len(skills["moderate"]) == 0
    assert len(skills["gaps"]) == 0


def test_parse_skills_section_empty():
    """Test parsing empty skills section."""
    content = ""

    skills = parse_skills_section(content)

    assert len(skills["strong"]) == 0
    assert len(skills["moderate"]) == 0
    assert len(skills["gaps"]) == 0


def test_parse_skills_section_mixed_format():
    """Test parsing skills with various formatting."""
    content = textwrap.dedent("""
        ### Strong Skills
        - **AWS:** Cloud infrastructure
        - **PostgreSQL:** Database design

        ### Gaps
        - **Blockchain:** No experience
    """).strip()

    skills = parse_skills_section(content)

    assert "AWS" in skills["strong"]
    assert "PostgreSQL" in skills["strong"]
    assert "Blockchain" in skills["gaps"]


# ============================================================================
# FAQ Parsing Tests (4 tests)
# ============================================================================


def test_extract_faq_chunks_basic():
    """Test extracting FAQ chunks."""
    content = textwrap.dedent("""
        ### What programming languages do you know?

        I have experience with Python, Go, and JavaScript.

        **Keywords:** python, go, javascript, programming

        ### What's your leadership style?

        I focus on servant leadership and empowering teams.

        **Keywords:** leadership, management, teams
    """).strip()

    chunks = extract_faq_chunks(content)

    assert len(chunks) == 2
    assert "programming languages" in chunks[0]["title"]
    assert "Python" in chunks[0]["content"]
    assert "python" in chunks[0]["keywords"]
    assert "leadership style" in chunks[1]["title"]


def test_extract_faq_chunks_no_keywords():
    """Test extracting FAQ chunks without keywords."""
    content = textwrap.dedent("""
        ### What is your experience?

        10 years in software engineering.
    """).strip()

    chunks = extract_faq_chunks(content)

    assert len(chunks) == 1
    assert "experience" in chunks[0]["title"]
    assert len(chunks[0]["keywords"]) == 0


def test_extract_faq_chunks_empty():
    """Test extracting FAQ chunks from empty content."""
    content = ""

    chunks = extract_faq_chunks(content)

    assert len(chunks) == 0


def test_extract_faq_chunks_single():
    """Test extracting single FAQ chunk."""
    content = textwrap.dedent("""
        ### Can you work remotely?

        Yes, I have 5 years of remote work experience.

        **Keywords:** remote, work-from-home, distributed
    """).strip()

    chunks = extract_faq_chunks(content)

    assert len(chunks) == 1
    assert "remotely" in chunks[0]["title"]
    assert "remote" in chunks[0]["keywords"]


# ============================================================================
# Fit Assessment Parsing Tests (5 tests)
# ============================================================================


def test_parse_fit_assessment_examples_complete():
    """Test parsing complete fit assessment example."""
    content = textwrap.dedent("""
        ### Example 1: Strong Fit — VP of Engineering, AI Startup

        **Job Description:**
        Looking for VP Engineering with AI/ML experience.

        **Assessment:**
        - **Verdict:** ⭐⭐⭐⭐⭐ Strong fit (95% match)
        - **Key Matches:**
          - AI/ML experience with production deployments
          - Leadership track record
        - **Gaps:**
          - No specific startup experience
        - **Recommendation:**
          - Highly recommended for this role
    """).strip()

    examples = parse_fit_assessment_examples(content)

    assert len(examples) == 1
    assert "VP of Engineering" in examples[0]["role"]
    assert examples[0]["fit_level"] == "strong_fit"
    assert "AI/ML" in examples[0]["job_description"]
    assert "Strong fit" in examples[0]["verdict"]
    assert "AI/ML experience" in examples[0]["key_matches"]
    assert "startup" in examples[0]["gaps"]
    assert "Highly recommended" in examples[0]["recommendation"]


def test_parse_fit_assessment_examples_weak_fit():
    """Test parsing weak fit assessment example."""
    content = textwrap.dedent("""
        ### Example 2: Weak Fit — Frontend Developer, E-commerce

        **Job Description:**
        Need expert frontend developer for React/Vue.

        **Assessment:**
        - **Verdict:** ⭐⭐ Weak fit (40% match)
        - **Key Matches:**
          - General web development knowledge
        - **Gaps:**
          - Limited frontend specialization
          - No e-commerce experience
        - **Recommendation:**
          - Not recommended unless willing to learn
    """).strip()

    examples = parse_fit_assessment_examples(content)

    assert len(examples) == 1
    assert examples[0]["fit_level"] == "weak_fit"
    assert "Frontend Developer" in examples[0]["role"]
    assert "Weak fit" in examples[0]["verdict"]
    assert "Limited frontend" in examples[0]["gaps"]


def test_parse_fit_assessment_examples_multiple():
    """Test parsing multiple fit assessment examples."""
    content = textwrap.dedent("""
        ### Example 1: Strong Fit — Platform Engineer

        **Job Description:**
        Platform engineering role.

        **Assessment:**
        - **Verdict:** ⭐⭐⭐⭐⭐ Strong fit
        - **Key Matches:**
          - Perfect match
        - **Gaps:**
          - None
        - **Recommendation:**
          - Apply now

        ---

        ### Example 2: Weak Fit — Sales Engineer

        **Job Description:**
        Sales role with technical background.

        **Assessment:**
        - **Verdict:** ⭐⭐ Weak fit
        - **Key Matches:**
          - Technical knowledge
        - **Gaps:**
          - No sales experience
        - **Recommendation:**
          - Consider alternatives
    """).strip()

    examples = parse_fit_assessment_examples(content)

    assert len(examples) == 2
    assert examples[0]["fit_level"] == "strong_fit"
    assert examples[1]["fit_level"] == "weak_fit"


def test_parse_fit_assessment_examples_empty():
    """Test parsing empty fit assessment content."""
    content = ""

    examples = parse_fit_assessment_examples(content)

    assert len(examples) == 0


def test_parse_fit_assessment_examples_multiline_jd():
    """Test parsing fit assessment with multiline job description."""
    content = textwrap.dedent("""
        ### Example 1: Strong Fit — Senior Engineer

        **Job Description:**
        ```
        We are looking for a Senior Engineer with:
        - 5+ years experience
        - Python expertise
        - Cloud infrastructure knowledge
        ```

        **Assessment:**
        - **Verdict:** ⭐⭐⭐⭐ Strong fit (90%)
        - **Key Matches:**
          - All requirements met
        - **Gaps:**
          - None significant
        - **Recommendation:**
          - Strong candidate
    """).strip()

    examples = parse_fit_assessment_examples(content)

    assert len(examples) == 1
    assert "5+ years" in examples[0]["job_description"]
    assert "Python" in examples[0]["job_description"]


# ============================================================================
# Utility Functions Tests (3 tests)
# ============================================================================


def test_extract_tags_from_content():
    """Test extracting tags from content with Tags line."""
    content = textwrap.dedent("""
        Some content here.

        **Tags:** python, kubernetes, aws, devops

        More content.
    """).strip()

    tags = extract_tags_from_content(content)

    assert len(tags) == 4
    assert "python" in tags
    assert "kubernetes" in tags
    assert "aws" in tags
    assert "devops" in tags


def test_extract_keywords_from_content():
    """Test extracting keywords from content with Keywords line."""
    content = textwrap.dedent("""
        Article content.

        **Keywords:** machine-learning, data-science, AI, neural-networks

        More text.
    """).strip()

    keywords = extract_keywords_from_content(content)

    assert len(keywords) == 4
    assert "machine-learning" in keywords
    assert "AI" in keywords


def test_get_current_timestamp():
    """Test that timestamp function returns a valid Unix timestamp."""
    timestamp = get_current_timestamp()

    assert isinstance(timestamp, int)
    assert timestamp > 0
    # Should be reasonable (after 2020)
    assert timestamp > 1577836800  # Jan 1, 2020


# ============================================================================
# Failure Chunks Parsing Tests (3 tests)
# ============================================================================


def test_extract_failure_chunks_single():
    """Extract single failure story from markdown."""
    content = textwrap.dedent("""
        ### Failure 1: Database Migration Gone Wrong

        **Situation:** Attempted zero-downtime migration but encountered lock contention.

        **What Went Wrong:** Didn't account for long-running transactions.

        **Lesson:** Always test migrations on staging with production-like load.
    """).strip()

    chunks = extract_failure_chunks(content)

    assert len(chunks) == 1
    assert "Failure 1" in chunks[0]["title"]
    assert "Database Migration" in chunks[0]["title"]
    assert "zero-downtime migration" in chunks[0]["content"]
    assert "Lesson" in chunks[0]["content"]


def test_extract_failure_chunks_multiple():
    """Extract multiple failure stories."""
    content = textwrap.dedent("""
        ### Failure 1: First Mistake

        **Situation:** Problem A
        **Lesson:** Solution A

        ### Failure 2: Second Mistake

        **Situation:** Problem B
        **Lesson:** Solution B
    """).strip()

    chunks = extract_failure_chunks(content)

    assert len(chunks) == 2
    assert "Failure 1" in chunks[0]["title"]
    assert "Failure 2" in chunks[1]["title"]
    assert "Problem A" in chunks[0]["content"]
    assert "Problem B" in chunks[1]["content"]


def test_extract_failure_chunks_empty():
    """Return empty list when no failure sections found."""
    content = "Just normal content without any failure headings."
    chunks = extract_failure_chunks(content)

    assert len(chunks) == 0
