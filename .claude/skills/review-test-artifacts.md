---
name: review-test-artifacts
description: Phase 3 skill. Reviews generated test cases against the Phase 1 test plan for coverage gaps, quality issues, and approval decision. Also applicable to reviewing a test plan against the original user story.
---

## Purpose
Act as a QA review lead — validate that the generated artifacts are complete, correct, and ready to execute. Catch gaps before they reach automation.

## When to invoke
- Phase 3: reviewing test cases against the Phase 1 test plan
- Reviewing a test plan against the original user story and ACs
- Any quality gate where generated QA artifacts need validation

## Review dimensions

### 1. Coverage check — did we test what we said we would?

For each Phase 1 scenario:
- Is there at least one test case that covers it?
- Does the test case actually test the scenario (not just mention it)?
- Are all in-scope items from the test plan represented?

**Gap** = a Phase 1 scenario with no test case → flag it

### 2. Quality check — are the test cases executable?

Check each test case for:

| Issue | Description |
|---|---|
| Vague steps | Steps that need interpretation ("click the button" — which button?) |
| Missing test data | Placeholders instead of actual values |
| Untestable expected result | "Should work correctly" — not a pass/fail criterion |
| Wrong test type | Positive test case with negative data |
| Duplicate | Two test cases testing the exact same thing |

### 3. Edge case check — are the edges covered?

- If risk_level=High: are there edge cases for each positive scenario?
- Is there at least one negative test case per major happy path?
- Are boundary values tested (min/max, empty, null, special chars)?

### 4. Security check — if applicable

- If test_type=Security or risk_level=High: are there security-focused cases?
- Are error messages validated to avoid information leakage?
- Are auth/session behaviors tested?

## Scoring

```
coverage_score: X/10

10 = all scenarios covered, strong edge cases, no quality issues
7-9 = minor gaps, addressable with additions
5-6 = notable gaps or quality issues affecting reliability
<5  = significant rework needed
```

**approved = true** only when:
- coverage_score ≥ 7/10
- No blocking issues (vague steps on P1 cases, missing test data, untestable results)
- All High-risk scenarios have at least one test case

## Output format
```
Phase 3 Review:
  coverage_score:          "8/10"
  scenarios_covered:       [list of covered scenarios]
  gaps:                    [Phase 1 scenarios with no test case]
  issues:                  [{test_case_id, issue, severity}]
  additions_recommended:   [suggested new test cases]
  approved:                true | false
  overall_notes:           "2-3 sentence summary"
```

## Rules
- Score must have justification — not just a number
- If approved=false, state exactly what must be fixed before re-review
- Additions recommended should be specific enough to implement without clarification
- Never approve if a P1 scenario has no test case
