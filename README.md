# STLC Pipeline Agent — Expert Capstone

**Expert Final Evaluation** | EPAM AI-Native Program  
Full enterprise multi-agent STLC pipeline · Phases 0–7 · MCP integrations · HITL gates · GitHub PR creation

---

## Architecture

```
python main.py --ticket KAN-28
        │
        ▼
  [MCP] Jira fetch → User Story
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR                         │
│         Owns PipelineState · 4 HITL gates              │
└──────────┬──────────┬──────────┬──────────┬────────────┘
           │          │          │          │
           ▼          ▼          ▼          ▼
    AnalysisAgent  GenerationAgent  AutomationAgent  FixAgent
    Phase 0+1      Phase 2+3        Phase 4+5        Phase 6
           └──────────┴──────────┴──────────┘
                              │
                              ▼
                         PTRAgent (Phase 7)
                   Project Test Report + GitHub PR
                              │
                              ▼
                   PR Review Orchestrator (separate)
                   python pr_orchestrator.py --pr-url <url>
```

---

## Pipeline Phases

| Phase | Agent | Output |
|---|---|---|
| 0 | AnalysisAgent | Classification: test type, risk, approach, priority |
| 1 | AnalysisAgent | Test Plan: objectives, scope, 7 scenarios, criteria |
| 2 | GenerationAgent | 8 executable test cases with steps + test data |
| 3 | GenerationAgent | Coverage review: score, gaps, approval |
| 4 | AutomationAgent | pytest functions for each test case |
| 5 | AutomationAgent | Automation quality review |
| 6 | FixAgent | Fixes Phase 5 blocking issues |
| 7 | PTRAgent | Project Test Report + GitHub Draft PR |

---

## Setup

```bash
git clone https://github.com/uppalashravanreddy/stlc-pipeline-agent.git
cd stlc-pipeline-agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # add ANTHROPIC_API_KEY, JIRA_*, GITHUB_* keys
```

---

## Run

```bash
python main.py --ticket KAN-28          # fetch from Jira via MCP
python main.py --feature "X" --story "Y"
python pr_orchestrator.py --pr-url https://github.com/.../pull/1
```

---

## Output

- `output/<ID>/stlc_summary_*.md` — success: one file, all phases
- `output/<ID>/debug_phase*.json` — failure: state dump
- `logs/*.jsonl` — full token trace per run
