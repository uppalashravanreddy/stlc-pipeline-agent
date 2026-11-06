# STLC Pipeline Agent — Claude Code Instructions

## What this project is
An agentic STLC (Software Testing Lifecycle) pipeline built with the Anthropic Claude API.
Input: a Jira ticket ID. Output: test plan, test cases, review, and pytest automation — all in one summary Markdown file.

## Architecture
```
main.py
  └── Orchestrator (agents/orchestrator.py)
        ├── AnalysisAgent   → Phase 0: Classify + Phase 1: Test Plan
        ├── GenerationAgent → Phase 2: Test Cases + Phase 3: Review
        └── AutomationAgent → Phase 4: pytest code + Phase 5: Code review
```

## Key files
| File | Purpose |
|---|---|
| `config/agent_configs.py` | Model + token + iteration config per agent |
| `memory/pipeline_state.py` | Shared state passed between agents |
| `memory/skill_loader.py` | Loads `.claude/skills/*.md` into prompts |
| `memory/summary_writer.py` | Writes final summary MD or debug JSON |
| `memory/checkpoint.py` | Resume from `.cache/<STORY-ID>/checkpoint.json` |
| `tools/jira_client.py` | MCP — fetch story by ticket ID |
| `.claude/skills/` | Reusable QA instruction packages per phase |

## Run commands
```bash
# From .claude/worktrees/advanced-capstone/
python main.py                        # default story
python main.py --ticket KAN-28        # fetch from Jira via MCP
python main.py --feature X --story Y  # manual story input
```

## Output
- **Success**: `output/<STORY-ID>/stlc_summary_<ts>.md` — one file, all phases
- **Error**: `output/<STORY-ID>/debug_phase<N>_<ts>.json` — state dump
- **Internal cache**: `.cache/<STORY-ID>/checkpoint.json` — for resume

## Conventions
- Python 3.11+, full type hints
- All agents inherit `BaseAgent` — never bypass `run_loop()`
- System prompts use `.format(skills=...)` to inject skill content
- `max_iterations` is a hard stop — never increase without understanding why
- Log every agent action via `_log()` — never suppress observability

## Domain terms
| Term | Meaning |
|---|---|
| Phase 0 | Classify: test type, risk, approach, priority |
| Phase 1 | Test Plan: objectives, scope, scenarios, criteria |
| Phase 2 | Test Cases: executable, specific, no placeholders |
| Phase 3 | Review: coverage score ≥ 7/10 to approve |
| Phase 4 | pytest automation from approved test cases |
| Phase 5 | Code review of automation quality |
| HITL | Human-in-the-Loop: pipeline pauses for y/n approval |
| Hard Stop | `max_iterations` cap — safety ceiling on every loop |
