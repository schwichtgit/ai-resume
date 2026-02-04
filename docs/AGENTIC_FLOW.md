# Agentic Flow Reference

**Version:** 1.0 (January 2026)
**Status:** Plan of Record (POR)

This document describes the end-to-end flow from user question to AI response, including query transformation, RAG retrieval, and LLM generation.

## <div class="page"/>

## Table of Contents

1. [Overview](#overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Query Transformation](#query-transformation)
4. [RAG Pipeline](#rag-pipeline)
5. [LLM Generation](#llm-generation)
6. [Session Management](#session-management)
7. [Error Handling](#error-handling)
8. [Observability](#observability)

## <div class="page"/>

## Overview

The AI Resume Agent uses a three-stage pipeline:

1. **Query Transformation** - Rewrite natural language questions into retrieval-optimized queries
2. **RAG Retrieval** - Fetch relevant context chunks from memvid
3. **LLM Generation** - Generate response using retrieved context + conversation history

```text
┌──────────────────────────────────────────────────────────────────────-─┐
│                           USER QUESTION                                │
│                 "What programming languages does Frank know?"          │
└────────────────────────────────────────────────────────-───────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────-──────────┐
│                     STAGE 1: QUERY TRANSFORMATION                      │
│  ┌───────────────────────────────────────────────────────────-──────┐  │
│  │ LLM rewrites question for retrieval optimization:                │  │
│  │ - "programming languages Frank coding skills Python Go Rust"     │  │
│  │ - May generate multiple query variants                           │  │
│  └────────────────────────────────────────────────────────────────-─┘  │
└───────────────────────────────────────────────────────────────-────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────-───┐
│                        STAGE 2: RAG RETRIEVAL                          │
│  ┌───────────────────────────────────────────────────────────────-──┐  │
│  │ Memvid semantic search (via gRPC to Rust service):               │  │
│  │ - Query: transformed search terms                                │  │
│  │ - Returns: Top-K chunks with scores and metadata                 │  │
│  │ - Latency target: <5ms                                           │  │
│  └────────────────────────────────────────────────────────────────-─┘  │
│                                                                        │
│  Retrieved chunks:                                                     │
│  ┌───────────────────────────────────────────────────────────-─--──┐   │
│  │ [0.92] FAQ: What programming languages does she know?           │   │
│  │ [0.85] Skills: Programming Languages & Development              │   │
│  │ [0.72] Experience: Acme Corp - Technical Highlights             │   │
│  └──────────────────────────────────────────────────────────────--─┘   │
└───────────────────────────────────────────────────────────────────-────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────-───┐
│                       STAGE 3: LLM GENERATION                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Prompt assembly:                                                 │  │
│  │ 1. System prompt (from master document)                          │  │
│  │ 2. Retrieved context (formatted chunks)                          │  │
│  │ 3. Conversation history (last N turns)                           │  │
│  │ 4. User question                                                 │  │
│  └───────────────────────────────────────────────────────────────-──┘  │
│                                                                        │
│  ┌───────────────────────────────────────────────────────────────-──┐  │
│  │ OpenRouter API call (streaming):                                 │  │
│  │ - Model: nvidia/nemotron-nano-9b-v2:free (or similar)            │  │
│  │ - Stream: SSE tokens back to frontend                            │  │
│  └───────────────────────────────────────────────────────────────-──┘  │
└───────────────────────────────────────────────────────────────────-────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────-───┐
│                           AI RESPONSE                                  │
│  "Frank is proficient in Python (10+ years), Go (5+ years),            │
│  and Bash..."                                                          │
└────────────────────────────────────────────────────────────────────────┘
```

## <div class="page"/>

## Architecture Diagram

```text
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Frontend     │     │   API Service   │     │ Memvid Service  │
│   (React SPA)   │     │    (FastAPI)    │     │     (Rust)      │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │ POST /api/v1/chat     │                       │
         │ ───────────────────►  │                       │
         │                       │                       │
         │                       │ 1. Query Transform    │
         │                       │    (local LLM call)   │
         │                       │                       │
         │                       │ 2. gRPC Search()      │
         │                       │ ──────────────────►   │
         │                       │                       │
         │                       │ ◄──────────────────── │
         │                       │    SearchResponse     │
         │                       │                       │
         │                       │ 3. Assemble Prompt    │
         │                       │                       │
         │                       │ 4. OpenRouter Call    │
         │                       │    (streaming)        │
         │                       │          │            │
         │  ◄─── SSE stream ─────│ ◄────────┘            │
         │                       │                       │
         ▼                       ▼                       ▼
```

## <div class="page"/>

## Query Transformation

### Why Transform Queries?

Raw user questions often don't match how information is indexed. Query transformation bridges this gap.

| User Question                   | Problem                 | Transformed Query                                           |
| ------------------------------- | ----------------------- | ----------------------------------------------------------- |
| "What does Frank know?"         | Too vague               | "Frank skills experience expertise capabilities"            |
| "Tell me about his Python work" | Missing context         | "Python programming development projects experience Frank"  |
| "Is he good at security?"       | Evaluative, not factual | "security experience certifications FedRAMP SOC compliance" |

### Transformation Strategies

#### Strategy 1: Keyword Expansion (Recommended for V1)

Fast, simple, deterministic. Use a small LLM to extract keywords.

```python
async def transform_query(question: str) -> str:
    """Transform user question into retrieval-optimized query."""

    prompt = f"""Extract 5-10 search keywords from this question.
Include synonyms and related terms. Output only keywords, space-separated.

Question: {question}
Keywords:"""

    response = await llm.generate(prompt, max_tokens=50)
    return response.strip()

# Example:
# Input:  "What programming languages does Frank know?"
# Output: "programming languages coding Python Go Rust skills development"
```

#### Strategy 2: HyDE (Hypothetical Document Embedding)

Generate a hypothetical answer, then search for similar real content.

```python
async def hyde_transform(question: str) -> str:
    """Generate hypothetical answer for embedding-based search."""

    prompt = f"""Write a brief answer to this question as if you were
a resume document. Include specific details that would appear in a resume.

Question: {question}
Answer:"""

    hypothetical = await llm.generate(prompt, max_tokens=150)
    return hypothetical

# The hypothetical answer is then embedded and used for similarity search.
# This often retrieves better matches than the original question.
```

#### Strategy 3: Multi-Query Expansion

Generate multiple query variants and merge results.

```python
async def multi_query_transform(question: str) -> list[str]:
    """Generate multiple query variants for broader retrieval."""

    prompt = f"""Generate 3 different ways to search for information
that would answer this question. Output one query per line.

Question: {question}
Queries:"""

    response = await llm.generate(prompt, max_tokens=100)
    return [q.strip() for q in response.strip().split('\n') if q.strip()]

# Results from all queries are merged and de-duplicated.
```

### Recommended Approach for V1

Use **Keyword Expansion** for simplicity and speed:

1. Fast (single LLM call with small output)
2. Deterministic (same question → same keywords)
3. Debuggable (easy to inspect transformed queries)
4. Works well with memvid's semantic search

Future iterations can add HyDE or Multi-Query for complex questions.

## <div class="page"/>

## RAG Pipeline

### Retrieval Flow

**Current Implementation**: As of February 2026, the system uses **Ask Mode** with cross-encoder re-ranking for improved retrieval precision.

```python
async def retrieve_context(question: str, top_k: int = 5) -> list[Chunk]:
    """Retrieve relevant chunks from memvid via gRPC using Ask mode with re-ranking."""

    # 1. Call Rust memvid service with Ask mode (hybrid search + re-ranking)
    ask_response = await memvid_client.ask(
        question=question,  # Pass full question (not transformed keywords)
        use_llm=False,      # Get context only, we'll use OpenRouter for generation
        top_k=top_k,
        snippet_chars=300,
        mode="hybrid",      # BM25 lexical + vector semantic + cross-encoder re-ranking
    )

    # 2. Extract pre-formatted context and evidence
    context = ask_response["answer"]  # Pre-formatted context from Ask mode
    chunks_retrieved = ask_response["stats"]["results_returned"]

    # 3. Convert evidence to structured chunks
    return [
        Chunk(
            title=hit["title"],
            content=hit["snippet"],
            score=hit["score"],
            tags=hit["tags"]
        )
        for hit in ask_response["evidence"]
    ]
```

**Ask Mode vs Find Mode:**

| Feature | Find Mode (Legacy) | Ask Mode (Current) |
|---------|-------------------|-------------------|
| Search Algorithm | BM25 or Vector only | Hybrid (BM25 + Vector) |
| Re-ranking | None | Cross-encoder (Reciprocal Rank Fusion) |
| Precision | Lower (single-pass) | Higher (two-pass retrieval + re-rank) |
| Latency | <5ms | <10ms |
| Metadata Filtering | Limited | Full support (filters, temporal, URI scoping) |

**Benefits of Ask Mode:**
- **Better relevance**: Cross-encoder re-ranks initial candidates for higher precision
- **Hybrid search**: Combines lexical (BM25) and semantic (vector) signals
- **Metadata support**: Filter by section, company, skills, time ranges
- **Future-ready**: Supports advanced features (pagination, time-travel queries, adaptive retrieval)

### Context Assembly

Format retrieved chunks for LLM consumption:

```python
def format_context(chunks: list[Chunk]) -> str:
    """Format chunks as context for LLM prompt."""

    if not chunks:
        return "No relevant information found in the knowledge base."

    sections = []
    for i, chunk in enumerate(chunks, 1):
        sections.append(f"""### Source {i}: {chunk.title}
Relevance: {chunk.score:.0%}

{chunk.content}
""")

    return "\n---\n".join(sections)
```

### Retrieval Optimization

| Technique       | Description                 | Status                                 |
| --------------- | --------------------------- | -------------------------------------- |
| Re-ranking      | Cross-encoder re-scores results | ✅ Built-in to Ask mode (Reciprocal Rank Fusion) |
| Metadata filtering | Filter by section, company, keywords | ✅ Supported via `filters` parameter |
| Temporal filtering | Filter by time ranges | ✅ Supported via `start`/`end` timestamps |
| Chunk expansion | Fetch surrounding chunks    | 🔮 Future enhancement                  |
| Score threshold | Drop low-relevance chunks   | ✅ Automatic in Ask mode               |

## <div class="page"/>

## LLM Generation

### Prompt Structure

The final prompt has four components assembled in order:

```text
┌─────────────────────────────────────────────────────────────┐
│ 1. SYSTEM PROMPT (from master document YAML frontmatter)    │
│                                                             │
│    You are helping hiring managers evaluate Jane Smith...   │
│    Be specific with dates, companies, and outcomes.         │
│    Be honest about gaps and limitations.                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. RETRIEVED CONTEXT (from RAG pipeline)                    │
│                                                             │
│    ### Source 1: Programming Languages & Development        │
│    Relevance: 92%                                           │
│    Primary Languages: Python (10+ years), Go (5+ years)...  │
│                                                             │
│    ### Source 2: FAQ - What programming languages...        │
│    Relevance: 85%                                           │
│    Jane's programming skills include...                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. CONVERSATION HISTORY (last N turns)                      │
│                                                             │
│    User: What's her background?                             │
│    Assistant: Jane has 15 years of experience...            │
│                                                             │
│    User: Tell me about her security work.                   │
│    Assistant: Jane led FedRAMP certification at...          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. CURRENT USER QUESTION                                    │
│                                                             │
│    User: What programming languages does she know?          │
└─────────────────────────────────────────────────────────────┘
```

### Prompt Template

```python
def build_prompt(
    system_prompt: str,
    context: str,
    history: list[Message],
    question: str
) -> list[dict]:
    """Build OpenRouter-compatible message list."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": f"""CONTEXT FROM KNOWLEDGE BASE:

{context}

Use this context to answer the user's question. If the context doesn't contain
relevant information, say so honestly. Don't make up information."""}
    ]

    # Add conversation history
    for msg in history[-6:]:  # Last 3 turns (6 messages)
        messages.append({
            "role": msg.role,
            "content": msg.content
        })

    # Add current question
    messages.append({
        "role": "user",
        "content": question
    })

    return messages
```

### Streaming Response

```python
async def generate_response(
    messages: list[dict],
    model: str = "nvidia/nemotron-nano-9b-v2:free"
) -> AsyncIterator[str]:
    """Stream response tokens from OpenRouter."""

    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": messages,
                "stream": True,
                "max_tokens": 1000,
                "temperature": 0.7
            },
            timeout=60.0
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    chunk = json.loads(data)
                    if content := chunk["choices"][0]["delta"].get("content"):
                        yield content
```

## <div class="page"/>

## Session Management

### Session State

Each chat session maintains:

```python
@dataclass
class Session:
    id: str                    # UUID
    created_at: datetime       # Session start
    last_activity: datetime    # Last interaction
    history: list[Message]     # Conversation turns
    metadata: dict             # Optional tracking data
```

### TTL and Cleanup

```python
SESSION_TTL = 1800  # 30 minutes

async def get_or_create_session(session_id: str | None) -> Session:
    """Get existing session or create new one."""

    if session_id and session_id in sessions:
        session = sessions[session_id]
        if (datetime.utcnow() - session.last_activity).seconds < SESSION_TTL:
            session.last_activity = datetime.utcnow()
            return session

    # Create new session
    return Session(
        id=str(uuid4()),
        created_at=datetime.utcnow(),
        last_activity=datetime.utcnow(),
        history=[],
        metadata={}
    )
```

### History Trimming

Keep conversation context manageable:

```python
MAX_HISTORY_TURNS = 10  # Keep last 10 exchanges

def trim_history(session: Session) -> None:
    """Trim history to prevent context overflow."""
    if len(session.history) > MAX_HISTORY_TURNS * 2:
        session.history = session.history[-(MAX_HISTORY_TURNS * 2):]
```

## <div class="page"/>

## Error Handling

### Error Categories

| Error Type         | HTTP Code | User Message                         | Internal Action        |
| ------------------ | --------- | ------------------------------------ | ---------------------- |
| Rate limited       | 429       | "Please wait a moment..."            | Log, increment counter |
| Memvid unavailable | 503       | "Search temporarily unavailable"     | Retry with backoff     |
| OpenRouter error   | 502       | "AI service temporarily unavailable" | Log, return gracefully |
| Invalid session    | 400       | "Session expired, starting new chat" | Create new session     |
| Context too long   | 400       | (internal handling)                  | Trim context, retry    |

### Graceful Degradation

```python
async def chat_with_fallback(question: str, session: Session) -> AsyncIterator[str]:
    """Chat with graceful fallback on errors."""

    try:
        # Try full pipeline
        transformed = await transform_query(question)
        chunks = await retrieve_context(transformed)
        context = format_context(chunks)

    except MemvidUnavailableError:
        # Fall back to no-context mode
        context = "Knowledge base temporarily unavailable. Responding with general information only."
        logger.warning("Memvid unavailable, using no-context fallback")

    try:
        messages = build_prompt(system_prompt, context, session.history, question)
        async for token in generate_response(messages):
            yield token

    except OpenRouterError as e:
        yield f"I apologize, but I'm having trouble generating a response. Please try again. (Error: {e.code})"
        logger.error(f"OpenRouter error: {e}")
```

## <div class="page"/>

## Observability

### Metrics to Track

| Metric                        | Type      | Description                |
| ----------------------------- | --------- | -------------------------- |
| `chat_requests_total`         | Counter   | Total chat requests        |
| `query_transform_latency_ms`  | Histogram | Query transformation time  |
| `memvid_retrieval_latency_ms` | Histogram | Memvid search time         |
| `llm_generation_latency_ms`   | Histogram | OpenRouter response time   |
| `llm_tokens_used`             | Counter   | Tokens consumed (by model) |
| `retrieval_chunks_returned`   | Histogram | Chunks per query           |
| `retrieval_empty_results`     | Counter   | Queries with no results    |
| `session_active_count`        | Gauge     | Active sessions            |

### Structured Logging

```python
import structlog

logger = structlog.get_logger()

async def handle_chat(request: ChatRequest) -> StreamingResponse:
    request_id = str(uuid4())

    logger.info(
        "chat_request_received",
        request_id=request_id,
        session_id=request.session_id,
        question_length=len(request.message)
    )

    # ... processing ...

    logger.info(
        "chat_request_completed",
        request_id=request_id,
        chunks_retrieved=len(chunks),
        transform_ms=transform_time,
        retrieval_ms=retrieval_time,
        total_ms=total_time
    )
```

### Trace Context

Propagate trace IDs through the pipeline:

```text
Request → Transform → Retrieve → Generate
   │          │          │          │
   └──────────┴──────────┴──────────┴──► Same trace_id
```

## <div class="page"/>

## Version History

| Version | Date     | Changes                            |
| ------- | -------- | ---------------------------------- |
| 1.0     | Jan 2026 | Initial POR based on design review |

## <div class="page"/>

## Related Documents

- [MASTER_DOCUMENT_SCHEMA.md](./MASTER_DOCUMENT_SCHEMA.md) - Resume data format for ingestion
- [DESIGN.md](./DESIGN.md) - Overall system architecture
