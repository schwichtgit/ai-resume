# Ontology Knowledge Graph Design

## Status: Stub Implementation (Phase 7)

Full graph RAG is deferred to Phase 10+. Current phase implements entity type annotations during ingest.

## Architecture Overview

### Entity Types

| Type | Description | Example |
| ---- | ----------- | ------- |
| Person | Candidate or referenced individual | Frank Schwichtenberg |
| Company | Employer or organization | Acme Corp |
| Role | Job title or position | Senior Engineer |
| Skill | Technology or competency | Python, Kubernetes |
| Project | Named project or initiative | Resume AI Platform |
| Achievement | Quantified accomplishment | "reduced latency by 40%" |

### Relationship Types

| Relationship | From | To | Example |
| ------------ | ---- | -- | ------- |
| WORKED_AT | Person | Company | Frank -> Acme Corp |
| HELD_ROLE | Person | Role | Frank -> Senior Engineer |
| USED_SKILL | Role/Project | Skill | Resume AI -> Python |
| ACHIEVED | Person/Role | Achievement | Senior Engineer -> "reduced latency" |
| AT_COMPANY | Role | Company | Senior Engineer -> Acme Corp |

### Data Flow

```text
master_resume.md
    |
    v
ingest.py (entity extraction)
    |
    v
.mv2 file (chunks with entity metadata)
    |
    v
memvid-service (vector + entity search)
    |
    v
api-service (hybrid retrieval)
```

### Entity Extraction Strategy

1. **Rule-based extraction**: Regex patterns for companies, dates, metrics
2. **Section-aware tagging**: Leverage markdown structure (## Company Name, ### Role)
3. **Skill extraction**: Match against known skill taxonomy from Skills Assessment section

### Current Implementation (Phase 7 Stub)

- Entity type annotations added to chunks during ingest
- Chunk metadata includes: `entity_types: list[str]`
- No graph database or graph traversal
- No multi-hop reasoning
- Vector search remains the primary retrieval method

### Future Implementation (Phase 10+)

- Full knowledge graph construction from entity/relationship extraction
- Graph database (NetworkX in-process or Neo4j for scale)
- Hybrid retrieval: vector search + graph traversal
- Multi-hop query resolution
- Entity disambiguation with confidence scoring
