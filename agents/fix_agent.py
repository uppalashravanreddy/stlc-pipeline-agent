"""
Phase 6 — Review Comments Fix Agent

Receives Phase 5 automation review issues and the Phase 4 test functions.
Fixes every blocking/major issue and produces a fix manifest showing what changed.
"""
import json
from config.agent_configs import AGENT_CONFIGS
from memory.pipeline_state import PipelineState
from agents.base_agent import BaseAgent
from tools.phase_67_tools import PHASE_6_TOOLS, handle_phase_6_tool

SYSTEM_PROMPT = """You are a Senior Automation Engineer fixing review comments on a pytest test suite.

You receive:
  - Phase 4 automation code (the EXISTING test functions)
  - Phase 5 review issues (what is wrong and severity)

CRITICAL RULE: Fix ONLY the EXISTING test functions listed in the Phase 4 output.
  - Do NOT add new test functions (TC-006, TC-007 etc.) -- that is Phase 2's job
  - Do NOT add new test cases -- only fix what exists
  - Missing test cases are P2 backlog items, not Phase 6 tasks

For each EXISTING function:
  - Fix BLOCKING and MAJOR issues only
  - Apply the fix precisely -- do not rewrite unrelated code
  - Document what you changed and why in the fix_manifest
  - Keep the original test_case_id and function_name

After fixing, call save_fixed_automation with:
  - ONLY the functions that were in Phase 4 (same count or fewer if any were removed)
  - A fix_manifest entry for every issue you addressed
  - A quality_score_after_fix estimate

RULES:
  - Return ONLY existing functions with fixes applied -- never add new functions
  - If a fix is too large to apply cleanly, skip it and document why
  - Call save_fixed_automation only when all blocking/major issues on EXISTING functions are resolved
"""


class FixAgent(BaseAgent):
    """Phase 6 — fixes automation review comments."""

    def __init__(self):
        super().__init__(config=AGENT_CONFIGS["fix"], tools=PHASE_6_TOOLS)

    def run(self, state: PipelineState) -> PipelineState:
        print(f"\n{'─'*60}")
        print(f"  FIX AGENT  (Phase 6 — Fix Review Comments)")
        print(f"  Model: {self.config.model}")
        print(f"{'─'*60}\n")

        auto   = state.phase_4_automation or {}
        review = state.phase_5_automation_review or {}
        issues = review.get("issues", [])

        if not issues:
            self._log("skip", "No issues to fix from Phase 5 review")
            state.current_phase = 6
            return state

        blocking = [i for i in issues if i.get("severity") == "blocking"]
        major    = [i for i in issues if i.get("severity") == "major"]
        self._log("issues to fix", f"blocking={len(blocking)} major={len(major)}")

        fns_json    = json.dumps(auto.get("test_functions", []), indent=2)
        issues_json = json.dumps(issues, indent=2)

        user_message = (
            f"Feature: {state.feature_name}\n\n"
            f"--- CURRENT TEST FUNCTIONS (Phase 4) ---\n{fns_json}\n\n"
            f"--- REVIEW ISSUES TO FIX (Phase 5) ---\n{issues_json}\n\n"
            "Fix all blocking and major issues. Call save_fixed_automation when done."
        )

        results = self.run_loop(
            system_prompt=SYSTEM_PROMPT,
            user_message=user_message,
            on_tool_call=handle_phase_6_tool,
            phase_label="Phase 6 — Fix Review Comments",
        )

        for phase_tag, data in results:
            if phase_tag == "phase_6":
                state.phase_6_fix = data
                state.current_phase = 6
                self._log("phase 6 complete", f"{len(data.get('fix_manifest',[]))} fixes applied")

        if not state.phase_6_fix:
            self._log("FAIL", "save_fixed_automation not called")

        return state
