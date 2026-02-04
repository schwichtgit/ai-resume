#!/usr/bin/env python3
"""
Ingest script for creating memvid memory from master_resume.md.

This script:
1. Parses the markdown document with YAML frontmatter
2. Chunks content by sections (## headings) following the chunking guidance
3. Adds appropriate tags for semantic retrieval
4. Creates a .mv2 file for use by the AI agent
5. Exports profile.json for API consumption

Note: This is data ingestion/indexing, not ML training. No model parameters
are updated - documents are embedded and indexed for hybrid retrieval.

Run with: uv run python ingest.py [--output PATH]
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

import memvid_sdk
from memvid_sdk.embeddings import HuggingFaceEmbeddings


# Embedding model configuration
# BAAI/bge-small-en-v1.5 is optimized for asymmetric retrieval (short query → long document)
# - Trained with hard negative mining (distinguishes "AI" from "Adobe Illustrator")
# - 3x smaller (130MB vs 420MB), 2x faster (384 dims vs 768 dims)
# - Higher MTEB scores than all-mpnet-base-v2 for retrieval tasks
# See: https://huggingface.co/BAAI/bge-small-en-v1.5
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RESUME_PATH = DATA_DIR / "master_resume.md"
EXAMPLE_PATH = DATA_DIR / "example_resume.md"
OUTPUT_DIR = DATA_DIR / ".memvid"
DEFAULT_OUTPUT = OUTPUT_DIR / "resume.mv2"


def get_current_timestamp() -> int:
    """Get current Unix timestamp for frame metadata."""
    return int(datetime.now().timestamp())


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter from markdown content."""
    frontmatter = {}
    body = content

    # Check for YAML frontmatter (--- delimited)
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            yaml_content = parts[1].strip()
            body = parts[2].strip()

            # Simple YAML parsing for flat key-value pairs
            current_key = None
            current_list = []
            in_multiline = False
            multiline_content = []

            for line in yaml_content.split("\n"):
                # Check for key: value
                match = re.match(r"^(\w+):\s*(.*)$", line)
                if match and not in_multiline:
                    # Save previous list if any
                    if current_key and current_list:
                        frontmatter[current_key] = current_list
                        current_list = []

                    key, value = match.groups()
                    if value == "|":
                        # Multiline string starts
                        current_key = key
                        in_multiline = True
                        multiline_content = []
                    elif value.startswith("[") or value == "":
                        current_key = key
                    else:
                        frontmatter[key] = value
                elif in_multiline:
                    if line and not line.startswith(" "):
                        # End of multiline
                        frontmatter[current_key] = "\n".join(multiline_content)
                        in_multiline = False
                        # Re-process this line
                        match = re.match(r"^(\w+):\s*(.*)$", line)
                        if match:
                            key, value = match.groups()
                            if value == "" or value.startswith("["):
                                current_key = key
                            else:
                                frontmatter[key] = value
                    else:
                        multiline_content.append(line.strip())
                elif line.strip().startswith("- "):
                    # List item
                    item = line.strip()[2:].strip().strip('"').strip("'")
                    current_list.append(item)

            # Save final list if any
            if current_key and current_list:
                frontmatter[current_key] = current_list
            if in_multiline and multiline_content:
                frontmatter[current_key] = "\n".join(multiline_content)

    return frontmatter, body


def extract_sections(content: str) -> list[dict]:
    """Extract sections from markdown, chunking by ## headings."""
    sections = []
    current_section = None
    current_content = []

    for line in content.split("\n"):
        # Check for ## heading (level 2)
        if line.startswith("## "):
            # Save previous section
            if current_section:
                sections.append({
                    "title": current_section,
                    "content": "\n".join(current_content).strip(),
                })
            current_section = line[3:].strip()
            current_content = []
        elif line.startswith("### ") and current_section:
            # Include ### as part of current section content
            current_content.append(line)
        else:
            if current_section:
                current_content.append(line)

    # Save final section
    if current_section:
        sections.append({
            "title": current_section,
            "content": "\n".join(current_content).strip(),
        })

    return sections


def extract_experience_chunks(section_content: str) -> list[dict]:
    """Extract individual experience entries from the Experience section."""
    chunks = []
    current_chunk = None
    current_content = []

    for line in section_content.split("\n"):
        # Check for ### heading (company/role)
        if line.startswith("### "):
            # Save previous chunk
            if current_chunk:
                chunks.append({
                    "title": current_chunk,
                    "content": "\n".join(current_content).strip(),
                })
            current_chunk = line[4:].strip()
            current_content = []
        else:
            if current_chunk:
                current_content.append(line)

    # Save final chunk
    if current_chunk:
        chunks.append({
            "title": current_chunk,
            "content": "\n".join(current_content).strip(),
        })

    return chunks


def extract_tags_from_content(content: str) -> list[str]:
    """Extract tags from **Tags:** line in content."""
    tags = []
    for line in content.split("\n"):
        if line.startswith("**Tags:**"):
            # Parse comma-separated tags
            tag_str = line.replace("**Tags:**", "").strip()
            tags = [t.strip() for t in tag_str.split(",")]
            break
    return tags


def extract_keywords_from_content(content: str) -> list[str]:
    """Extract keywords from **Keywords:** line in content (per schema spec)."""
    keywords = []
    for line in content.split("\n"):
        if line.startswith("**Keywords:**"):
            # Parse comma-separated keywords
            kw_str = line.replace("**Keywords:**", "").strip()
            keywords = [k.strip() for k in kw_str.split(",")]
            break
    return keywords


def extract_faq_chunks(section_content: str) -> list[dict]:
    """
    Extract individual FAQ entries from the FAQ section.

    Each ### heading becomes a separate chunk for optimal retrieval.
    This ensures suggested questions can retrieve their matching FAQ answers.
    """
    chunks = []
    current_question = None
    current_content = []

    for line in section_content.split("\n"):
        # Check for ### heading (FAQ question)
        if line.startswith("### "):
            # Save previous chunk
            if current_question:
                content_text = "\n".join(current_content).strip()
                keywords = extract_keywords_from_content(content_text)
                chunks.append({
                    "title": current_question,
                    "content": content_text,
                    "keywords": keywords,
                })
            current_question = line[4:].strip()
            current_content = []
        else:
            if current_question:
                current_content.append(line)

    # Save final chunk
    if current_question:
        content_text = "\n".join(current_content).strip()
        keywords = extract_keywords_from_content(content_text)
        chunks.append({
            "title": current_question,
            "content": content_text,
            "keywords": keywords,
        })

    return chunks


def extract_failure_chunks(section_content: str) -> list[dict]:
    """Extract individual failure stories."""
    chunks = []
    current_chunk = None
    current_content = []

    for line in section_content.split("\n"):
        # Check for ### Failure heading
        if line.startswith("### Failure"):
            # Save previous chunk
            if current_chunk:
                chunks.append({
                    "title": current_chunk,
                    "content": "\n".join(current_content).strip(),
                })
            current_chunk = line[4:].strip()
            current_content = []
        else:
            if current_chunk:
                current_content.append(line)

    # Save final chunk
    if current_chunk:
        chunks.append({
            "title": current_chunk,
            "content": "\n".join(current_content).strip(),
        })

    return chunks


def parse_experience_entry(content: str) -> dict:
    """Parse a single experience entry from markdown."""
    lines = content.split("\n")

    # Extract structured fields
    entry = {
        "role": "",
        "period": "",
        "location": "",
        "tags": [],
        "highlights": [],
        "ai_context": {}
    }

    current_section = None
    current_content = []

    for line in lines:
        # Extract **Field:** value patterns
        if line.startswith("**Role:**"):
            entry["role"] = line.replace("**Role:**", "").strip()
        elif line.startswith("**Period:**"):
            entry["period"] = line.replace("**Period:**", "").strip()
        elif line.startswith("**Location:**"):
            entry["location"] = line.replace("**Location:**", "").strip()
        elif line.startswith("**Tags:**"):
            tag_str = line.replace("**Tags:**", "").strip()
            entry["tags"] = [t.strip() for t in tag_str.split(",")]

        # Track sections for AI Context
        elif line.startswith("**AI Context:**"):
            current_section = "ai_context"
        elif line.startswith("- **Situation:**"):
            current_section = "situation"
            current_content = [line.replace("- **Situation:**", "").strip()]
        elif line.startswith("- **Approach:**"):
            if current_section == "situation" and current_content:
                entry["ai_context"]["situation"] = " ".join(current_content)
            current_section = "approach"
            current_content = [line.replace("- **Approach:**", "").strip()]
        elif line.startswith("- **Technical Work:**"):
            if current_section == "approach" and current_content:
                entry["ai_context"]["approach"] = " ".join(current_content)
            current_section = "technical_work"
            current_content = [line.replace("- **Technical Work:**", "").strip()]
        elif line.startswith("- **Lessons Learned:**"):
            if current_section == "technical_work" and current_content:
                entry["ai_context"]["technical_work"] = " ".join(current_content)
            current_section = "lessons_learned"
            current_content = [line.replace("- **Lessons Learned:**", "").strip()]

        # Extract Key Achievements bullets
        elif line.startswith("- **") and ":" in line and current_section != "ai_context":
            # This is a highlight bullet
            entry["highlights"].append(line[2:].strip())  # Remove "- "

        # Continue accumulating content for current AI context section
        elif current_section in ["situation", "approach", "technical_work", "lessons_learned"] and line.strip():
            if not line.startswith("**") and not line.startswith("- **"):
                current_content.append(line.strip())

    # Save final AI context section
    if current_section == "lessons_learned" and current_content:
        entry["ai_context"]["lessons_learned"] = " ".join(current_content)

    return entry


def parse_skills_section(content: str) -> dict:
    """Parse the Skills Assessment section."""
    skills = {
        "strong": [],
        "moderate": [],
        "gaps": []
    }

    current_category = None

    for line in content.split("\n"):
        # Match ### headings for skill categories
        if line.startswith("### Strong"):
            current_category = "strong"
        elif line.startswith("### Moderate"):
            current_category = "moderate"
        elif line.startswith("### Gaps"):
            current_category = "gaps"
        # Extract skill bullets (format: "- **Skill Name:** description")
        elif line.startswith("- **") and current_category:
            # Extract just the skill name (between ** and :**)
            # Remove "- " prefix first
            line_content = line[2:].strip()
            if line_content.startswith("**") and ":**" in line_content:
                # Extract between ** and :**
                skill_name = line_content[2:].split(":**", 1)[0].strip()
                skills[current_category].append(skill_name)

    return skills


def parse_fit_assessment_examples(content: str) -> list[dict]:
    """Parse fit assessment examples from the Fit Assessment Examples section.

    Expected format:
    ### Example 1: Strong Fit — Title
    **Job Description:**
    ...
    **Assessment:**
    - **Verdict:** ⭐⭐⭐⭐⭐ Strong fit (95% match)
    - **Key Matches:** ...
    - **Gaps:** ...
    - **Recommendation:** ...
    """
    examples = []
    current_example = None
    current_field = None

    for line in content.split("\n"):
        # Match example headings (### Example N: ...)
        if line.startswith("### Example"):
            # Save previous example if exists
            if current_example:
                examples.append(current_example)

            # Extract example number and title
            # Format: "### Example 1: Strong Fit — VP of Engineering, AI Infrastructure Startup"
            parts = line[4:].strip().split(":", 1)
            # parts[0] is "Example 1" (not used, just metadata)
            title_parts = parts[1].strip().split("—", 1) if len(parts) > 1 else ["", ""]
            fit_level = title_parts[0].strip()  # "Strong Fit" or "Weak Fit"
            role_title = title_parts[1].strip() if len(title_parts) > 1 else ""

            current_example = {
                "title": f"{fit_level} — {role_title}",
                "fit_level": fit_level.lower().replace(" ", "_"),  # "strong_fit" or "weak_fit"
                "role": role_title,
                "job_description": "",
                "verdict": "",
                "key_matches": "",
                "gaps": "",
                "recommendation": ""
            }
            current_field = None

        # Match field markers
        elif line.startswith("**Job Description:**"):
            current_field = "job_description"
        elif line.startswith("**Assessment:**"):
            current_field = "assessment_header"
        elif line.startswith("- **Verdict:**"):
            # Extract verdict text
            verdict = line.split("**Verdict:**", 1)[1].strip()
            if current_example:
                current_example["verdict"] = verdict
        elif line.startswith("- **Key Matches:**"):
            current_field = "key_matches"
        elif line.startswith("- **Gaps:**"):
            current_field = "gaps"
        elif line.startswith("- **Recommendation:**"):
            current_field = "recommendation"

        # Accumulate content for current field
        elif current_example and current_field and line.strip():
            # Skip "---" separators
            if line.strip() == "---":
                continue

            # Append to current field
            if current_field == "job_description":
                # Skip triple backticks for code blocks
                if line.strip() != "```":
                    current_example[current_field] += line.strip() + "\n"
            elif current_field in ["key_matches", "gaps", "recommendation"]:
                # Remove bullet list formatting
                clean_line = line.strip()
                if clean_line.startswith("  -"):
                    clean_line = clean_line[3:].strip()
                current_example[current_field] += clean_line + "\n"

    # Add last example
    if current_example:
        examples.append(current_example)

    # Clean up whitespace
    for example in examples:
        for key in ["job_description", "key_matches", "gaps", "recommendation"]:
            example[key] = example[key].strip()

    return examples


def build_profile_dict(
    frontmatter: dict,
    sections: list[dict],
    verbose: bool = True,
) -> dict:
    """
    Build profile dictionary from frontmatter and sections.

    Args:
        frontmatter: Parsed YAML frontmatter dictionary
        sections: Parsed sections from markdown body
        verbose: Print progress messages

    Returns:
        Profile dictionary
    """
    # Build base profile object
    profile = {
        "name": frontmatter.get("name", ""),
        "title": frontmatter.get("title", ""),
        "email": frontmatter.get("email", ""),
        "linkedin": frontmatter.get("linkedin", ""),
        "location": frontmatter.get("location", ""),
        "status": frontmatter.get("status", ""),
        "suggested_questions": frontmatter.get("suggested_questions", []),
        "system_prompt": frontmatter.get("system_prompt", ""),
        "tags": frontmatter.get("tags", []),
        "experience": [],
        "skills": {"strong": [], "moderate": [], "gaps": []},
        "fit_assessment_examples": []
    }

    # Extract experience and skills from sections
    for section in sections:
        title = section["title"]
        content = section["content"]

        if title == "Professional Experience":
            # Parse individual experience entries
            exp_chunks = extract_experience_chunks(content)
            for chunk in exp_chunks:
                parsed = parse_experience_entry(chunk["content"])
                parsed["company"] = chunk["title"]
                profile["experience"].append(parsed)

        elif title == "Skills Assessment":
            profile["skills"] = parse_skills_section(content)

        elif title == "Fit Assessment Examples":
            profile["fit_assessment_examples"] = parse_fit_assessment_examples(content)

    if verbose:
        print(f"Built profile metadata:")
        print(f"  Experience entries: {len(profile['experience'])}")
        print(f"  Skills: {len(profile['skills']['strong'])} strong, {len(profile['skills']['moderate'])} moderate, {len(profile['skills']['gaps'])} gaps")
        print(f"  Fit assessment examples: {len(profile['fit_assessment_examples'])}")

    return profile


def ingest_memory(
    input_path: Path = RESUME_PATH,
    output_path: Path = DEFAULT_OUTPUT,
    verbose: bool = True,
    debug: bool = False,
    embedding_model: str = EMBEDDING_MODEL,
) -> dict:
    """
    Ingest master resume markdown into memvid memory.

    This embeds and indexes documents for hybrid (lexical + vector) retrieval.
    No ML model parameters are updated - this is data ingestion, not training.

    Args:
        input_path: Path to master_resume.md
        output_path: Path to output .mv2 file
        verbose: Print progress messages
        embedding_model: HuggingFace model for embeddings (default: all-mpnet-base-v2)

    Returns stats dict with frame_count, size_bytes, etc.
    """
    if verbose:
        print(f"Reading: {input_path}")
        print(f"Embedding model: {embedding_model}")

    # Read and parse content
    content = input_path.read_text()
    frontmatter, body = parse_frontmatter(content)

    if verbose:
        print(f"Frontmatter keys: {list(frontmatter.keys())}")

    # Extract global tags from frontmatter
    global_tags = frontmatter.get("tags", [])
    if isinstance(global_tags, str):
        global_tags = [t.strip() for t in global_tags.split(",")]

    # Extract sections
    sections = extract_sections(body)
    if verbose:
        print(f"Found {len(sections)} top-level sections")

    # Build profile dictionary (will be stored in memvid)
    profile = build_profile_dict(frontmatter, sections, verbose=verbose)

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing file if present
    if output_path.exists():
        output_path.unlink()
        if verbose:
            print(f"Removed existing: {output_path}")

    # Initialize embedding model
    if verbose:
        print(f"Loading embedding model: {embedding_model}...")
    embedder = HuggingFaceEmbeddings(model=embedding_model)
    if verbose:
        print(f"  Dimension: {embedder.dimension}")

    # Create memory with both lexical and vector search enabled
    if verbose:
        print(f"Creating memory: {output_path}")

    mem = memvid_sdk.create(
        str(output_path),
        kind="basic",
        enable_lex=True,  # Lexical (BM25) search
        enable_vec=True,  # Vector (semantic) search
    )
    # Collect all documents for batch embedding
    documents = []

    # Serialize profile JSON for storage as memory card (not as frame)
    # Memory cards support O(1) retrieval without text truncation
    profile_json = json.dumps(profile, indent=2)
    if verbose:
        print(f"  Prepared: Profile Metadata ({len(profile_json)} bytes, will store as memory card)")

    # Add system prompt as frame (for retrieval)
    system_prompt = frontmatter.get("system_prompt", "")
    if system_prompt:
        documents.append({
            "title": "AI System Prompt",
            "label": "AI System Prompt",
            "text": system_prompt,
            "tags": ["system-prompt", "ai-instructions"],
            "metadata": {
                "section": "system",
            },
            "timestamp": get_current_timestamp(),
        })
        if verbose:
            print(f"  Prepared: AI System Prompt")

    # Process each section
    for section in sections:
        title = section["title"]
        content = section["content"]

        if title == "Professional Experience":
            # Chunk by company/role
            exp_chunks = extract_experience_chunks(content)
            for chunk in exp_chunks:
                # Extract tags from content
                chunk_tags = extract_tags_from_content(chunk["content"])
                tags = list(set(global_tags + chunk_tags + ["experience"]))

                # Extract keywords for metadata
                keywords = extract_keywords_from_content(chunk["content"])

                documents.append({
                    "title": f"Experience: {chunk['title']}",
                    "label": f"Experience: {chunk['title']}",
                    "text": chunk["content"],
                    "tags": tags,
                    "metadata": {
                        "section": "experience",
                        "company": chunk['title'],
                        "keywords": ",".join(keywords[:10]) if keywords else "",  # Top 10 keywords
                    },
                    "timestamp": get_current_timestamp(),  # Current timestamp (resume doesn't have time-series data)
                })
                if verbose:
                    print(f"  Prepared: Experience: {chunk['title']}")
                    if debug:
                        print(f"    Tags: {tags}")
                        print(f"    Metadata: section=experience, company={chunk['title']}")
                        print(f"    Text: {chunk['content'][:200]}..." if len(chunk['content']) > 200 else f"    Text: {chunk['content']}")

        elif title == "Frequently Asked Questions":
            # Chunk by individual FAQ entry for optimal retrieval
            # Each question becomes its own searchable chunk
            faq_chunks = extract_faq_chunks(content)
            for chunk in faq_chunks:
                # Combine global tags with extracted keywords
                keywords = chunk.get("keywords", [])
                tags = list(set(global_tags + keywords + ["faq", "question-answer"]))

                documents.append({
                    "title": f"FAQ: {chunk['title']}",
                    "label": f"FAQ: {chunk['title']}",
                    "text": chunk["content"],
                    "tags": tags,
                    "metadata": {
                        "section": "faq",
                        "keywords": ",".join(keywords[:10]) if keywords else "",
                    },
                    "timestamp": get_current_timestamp(),
                })
                if verbose:
                    print(f"  Prepared: FAQ: {chunk['title']}")
                    if debug:
                        print(f"    Tags: {tags}")
                        print(f"    Keywords: {keywords}")
                        print(f"    Metadata: section=faq")
                        print(f"    Text: {chunk['content'][:200]}..." if len(chunk['content']) > 200 else f"    Text: {chunk['content']}")

        elif title == "Documented Failures & Lessons Learned":
            # Chunk by individual failure
            failure_chunks = extract_failure_chunks(content)
            for chunk in failure_chunks:
                tags = list(set(global_tags + ["failure", "lessons-learned"]))

                documents.append({
                    "title": chunk["title"],
                    "label": chunk["title"],
                    "text": chunk["content"],
                    "tags": tags,
                    "metadata": {
                        "section": "failures",
                    },
                    "timestamp": get_current_timestamp(),
                })
                if verbose:
                    print(f"  Prepared: {chunk['title']}")

        elif title == "Skills Assessment":
            # Add as single chunk with skill tags
            tags = list(set(global_tags + ["skills", "assessment"]))
            keywords = extract_keywords_from_content(content)
            documents.append({
                "title": "Skills Assessment",
                "label": "Skills Assessment",
                "text": content,
                "tags": tags,
                "metadata": {
                    "section": "skills",
                    "keywords": ",".join(keywords[:15]) if keywords else "",  # More keywords for skills
                },
                "timestamp": get_current_timestamp(),
            })
            if verbose:
                print(f"  Prepared: Skills Assessment")
                if debug:
                    print(f"    Tags: {tags}")
                    print(f"    Metadata: section=skills")
                    print(f"    Text: {content[:200]}..." if len(content) > 200 else f"    Text: {content}")

        elif title == "Fit Assessment Guidance":
            # Add as single chunk for fit matching
            tags = list(set(global_tags + ["fit-assessment", "job-matching"]))
            documents.append({
                "title": "Fit Assessment Guidance",
                "label": "Fit Assessment Guidance",
                "text": content,
                "tags": tags,
                "metadata": {
                    "section": "fit-assessment",
                },
                "timestamp": get_current_timestamp(),
            })
            if verbose:
                print(f"  Prepared: Fit Assessment Guidance")
                if debug:
                    print(f"    Tags: {tags}")
                    print(f"    Metadata: section=fit-assessment")
                    print(f"    Text: {content[:200]}..." if len(content) > 200 else f"    Text: {content}")

        elif title == "Leadership & Management":
            tags = list(set(global_tags + ["leadership", "management", "soft-skills"]))
            documents.append({
                "title": "Leadership & Management",
                "label": "Leadership & Management",
                "text": content,
                "tags": tags,
                "metadata": {
                    "section": "leadership",
                },
                "timestamp": get_current_timestamp(),
            })
            if verbose:
                print(f"  Prepared: Leadership & Management")
                if debug:
                    print(f"    Tags: {tags}")
                    print(f"    Metadata: section=leadership")
                    print(f"    Text: {content[:200]}..." if len(content) > 200 else f"    Text: {content}")

        elif title == "Summary":
            tags = list(set(global_tags + ["summary", "overview"]))
            documents.append({
                "title": "Professional Summary",
                "label": "Professional Summary",
                "text": content,
                "tags": tags,
                "metadata": {
                    "section": "summary",
                },
                "timestamp": get_current_timestamp(),
            })
            if verbose:
                print(f"  Prepared: Professional Summary")
                if debug:
                    print(f"    Tags: {tags}")
                    print(f"    Metadata: section=summary")
                    print(f"    Text: {content[:200]}..." if len(content) > 200 else f"    Text: {content}")

        elif title not in ["Contact & Links", "Metadata for Memvid Chunking"]:
            # Add other sections as-is
            tags = list(set(global_tags))
            documents.append({
                "title": title,
                "label": title,
                "text": content,
                "tags": tags,
                "metadata": {
                    "section": title.lower().replace(" ", "-").replace("&", "and"),
                },
                "timestamp": get_current_timestamp(),
            })
            if verbose:
                print(f"  Prepared: {title}")
                if debug:
                    print(f"    Tags: {tags}")
                    print(f"    Metadata: section={title}")
                    print(f"    Text: {content[:200]}..." if len(content) > 200 else f"    Text: {content}")

    # Store profile as a memory card using add_memory_cards() for O(1) retrieval
    # This avoids text truncation issues in search results
    # Retrieve with: mem.state('__profile__')['slots']['data']['value']
    if verbose:
        print(f"\nAdding profile as memory card (O(1) retrieval)...")

    profile_card_result = mem.add_memory_cards([
        {
            "entity": "__profile__",
            "slot": "data",
            "value": profile_json,  # Full JSON, no truncation
            "kind": "Profile",
        }
    ])

    if verbose:
        print(f"  Inserted profile memory card: {profile_card_result}")

    # Batch insert all other documents with embeddings
    if verbose:
        print(f"\nEmbedding and inserting {len(documents)} documents...")

    frame_ids = mem.put_many(documents, embedder=embedder)
    frame_count = len(frame_ids)  # Profile stored as memory card, not frame

    if verbose:
        print(f"  Inserted {len(frame_ids)} frames with embeddings")

    # Get stats before closing
    stats = mem.stats()

    # Close saves automatically
    mem.close()

    if verbose:
        print(f"\nIngestion complete!")
        print(f"  Frames: {stats.get('frame_count', frame_count)}")
        print(f"  Size: {stats.get('size_bytes', 0):,} bytes")
        print(f"  Output: {output_path}")

    return stats


def verify(output_path: Path = DEFAULT_OUTPUT, verbose: bool = True) -> bool:
    """
    Verify the ingested memory with semantic quality checks.

    Validates:
    - Minimum frame count (>= 5)
    - Score thresholds for relevance
    - Tag matching for expected content
    """
    if not output_path.exists():
        if verbose:
            print(f"Memory file not found: {output_path}")
        return False

    if verbose:
        print(f"\nVerifying: {output_path}")

    mem = memvid_sdk.use("basic", str(output_path))
    stats = mem.stats()

    # Check minimum frame count
    frame_count = stats.get("frame_count", 0)
    if verbose:
        print(f"  Frame count: {frame_count}")

    if frame_count < 5:
        if verbose:
            print("FAILED: Insufficient frames (< 5)")
        mem.close()
        return False

    # Test semantic queries with relevance scoring and tag matching
    # Format: (query, score_threshold, expected_tags)
    # These test cases verify:
    # 1. FAQ questions retrieve their matching FAQ entries
    # 2. General queries find relevant content
    test_queries = [
        # FAQ mirroring tests - suggested questions should find FAQ entries
        ("What programming languages does she know?", 0.3, ["faq", "question-answer"]),
        ("What's her security track record?", 0.3, ["faq", "question-answer"]),
        ("What are her biggest failures?", 0.3, ["faq", "question-answer"]),
        # General semantic queries
        ("Python Go Rust programming", 0.3, ["faq", "question-answer"]),
        ("leadership team building", 0.3, ["team-leadership"]),
        ("professional summary overview", 0.3, ["summary", "overview"]),
    ]

    # Negative queries (expect <1 relevant hit or low scores)
    neg_queries = [
        ("quantum physics", 0.2),  # Unrelated to resume
        ("unrelated hobby knitting", 0.2),  # Irrelevant tags
    ]

    all_passed = True
    for query, score_thresh, expected_tags in test_queries:
        result = mem.find(query, k=3)
        hits = result.get("hits", [])

        # Filter by score threshold
        relevant_hits = [h for h in hits if h.get("score", 0) >= score_thresh]

        # Check if any hit has matching tags
        tag_match = any(
            any(tag in h.get("tags", []) for tag in expected_tags)
            for h in relevant_hits
        )

        if verbose:
            print(f"\n  Query: '{query}'")
            print(f"    Hits: {len(hits)} total, {len(relevant_hits)} relevant (score >= {score_thresh})")
            print(f"    Tag match: {tag_match}")
            for hit in relevant_hits[:2]:
                score = hit.get("score", 0)
                title = hit.get("title", "N/A")
                tags = hit.get("tags", [])
                print(f"      - [{score:.3f}] {title} {tags[:3]}")

        if len(relevant_hits) == 0:
            all_passed = False
            if verbose:
                print(f"    WARNING: No relevant results for '{query}'")
        elif not tag_match:
            all_passed = False
            if verbose:
                print(f"    WARNING: No tag match for '{query}' (expected: {expected_tags})")

    for query, score_thresh in neg_queries:
        result = mem.find(query, k=3)
        hits = result.get("hits", [])
        relevant_hits = [h for h in hits if h.get('score', 0) > score_thresh]

        if verbose:
            print(f"\n  Neg Query: '{query}' | Unexpected relevant: {len(relevant_hits)}")

        if len(relevant_hits) > 0:
            all_passed = False
    mem.close()

    if verbose:
        print(f"\nVerification: {'PASSED' if all_passed else 'FAILED'}")

    return all_passed


def check_input_file(input_path: Path, verbose: bool = True) -> bool:
    """
    Check if input file exists and provide helpful guidance if not.

    Returns True if file exists, False otherwise.
    """
    if input_path.exists():
        return True

    if verbose:
        print(f"Error: Input file not found: {input_path}")
        print()

        # Check if this is the default path
        if input_path == RESUME_PATH:
            print("The master_resume.md file contains your personal resume data.")
            print("This file is excluded from version control for privacy.")
            print()

            if EXAMPLE_PATH.exists():
                print("To get started, create your resume using the example as a template:")
                print()
                print(f"    cp {EXAMPLE_PATH} {RESUME_PATH}")
                print()
                print("Then edit data/master_resume.md with your information.")
                print()
                print("For schema documentation, see: docs/MASTER_DOCUMENT_SCHEMA.md")
            else:
                print("Expected example file not found. Please check your installation.")
        else:
            print(f"Please ensure the file exists at: {input_path}")

    return False


def main():
    parser = argparse.ArgumentParser(
        description="Ingest master resume into memvid memory"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=RESUME_PATH,
        help=f"Input markdown file (default: {RESUME_PATH})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output .mv2 file (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Run verification queries after ingestion",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress verbose output",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show detailed content being indexed (implies verbose)",
    )

    args = parser.parse_args()

    # Debug mode implies verbose
    if args.debug:
        args.quiet = False

    # Check input file exists
    if not check_input_file(args.input, verbose=not args.quiet):
        raise SystemExit(1)

    # Ingest
    ingest_memory(
        input_path=args.input,
        output_path=args.output,
        verbose=not args.quiet,
        debug=args.debug,
    )

    # Verify if requested
    if args.verify:
        verify(output_path=args.output, verbose=not args.quiet)


if __name__ == "__main__":
    main()
