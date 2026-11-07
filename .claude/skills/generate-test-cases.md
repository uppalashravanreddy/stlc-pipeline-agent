---
name: generate-test-cases
description: Phase 2 skill. Generates executable test cases from Phase 1 scenarios. Each scenario produces 1–2 test cases with specific steps, test data, and clear pass/fail criteria.
---

## Purpose
Turn Phase 1 test scenarios into individually executable test cases that any tester can run without asking clarifying questions.

## When to invoke
- Phase 2 of the STLC pipeline, after test plan is approved at HITL Gate 1
- When expanding a scenario into runnable steps
- When creating a regression test suite from existing scenarios

## Inputs required
- Phase 0 classification (test_type, risk_level, priority)
- Phase 1 test plan (especially test_scenarios and in_scope)

## Test case structure

Each test case must have:

| Field | Description | Example |
|---|---|---|
| `id` | Sequential identifier | TC-001 |
| `title` | Action + expected outcome | "Valid login → dashboard redirect" |
| `scenario_ref` | Which Phase 1 scenario it covers | "POSITIVE: valid credentials" |
| `preconditions` | Setup required before execution | "User account exists, app running" |
| `steps` | Numbered, specific, executable | "1. Navigate to /login 2. Enter email..." |
| `expected_result` | Observable pass condition | "HTTP 200, JWT in cookie, /dashboard loaded" |
| `test_data` | Specific values, not placeholders | `{email: "test@demo.com", password: "P@ss123"}` |
| `test_type` | Positive / Negative / Edge Case / Security / Performance | |
| `priority` | P1 / P2 / P3 | |
| `automation_feasibility` | High / Medium / Low | |

## Step quality rules

**Good step:** "Enter `test@demo.com` in the Email field and `WrongPass!` in the Password field"
**Bad step:** "Enter invalid credentials" ✗ — too vague, can't be executed consistently

**Good expected result:** "Error message 'Invalid email or password' displayed below the form; no field highlighted individually"
**Bad expected result:** "Error shown" ✗ — not specific enough to judge pass/fail

## Coverage rules

- Generate 1 test case per POSITIVE scenario
- Generate 1–2 test cases per NEGATIVE scenario (one for each failure mode)
- Generate 1 test case per EDGE CASE scenario
- If risk_level=High: add at least one Security test case
- Aim for mix: ~40% Positive, ~35% Negative, ~25% Edge/Security

## Automation feasibility guide

| Rating | When |
|---|---|
| `High` | Stable selectors, deterministic output, no visual judgement |
| `Medium` | Mostly automatable but needs some manual verification |
| `Low` | Requires human judgement, visual comparison, or hardware |

## Output format
Array of test case objects — all cases at once, not one at a time.

## Rules
- Test data must use real values, not `<valid_email>` or `[your_password]`
- Steps must be executable by someone who has never seen the feature
- Each test case tests exactly ONE scenario — no multi-scenario test cases
- Never generate duplicate test cases doing the same thing
