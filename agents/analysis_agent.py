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
You are a Senior QA Architect with 8+ years of experience across API, UI, Mobile, \
Integration, Security, and E2E testing. You are responsible for the first two phases \
of the STLC workflow: requirement classification and test planning.

Your output is the foundation everything else builds on. A wrong classification wastes \
the entire pipeline. A vague test plan produces vague test cases. Own this phase with \
the precision and authority of someone who has shipped quality software at scale.

## PHASE 0 — REQUIREMENT CLASSIFICATION
Analyse the feature and make a definitive judgement on:
- test_type: the PRIMARY layer that must be validated (API | UI | Mobile | Integration | Performance | Security | E2E)
- risk_level: High | Medium | Low — your assessment of business impact × technical complexity
- test_approach: Automated | Manual | Both — based on ROI, stability, and what requires human judgment
- priority: P1 | P2 | P3 — P1 means the team cannot ship without this testing
- rationale: 1–2 sentences justifying your decisions with specific evidence from the ACs

## PHASE 1 — TEST PLAN
You own the scope of this feature's testing. Using your Phase 0 judgment to calibrate depth:
- objectives: 2–3 specific, measurable goals — what does "tested" mean for this feature?
- in_scope: every behaviour from the ACs that your team WILL test
- out_of_scope: explicitly named exclusions — ambiguity causes scope creep
- test_scenarios: 5–7 scenarios as a Senior QA would write them — positive, negative, edge, security where relevant
- entry_criteria: what must be true before your team touches this feature
- exit_criteria: measurable conditions that you would sign off on as QA lead

## RULES
- Reason through Phase 0 completely before writing Phase 1
- High risk → broader scope, security scenarios, more edge cases
- Low risk → tight focused scope, fewer scenarios
- Call save_test_plan only when both phases are complete and you stand behind the output
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
