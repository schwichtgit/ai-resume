# Memvid Ingest Pipeline

This directory contains the local ingestion pipeline for creating memvid memory files (.mv2) from the master resume.

**Note:** This is data ingestion/indexing, not ML training. No model parameters are updated - documents are embedded and indexed for hybrid retrieval.

## Why Native (Not Containerized)?

The ingest pipeline runs **natively on MacOS** (not in containers) because:

- Apple Silicon Neural Engine (NPU) acceleration requires native execution
- Faster iteration during development
- The output (.mv2 files) is small and can be copied into containers for deployment

## Prerequisites

- Python 3.12+
- UV package manager

## Setup

```bash
cd ingest
uv sync
```

This creates a `.venv` with:

- `memvid-sdk` - Core memory file creation and search
- `sentence-transformers` - Local embedding model support

## Usage

### Ingest from master_resume.md

```bash
uv run python ingest.py
```

Options:

- `--input PATH` - Custom input markdown (default: `data/master_resume.md`)
- `--output PATH` - Custom output .mv2 (default: `data/.memvid/resume.mv2`)
- `--verify` - Run verification queries after ingestion
- `--quiet` - Suppress verbose output

### Run Tests

```bash
# SDK validation test
uv run python test_memvid.py

# Run pytest suite
uv run pytest
```

## Output

Ingestion creates:

- `data/.memvid/resume.mv2` - The memvid memory file (~280KB)

This file contains:

- 13 frames (chunked content) with 768-dimensional embeddings
- Profile metadata
- AI system prompt
- Experience entries (4 companies)
- Skills assessment
- Leadership & management
- Failure stories (3)
- Fit assessment guidance

## Embedding Model

The ingest pipeline uses **`all-mpnet-base-v2`** from sentence-transformers:

- 768-dimensional embeddings
- Optimized for semantic search on professional/career documents
- Runs locally on CPU (no API keys required)
- Model is downloaded on first run (~420MB)

Alternative models can be configured in `ingest.py` by changing `EMBEDDING_MODEL`.

## Chunking Strategy

The ingest script follows the chunking guidance in `master_resume.md`:

| Section                 | Chunking           |
| ----------------------- | ------------------ |
| Professional Experience | By company/role    |
| Skills Assessment       | Single chunk       |
| Documented Failures     | Individual stories |
| Fit Assessment          | Single chunk       |
| Leadership              | Single chunk       |

Each chunk is tagged with relevant keywords for semantic retrieval.

## Verification

Run with `--verify` to test semantic quality:

```bash
uv run python ingest.py --verify
```

Verification checks:

- Minimum frame count (>= 5)
- Score thresholds for relevance (>= 0.3)
- Tag matching for expected content

Test queries:

- "Python experience" → expects `experience` or `skills` tags
- "leadership philosophy" → expects `leadership` or `management` tags
- "failure lessons" → expects `failure` or `lessons-learned` tags
- "professional summary" → expects `summary` or `overview` tags

## Integration

The generated `.mv2` file is used by:

- `memvid-service/` - Rust gRPC service for memvid queries
- `api-service/` - Python FastAPI orchestration layer

**Important:** Containers do NOT embed instance data. The `.mv2` file is mounted into containers at runtime via Podman volumes (see `docs/DESIGN.md` for storage design).
