# Master Document Schema Reference

**Version:** 1.0 (January 2026)
**Status:** Plan of Record (POR)

This document defines the optimal schema for resume data files used by the AI Resume Agent. The schema is designed for maximum retrieval accuracy when ingested into memvid and queried via the agentic RAG pipeline.

---

## Table of Contents

1. [Design Principles](#design-principles)
2. [Document Structure](#document-structure)
3. [Section Reference](#section-reference)
4. [Chunking Strategy](#chunking-strategy)
5. [Ingest Pipeline](#ingest-pipeline)
6. [Examples](#examples)

---

## Design Principles

### 1. Optimize for Retrieval, Not Reading

The master document is **not** a traditional resume. It's a knowledge base optimized for semantic search and LLM augmentation. Structure content for how it will be *queried*, not how it would be *read*.

**Bad:** Long narrative paragraphs mixing multiple topics
**Good:** Focused sections with explicit topic markers and keywords

### 2. Anticipate Questions, Pre-Index Answers

Every suggested question in the UI should have a corresponding FAQ entry that will be retrieved when that question is asked. The suggested questions and FAQ entries are **mirrors** of each other.

**Bad:** Suggested question "What's their security track record?" with no FAQ entry
**Good:** FAQ entry titled "What's their security track record?" containing the canonical answer

### 3. Small Chunks Beat Large Chunks

Memvid (and vector search generally) works better with focused, topical chunks than large documents. A 200-word chunk about security will rank higher for security queries than a 2000-word "Skills" section that mentions security once.

**Bad:** Single "Skills" section listing everything
**Good:** Separate sections for "Security Skills", "Programming Languages", "Cloud Platforms"

### 4. Explicit Keywords Enable Matching

Semantic search can miss obvious matches. If the resume says "Python, Go, Bash" but the user asks about "programming languages", the search may fail. Add explicit keyword markers.

**Bad:** `Programming: Python, Go, Bash, Rust`
**Good:** `Programming Languages & Coding Skills: Python, Go, Bash, Rust (learning)`

### 5. Multiple Representations Improve Coverage

The same information indexed in multiple forms (narrative, Q&A, keywords) catches different query styles.

---

## Document Structure

The master document is a Markdown file with YAML frontmatter. Required sections:

```text
┌─────────────────────────────────────────────────────────────┐
│  YAML Frontmatter                                           │
│  - Profile metadata (name, title, contact)                  │
│  - System prompt for LLM                                    │
│  - Suggested questions (mirrored in FAQ)                    │
│  - Global tags for memvid                                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  ## Summary                                                 │
│  Brief overview (2-3 paragraphs)                            │
│  - Who they are                                             │
│  - What they do best                                        │
│  - What they're NOT (honest limitations)                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  ## Frequently Asked Questions                              │
│  Pre-indexed Q&A pairs for anticipated queries              │
│  - Each suggested question has an FAQ entry                 │
│  - Canonical answers you control                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  ## Professional Experience                                 │
│  Chunked by company/role                                    │
│  - Context, achievements, AI context, lessons learned       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  ## Skills (Topic-Focused Sections)                         │
│  Small, focused chunks by topic                             │
│  - Security Skills                                          │
│  - Programming Languages                                    │
│  - Cloud & Infrastructure                                   │
│  - AI/ML & GenAI                                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  ## Leadership & Management                                 │
│  Philosophy, team building, communication style             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  ## Failures & Lessons Learned                              │
│  Each failure as separate chunk                             │
│  - What happened, what was learned, how behavior changed    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  ## Fit Assessment                                          │
│  Strong fit, moderate fit, weak fit scenarios               │
└─────────────────────────────────────────────────────────────┘
```

---

## Section Reference

### YAML Frontmatter

```yaml
---
# Profile Metadata
name: Jane Smith
title: VP of Engineering
email: jane@example.com
linkedin: https://linkedin.com/in/janesmith
location: San Francisco, CA
status: Open to VP/Head of Engineering roles

# System Prompt for LLM
system_prompt: |
  You are helping hiring managers evaluate Jane Smith as a candidate.

  CORE INSTRUCTIONS:
  - Be specific with dates, companies, and outcomes
  - Be honest about gaps and limitations
  - Don't oversell - credibility matters
  - Include failure stories when relevant
  - Acknowledge what she's NOT good at

# Suggested Questions (MUST mirror FAQ entries)
suggested_questions:
  - "What's her security track record?"
  - "What programming languages does she know?"
  - "Tell me about her AI/ML experience."
  - "What are her biggest failures?"
  - "Would she be good for an early-stage startup?"

# Global Tags (for memvid indexing)
tags:
  - vp-engineering
  - ai-infrastructure
  - security-architecture
  - cloud-native
  - kubernetes
---
```

**Key Points:**

- `suggested_questions` MUST have corresponding FAQ entries
- `system_prompt` shapes all LLM responses
- `tags` are indexed globally for broad topic matching

---

### Frequently Asked Questions Section

**This is the most critical section for retrieval accuracy.**

Each FAQ entry should:

1. Use the EXACT question text from `suggested_questions`
2. Provide a comprehensive, canonical answer
3. Include specific examples, dates, and metrics
4. Be self-contained (don't assume context from other sections)

```markdown
## Frequently Asked Questions

### What's her security track record?
**Keywords:** security, zero-trust, FedRAMP, SOC 2, compliance, audit, encryption

Jane has 12+ years of security architecture experience in regulated industries:

**Compliance Certifications:**
- Led FedRAMP Moderate certification (passed first attempt)
- Achieved SOC 2 Type II compliance for SaaS platform
- Maintained PCI-DSS compliance for payment processing systems

**Security Architecture:**
- Designed zero-trust network architecture at Acme Corp
- Implemented HashiCorp Vault for secrets management
- Built automated security scanning in CI/CD (Snyk, Trivy, Grype)

**Track Record:**
- Zero security breaches across 5 years at previous company
- Reduced vulnerability remediation time from 30 days to 48 hours
- Passed 3 external penetration tests with no critical findings

### What programming languages does she know?
**Keywords:** programming, languages, coding, Python, Go, Rust, development

Jane's programming skills:

**Primary Languages (daily use):**
- Python: 10+ years, data pipelines, automation, ML tooling
- Go: 5+ years, microservices, CLI tools, Kubernetes operators
- Bash: System scripting, CI/CD automation

**Secondary Languages (working knowledge):**
- Rust: Learning, interested in systems programming
- JavaScript/TypeScript: Can read/review, not primary developer

**Not a fit for:**
- Frontend development (React, Vue) - limited experience
- Mobile development - no production experience
- Low-level systems (C, C++) - hasn't used in 10+ years
```

**Key Points:**

- Include `**Keywords:**` line for explicit term matching
- Structure with headers for scannability
- Include "Not a fit for" to handle negative queries honestly

---

### Professional Experience Section

Each role should be a separate chunk with consistent structure:

```markdown
## Professional Experience

### Acme Corp
**Role:** VP of Platform Engineering
**Period:** January 2022 – Present (3 years)
**Location:** San Francisco, CA (Hybrid)
**Keywords:** platform-engineering, kubernetes, mlops, team-leadership

**Context:**
Built and led platform engineering team supporting 200+ developers across 5 product teams.

**Key Achievements:**
- Reduced deployment time from 2 weeks to 4 hours (50x improvement)
- Grew team from 3 to 15 engineers while maintaining <10% attrition
- Achieved 99.95% platform availability (up from 99.5%)

**Technical Highlights:**
- Kubernetes: Managed 50+ clusters across AWS and GCP
- MLOps: Built model serving platform handling 10M inferences/day
- Observability: Prometheus/Grafana stack with SLO-based alerting

**AI Context (Story Behind the Achievement):**
- **Situation:** Developers blocked for weeks waiting for infrastructure
- **Approach:** Built self-service platform with guardrails, not gatekeepers
- **Technical Work:** Kubernetes operators, GitOps with ArgoCD, Backstage developer portal
- **Lessons Learned:** Developer experience and security are not opposites

---
```

**Key Points:**

- Include `**Keywords:**` for explicit matching
- "AI Context" provides the story for behavioral questions
- Keep each role to ~300 words for optimal chunk size

---

### Skills Sections (Topic-Focused)

**DO NOT** create a single "Skills" section. Create separate sections by topic:

```markdown
## Security Skills & Experience
**Keywords:** security, zero-trust, compliance, FedRAMP, SOC 2, Vault, encryption

**Certifications & Compliance:**
- FedRAMP Moderate (led certification)
- SOC 2 Type II (designed controls)
- PCI-DSS (maintained compliance)

**Security Tools:**
- Secrets Management: HashiCorp Vault, AWS Secrets Manager
- Scanning: Snyk, Trivy, Grype, SBOM generation
- Policy: Open Policy Agent, Kyverno

**Architecture Patterns:**
- Zero-trust networking (mTLS, service mesh)
- Defense in depth (network segmentation, WAF, DDoS protection)
- Secure CI/CD (signed commits, image scanning, SLSA compliance)

---

## Programming Languages & Development
**Keywords:** programming, languages, coding, Python, Go, Bash, Rust, software

**Primary Languages:**
- **Python:** Data pipelines, ML tooling, automation (10+ years)
- **Go:** Microservices, Kubernetes operators, CLI tools (5+ years)
- **Bash:** System administration, CI/CD scripting

**Infrastructure as Code:**
- Terraform (AWS, GCP, Azure)
- Pulumi (Python-based IaC)
- Ansible (configuration management)

**Limitations:**
- Not a frontend developer (limited React/Vue)
- No mobile development experience
- Rust: Currently learning, not production-ready

---

## Cloud & Infrastructure
**Keywords:** cloud, AWS, GCP, Azure, Kubernetes, infrastructure, containers

[Similar structure...]
```

**Key Points:**

- Each topic is a separate, searchable chunk
- Include limitations honestly
- Use consistent structure across topics

---

### Failures Section

Each failure should be a separate chunk:

```markdown
## Documented Failures & Lessons Learned

### Failure: The Over-Engineered Platform (2023)
**Keywords:** failure, complexity, maintainability, documentation, lessons

**What Happened:**
Built an internal platform so complex that only I could maintain it. When I moved to another project, it required a complete rewrite within 6 months.

**Root Cause:**
- Prioritized "elegant" architecture over maintainability
- No documentation or knowledge transfer
- Assumed I'd always be available to support it

**What I Learned:**
- Simplicity is a feature, complexity is a liability
- "If only one person understands it, it's not production-ready"
- Now: Always ask "can a new team member maintain this in 6 months?"

**How Behavior Changed:**
- Write documentation as I build, not after
- Favor boring technology over clever solutions
- Require code reviews from junior engineers (if they can't understand it, simplify)

---

### Failure: The Migration That Took 2x Longer (2021)
[Similar structure...]
```

---

## Chunking Strategy

### How Ingest Creates Chunks

The ingest pipeline splits the master document into chunks for memvid indexing:

```text
┌────────────────────────────────────────────────────────────────┐
│  master_resume.md                                              │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼ Parse YAML frontmatter
┌────────────────────────────────────────────────────────────────┐
│  Extract: system_prompt, suggested_questions, tags             │
│  Store separately for runtime use                              │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼ Split by ## headings
┌────────────────────────────────────────────────────────────────┐
│  Chunk 1: Summary                                              │
│  Chunk 2: FAQ - What's her security track record?              │
│  Chunk 3: FAQ - What programming languages...                  │
│  Chunk 4: Experience - Acme Corp                               │
│  Chunk 5: Experience - Previous Company                        │
│  Chunk 6: Security Skills                                      │
│  Chunk 7: Programming Languages                                │
│  Chunk 8: Failure - Over-Engineered Platform                   │
│  ...                                                           │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼ Extract metadata per chunk
┌────────────────────────────────────────────────────────────────┐
│  For each chunk:                                               │
│  - title: Section heading                                      │
│  - keywords: From **Keywords:** line or generated              │
│  - tags: From section or inherited from global                 │
│  - content: Section body text                                  │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼ Index in memvid
┌────────────────────────────────────────────────────────────────┐
│  memvid.put_many([                                             │
│    {"title": "...", "content": "...", "tags": [...]},          │
│    ...                                                         │
│  ])                                                            │
└────────────────────────────────────────────────────────────────┘
```

### Chunk Size Guidelines

| Section Type         | Target Size   | Rationale               |
| -------------------- | ------------- | ----------------------- |
| FAQ Entry            | 150-300 words | Focused, complete answer |
| Experience (per role)| 200-400 words | Full context for one job |
| Skills (per topic)   | 100-200 words | Focused topic cluster   |
| Failure (each)       | 150-250 words | Complete story arc      |
| Summary              | 200-300 words | Overview, not details   |

**Why these sizes?**

- Too small (<100 words): Lacks context, many false positives
- Too large (>500 words): Diluted relevance, topics mix together
- Sweet spot: 150-300 words with clear topic focus

---

## Ingest Pipeline

### Current Implementation

```python
# ingest/ingest.py (simplified)

def ingest_master_resume(filepath: str) -> None:
    # 1. Parse document
    frontmatter, content = parse_markdown(filepath)

    # 2. Extract metadata
    system_prompt = frontmatter['system_prompt']
    suggested_questions = frontmatter['suggested_questions']
    global_tags = frontmatter['tags']

    # 3. Chunk by ## headings
    chunks = split_by_headings(content, level=2)

    # 4. Process each chunk
    frames = []
    for chunk in chunks:
        title = extract_title(chunk)
        keywords = extract_keywords(chunk)  # From **Keywords:** line
        tags = extract_tags(chunk) or global_tags
        body = extract_body(chunk)

        frames.append({
            'title': title,
            'content': body,
            'tags': tags + keywords,
        })

    # 5. Index in memvid
    mv = MemvidEncoder()
    mv.put_many(frames)
    mv.save('resume.mv2')
```

### Future Enhancement: LLM-Augmented Ingest

```python
# Future: Generate additional search terms at ingest time

async def augment_chunk(chunk: dict) -> dict:
    """Use LLM to generate search-friendly metadata."""

    # Generate questions this chunk answers
    questions = await llm.generate(
        f"What 5 questions would this content answer?\n{chunk['content']}"
    )

    # Generate synonyms and related terms
    keywords = await llm.generate(
        f"List 10 keywords and synonyms for searching this content:\n{chunk['content']}"
    )

    return {
        **chunk,
        'generated_questions': questions,
        'generated_keywords': keywords,
    }
```

---

## Examples

### Example: Hypothetical Resume (Demo)

See `data/example_resume.md` for a complete hypothetical example designed to demonstrate the system's capabilities.

### Example: Real Resume

See `data/master_resume.md` for the production resume (Frank Schwichtenberg).

---

## Checklist: Master Document Quality

Before ingesting a master document, verify:

- [ ] Every `suggested_question` has a corresponding FAQ entry
- [ ] FAQ entries use the EXACT question text as the heading
- [ ] Each FAQ entry includes `**Keywords:**` line
- [ ] Skills are split into topic-focused sections (not one giant "Skills" section)
- [ ] Each experience entry has Keywords and AI Context
- [ ] Failures are separate chunks with clear structure
- [ ] No section exceeds 500 words
- [ ] Honest limitations are documented (what they're NOT good at)
- [ ] System prompt includes instructions for handling gaps honestly

---

## Version History

| Version | Date     | Changes                               |
| ------- | -------- | ------------------------------------- |
| 1.0     | Jan 2026 | Initial POR based on retrieval testing |

---

## Related Documents

- [AGENTIC_FLOW.md](./AGENTIC_FLOW.md) - Query transformation and RAG pipeline
- [DESIGN.md](./DESIGN.md) - Overall system architecture
