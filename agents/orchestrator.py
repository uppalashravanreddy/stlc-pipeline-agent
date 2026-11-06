"""
CAPSTONE CONCEPTS DEMONSTRATED:
  - Agent vs Sub-Agents: Orchestrator is the COORDINATOR. It decides sequencing,
      handles HITL gates, and delegates all QA work to sub-agents. It never
      generates test artifacts itself.
  - Workflow / Pipelines: explicit sequential pipeline —
      Phase 0+1 → HITL → Phase 2+3 → HITL → Phase 4+5 → HITL → done
  - Hard Stops: each HITL gate is a stop point where the human can abort.
      The pipeline never auto-proceeds past a gate — approval is required.
  - Memory Types: PipelineState is the shared memory passed between agents.
      The orchestrator owns it and passes it to each sub-agent by reference.
"""
import json
from datetime import datetime
from pathlib import Path
from memory.pipeline_state import PipelineState
from agents.analysis_agent import AnalysisAgent
from agents.generation_agent import GenerationAgent
from agents.automation_agent import AutomationAgent

LOGS_DIR = Path(__file__).parent.parent / "logs"


class Orchestrator:
    """
    CAPSTONE: Agent vs Sub-Agents

    The orchestrator is the ONLY agent the user interacts with directly.
    Sub-agents (Analysis, Generation, Automation) are invisible to the user —
    the orchestrator calls them, collects their output, and decides what happens next.

    This is the "coordinator" pattern:
    - Orchestrator = knows the pipeline, owns the state, handles HITL
    - Sub-agents   = specialists, know only their phase, unaware of each other
    """

    def __init__(self):
        self.analysis_agent   = AnalysisAgent()
        self.generation_agent = GenerationAgent()
        self.automation_agent = AutomationAgent()

    def run(self, feature_name: str, user_story: str) -> PipelineState | None:
        """
        CAPSTONE: Workflow / Pipelines

        Phases run in strict sequence. Each HITL gate is a pause where the human
        reviews output and decides whether to continue. If the human aborts,
        the function returns the partial state — whatever was completed is saved.

        Pipeline:
            Phase 0+1  (AnalysisAgent)
                ↓
            HITL Gate 1: Review test plan → approve to continue
                ↓
            Phase 2    (GenerationAgent — test cases)
                ↓
            Phase 3    (GenerationAgent — review)
                ↓
            HITL Gate 2: Review test case coverage → approve to continue
                ↓
            Phase 4    (AutomationAgent — generate pytest)
                ↓
            Phase 5    (AutomationAgent — review code)
                ↓
            HITL Gate 3: Review automation quality → final sign-off
        """
        _banner("STLC PIPELINE — ADVANCED  (Phases 0–5)")
        print(f"  Feature : {feature_name}\n")

        # CAPSTONE: Observability — create a log file for this run
        LOGS_DIR.mkdir(exist_ok=True)
        slug = feature_name.lower().replace(" ", "_")[:30]
        slug = "".join(c for c in slug if c.isalnum() or c == "_")
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = LOGS_DIR / f"{slug}_{ts}.jsonl"

        # Write the pipeline header to the log
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts":           datetime.now().isoformat(),
                "event":        "pipeline_start",
                "feature":      feature_name,
                "log_file":     log_path.name,
            }) + "\n")

        # Share the log path with all sub-agents
        self.analysis_agent.log_path   = log_path
        self.generation_agent.log_path = log_path
        self.automation_agent.log_path = log_path
        print(f"  Log     : logs/{log_path.name}\n")

        # CAPSTONE: Memory Types — PipelineState is the shared working memory
        state = PipelineState(feature_name=feature_name, user_story=user_story)

        # ── Phase 0 + 1 ─────────────────────────────────────────────────────
        state = self.analysis_agent.run(state)
        if not state.phase_1_test_plan:
            print("\n[Orchestrator] Phase 0+1 failed — aborting pipeline.")
            return None

        # ── HITL Gate 1 ──────────────────────────────────────────────────────
        _banner("HITL GATE 1 — Review Test Plan")
        _print_phase_01_summary(state)

        if not _hitl_prompt("Approve test plan and generate test cases?"):
            print("\n[Orchestrator] Pipeline aborted at Gate 1.")
            state.hitl_approvals["gate_1"] = "rejected"
            return state
        state.hitl_approvals["gate_1"] = "approved"

        # ── Phase 2 (Test Cases) ─────────────────────────────────────────────
        state = self.generation_agent.run_phase_2(state)
        if not state.phase_2_test_cases:
            print("\n[Orchestrator] Phase 2 failed — aborting pipeline.")
            return state

        # ── Phase 3 (Review) ─────────────────────────────────────────────────
        state = self.generation_agent.run_phase_3(state)

        # ── HITL Gate 2 ──────────────────────────────────────────────────────
        _banner("HITL GATE 2 — Review Test Case Coverage")
        _print_phase_23_summary(state)

        if not _hitl_prompt("Approve test cases and generate automation?"):
            print("\n[Orchestrator] Pipeline aborted at Gate 2.")
            state.hitl_approvals["gate_2"] = "rejected"
            return state
        state.hitl_approvals["gate_2"] = "approved"

        # ── Phase 4 (Automation Generate) ────────────────────────────────────
        state = self.automation_agent.run_phase_4(state)
        if not state.phase_4_automation:
            print("\n[Orchestrator] Phase 4 failed — aborting pipeline.")
            return state

        # ── Phase 5 (Automation Review) ──────────────────────────────────────
        state = self.automation_agent.run_phase_5(state)

        # ── HITL Gate 3 ──────────────────────────────────────────────────────
        _banner("HITL GATE 3 — Final Sign-off")
        _print_phase_45_summary(state)

        if not _hitl_prompt("Approve automation and complete pipeline?"):
            print("\n[Orchestrator] Pipeline aborted at Gate 3.")
            state.hitl_approvals["gate_3"] = "rejected"
            return state
        state.hitl_approvals["gate_3"] = "approved"

        _banner("PIPELINE COMPLETE")
        _print_final_summary(state)

        # Write pipeline end to log
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts":            datetime.now().isoformat(),
                "event":         "pipeline_complete",
                "phases_done":   state.current_phase,
                "test_cases":    len(state.phase_2_test_cases or []),
                "hitl_approvals": state.hitl_approvals,
            }) + "\n")
        print(f"\n  Full trace → logs/{log_path.name}")

        return state


# ── HITL helpers ─────────────────────────────────────────────────────────────

def _hitl_prompt(message: str) -> bool:
    """
    CAPSTONE: Hard Stops / HITL

    The pipeline pauses here. Execution cannot continue without explicit
    human approval. Three options:
      y = approve and continue
      n = reject and abort
      s = skip remaining phases (useful for testing the pipeline itself)
    """
    print(f"\n  ┌─ HUMAN DECISION REQUIRED ─────────────────────────────┐")
    print(f"  │  {message:<52} │")
    print(f"  │  y = approve  │  n = abort  │  s = skip to end         │")
    print(f"  └────────────────────────────────────────────────────────┘")

    while True:
        answer = input("  > ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        if answer in ("s", "skip"):
            return True  # treat skip as approval for demo purposes
        print("  Please enter y, n, or s.")


# ── Print helpers ─────────────────────────────────────────────────────────────

def _banner(title: str) -> None:
    print(f"\n{'═' * 62}")
    print(f"  {title}")
    print(f"{'═' * 62}\n")


def _print_phase_01_summary(state: PipelineState) -> None:
    c = state.phase_0_classification or {}
    p = state.phase_1_test_plan or {}
    print(f"  Phase 0 Classification:")
    print(f"    Type: {c.get('test_type')}  |  Risk: {c.get('risk_level')}  |  Priority: {c.get('priority')}")
    print(f"    {c.get('rationale', '')}")
    print(f"\n  Phase 1 Test Plan — {len(p.get('test_scenarios', []))} scenarios:")
    for i, s in enumerate(p.get("test_scenarios", []), 1):
        print(f"    {i}. {s}")


def _print_phase_23_summary(state: PipelineState) -> None:
    tcs = state.phase_2_test_cases or []
    r = state.phase_3_review or {}
    print(f"  Phase 2 — {len(tcs)} test cases generated")
    for tc in tcs:
        flag = "✓" if tc.get("test_type") != "Edge Case" else "◎"
        print(f"    {flag} {tc.get('id')} | {tc.get('test_type')} | {tc.get('title', '')[:55]}")
    print(f"\n  Phase 3 Review — Coverage: {r.get('coverage_score', '?')}  |  Approved: {r.get('approved', '?')}")
    if r.get("gaps"):
        print(f"  Gaps: {', '.join(r['gaps'])}")


def _print_phase_45_summary(state: PipelineState) -> None:
    auto = state.phase_4_automation or {}
    rev = state.phase_5_automation_review or {}
    fns = auto.get("test_functions", [])
    print(f"  Phase 4 — {len(fns)} test functions generated  →  {auto.get('test_file_name', '?')}")
    print(f"  Phase 5 Review — Quality: {rev.get('quality_score', '?')}  |  Approved: {rev.get('approved', '?')}")
    issues = rev.get("issues", [])
    if issues:
        print(f"  Issues ({len(issues)}):")
        for iss in issues[:3]:
            print(f"    [{iss.get('severity')}] {iss.get('function_name')}: {iss.get('issue')}")
        if len(issues) > 3:
            print(f"    ... and {len(issues) - 3} more")


def _print_final_summary(state: PipelineState) -> None:
    print(f"  Feature  : {state.feature_name}")
    print(f"  Phases   : 0 ✓  1 ✓  2 ✓  3 ✓  4 ✓  5 ✓")
    print(f"  Test Cases: {len(state.phase_2_test_cases or [])}")
    print(f"  Automation: {len((state.phase_4_automation or {}).get('test_functions', []))} functions")
    print(f"  Gates     : {state.hitl_approvals}")
    print(f"\n  All output saved to ./output/\n")
