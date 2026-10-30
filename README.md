# STLC Pipeline Agent — Intermediate Capstone

**Intermediate Final Evaluation** | EPAM AI-Native Program  
Single-agent pipeline: Phase 0 (Classification) + Phase 1 (Test Plan) | ONE tool

---

## Architecture

```
User Story (input)
       │
       ▼
┌──────────────────────────────────────────┐
│           STLC Agent (LLM)               │
│                                          │
│  Phase 0 — Classification                │
│  ├── test_type  (API/UI/E2E/…)           │
│  ├── risk_level (High/Medium/Low)        │
│  ├── test_approach (Auto/Manual/Both)    │
│  └── priority   (P1/P2/P3)              │
│                                          │
│  Phase 1 — Test Plan                     │
│  ├── objectives (2-3 measurable goals)   │
│  ├── in_scope / out_of_scope             │
│  ├── test_scenarios (5-7, pos+neg+edge)  │
│  ├── entry_criteria                      │
│  └── exit_criteria                       │
│                                          │
│  ──► Tool Call: save_test_plan ──────────┼──► Markdown + JSON output
└──────────────────────────────────────────┘
```

## The ONE Tool: `save_test_plan`

The agent has exactly **one** tool. Its schema requires both Phase 0 and Phase 1 fields — so the agent **must** complete both phases before it can call the tool.

| Tool Field | Type | Description |
|------------|------|-------------|
| `feature_name` | string | Feature under test |
| `phase_0_classification.test_type` | enum | API \| UI \| Mobile \| Integration \| Performance \| Security \| E2E |
| `phase_0_classification.risk_level` | enum | High \| Medium \| Low |
| `phase_0_classification.test_approach` | enum | Automated \| Manual \| Both |
| `phase_0_classification.priority` | enum | P1 \| P2 \| P3 |
| `phase_0_classification.rationale` | string | Justification for classification |
| `phase_1_test_plan.objectives` | string[] | 2-3 measurable goals |
| `phase_1_test_plan.in_scope` | string[] | Areas being tested |
| `phase_1_test_plan.out_of_scope` | string[] | Explicitly excluded |
| `phase_1_test_plan.test_scenarios` | string[] | 5-7 concrete scenarios |
| `phase_1_test_plan.entry_criteria` | string[] | Pre-conditions |
| `phase_1_test_plan.exit_criteria` | string[] | Done definition |

## File Structure

```
stlc-pipeline-agent/
├── agent.py          ← agentic loop (Phase 0 → Phase 1 → tool call)
├── tools.py          ← ONE tool definition + implementation
├── main.py           ← CLI entry point with sample user story
├── requirements.txt
├── .env.example
└── output/           ← generated test plans (gitignored)
```

## Setup

```bash
cd stlc-pipeline-agent
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt

# Copy .env.example → .env and add your key
copy .env.example .env
# Edit .env: ANTHROPIC_API_KEY=your_key_here

python main.py
```

## Sample Run

```
============================================================
  STLC PIPELINE AGENT
  Feature: User Authentication — Login
============================================================

[Agent Reasoning]
## Phase 0 — Classification
This is a security-sensitive feature with direct access control implications...
Risk: High | Type: E2E | Approach: Both | Priority: P1

## Phase 1 — Test Plan
Given High risk and P1 priority, scope must cover all positive, negative,
and security edge cases...

[Tool Call] save_test_plan
[Tool] Saved → user_authentication_login_20261030_143012.md
[Tool] Saved → user_authentication_login_20261030_143012.json

============================================================
  PIPELINE SUMMARY
  Feature  : User Authentication — Login
  Type     : E2E
  Risk     : High
  Approach : Both
  Priority : P1

  Output saved to ./output/
============================================================
```

## Agentic AI Concepts Demonstrated

| Concept | Implementation |
|---------|---------------|
| Tool calling | `save_test_plan` with JSON schema |
| Structured output | Schema enforces Phase 0 + Phase 1 completeness |
| Agentic loop | `while True` loop drives reasoning → tool → confirmation |
| System prompt | Explicit phase pipeline instructions |
| Single-agent pattern | One model instance handles classification and planning |

## Run with Custom User Story

```bash
python main.py --feature "Shopping Cart" --story "As a user I want to add items..."
```
