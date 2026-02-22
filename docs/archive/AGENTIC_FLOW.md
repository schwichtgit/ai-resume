# Agentic Flow Reference

**Version:** 1.1 (February 2026)
**Status:** Plan of Record (POR)

This document describes the end-to-end flow from user question to AI response, including RAG retrieval with Ask mode, LLM generation, and dynamic fit assessment.

**Note on Code Examples:** Code examples in this document are simplified for clarity and may not match the actual implementation exactly. They illustrate concepts and flow rather than production code. For exact implementation details, refer to the source files in `api-service/ai_resume_api/`.

## <div class="page"/>

## Table of Contents

1. [Overview](#overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Chat Flow](#chat-flow)
4. [RAG Pipeline (Ask Mode)](#rag-pipeline-ask-mode)
5. [LLM Generation](#llm-generation)
6. [Fit Assessment with Dynamic Role Classification](#fit-assessment-with-dynamic-role-classification)
7. [Session Management](#session-management)
8. [Error Handling](#error-handling)
9. [Observability](#observability)

## <div class="page"/>

## Overview

The AI Resume Agent uses a three-stage pipeline:

1. **RAG Retrieval** - Fetch relevant context chunks from memvid using Ask mode (hybrid search + cross-encoder re-ranking)
2. **Context Injection** - Inject retrieved context into system prompt as ground truth
3. **LLM Generation** - Generate response using system prompt + context + conversation history

```text
┌──────────────────────────────────────────────────────────────────────┐
│                           USER QUESTION                              │
│                 "What programming languages does she know?"          │
└────────────────────────────────────┬─────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      STAGE 1: RAG RETRIEVAL (Ask Mode)               │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ Memvid semantic search via gRPC (Rust service):                │  │
│  │ - Query: original user question (no transformation)            │  │
│  │ - Mode: hybrid (BM25 lexical + vector semantic)                │  │
│  │ - Re-ranking: cross-encoder (Reciprocal Rank Fusion)           │  │
│  │ - Returns: Top-K chunks with scores and metadata               │  │
│  │ - Latency: <10ms typical                                       │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  Retrieved chunks with pre-formatted context:                        │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ [0.92] Skills: Programming Languages & Development             │  │
│  │ [0.85] FAQ: What programming languages does she know?          │  │
│  │ [0.72] Experience: Acme Corp - Technical Highlights            │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────┐
│                  STAGE 2: CONTEXT INJECTION                          │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ Inject retrieved context into system prompt as ground truth:   │  │
│  │                                                                │  │
│  │ SYSTEM PROMPT:                                                 │  │
│  │   {original_system_prompt}                                     │  │
│  │                                                                │  │
│  │   ---                                                          │  │
│  │   CONTEXT FROM RESUME:                                         │  │
│  │   {retrieved_context}                                          │  │
│  │   ---                                                          │  │
│  │                                                                │  │
│  │   Use the context above to answer the user's question...       │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       STAGE 3: LLM GENERATION                        │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ Prompt assembly:                                               │  │
│  │ 1. System prompt (with injected context)                       │  │
│  │ 2. Conversation history (last N turns)                         │  │
│  │ 3. User question                                               │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ OpenRouter API call (streaming):                               │  │
│  │ - Model: configurable via settings                             │  │
│  │ - Stream: SSE tokens back to frontend                          │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────┐
│                           AI RESPONSE                                │
│  "She is proficient in Python (10+ years), Go (5+ years),            │
│  and Bash..."                                                        │
└──────────────────────────────────────────────────────────────────────┘
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
         │                       │ 1. Load Profile       │
         │                       │    (system prompt +   │
         │                       │     metadata)         │
         │                       │        │              │
         │                       │        ▼              │
         │                       │ gRPC GetState()       │
         │                       │ ──────────────────►   │
         │                       │                       │
         │                       │ ◄──────────────────── │
         │                       │  Profile metadata     │
         │                       │                       │
         │                       │ 2. Retrieve Context   │
         │                       │ gRPC Ask()            │
         │                       │ ──────────────────►   │
         │                       │                       │
         │                       │ ◄──────────────────── │
         │                       │    AskResponse        │
         │                       │                       │
         │                       │ 3. Inject Context     │
         │                       │    into System Prompt │
         │                       │                       │
         │                       │ 4. OpenRouter Call    │
         │                       │    (streaming)        │
         │                       │          │            │
         │  ◄─── SSE stream ─────│ ◄────────┘            │
         │                       │                       │
         ▼                       ▼                       ▼
```

## <div class="page"/>

## Chat Flow

### Endpoint: POST /api/v1/chat

**Current Implementation** (as of February 2026)

```python
async def chat(request: Request, chat_request: ChatRequest):
    """Chat endpoint with streaming SSE response."""

    # 1. Get or create session
    session = session_store.get_or_create(chat_request.session_id)

    # 2. Input guardrail check
    is_safe, blocked_response = check_input(chat_request.message)
    if not is_safe:
        return blocked_response

    # 3. Retrieve context from memvid (Ask mode with re-ranking)
    ask_response = await memvid_client.ask(
        question=chat_request.message,  # Original question, no transformation
        use_llm=False,  # Get context only
        top_k=5,
        snippet_chars=300,
        mode="hybrid",  # BM25 + vector + cross-encoder re-ranking
    )

    context = ask_response["answer"]  # Pre-formatted context string
    chunks_retrieved = ask_response["stats"]["results_returned"]

    # 4. Early return if no context found
    if chunks_retrieved == 0:
        return "I couldn't find relevant information to answer that question..."

    # 5. Get conversation history
    history = session.get_history_for_llm(settings.max_history_messages)

    # 6. Add user message to session
    session.add_message("user", chat_request.message)

    # 7. Stream response from OpenRouter
    return StreamingResponse(
        _stream_chat_response(
            openrouter_client,
            context,
            chat_request.message,
            history,
            session,
            session_store,
            chunks_retrieved,
        ),
        media_type="text/event-stream",
    )
```

**Note:** Query transformation is currently disabled due to acronym expansion issues. The original user question is passed directly to Ask mode.

## <div class="page"/>

## RAG Pipeline (Ask Mode)

### Retrieval Flow

**Current Implementation:** Uses **Ask Mode** with cross-encoder re-ranking for improved precision.

```python
async def retrieve_context(question: str, top_k: int = 5) -> dict:
    """Retrieve relevant chunks from memvid via gRPC using Ask mode."""

    # Call Rust memvid service with Ask mode (hybrid search + re-ranking)
    ask_response = await memvid_client.ask(
        question=question,  # Pass full question
        use_llm=False,      # Get context only, we'll use OpenRouter for generation
        top_k=top_k,
        snippet_chars=300,
        mode="hybrid",      # BM25 lexical + vector semantic + cross-encoder
    )

    # Returns dict with:
    # {
    #     "answer": "pre-formatted context string",
    #     "evidence": [{"title": "...", "snippet": "...", "score": 0.92}, ...],
    #     "stats": {
    #         "results_returned": 3,
    #         "candidates_retrieved": 50,
    #         "retrieval_ms": 4.2,
    #         "reranking_ms": 8.7
    #     }
    # }

    return ask_response
```

**Ask Mode Benefits:**

| Feature               | Description                                                    |
| --------------------- | -------------------------------------------------------------- |
| Hybrid Search         | Combines BM25 (lexical) and vector (semantic) signals          |
| Re-ranking            | Cross-encoder scores query-document pairs for better precision |
| Pre-formatted Context | Returns ready-to-use context string for LLM prompts            |
| Metadata Support      | Filter by section, company, skills, time ranges                |
| Low Latency           | <10ms typical (retrieval + re-ranking)                         |

### Context Assembly

The Ask mode returns `ask_response["answer"]` as a pre-formatted context string ready for LLM consumption:

```text
### Source 1: Skills Assessment
Relevance: 92%

Primary Languages: Python (10+ years), Go (5+ years), Bash/Shell...

---

### Source 2: FAQ - What programming languages does she know?
Relevance: 85%

Jane's programming skills include Python, Go, Rust...
```

This pre-formatted context is passed directly to the LLM prompt.

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
│ 2. RETRIEVED CONTEXT (pre-formatted from Ask mode)          │
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

### Prompt Assembly Code

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

    # Add conversation history (trimmed to last N turns)
    for msg in history:
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
async def _stream_chat_response(
    openrouter_client,
    context: str,
    user_message: str,
    history: list,
    session,
    session_store,
    chunks_retrieved: int,
) -> AsyncIterator[str]:
    """Generate streaming SSE response."""

    # Send retrieval info
    event = ChatStreamEvent(type="retrieval", chunks=chunks_retrieved)
    yield f"data: {event.model_dump_json()}\n\n"

    # Stream tokens from OpenRouter
    full_response = ""
    async for chunk in openrouter_client.chat_stream(
        system_prompt=settings.get_system_prompt_from_profile(),
        context=context,
        user_message=user_message,
        history=history,
    ):
        if chunk.content:
            full_response += chunk.content
            event = ChatStreamEvent(type="token", content=chunk.content)
            yield f"data: {event.model_dump_json()}\n\n"

    # Save response to session
    session.add_message("assistant", full_response)
    session_store.set(session.id, session)

    # Send stats event
    stats_data = {
        "chunks_retrieved": chunks_retrieved,
        "tokens_used": tokens_used,
        "elapsed_seconds": elapsed,
        "trace_id": get_trace_id(),
    }
    yield f"event: stats\ndata: {json.dumps(stats_data)}\n\n"

    # Send completion event
    yield "event: end\ndata: [DONE]\n\n"
```

## <div class="page"/>

## Fit Assessment with Dynamic Role Classification

### Overview

The `/api/v1/assess-fit` endpoint evaluates candidate fit against job descriptions using a **dynamic role classification system** that selects appropriate assessor personas based on career domain and seniority level.

```text
┌────────────────────────────────────────────────────────────────┐
│                    JOB DESCRIPTION INPUT                       │
│   "Chief Technology Officer - Lead 100+ engineers..."          │
└─────────────────────────┬──────────────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────────────┐
│              STAGE 1: ROLE CLASSIFICATION                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 1. Domain Detection (word-boundary keyword matching):    │  │
│  │    - Technology: software, cloud, API, distributed...    │  │
│  │    - Culinary: chef, kitchen, menu, gastronomy...        │  │
│  │    - Finance: trader, quant, portfolio, derivatives...   │  │
│  │    - Life Sciences: biotech, clinical, R&D, FDA...       │  │
│  │    - Healthcare: patient care, nursing, clinical ops...  │  │
│  │    - Sales: revenue, quota, SaaS, pipeline, CRM...       │  │
│  │                                                          │  │
│  │ 2. Primary/Secondary Domain with Confidence:             │  │
│  │    - Primary: technology (score: 12)                     │  │
│  │    - Secondary: None (no other domain >= 3 keywords)     │  │
│  │    - Confident: True (gap >= 2)                          │  │
│  │                                                          │  │
│  │ 3. Role Level Detection (title pattern matching):        │  │
│  │    - C-Suite: CTO, CIO, Chief X Officer                  │  │
│  │    - VP: Vice President, SVP                             │  │
│  │    - Director: Director, Head of X                       │  │
│  │    - Manager: Engineering Manager, Team Lead             │  │
│  │    - IC-Senior: Staff/Principal Engineer, Architect      │  │
│  │    - IC: Engineer, Developer, SRE                        │  │
│  │                                                          │  │
│  │ Result: domain="technology", level="c-suite"             │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────────────┐
│            STAGE 2: PERSONA & CRITERIA SELECTION               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Selected Assessor Persona (technology + c-suite):        │  │
│  │   "You are a board-level executive recruiter who has     │  │
│  │    placed hundreds of C-suite technology leaders..."     │  │
│  │                                                          │  │
│  │ Evaluation Criteria:                                     │  │
│  │   - Org-wide technical strategy ownership                │  │
│  │   - Board/investor communication                         │  │
│  │   - P&L authority at company scale                       │  │
│  │   - Team scale (100+ engineers)                          │  │
│  │   - Industry thought leadership                          │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────────────┐
│              STAGE 3: CONTEXT RETRIEVAL (ASK MODE)             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Query memvid with Ask mode (hybrid + re-ranking):        │  │
│  │   "What relevant experience, skills, and qualifications  │  │
│  │    does the candidate have for this role: [JD]..."       │  │
│  │                                                          │  │
│  │ Retrieved context (top_k=10, snippet_chars=500):         │  │
│  │   - [0.94] Experience: CTO at Acme Corp (2018-2023)      │  │
│  │   - [0.88] Leadership: Built 120-person eng org          │  │
│  │   - [0.82] Strategy: Cloud migration $50M project        │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────────────┐
│                STAGE 4: LLM ASSESSMENT GENERATION              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Prompt Structure:                                        │  │
│  │   1. System Prompt: Selected assessor persona            │  │
│  │   2. Job Description                                     │  │
│  │   3. Candidate Context (retrieved from memvid)           │  │
│  │   4. Domain Classification Note (if cross-domain)        │  │
│  │   5. Evaluation Instructions:                            │  │
│  │      - Step 1: Domain Check (tech vs culinary?)          │  │
│  │      - Step 2: Role Title Identification                 │  │
│  │      - Step 3: Seniority Gap Assessment                  │  │
│  │      - Step 4: Criteria Evaluation                       │  │
│  │      - Step 5: Star Rating with Rubric                   │  │
│  │                                                          │  │
│  │ Star Rating Rubric:                                      │  │
│  │   ⭐      = Different domain (tech vs culinary)          │  │
│  │   ⭐⭐    = Weak fit (<40% requirements met)             │  │
│  │   ⭐⭐⭐  = Partial fit (40-60% met)                     │  │
│  │   ⭐⭐⭐⭐ = Strong fit (60-80% met)                     │  │
│  │   ⭐⭐⭐⭐⭐ = Exceptional fit (>80% met)                │  │
│  └─────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────────────┐
│                      STRUCTURED OUTPUT                         │
│  VERDICT: ⭐⭐⭐⭐ Strong fit - Senior Director → CTO           │
│                                                                │
│  ROLE LEVEL:                                                   │
│  - JD Title: Chief Technology Officer                          │
│  - Candidate Title: Senior Director of Engineering             │
│  - Gap: One level jump (Director → CTO) requires scope proof   │
│                                                                │
│  KEY MATCHES:                                                  │
│  - Led 120-person engineering organization at Acme             │
│  - $50M cloud migration demonstrates company-scale execution   │
│  - Board presentation experience (quarterly eng updates)       │
│                                                                │
│  GAPS:                                                         │
│  - No prior C-level title (currently Director-level)           │
│  - Limited external thought leadership (2 conference talks)    │
│                                                                │
│  RECOMMENDATION: Strong candidate with scope gap. Led org at   │
│  CTO scale (120 engineers) despite Director title. Recommend   │
│  for interview to assess exec communication and strategy.      │
└────────────────────────────────────────────────────────────────┘
```

### Role Classification Algorithm

**Domain Detection (Word-Boundary Matching):**

```python
def classify_domain(job_description: str) -> dict:
    """Score each domain by keyword frequency using word-boundary regex."""

    scores = {}
    for domain, config in CAREER_DOMAINS.items():
        score = 0
        for keyword in config["keywords"]:
            # Use \b word boundaries to prevent false positives
            pattern = re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE)
            if pattern.search(job_description):
                score += 1
        scores[domain] = score

    # Require minimum 3 keyword matches
    # Report primary + secondary if secondary >= 3 and gap < 2
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    primary, primary_score = ranked[0]
    secondary, secondary_score = ranked[1] if len(ranked) > 1 else (None, 0)

    confident = (primary_score - secondary_score) >= 2

    return {
        "primary": primary if primary_score >= 3 else None,
        "secondary": secondary if secondary_score >= 3 else None,
        "confident": confident
    }
```

**Cross-Domain Handling:**

When a JD triggers multiple domains (e.g., "VP of Engineering at a healthcare company"), the system:

1. Reports both primary and secondary domain
2. Flags the classification as ambiguous if keyword gap < 2
3. Injects context into the LLM prompt:

```text
DOMAIN CLASSIFICATION NOTE: This JD was classified as primarily 'technology'
with secondary signals from 'healthcare'. The classification is ambiguous —
consider whether the role is genuinely cross-domain (e.g., a tech role at a
healthcare company).
```

**Benefits:**

- **Domain-specific evaluation**: Culinary candidates assessed by hospitality recruiters, tech candidates by engineering recruiters
- **Cross-domain awareness**: VP Eng at health tech gets both tech and healthcare context
- **Prevents false positives**: Word boundaries stop "AI" from matching "catering", "SRE" from matching "desire"
- **Prevents domain mismatch**: Culinary JD vs tech resume correctly rates ⭐ (different profession)
- **Seniority calibration**: Director→VP jump is acknowledged and assessed for scope equivalence

### Supported Domains

| Domain              | Keywords (Sample)                                 | Role Levels                                   | Use Case                                      |
| ------------------- | ------------------------------------------------- | --------------------------------------------- | --------------------------------------------- |
| **Technology**      | software, cloud, API, distributed, ML             | c-suite, vp, director, manager, ic-senior, ic | Software engineers, CTOs, SREs                |
| **Culinary**        | chef, culinary, menu, michelin, gastronomy        | c-suite, director                             | Executive chefs, culinary directors           |
| **Finance/Trading** | trader, quant, portfolio, derivatives, hedge fund | c-suite, ic-senior                            | Quant traders, portfolio managers             |
| **Life Sciences**   | biotech, clinical, R&D, FDA, pharmacology         | director, ic                                  | Drug discovery scientists, clinical directors |
| **Healthcare**      | patient care, nursing, clinical ops, HIPAA        | c-suite, manager                              | CMOs, nurse managers, clinic directors        |
| **Sales/Growth**    | revenue, quota, SaaS, pipeline, ARR               | vp, ic                                        | VPs of Sales, account executives              |

### Testing

The role classifier has comprehensive E2E test coverage (35 tests, 96% code coverage):

```bash
cd api-service
pytest tests/test_role_classifier_e2e.py -v
```

Tests validate:

- Domain classification accuracy across all 6 domains
- Role level detection (c-suite through ic)
- Word-boundary matching (prevents false positives)
- Cross-domain scenarios (VP Eng at healthcare company)
- Ambiguous classifications (RevOps spanning sales + tech)
- Confidence scoring and thresholds

## <div class="page"/>

## Session Management

### Implementation

Sessions use `cachetools.TTLCache` for automatic expiration with thread-safe access:

```python
from cachetools import TTLCache
import threading

class SessionStore:
    def __init__(self, ttl_seconds: int = 1800, maxsize: int = 10000):
        self._cache = TTLCache(maxsize=maxsize, ttl=ttl_seconds)
        self._lock = threading.Lock()

    def get_or_create(self, session_id: UUID | None = None) -> Session:
        """Get existing session or create new one."""
        with self._lock:
            if session_id:
                session = self._cache.get(session_id)
                if session:
                    return session

            # Create new session
            session = Session()
            self._cache[session.id] = session
            return session
```

### Session Structure

```python
@dataclass
class Session:
    id: UUID
    created_at: datetime
    last_activity: datetime
    messages: list[Message]  # Conversation history

    def add_message(self, role: str, content: str):
        """Add message to conversation history."""
        self.messages.append(Message(role=role, content=content))

    def get_history_for_llm(self, max_messages: int) -> list[Message]:
        """Get last N messages for LLM context."""
        return self.messages[-max_messages:] if max_messages else self.messages
```

### History Trimming

History is trimmed **at prompt assembly time** (not at storage time):

```python
# In chat endpoint (main.py)
history = session.get_history_for_llm(settings.max_history_messages)
```

This allows flexible history windows per request while preserving full history in the session.

### TTL Behavior

- Sessions automatically expire after 1800 seconds (30 minutes) of inactivity
- `TTLCache` handles expiration automatically (no manual cleanup needed)
- Thread-safe with `threading.Lock` for concurrent access

## <div class="page"/>

## Error Handling

### Error Categories

| Error Type         | HTTP Code | User Message                         | Internal Action        |
| ------------------ | --------- | ------------------------------------ | ---------------------- |
| Rate limited       | 429       | "Please wait a moment..."            | Log, increment counter |
| Memvid unavailable | 503       | "Search temporarily unavailable"     | Retry with backoff     |
| OpenRouter error   | 502       | "AI service temporarily unavailable" | Log, return gracefully |
| Invalid session    | 400       | "Session expired, starting new chat" | Create new session     |

### Graceful Degradation

```python
async def chat_with_fallback(question: str, session: Session):
    """Chat with graceful fallback on errors."""

    try:
        # Try Ask mode retrieval
        ask_response = await memvid_client.ask(question=question, ...)
        context = ask_response["answer"]

    except MemvidConnectionError:
        # Return early with error message
        raise HTTPException(
            status_code=503,
            detail="Search service unavailable. Please try again later.",
        )

    try:
        # Stream response from OpenRouter
        async for token in openrouter_client.chat_stream(...):
            yield token

    except OpenRouterError as e:
        yield f"I apologize, but I'm having trouble generating a response..."
        logger.error(f"OpenRouter error: {e}")
```

## <div class="page"/>

## Observability

### Current Implementation

**Prometheus Metrics (via Instrumentator):**

The API service exposes Prometheus metrics at `/metrics`:

```python
# main.py
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)
```

**Structured Logging (via structlog):**

```python
import structlog

logger = structlog.get_logger()

logger.info(
    "chat_request_received",
    session_id=session.id,
    message_length=len(chat_request.message)
)
```

**Trace Context Propagation:**

```python
# Middleware adds X-Trace-ID to every request
@app.middleware("http")
async def trace_id_middleware(request: Request, call_next):
    trace_id = request.headers.get("X-Trace-ID", generate_trace_id())
    set_trace_id(trace_id)

    # Bind to structlog context
    structlog.contextvars.bind_contextvars(trace_id=trace_id)

    response = await call_next(request)
    response.headers["X-Trace-ID"] = trace_id
    return response
```

### Custom Metrics (Implemented)

Currently implemented custom metrics:

- `memvid_search_latency_seconds` - Histogram of memvid search times (memvid_client.py)

### Planned Metrics

Future metrics to add:

- `chat_requests_total` - Counter of chat requests
- `llm_tokens_used` - Counter of tokens consumed by model
- `retrieval_chunks_returned` - Histogram of chunks per query
- `retrieval_empty_results` - Counter of queries with no results

## <div class="page"/>

## Version History

| Version | Date     | Changes                                                                                                           |
| ------- | -------- | ----------------------------------------------------------------------------------------------------------------- |
| 1.0     | Jan 2026 | Initial POR based on design review                                                                                |
| 1.1     | Feb 2026 | Updated to reflect current implementation (Ask mode, disabled query transform, TTLCache sessions, fit assessment) |

## <div class="page"/>

## Related Documents

- [MASTER_DOCUMENT_SCHEMA.md](./MASTER_DOCUMENT_SCHEMA.md) - Resume data format for ingestion
- [ARCHITECTURE.md](./ARCHITECTURE.md) - Overall system architecture
- [TODO.md](./TODO.md) - Development roadmap and phase tracking
