---
name: generate-test-plan
description: Phase 1 skill. Generates a structured test plan from a classified user story. Scope depth and scenario count are driven by Phase 0 risk level.
---

## Purpose
Produce a complete, actionable test plan that tells a QA team exactly what to test, what to skip, and what done looks like.

## When to invoke
- Phase 1 of the STLC pipeline, immediately after `classify-requirement`
- When generating a test strategy for a new feature
- When updating scope after a story change

## Inputs required
- Phase 0 classification output (test_type, risk_level, priority, rationale)
- Full user story with acceptance criteria

## Risk-driven scope rules

| Risk Level | Objectives | Scenarios | Edge cases |
|---|---|---|---|
| `High` | 3 | 7+ | At least 2 per positive scenario |
| `Medium` | 2–3 | 5–6 | At least 1 per positive scenario |
| `Low` | 2 | 3–4 | 1 overall |

## Steps

### 1. Write Objectives (2–3)
- Specific, measurable testing goals tied directly to the ACs
- Format: "Verify that [behaviour] [under condition] [meets criterion]"
- Bad: "Test the login feature" ✗
- Good: "Verify that 5 consecutive failed login attempts lock the account and deny all subsequent attempts including correct credentials" ✓

### 2. Define Scope

**In Scope** — behaviours from the ACs that WILL be tested:
- List each AC as a testable scope item
- Add implicit behaviours the ACs imply (e.g., if AC says "error message shown" → error message content is in scope)

**Out of Scope** — explicitly state what will NOT be tested:
- Related features not in this story
- Performance unless AC mentions it
- Third-party internals
- Out-of-scope prevents scope creep and sets expectations

### 3. Write Test Scenarios (5–7+)
Each scenario is one sentence describing a testable situation:
- Format: `[TYPE] [Actor] [action] [condition] — [expected outcome]`
- Types: POSITIVE / NEGATIVE / EDGE CASE / SECURITY / PERFORMANCE
- Mix: ~40% positive, ~35% negative, ~25% edge/security

### 4. Entry Criteria
Pre-conditions that must be true before testing begins:
- Environment deployed and stable
- Test data seeded
- Access/permissions configured
- Dependencies available

### 5. Exit Criteria
Measurable conditions that define "testing is done":
- Specific pass rates (e.g., "100% of P1 scenarios pass")
- Defect thresholds ("zero open P1/P2 defects")
- Coverage requirements ("automated suite green × 2 CI runs")

## Output format
```
Phase 1 Test Plan:
  objectives:     [array]
  in_scope:       [array]
  out_of_scope:   [array]
  test_scenarios: [array]
  entry_criteria: [array]
  exit_criteria:  [array]
```

## Rules
- Never copy-paste ACs as scenarios — scenarios describe HOW to test them
- Out of scope must name specific exclusions, not say "out of scope"
- Exit criteria must be measurable — no "all tests pass" without a number
