# Medium Article Series: Narrative Templates

Fill in the `>>> YOUR INPUT` blocks. Leave my pre-filled "FROM CODE" sections as-is -- I'll weave them together with your narrative in the final drafts. Delete the guiding questions once you've answered them.

---

## ARTICLE 2: "The Pipeline"

---

### Q1: The Memvid Discovery Story

**FROM CODE:** The project depends on memvid in two layers: Python SDK (2.0.153) for ingestion, Rust core (2.0.135) for runtime search. The architecture isolates these -- Python is never loaded at runtime. The `.mv2` file replaces an entire vector DB stack. The production target is a NanoPi R6S (ARM64, 4GB RAM, no swap). Three upstream bugs were filed Feb 7-8, 2026 (#194, #195, #196), each with standalone reproduction scripts. The comparison table in `technical-report-for-medium.md:1076-1083` already covers memvid vs Pinecone/Weaviate/ChromaDB.

**FROM CODE (the bugs):**

- Bug A (#194): `MemvidRetriever.open()` never sets `vec_enabled=True`, so vec search raises `MV011`. Hybrid silently degrades to lex-only. Irrelevant at runtime because Rust reads directly.
- Bug B (#195): SDK 2.0.156 bundles internal core at 2.0.156, but crates.io only has 2.0.136. 20-version gap causes `bincode enum discriminant 75502700 out of range`. Fix: pin SDK to 2.0.153.
- Bug C (#196): Fresh `.mv2` files load and `search()` works, but `ask()` fails with "frame id out of range" in the time index. Fix: `memvid doctor --rebuild-time-index` after ingestion.

> > > YOUR INPUT: The discovery

How did you find memvid? (GitHub trending? HN? Recommendation? Research for a specific need?)

_[Write here]_

> > > YOUR INPUT: What came before

Were you using anything before memvid? (ChromaDB prototype? FAISS? Starting fresh?) What was the selection process?

_[Write here]_

> > > YOUR INPUT: The bug experience

You hit 3 upstream bugs in 2 days. Walk me through the emotional arc. Was there a moment of regret? Did you consider switching? How long did the reproduction scripts take to write?

_[Write here]_

> > > YOUR INPUT: The upstream relationship

Has the memvid maintainer responded to any of the 3 issues? What was the interaction like? Is this a solo maintainer or a team?

_[Write here]_

> > > YOUR INPUT: The MP4 angle

Memvid stores data in an MP4-based format. Was that a factor in the decision -- curiosity, novelty, or just irrelevant plumbing?

_[Write here]_

---

### Q2: The Search Architecture Journey

**FROM CODE:** The commit history shows a clear Find → Ask mode transition. Find mode = raw vector similarity, no BM25, no re-ranking. Limitations documented in `ARCHITECTURE.md:129-145`: cannot distinguish context (e.g., "AI" = artificial intelligence vs Adobe Illustrator), distance-only ranking.

Commit `72e788e` (Feb 4): "Implement Ask mode with cross-encoder re-ranking and full API support." Added hybrid BM25 + vector with re-ranking.

A `query_transform.py` exists but is disabled in production. Comment in `main.py:261-278`: "TEMPORARILY DISABLED: Query transformation was expanding 'AI' to 'artificial intelligence' which doesn't match 'AI/ML' content." The prompt template even includes "IMPORTANT: For acronyms like AI, ML, DevOps, CI/CD -- include BOTH the acronym AND the expanded form" -- evidence the fix was attempted in-prompt but failed.

Embedding model choice (`ingest/ingest.py:28-34`): BAAI/bge-small-en-v1.5, chosen specifically for hard-negative mining ("distinguishes 'AI' from 'Adobe Illustrator'"), 384 dims, 130MB, asymmetric retrieval.

Chat uses `top_k=5, snippet_chars=300`. Fit assessment uses `top_k=10, snippet_chars=500`.

> > > YOUR INPUT: Was hybrid the plan from the start?

Did you start with vector-only search intentionally (as an MVP), or was hybrid always the goal? When did you realize vector-only wasn't enough?

_[Write here]_

> > > YOUR INPUT: The queries that failed

What specific queries or query types failed under Find mode that forced the move to Ask? Were there specific user interactions or test scenarios that broke?

_[Write here]_

> > > YOUR INPUT: The "AI" problem

The acronym problem is well-documented in code comments. Was this discovered through testing, a live demo, or something else? Walk me through the moment you realized "AI" was matching the wrong things.

_[Write here]_

> > > YOUR INPUT: Query transformation -- tried and abandoned

You built query_transform.py, it didn't work, you disabled it. Was the fix to improve the embedding model and switch to hybrid search a deliberate alternative, or did those happen independently?

_[Write here]_

> > > YOUR INPUT: The top_k tuning

Chat gets 5 chunks, fit assessment gets 10. Was this tuned empirically (you tried different values and measured quality), or was it a design decision from the start?

_[Write here]_

> > > YOUR INPUT: The moment hybrid "clicked"

Was there a specific query or test where hybrid search visibly outperformed vector-only? What did the before/after look like?

_[Write here]_

---

### Q3: Cross-Encoder Re-Ranking

**FROM CODE:** Re-ranking is built into memvid SDK's native Ask mode, not a custom implementation. The Rust service (`memvid-service/src/memvid/real.rs:204-344`) maps gRPC `AskRequest` to `memvid_core::AskRequest` and calls `memvid.ask()` directly. Architecture: 50 candidates retrieved → re-ranked → top 5 returned.

The proto has separate `retrieval_ms` and `reranking_ms` fields (`proto/memvid/v1/memvid.proto:109-120`), but the Rust implementation sets `reranking_ms: 0` because memvid-core doesn't expose it separately.

`ARCHITECTURE.md:175` notes: "Using memvid SDK's native Ask capabilities; custom cross-encoder model selection is future research."

> > > YOUR INPUT: Observability gap

You designed telemetry fields (reranking_ms) that the library doesn't yet expose. Was this intentional forward-design, or did you expect memvid to populate them?

_[Write here]_

> > > YOUR INPUT: Before/after quality

Was there an observable difference in result quality when you switched from Find to Ask mode? Can you describe what changed -- specific queries that suddenly worked, or a general improvement in relevance?

_[Write here]_

> > > YOUR INPUT: Alternative approaches considered

Did you evaluate other re-ranking approaches? (Custom cross-encoder, Cohere rerank API, LLM-as-reranker, etc.) Or was "use what memvid provides" always the plan?

_[Write here]_

---

### Q4: The "Agentic" Framing

**FROM CODE:** `AGENTIC_FLOW.md` describes a 3-stage pipeline: RAG Retrieval → Context Injection → LLM Generation. The system has:

- No tool use definitions
- No planning loops
- No self-reflection or self-evaluation
- No multi-step reasoning
- No autonomous decision-making about what action to take next
- Single LLM call per user message

The closest to "agentic" behavior is the role classifier dynamically selecting an evaluator persona based on JD domain and seniority. This is conditional routing, not agent planning.

The Phase 3 roadmap in `ARCHITECTURE.md` mentions "Multi-agent orchestration" and "Tool calling" as future work.

> > > YOUR INPUT: What do you mean by "agentic"?

Article 1 promises readers "The Agentic Flow." But the code is standard RAG with guardrails. How do you want to frame this honestly for the Medium audience? Options to consider:

- **Option A:** "We call it agentic because the role classifier makes autonomous evaluation decisions -- it's the seed of agentic behavior, not the full flower."
- **Option B:** "Agentic is aspirational. Here's what we built (RAG + conditional routing), here's what makes it different from a naive chatbot, and here's what a truly agentic version would look like."
- **Option C:** "The word 'agentic' is overloaded. Here's our definition: a system that adapts its behavior based on input analysis. The role classifier qualifies."
- **Option D:** Something else entirely.

_[Write here]_

> > > YOUR INPUT: The honest distinction

What do you think is the real gap between "a RAG chatbot" and what you built? Not the marketing -- what actually makes this different from someone who just threw LangChain + ChromaDB together?

_[Write here]_

---

## ARTICLE 3: "The Vision"

---

### Q5: The Moment Role Classification Was Born

**FROM CODE:** The role classifier (`role_classifier.py`, 691 lines) defines 6 career domains: technology, culinary, finance_trading, life_sciences, healthcare, sales_growth. Each has keyword dictionaries with word-boundary regex and up to 6 seniority levels. Confidence gap = 2 keyword matches. Minimum 3 matches to classify.

The technical report (`technical-report-for-medium.md:309-337`) frames the strategic problem: without classification, "Has leadership experience" matches both a VP of Engineering and an Executive Chef. A Director applying for a CTO gets no scope gap acknowledgment.

Git history shows 3 key commits:

- `a7813ba`: "Dynamic role classification for fit assessment accuracy"
- `9201d8c`: "Multi-domain role classifier with cross-domain detection"
- `5435b26`: "Add domain mismatch check to prevent contradictory fit ratings"

> > > YOUR INPUT: The inciting incident

What specific bad fit assessment made you realize a generic evaluator wasn't enough? Was there a real JD that produced a laughably wrong result? Walk me through the moment.

_[Write here]_

> > > YOUR INPUT: Why culinary?

Culinary is the most obviously absurd mismatch domain for a tech candidate. Was it the first "ridiculous mismatch" you tested? Was there a specific chef JD that rated too high? Or did culinary come from a different motivation?

_[Write here]_

> > > YOUR INPUT: The word-boundary discovery

The code uses `\b` word boundaries to prevent "AI" from matching "catering." Was this fix driven by a specific false positive you hit in testing?

_[Write here]_

---

### Q6: Design Choices You Rejected

**FROM CODE:**

Rejected/abandoned approaches discoverable from code:

1. **Query transformation** (`query_transform.py`): Built, tested, disabled. Acronym expansion broke more than it fixed.
2. **`all-mpnet-base-v2` embedding model**: The `ingest.py` comment explicitly compares against it (420MB, 768 dims). BGE was chosen for hard-negative mining.
3. **`Math.random()` for session IDs**: Replaced with `crypto.getRandomValues()` after CodeQL alert.
4. **Architecture Options 1-4**: `ARCHITECTURE.md:15` says "Option 5: Hybrid Rust + Python" was selected, implying 4 alternatives existed.
5. **`compare_models.py`**: An embedding model comparison script exists in `ingest/` -- models were evaluated.

> > > YOUR INPUT: Why regex over LLM for domain detection?

The role classifier uses regex keyword matching, not the LLM. Was LLM-based classification tried? What drove the regex decision -- speed, determinism, cost, transparency, all of the above?

_[Write here]_

> > > YOUR INPUT: Why 6 domains? Did you start with fewer?

The 6 domains feel deliberate. Were there originally fewer (e.g., just technology + a mismatch domain)? Did you add domains iteratively? Was there a domain you considered but dropped?

_[Write here]_

> > > YOUR INPUT: The architecture options

`ARCHITECTURE.md` says "Option 5" was chosen. What were Options 1-4? (Python-only? TypeScript? Rust-only? Something else?) What killed each one?

_[Write here]_

> > > YOUR INPUT: The model comparison

`ingest/compare_models.py` exists. What did it show? Which models were evaluated, and what made BGE win? Was there a runner-up?

_[Write here]_

> > > YOUR INPUT: Frontend choices

The frontend is a custom React SPA -- not Streamlit, not Gradio, not Next.js. Was anything else tried first? Why custom React?

_[Write here]_

---

### Q7: A Real Fit Assessment Walkthrough

**FROM CODE:** The full fit assessment pipeline lives in `main.py:643-839`:

1. JD comes in (min 50 chars)
2. `classify_job_description()` runs domain + level detection
3. memvid Ask with `top_k=10, snippet_chars=500` retrieves candidate context
4. LLM receives: assessor persona, JD, candidate context, 7-step evaluation instructions, star rubric, mandatory rules
5. Output parsed into: VERDICT, ROLE LEVEL, KEY MATCHES, GAPS, RECOMMENDATION

Star rubric: 1 = different domain, 2 = weak (<40%), 3 = partial (40-60%), 4 = strong (60-80%), 5 = exceptional (>80%).

Mandatory rules: "Different professional domain = 1 star maximum," "A seniority gap should reduce the rating by at least one star," "The star rating MUST be consistent with GAPS and RECOMMENDATION."

> > > YOUR INPUT: Walk me through a strong-fit assessment

Pick a real VP of Engineering or similar tech leadership JD. Paste the JD (or a summary), then paste the actual system output: verdict, star rating, role level analysis, matches, gaps, recommendation. Let me see the real text.

_[Write here -- paste actual JD summary and output]_

> > > YOUR INPUT: Walk me through a mismatch assessment

Now a deliberate mismatch -- a culinary JD, or a finance trading role, or something clearly outside your domain. What does the system actually produce? Paste the output.

_[Write here -- paste actual JD summary and output]_

> > > YOUR INPUT: Has the system ever been wrong?

Has there been a case where the star rating was too generous or too harsh? How did you tune the rubric? Did the "mandatory rules" enforcement work reliably, or does the LLM sometimes ignore them?

_[Write here]_

> > > YOUR INPUT: Recruiter reactions

Has anyone outside of you used the fit assessment? What was their reaction to the output format? Did anyone find the star rating or the gap analysis useful?

_[Write here]_

---

### Q8: The Product Arc -- What This Thing Feels Like

**FROM CODE:** The user journey is: Profile loads → Suggested questions appear → Chat opens with health indicator → SSE streaming with visible retrieval stats → Fit assessment (3 tabs: pre-analyzed strong, pre-analyzed weak, paste-your-own). Edge deployment on NanoPi R6S with zero hosting cost. Roadmap shows Phase 2 (auth, persistent history, analytics), Phase 3 (multi-agent, tool calling, streaming reasoning, voice), Phase 4 (ontology-based knowledge graph RAG).

> > > YOUR INPUT: What does it feel like to use?

Forget the architecture for a moment. You're a recruiter. You land on the page. What happens? What does the experience feel like compared to reading a PDF resume? What's the "aha" moment for a first-time user?

_[Write here]_

> > > YOUR INPUT: The gap between "resume chatbot" and this

If someone says "it's just a chatbot on a resume," what's your response? What specifically makes this different from the commodity version?

_[Write here]_

> > > YOUR INPUT: Where is this going?

The roadmap mentions multi-agent orchestration, tool calling, voice, and knowledge graph RAG. Which of these are you actually working toward? What's the next concrete step?

_[Write here]_

> > > YOUR INPUT: What would you tell someone who wants to build their own?

If a developer came to you and said "I want to build my own AI resume," what would you tell them? What's the minimum viable version, and what's the trap they'll fall into?

_[Write here]_

---

## CROSS-CUTTING: Quick-Hit Questions

These are smaller items that add color. One or two sentences each is fine.

> > > YOUR INPUT: Origin story -- Nate B Jones

The technical report mentions Nate B Jones as inspiration. Who is he to you? Did you interact with him, or just watch the video?

_[Write here]_

> > > YOUR INPUT: Funniest bug

What was the most entertaining failure? (The `((VAR++))` bash arithmetic bug? Something else?)

_[Write here]_

> > > YOUR INPUT: Development pace

The technical report says "first proof-of-concept took approximately 2 days" and was "constrained by a Claude Pro subscription." What does AI-assisted development actually feel like at this pace?

_[Write here]_

> > > YOUR INPUT: Monthly cost

What does a typical month cost in OpenRouter credits? Is this project effectively free to run?

_[Write here]_

> > > YOUR INPUT: What would you do differently?

If you started over tomorrow with everything you know now, what's the one thing you'd change?

_[Write here]_

---

## Process

1. Fill in your `>>> YOUR INPUT` blocks above
2. Push or let me know when you're done (partial is fine -- we can iterate)
3. I'll review your narrative against the codebase evidence for consistency
4. We collaborate on wording, structure, and article flow
5. Final drafts emerge from the merge of your stories + code evidence
