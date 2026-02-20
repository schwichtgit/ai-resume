# Feature Specification: [PROJECT_NAME]

## Overview

**Project:** [PROJECT_NAME]
**Version:** [SPEC_VERSION]
**Last Updated:** [DATE]
**Status:** Draft | In Review | Approved

### Summary

[2-3 sentence summary of what the project does and who it serves.]

### Scope

- [AREA_1]
- [AREA_2]
- [AREA_3]

---

## Infrastructure Features

Infrastructure features have NO dependencies. They establish the foundation.

### INFRA-001: [Title]

**Description:** [What this sets up and why.]

**Acceptance Criteria:**

- [ ] [Criterion with specific, measurable outcome]
- [ ] [Criterion with specific, measurable outcome]

**Dependencies:** None

---

## Functional Features

Core application behavior. Each includes Given/When/Then criteria, error handling, and dependencies.

### FUNC-001: [Title]

**Description:** [What the user can do.]

**Acceptance Criteria:**

- **Given** [precondition]
  **When** [action]
  **Then** [expected outcome with specific values]

**Error Handling:**

| Error Condition | Expected Behavior | User-Facing Message |
| --------------- | ----------------- | ------------------- |
| [Condition]     | [Behavior]        | [Message]           |

**Edge Cases:**

- [Edge case and expected behavior]

**Dependencies:** [INFRA-001, FUNC-XXX, or "None"]

---

## Style Features

Visual presentation, responsive design, and accessibility.

### STYLE-001: [Title]

**Description:** [Visual/UX requirement.]

**Acceptance Criteria:**

- [ ] [Visual criterion with specific values]
- [ ] [Responsive criterion with specific viewport widths]
- [ ] [Accessibility criterion referencing WCAG level]

**Dependencies:** [FUNC-XXX]

---

## Testing Features

Test infrastructure and coverage targets.

### TEST-001: [Title]

**Description:** [What testing capability this establishes.]

**Acceptance Criteria:**

- [ ] [Coverage target with specific percentage]
- [ ] [Test infrastructure requirement]

**Dependencies:** [Feature IDs]

---

## Non-Functional Requirements

### Performance

- [Metric]: [Target with specific value]

### Security

- [Requirement with specific standard]

### Accessibility

- WCAG compliance level: [A | AA | AAA]

### Browser/Platform Support

- [Platform]: [Version range]
