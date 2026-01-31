# Product Requirements Document

## Problem Statement

Static resumes fail to convey the depth of a candidate's experience. Recruiters scan PDFs for keywords, missing context about how skills were applied, what challenges were overcome, and whether the candidate fits a specific role.

## Solution

An AI-powered resume agent that:

- Answers natural language questions about the candidate's background
- Provides honest, context-aware fit assessments for specific roles
- Surfaces relevant experience through semantic search, not keyword matching

## Target Users

| Persona | Need |
| ------- | ---- |
| **Resume Owner** | Present their experience interactively without constant availability |
| **Recruiter/Hiring Manager** | Get immediate, detailed answers without scheduling calls |

## Functional Requirements

### Must Have (MVP)

- Chat interface with streaming responses
- Semantic search over resume content
- Pre-defined job fit examples (strong fit, weak fit)
- Suggested questions from resume data
- Mobile-responsive design

### Should Have (Post-MVP)

- Real-time job fit analysis (paste any job description)
- Conversation history persistence
- Analytics (question types, session depth)

### Could Have (Future)

- Voice interface
- Multi-agent orchestration
- PDF/document export

## Non-Functional Requirements

| Requirement | Target |
| ----------- | ------ |
| Response latency (P95) | <2 seconds |
| Semantic search latency | <5 milliseconds |
| Monthly operating cost | <$5 at 100 chats/day |
| Container startup time | <5 seconds |
| Memory footprint | <200MB total |

## Data Requirements

All instance data must be:

- Stored in a single portable file (`.mv2`)
- Generated from human-readable markdown source
- Separate from application code (no hardcoded content)

## Constraints

- Must run on ARM64 edge hardware (4GB RAM)
- No external database dependencies
- API keys via environment variables only
- Multi-architecture container support (amd64 + arm64)

## Success Metrics

| Metric | Definition | Target |
| ------ | ---------- | ------ |
| Engagement | Questions per session | >3 |
| Quality | Relevant answer rate | >90% |
| Honesty | Accurate gap identification | 100% |
| Cost | Monthly LLM spend | <$5 |

## Out of Scope

- User authentication (public resume)
- Multi-user/multi-resume support
- Real-time resume editing
- Integration with ATS systems

## End-to-End Quality Acceptance Criteria

The system must demonstrate complete and accurate retrieval of all resume facts when queried by a recruiter persona. Testing uses `data/example_resume.md` as ground truth against the live deployment.

### Data Exposure Coverage

All factual categories in the source resume must be retrievable through natural language questions:

| Category | Example Facts | Validation Query |
| -------- | ------------- | ---------------- |
| **Profile** | Name, title, location, status | "Who is this candidate?" |
| **Experience Timeline** | 3 companies, roles, dates, durations | "Walk me through her career" |
| **Technical Skills** | Python 10+y, Go 5+y, Terraform, K8s | "What languages does she know?" |
| **Accomplishments** | 50x deployment speed, 10M inferences/day | "What are her key achievements?" |
| **Security Track Record** | FedRAMP, SOC 2, zero breaches | "What's her security experience?" |
| **AI/ML Experience** | MLOps, RAG pipelines, model serving | "Tell me about her AI experience" |
| **Leadership** | Team 3→15, <10% attrition, 25+ hires | "How has she grown teams?" |
| **Failures & Growth** | 3 specific failures with lessons | "What are her biggest failures?" |
| **Honest Limitations** | No mobile, no frontend, no C/C++ | "What is she NOT good at?" |
| **Fit Scenarios** | Strong/moderate/weak role types | "Would she fit an early-stage startup?" |

**Target: 100% category coverage** — Every category must be surfaceable through questions.

### Extraction Quality Criteria

| Criterion | Definition | Target |
| --------- | ---------- | ------ |
| **Factual Accuracy** | Claims match source resume exactly | 100% |
| **No Hallucination** | No fabricated companies, dates, or metrics | 0 hallucinations |
| **Completeness** | Answers include relevant details, not just surface | >80% detail retention |
| **Attribution** | Facts linked to correct company/role/period | 100% |
| **Honest Gaps** | System says "I don't know" for facts not in resume | Required |

### Negative Testing

The system must correctly refuse to answer or acknowledge uncertainty for:

- Facts not present in the resume (e.g., "What's her salary expectation?")
- Fabricated companies or roles (e.g., "Tell me about her time at Google")
- Skills not claimed (e.g., "How good is she at iOS development?")

**Target: 100% refusal rate for out-of-scope queries** — No hallucinated answers.

### Test Execution Method

1. **Ground Truth Extraction**: Parse `data/example_resume.md` into structured facts
2. **Question Bank**: Recruiter-style questions covering all categories
3. **Live Execution**: Query live site via automated testing or manual verification
4. **Response Parsing**: Extract factual claims from LLM responses
5. **Scoring**: Compare extracted claims against ground truth

### Acceptance Threshold

| Metric | Threshold | Blocking? |
| ------ | --------- | --------- |
| Category coverage | 100% | Yes |
| Factual accuracy | 100% | Yes |
| Hallucination rate | 0% | Yes |
| Detail completeness | >80% | No |
| Response latency P95 | <2s | No |

**Release gate**: All blocking metrics must pass before production deployment.
