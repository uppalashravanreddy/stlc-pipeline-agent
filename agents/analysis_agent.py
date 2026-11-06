"""
CAPSTONE CONCEPTS DEMONSTRATED:
  - Agent vs Sub-Agents: AnalysisAgent is a SUB-AGENT — it only knows Phase 0+1.
      The orchestrator decides when to call it and what to do with its output.
  - Agent Configurations: uses AGENT_CONFIGS["analysis"] — Sonnet, 3000 tokens, 8 iter cap
  - Prompt Engineering: CoT via Phase 0 → Phase 1 reasoning chain;
      critical instructions at TOP of system prompt (Lost in the Middle mitigation)
"""
from config.agent_configs import AGENT_CONFIGS
from memory.pipeline_state import PipelineState
from agents.base_agent import BaseAgent
from tools.phase_01_tools import PHASE_01_TOOLS, handle_phase_01_tool


SYSTEM_PROMPT = """\
You are a senior QA architect running a 2-phase STLC analysis pipeline.

## YOUR ROLE
You are a SUB-AGENT. You only do Phase 0 and Phase 1. You do NOT generate test cases.
When both phases are complete, call save_test_plan and stop.

## PHASE 0 — CLASSIFICATION
Analyze the feature and determine:
- test_type: primary type (API | UI | Mobile | Integration | Performance | Security | E2E)
- risk_level: High | Medium | Low — business impact × technical complexity
- test_approach: Automated | Manual | Both — based on ROI and feasibility
- priority: P1 | P2 | P3 — P1 = release blocker
- rationale: 1–2 sentences explaining the classification

## PHASE 1 — TEST PLAN
Using Phase 0 output to calibrate scope and depth:
- objectives: 2–3 specific, measurable testing goals
- in_scope: behaviors that WILL be tested
- out_of_scope: explicitly excluded (no ambiguity allowed)
- test_scenarios: 5–7 scenarios — mix of positive, negative, edge cases
- entry_criteria: pre-conditions before testing begins
- exit_criteria: measurable conditions that define "done"

## REASONING RULES
1. Complete Phase 0 reasoning before writing Phase 1
2. High risk → broader scope, more edge cases
3. Low risk → focused scope, fewer scenarios
4. Only call save_test_plan when BOTH phases are fully complete
"""


class AnalysisAgent(BaseAgent):
    """Sub-agent responsible for Phase 0 (Classification) and Phase 1 (Test Plan)."""

    def __init__(self):
        super().__init__(
            config=AGENT_CONFIGS["analysis"],
            tools=PHASE_01_TOOLS,
        )

    def run(self, state: PipelineState) -> PipelineState:
        """
        Run Phase 0 + Phase 1 for the given pipeline state.
        Updates state.phase_0_classification and state.phase_1_test_plan on success.
        """
        print(f"\n{'─' * 60}")
        print(f"  ANALYSIS AGENT  (Phase 0 → Phase 1)")
        print(f"  Model: {self.config.model}")
        print(f"{'─' * 60}\n")

        user_message = (
            f"Feature: {state.feature_name}\n\n"
            f"User Story:\n{state.user_story}\n\n"
            "Run Phase 0 (Classification) then Phase 1 (Test Plan). "
            "Call save_test_plan when both are complete."
        )

        results = self.run_loop(
            system_prompt=SYSTEM_PROMPT,
            user_message=user_message,
            on_tool_call=handle_phase_01_tool,
        )

        if results:
            result = results[0]
            state.phase_0_classification = result["phase_0_classification"]
            state.phase_1_test_plan = result["phase_1_test_plan"]
            state.current_phase = 1
            self._log("phase 0+1 complete")
        else:
            self._log("FAIL", "save_test_plan was never called — agent did not complete both phases")

        return state
