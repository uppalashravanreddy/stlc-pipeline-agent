# STLC Pipeline Agent — Copilot Instructions

## Project
Agentic STLC pipeline using the Anthropic Claude API. Takes a software requirement
as input; produces QA artifacts (classification → test plan → test cases → review)
across coordinated sub-agents.

## Architecture
- Orchestrator (`agents/orchestrator.py`) — coordinates phases, runs HITL gates
- AnalysisAgent (`agents/analysis_agent.py`) — Phase 0 (classify) + Phase 1 (test plan)
- GenerationAgent (`agents/generation_agent.py`) — Phase 2 (test cases) + Phase 3 (review)
- Shared state flows through `memory/pipeline_state.py`

## Conventions
- Python 3.11+ with full type hints
- Agent configs (model, max_tokens, max_iterations) live in `config/agent_configs.py`
- Tools (Anthropic tool-use schemas) live in `tools/`
- All agents inherit from `agents/base_agent.py`
- Each agent logs token usage — never suppress `_log()` calls

## Domain Terms
| Term | Meaning |
|------|---------|
| STLC | Software Testing Lifecycle |
| Phase 0 | Classification: test type, risk level, approach, priority |
| Phase 1 | Test Plan: objectives, scope, scenarios, entry/exit criteria |
| Phase 2 | Test Cases: individual executable test cases from Phase 1 scenarios |
| Phase 3 | Review: coverage gap analysis and approval decision |
| HITL | Human-in-the-Loop: pipeline pauses for human approval before proceeding |
| Hard Stop | max_iterations cap on every agentic loop |

## Model Mapping Rule
- Haiku → routing, classification, coordination (cheap + fast)
- Sonnet → generation, reasoning, review (quality matters)
- Never use Opus unless explicitly needed for complex reasoning

## When adding a new phase
1. Add a config entry in `config/agent_configs.py`
2. Add a tool schema in `tools/`
3. Create or extend an agent in `agents/`
4. Add the phase call in `agents/orchestrator.py`
5. Update `memory/pipeline_state.py` to carry the new output
