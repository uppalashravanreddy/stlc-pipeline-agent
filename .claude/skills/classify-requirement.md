---
name: classify-requirement
description: Phase 0 classification skill. Analyses a user story and determines test type, risk level, test approach, and priority using a structured decision framework.
---

## Purpose
Classify a user story across four dimensions before any test planning begins.
Classification drives everything downstream — risk level sets scope depth, test type sets tooling, priority sets urgency.

## When to invoke
- Start of Phase 0 in the STLC pipeline
- Any time a new story needs test strategy alignment
- When re-classifying after a story is updated

## Classification Framework

### 1. Test Type — what layer does this feature primarily live at?

| Type | Use when |
|---|---|
| `API` | Backend endpoints, data contracts, no UI involved |
| `UI` | Frontend interactions, form validation, visual behaviour |
| `Mobile` | Native iOS/Android, gestures, offline, device-specific |
| `Integration` | Two or more systems communicating (DB + API, API + third-party) |
| `Performance` | Response times, load, throughput, scalability |
| `Security` | Auth, authorisation, injection, data exposure, encryption |
| `E2E` | Full user journey across multiple layers (UI → API → DB) |

**Rule:** If the story spans multiple layers and a defect in any layer blocks the user, classify as `E2E`.

### 2. Risk Level — business impact × technical complexity

| Level | Criteria |
|---|---|
| `High` | Feature is a release blocker OR touches security/payments/auth OR high technical complexity |
| `Medium` | Feature is important but defect is recoverable OR moderate complexity |
| `Low` | Cosmetic, informational, or isolated with no downstream impact |

### 3. Test Approach — what delivers the best ROI?

| Approach | Use when |
|---|---|
| `Automated` | Stable UI, well-defined API, high regression risk, repeatable flows |
| `Manual` | Exploratory, visual/UX judgement, one-time setup, low regression risk |
| `Both` | High risk features needing regression automation AND security/UX manual probing |

### 4. Priority — when must this be tested?

| Priority | Meaning |
|---|---|
| `P1` | Release blocker — application cannot ship without this testing |
| `P2` | Important — ship without risk only if no P1 defects found |
| `P3` | Nice to have — defer to next cycle if time-constrained |

## Output format
```
Phase 0 Classification:
  test_type:     [type]
  risk_level:    [High | Medium | Low]
  test_approach: [Automated | Manual | Both]
  priority:      [P1 | P2 | P3]
  rationale:     [2 sentences explaining the classification decisions]
```

## Rules
- Always justify risk_level with specific evidence from the ACs
- If security keywords appear (auth, password, token, permission) → minimum `High` risk
- Classification must be completed before Phase 1 test plan begins
