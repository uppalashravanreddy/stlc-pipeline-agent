"""
CAPSTONE CONCEPTS DEMONSTRATED:
  - Agent vs Sub-Agents: AutomationAgent is the third sub-agent in the pipeline.
      It receives context only from PipelineState, never from prior agents directly.
  - Workflow / Pipelines: sequential execution — Phase 4 must complete before Phase 5.
      Each phase is a separate agentic loop with its own system prompt + tool.
"""
import json
from config.agent_configs import AGENT_CONFIGS
from memory.pipeline_state import PipelineState
from agents.base_agent import BaseAgent
from tools.phase_45_tools import PHASE_45_TOOLS, handle_phase_45_tool


PHASE_4_SYSTEM_PROMPT = """\
You are a senior automation engineer generating pytest test automation.

## YOUR ROLE
You are a SUB-AGENT. You receive Phase 2 test cases and generate pytest code.
When all test functions are generated, call save_automation and stop.

## PYTEST RULES
- One test function per test case
- Function name: test_{test_case_id}_{short_title_snake_case}
- Use fixtures for setup/teardown (don't repeat setup in every test)
- No hardcoded credentials — use fixtures or environment variables
- Each function has exactly ONE assert or raises block
- Add a one-line docstring referencing the test case ID and scenario

## AUTOMATION DECISIONS
- test_type=Positive: happy-path assertion
- test_type=Negative: pytest.raises() or assert error message in response
- test_type=Security: check response headers, status codes, error messages
- automation_feasibility=Low: generate the function with a pytest.skip() and a comment explaining why

## RULE
Generate ALL test functions before calling save_automation.
"""

PHASE_5_SYSTEM_PROMPT = """\
You are a QA automation lead reviewing generated pytest code.

## YOUR ROLE
Review all generated test functions for quality and coverage.
Call save_automation_review when complete.

## WHAT TO REVIEW
1. Missing assertions (a test that doesn't assert anything always passes — that's a bug)
2. Hardcoded credentials or environment-specific values
3. Tests that duplicate each other exactly
4. Missing test cases from Phase 2 (automation_feasibility != Low)
5. Functions that will fail on import (syntax errors, wrong imports)

## SCORING
quality_score: X/10
  10 = clean, complete, production-ready
  7-9 = minor issues
  5-6 = issues that would cause false positives/negatives
  <5 = blocking — needs rework

approved = true only if quality_score >= 7 AND no blocking severity issues.
"""


class AutomationAgent(BaseAgent):
    """Sub-agent responsible for Phase 4 (Automation Generate) and Phase 5 (Review)."""

    def __init__(self):
        super().__init__(
            config=AGENT_CONFIGS["automation"],
            tools=PHASE_45_TOOLS,
        )

    def run_phase_4(self, state: PipelineState) -> PipelineState:
        """Generate pytest automation from Phase 2 test cases."""
        print(f"\n{'─' * 60}")
        print(f"  AUTOMATION AGENT  (Phase 4 — Generate)")
        print(f"  Model: {self.config.model}")
        print(f"{'─' * 60}\n")

        tc_summary = json.dumps(state.phase_2_test_cases, indent=2)
        context = state.summary_for_next_agent()

        user_message = (
            f"{context}\n\n"
            "--- TEST CASES TO AUTOMATE (Phase 2) ---\n"
            f"{tc_summary}\n\n"
            f"Generate pytest automation for the feature '{state.feature_name}'. "
            "Call save_automation when all test functions are ready."
        )

        results = self.run_loop(
            system_prompt=PHASE_4_SYSTEM_PROMPT,
            user_message=user_message,
            on_tool_call=handle_phase_45_tool,
        )

        for phase_tag, data in results:
            if phase_tag == "phase_4":
                state.phase_4_automation = data
                state.current_phase = 4
                fn_count = len(data.get("test_functions", []))
                self._log("phase 4 complete", f"{fn_count} test functions")

        if not state.phase_4_automation:
            self._log("FAIL", "save_automation was never called — no automation code in output")

        return state

    def run_phase_5(self, state: PipelineState) -> PipelineState:
        """Review the generated automation code."""
        print(f"\n{'─' * 60}")
        print(f"  AUTOMATION AGENT  (Phase 5 — Review)")
        print(f"  Model: {self.config.model}")
        print(f"{'─' * 60}\n")

        auto_summary = json.dumps(state.phase_4_automation, indent=2)

        user_message = (
            f"Feature: {state.feature_name}\n\n"
            "--- GENERATED AUTOMATION (Phase 4) ---\n"
            f"{auto_summary}\n\n"
            "Review this automation code. Call save_automation_review when complete."
        )

        results = self.run_loop(
            system_prompt=PHASE_5_SYSTEM_PROMPT,
            user_message=user_message,
            on_tool_call=handle_phase_45_tool,
        )

        for phase_tag, data in results:
            if phase_tag == "phase_5":
                state.phase_5_automation_review = data
                state.current_phase = 5
                self._log("phase 5 complete", f"approved={data.get('approved')} score={data.get('quality_score')}")

        if not state.phase_5_automation_review:
            self._log("FAIL", "save_automation_review was never called — no review in output")

        return state
