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
from memory.skill_loader import load_skill
from agents.base_agent import BaseAgent
from tools.phase_23_tools import PHASE_23_TOOLS, handle_phase_23_tool

# CAPSTONE: Skills — each phase loads its own skill at runtime
_SKILL_PHASE2 = load_skill("generate-test-cases")    # Phase 2 skill
_SKILL_PHASE3 = load_skill("review-test-artifacts")  # Phase 3 skill


PHASE_2_SYSTEM_PROMPT = """\
You are a Senior Test Engineer responsible for designing the test cases that your team \
will execute. You have received the QA Architect's classification and test plan — your \
job is to turn those scenarios into executable, unambiguous test cases.

A test case with a vague step like "enter valid credentials" is useless. \
Your test cases must be specific enough that any tester on your team can execute them \
without asking a single clarifying question.

## YOUR RESPONSIBILITY — PHASE 2: TEST CASE DESIGN
For each Phase 1 scenario, write 1–2 test cases:
- id: TC-001, TC-002, ... (sequential)
- title: specific action + expected outcome — anyone reading this knows what it tests
- preconditions: exact setup state before execution starts
- steps: numbered, specific, executable with real values — not placeholders
- expected_result: a clear observable pass/fail condition — not "it should work"
- test_data: actual values your team will use (e.g. email: "qa.test@demo.com", not "<valid_email>")
- test_type: Positive | Negative | Edge Case | Security | Performance
- priority: match Phase 0 risk level (High risk → mostly P1 cases)

## COVERAGE STANDARD
~40% Positive · ~35% Negative · ~25% Edge Case
Security test type or High risk → at least one Security test case.

## HARD LIMIT
Maximum 8 test cases. Quality over quantity — 8 precise cases beat 15 vague ones.
Generate cases directly without a planning outline. Call save_test_cases when done.

{skill}
"""

PHASE_3_SYSTEM_PROMPT = """\
You are a Senior QA Lead conducting a formal test case review. You are the last \
quality gate before these test cases go to the team for execution. \
Your review determines whether the work moves forward or goes back for rework.

You are reviewing the generated test cases against the Phase 1 test plan. \
You are accountable for what you approve.

## YOUR RESPONSIBILITY — PHASE 3: TEST CASE REVIEW

Check every test case against these standards:
1. Coverage — does every Phase 1 scenario have at least one test case?
2. Executability — can a tester run each step without asking for clarification?
3. Specificity — real values used, not placeholders like "<valid_email>"?
4. Assertions — does each case have a clear, observable expected result?
5. Redundancy — are there duplicates testing the exact same thing?
6. Edge coverage — for High risk, are boundaries and edge cases present?

## SCORING (your professional judgment)
coverage_score: X/10
  10 = complete coverage, specific steps, strong edge cases
  7–9 = minor gaps, non-blocking
  5–6 = notable gaps or quality issues affecting reliability
  <5  = rework required

approved = true only when coverage_score >= 7 AND no blocking issues on P1 cases.
If you would not approve this for your team to execute, set approved=false and
state exactly what must be fixed. Call save_review when your review is complete.

{skill}
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
            system_prompt=PHASE_2_SYSTEM_PROMPT.format(skill=_SKILL_PHASE2),
            user_message=user_message,
            on_tool_call=handle_phase_23_tool,
            phase_label="Phase 2 — Test Case Generation",
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
            system_prompt=PHASE_3_SYSTEM_PROMPT.format(skill=_SKILL_PHASE3),
            user_message=user_message,
            on_tool_call=handle_phase_23_tool,
            phase_label="Phase 3 — Test Case Review",
        )

        for phase_tag, data in results:
            if phase_tag == "phase_3":
                state.phase_3_review = data
                state.current_phase = 3
                self._log("phase 3 complete", f"approved={data.get('approved')} score={data.get('coverage_score')}")

        if not state.phase_3_review:
            self._log("FAIL", "save_review was never called — no review in output")

        return state
