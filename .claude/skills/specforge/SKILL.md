# /specforge -- Interactive Specification Workflow

An interactive skill for collaborative specification authoring. Guides humans and Claude Code through seven phases that produce all artifacts needed for autonomous implementation.

## Sub-Commands

### `/specforge constitution`

Define immutable project principles.

1. Read `.specify/templates/constitution-template.md`
2. Present each section one at a time: Project Identity, Non-Negotiable Principles, Quality Standards, Architectural Constraints, Security Requirements, Out of Scope
3. For each section, ask focused questions. Do not auto-fill. Every value requires human input.
4. Assemble responses into `.specify/memory/constitution.md`
5. Present the complete constitution for review. Apply changes if requested.

### `/specforge spec`

Document features and acceptance criteria.

1. Read `.specify/memory/constitution.md`
2. Ask the human to describe features in plain language
3. For each feature area, ask:
   - What can a user do?
   - What happens when it goes wrong?
   - What are the edge cases?
   - What does success look like?
4. Group features into categories: infrastructure, functional, style, testing
5. Document each with: title, description, acceptance criteria (Given/When/Then for functional), error handling, dependencies
6. Write to `.specify/specs/spec.md` using the spec template format

### `/specforge clarify`

Surface ambiguities for human resolution.

1. Read `.specify/memory/constitution.md` and `.specify/specs/spec.md`
2. Analyze for:
   - Ambiguous requirements (multiple interpretations)
   - Missing error handling
   - Undefined edge cases
   - Contradictions between features or with constitution
   - Missing non-functional requirements (performance, security, accessibility)
   - Unstated assumptions
3. Present each as a numbered question with:
   - Quoted text from the spec
   - Why it matters for autonomous implementation
   - 2-3 suggested resolutions
4. Record decisions inline
5. Update spec.md with resolved decisions
6. Repeat until no unresolved items remain

### `/specforge plan`

Make technical architecture decisions.

1. Read all previous artifacts: constitution, spec
2. Propose technical decisions for each area:
   - Project structure (directory layout)
   - Tech stack (frontend, backend, storage, API)
   - Data storage approach
   - API design (REST/GraphQL/RPC, URL structure, auth)
   - Deployment architecture
   - Testing strategy (frameworks, coverage tools)
   - CI/CD platform
3. For each decision: recommendation with rationale, alternatives considered, trade-offs
4. Get explicit human approval for each decision
5. Write to `.specify/specs/plan.md` using the plan template format

### `/specforge features`

Generate feature_list.json with testing steps.

1. Read all artifacts: constitution, spec, plan
2. For each feature in the spec, create a feature_list.json entry:
   - `id`: kebab-case identifier
   - `category`: infrastructure | functional | style | testing
   - `title`: human-readable title (5-100 chars)
   - `description`: what it does (10+ chars)
   - `testing_steps`: 3-15 concrete, verifiable steps an autonomous agent can execute
   - `passes`: false (always starts false)
   - `dependencies`: array of feature IDs that must pass first
3. Order by priority: infrastructure first, then functional, style, testing last
4. Validate:
   - Dependency graph is acyclic
   - Every feature has at least 3 testing steps
   - At least 20% of features have 10+ testing steps
   - All dependency references resolve to existing feature IDs
5. Validate against `.specify/templates/feature-list-schema.json`
6. Write to `feature_list.json` in the project root

### `/specforge analyze`

Score spec for autonomous-readiness on a 0-100 scale.

**Dimensions (weighted):**

- **Completeness (25%):** Constitution fully filled, acceptance criteria for every feature, plan complete, feature_list.json validates against schema
- **Testability (25%):** Testing steps are concrete with specific values, sufficient step depth (3+ per feature, 20%+ with 10+), no vague criteria ("works correctly", "looks good")
- **Dependency Quality (15%):** No circular dependencies, dependency graph is wide (not a single chain), infrastructure features have no dependencies
- **Ambiguity (20%):** No unresolved questions from clarify phase, error handling specified for all functional features, edge cases documented, non-functional requirements quantified
- **Autonomous Feasibility (15%):** No features requiring human judgment to test, no unavailable credentials or external services, all testing steps are programmatically executable

**Output:**

- Score per dimension with breakdown
- Overall weighted score
- Remediation steps for any dimension scoring below 70
- Recommendation: "ready" if overall >= 80, otherwise "needs work"

### `/specforge setup`

Generate platform-specific project setup checklist.

1. Read plan for CI platform choice (default: GitHub)
2. For GitHub, generate an actionable checklist:
   - Branch protection on main (require PR, status checks, reviews)
   - Required status checks: summary job only
   - CODEOWNERS for critical paths (.claude/, .github/, scripts/hooks/, ci/, .specify/memory/)
   - Dependabot configuration per detected ecosystem
   - CodeQL for detected languages + secret scanning with push protection
   - Squash merge default, auto-delete head branches
   - PR and issue templates
3. Provide `gh` CLI commands where possible
4. Print as numbered steps the human can execute
