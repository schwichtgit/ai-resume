# Technical Plan: [PROJECT_NAME]

## Overview

**Project:** [PROJECT_NAME]
**Spec Version:** [SPEC_VERSION]
**Plan Version:** [PLAN_VERSION]
**Last Updated:** [DATE]
**Status:** Draft | Approved

---

## Project Structure

```text
[PROJECT_NAME]/
├── [directory]/
│   ├── [file]                 # [purpose]
│   └── [file]                 # [purpose]
├── [config-file]              # [purpose]
└── [config-file]              # [purpose]
```

---

## Tech Stack

### Frontend (if applicable)

| Component  | Choice      | Version   | Rationale |
| ---------- | ----------- | --------- | --------- |
| Framework  | [FRAMEWORK] | [VERSION] | [Why]     |
| Styling    | [APPROACH]  | [VERSION] | [Why]     |
| Build Tool | [TOOL]      | [VERSION] | [Why]     |

### Backend (if applicable)

| Component | Choice      | Version   | Rationale |
| --------- | ----------- | --------- | --------- |
| Framework | [FRAMEWORK] | [VERSION] | [Why]     |
| ORM       | [LIBRARY]   | [VERSION] | [Why]     |

### Data Storage

| Component | Choice     | Version   | Rationale |
| --------- | ---------- | --------- | --------- |
| Database  | [DATABASE] | [VERSION] | [Why]     |

### API Design

- **Style:** [REST | GraphQL | RPC | None]
- **Authentication:** [Method]
- **Error Format:** [Structure]

---

## Testing Strategy

| Type        | Framework   | Coverage Target | Command   |
| ----------- | ----------- | --------------- | --------- |
| Unit        | [FRAMEWORK] | [PERCENTAGE]%   | [COMMAND] |
| Integration | [FRAMEWORK] | [PERCENTAGE]%   | [COMMAND] |
| E2E         | [FRAMEWORK] | N/A             | [COMMAND] |

### Coverage

- **Minimum threshold:** [PERCENTAGE]% (from constitution)
- **Coverage tool:** [TOOL]
- **Excluded paths:** [List]

---

## Deployment Architecture

| Component   | Platform   | Rationale |
| ----------- | ---------- | --------- |
| Application | [PLATFORM] | [Why]     |
| Database    | [PLATFORM] | [Why]     |

---

## Development Environment

### init.sh Requirements

1. **System dependencies:** [List]
2. **Language runtime:** [Version]
3. **Package installation:** [Command]
4. **Database setup:** [Command or N/A]
5. **Verification:** [Health check]

---

## Architectural Decisions

### ADR-001: [Decision Title]

**Date:** [DATE]
**Status:** Accepted

**Context:** [What issue motivates this decision?]

**Decision:** [What is being decided?]

**Alternatives Considered:**

1. **[Alternative A]:** [Pros, cons]
2. **[Alternative B]:** [Pros, cons]

**Consequences:**

- [Positive consequence]
- [Negative consequence or trade-off]
