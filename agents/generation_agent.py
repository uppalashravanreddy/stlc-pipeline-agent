"""
CAPSTONE CONCEPTS DEMONSTRATED:
  - Agent vs Sub-Agents: GenerationAgent is a SUB-AGENT — it receives a compressed
      summary of Phases 0+1 from the orchestrator via PipelineState, not raw history.
  - Token Optimization: state.summary_for_next_agent() replaces passing full conversation
      history. The sub-agent only sees what it needs.
  - Prompt Engineering: role priming ("You are a test case generator"),
      structured output enforced via tool schema, explicit output format rules.
"""
from config.agent_configs import AGENT_CONFIGS
from memory.pipeline_state import PipelineState
from agents.base_agent import BaseAgent
from tools.phase_23_tools import PHASE_23_TOOLS, handle_phase_23_tool


PHASE_2_SYSTEM_PROMPT = """\
You are a senior QA engineer generating executable test cases.

## YOUR ROLE
You are a SUB-AGENT. You only generate test cases (Phase 2).
You receive Phase 0 classification and Phase 1 test plan as context.
When all test cases are generated, call save_test_cases and stop.

## TEST CASE RULES
For EACH Phase 1 scenario, generate 1–2 test cases:
- id: TC-001, TC-002, ... (sequential)
- title: specific action + expected outcome (not vague)
- preconditions: setup that must be true BEFORE the test
- steps: numbered, specific, executable (someone else can run this without asking)
- expected_result: clear observable outcome — pass = X happens, fail = Y happens
- test_data: specific values, NOT "enter a valid email" — use actual values
- test_type: Positive | Negative | Edge Case | Security | Performance
- priority: inherit from Phase 0 risk level (High risk = mostly P1)

## MIX REQUIREMENT
Aim for: ~40% Positive, ~35% Negative, ~25% Edge Case
If Phase 0 test_type is Security: add at least one Security test case.
If Phase 0 risk_level is High: at least one Edge Case per scenario.

## HARD LIMIT
Generate a MAXIMUM of 8 test cases total. Do not plan more than 8.
Quality over quantity — 8 well-written cases beat 15 vague ones.

## RULE
Do NOT write a planning outline first. Generate test cases directly and
call save_test_cases immediately when done. Never exceed 8 cases.
"""

PHASE_3_SYSTEM_PROMPT = """\
You are a QA review lead reviewing test cases for completeness and quality.

## YOUR ROLE
Review the test cases generated in Phase 2 against the Phase 1 test plan.
When review is complete, call save_review and stop.

## WHAT TO CHECK
1. Coverage gaps — Phase 1 scenarios with no test case
2. Redundancy — near-duplicate test cases doing the same thing
3. Vague steps — "navigate to the page" with no URL/action is vague
4. Missing test data — placeholders instead of actual values
5. Missing assertions — steps with no clear expected result

## SCORING
coverage_score: X/10
  10 = all scenarios covered with good edge cases
  7-9 = minor gaps
  5-6 = notable gaps
  <5 = significant rework needed

approved = true only if coverage_score >= 7 AND no blocking issues.

## RULE
Only call save_review when the full review is complete.
"""


class GenerationAgent(BaseAgent):
    """Sub-agent responsible for Phase 2 (Test Cases) and Phase 3 (Review)."""

    def __init__(self):
        super().__init__(
            config=AGENT_CONFIGS["generation"],
            tools=PHASE_23_TOOLS,
        )

    def run_phase_2(self, state: PipelineState) -> PipelineState:
        """
        Generate test cases from Phase 1 test plan.

        CAPSTONE: Token Optimization — passes compressed state summary,
        not the raw Phase 0+1 conversation history.
        """
        print(f"\n{'─' * 60}")
        print(f"  GENERATION AGENT  (Phase 2 — Test Cases)")
        print(f"  Model: {self.config.model}")
        print(f"{'─' * 60}\n")

        # CAPSTONE: Token Optimization — compressed context, not full history
        context = state.summary_for_next_agent()
        user_message = (
            f"{context}\n\n"
            "Generate executable test cases from the Phase 1 scenarios above. "
            "Call save_test_cases when all are complete."
        )

        results = self.run_loop(
            system_prompt=PHASE_2_SYSTEM_PROMPT,
            user_message=user_message,
            on_tool_call=handle_phase_23_tool,
        )

        # Agent may call both save_test_cases AND save_review in one loop — handle both
        for phase_tag, data in results:
            if phase_tag == "phase_2":
                state.phase_2_test_cases = data
                state.current_phase = 2
                self._log("phase 2 complete", f"{len(data)} test cases")
            elif phase_tag == "phase_3":
                state.phase_3_review = data
                state.current_phase = 3
                self._log("phase 3 also captured in same loop", f"approved={data.get('approved')}")

        if not state.phase_2_test_cases:
            self._log("FAIL", "save_test_cases was never called — no test cases in output")

        return state

    def run_phase_3(self, state: PipelineState) -> PipelineState:
        """
        Review test cases from Phase 2 against the Phase 1 plan.
        """
        print(f"\n{'─' * 60}")
        print(f"  GENERATION AGENT  (Phase 3 — Review)")
        print(f"  Model: {self.config.model}")
        print(f"{'─' * 60}\n")

        import json
        tc_summary = json.dumps(state.phase_2_test_cases, indent=2)
        context = state.summary_for_next_agent()

        user_message = (
            f"{context}\n\n"
            "--- GENERATED TEST CASES (Phase 2) ---\n"
            f"{tc_summary}\n\n"
            "Review these test cases against the Phase 1 scenarios. "
            "Call save_review when complete."
        )

        results = self.run_loop(
            system_prompt=PHASE_3_SYSTEM_PROMPT,
            user_message=user_message,
            on_tool_call=handle_phase_23_tool,
        )

        for phase_tag, data in results:
            if phase_tag == "phase_3":
                state.phase_3_review = data
                state.current_phase = 3
                self._log("phase 3 complete", f"approved={data.get('approved')} score={data.get('coverage_score')}")

        if not state.phase_3_review:
            self._log("FAIL", "save_review was never called — no review in output")

        return state
