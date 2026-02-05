# Resume Data Ingestion Pipeline

This directory contains the **data ingestion pipeline** for creating memvid memory files (.mv2) from resume markdown files.

**Key Concept:** This is data ingestion/indexing, **not ML training**. Pre-trained embedding models are used to vectorize and index documents - no model parameters are modified.

## Prerequisites

- Python 3.12+
- UV package manager (for dependency management)

## Quick Start

```bash
# From project root
cd ingest
uv sync                          # Install dependencies
uv run python ingest.py          # Ingest default resume
uv run python ingest.py --verify # Ingest + run verification queries
```

## Data Flow

```
data/example_resume.md (YAML + Markdown)
    ↓
ingest.py (parse, chunk, embed, index)
    ↓
data/.memvid/resume.mv2 (~290KB vector database)
    ↓
memvid-service (Rust gRPC server)
    ↓
api-service (Python FastAPI)
    ↓
Frontend (React UI)
```

The `.mv2` file is a self-contained vector database containing:
- Chunked resume content (~13 frames)
- 384-dimensional embeddings per chunk
- Profile metadata (name, title, email, skills, experience entries)
- Tags for semantic filtering during retrieval

## Embedding Model

**Current:** `BAAI/bge-small-en-v1.5`

- 384 dimensions (2x faster than 768-dim models)
- Trained with hard negative mining (distinguishes "AI" from "Adobe Illustrator")
- Higher MTEB scores than all-mpnet-base-v2 for retrieval tasks
- Model size: ~130MB (downloads automatically on first run)
- Runs locally via `sentence-transformers` (no API keys required)

**Why BGE over MPNet?** Better semantic understanding for acronyms and technical terms common in resumes (e.g., "AI" vs "artificial intelligence").

See `compare_models.py` for the benchmark that drove this choice.

## Commands

### Core Operations

```bash
# Ingest with custom paths
uv run python ingest.py --input data/your_resume.md --output data/.memvid/your_resume.mv2

# Verify semantic quality after ingestion
uv run python ingest.py --verify

# Quiet mode (suppress verbose logs)
uv run python ingest.py --quiet
```

### Testing Tools

```bash
# Validate memvid SDK integration
uv run python test_memvid.py

# Test embedding similarity (validates semantic search)
uv run python test_embeddings.py

# Compare BGE vs MPNet for AI/ML queries
uv run python compare_models.py

# Run full pytest suite (requires: uv sync --extra test)
uv sync --extra test
uv run pytest
```

### Update Workflow

When you update `data/example_resume.md`:

1. Run ingestion: `uv run python ingest.py --verify`
2. Restart memvid-service (it loads the .mv2 file on startup)
3. Restart api-service (it queries memvid-service for data)
4. Frontend automatically picks up new data via API

**Note:** The .mv2 file must be regenerated after ANY resume content changes.

## Chunking Strategy

Content is chunked according to semantic boundaries defined in the resume markdown:

| Section                 | Chunking Strategy  | Tag Example         |
| ----------------------- | ------------------ | ------------------- |
| Professional Experience | One chunk per role | `experience`, `aws` |
| Skills Assessment       | Single chunk       | `skills`            |
| Documented Failures     | One per story      | `failure`, `lessons-learned` |
| Fit Assessment          | Single chunk       | `fit-assessment`    |
| Leadership              | Single chunk       | `leadership`, `management` |

Each chunk includes relevant tags for filtering during semantic search.

## Verification

The `--verify` flag runs test queries to validate semantic quality:

```bash
uv run python ingest.py --verify
```

**Checks performed:**
- Minimum frame count (>= 5 chunks)
- Relevance scores meet threshold (>= 0.3)
- Expected tags are present for domain queries

**Example queries:**
- "Python experience" → expects `experience` or `skills` tags
- "leadership philosophy" → expects `leadership` or `management` tags
- "failure lessons" → expects `failure` tag
- "professional summary" → expects `summary` or `overview` tags

## Integration with Services

The generated `.mv2` file integrates with downstream services:

- **`memvid-service/`** - Rust gRPC server that loads the .mv2 file and handles vector similarity queries (<5ms response time)
- **`api-service/`** - Python FastAPI layer that calls memvid-service and serves profile data to the frontend

**Important:** Services do NOT perform embedding or indexing. The `.mv2` file is a read-only resource mounted at runtime.

## Why Native (Not Containerized)?

Ingestion runs **natively** rather than in containers because:

1. **Apple Silicon NPU acceleration** - sentence-transformers can leverage the Neural Engine for faster embedding generation
2. **Development speed** - Faster iteration when tuning chunking/tagging strategies
3. **Small output** - The .mv2 file (~295KB) is portable and copied into containers for deployment

The output is platform-agnostic, so native ingestion on MacOS produces files that work in Linux containers.
