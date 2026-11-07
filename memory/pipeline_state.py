"""
CAPSTONE CONCEPTS DEMONSTRATED:
  - Memory Types: three types are active in this pipeline
      1. In-Context Memory  — the messages[] list inside each agent's agentic loop
      2. Shared State (this class) — cross-agent working memory passed by the orchestrator
      3. External Memory — persisted JSON/Markdown files written to output/
  - Token Optimization: summary_for_next_agent() compresses completed phases
      instead of passing full conversation history to the next agent
  - Lost in the Middle: critical context placed at the TOP of the summary,
      not buried in the middle of a long message
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PipelineState:
    # Input
    feature_name: str
    user_story: str

    # Phase outputs — populated as the pipeline progresses
    phase_0_classification: Optional[dict] = None
    phase_1_test_plan: Optional[dict] = None
    phase_2_test_cases: Optional[list] = None
    phase_3_review: Optional[dict] = None
    phase_4_automation: Optional[dict] = None
    phase_5_automation_review: Optional[dict] = None
    phase_6_fix: Optional[dict] = None          # Review Comments Fix
    phase_7_ptr: Optional[dict] = None          # Project Test Report
    github_pr_url: Optional[str] = None         # created PR URL

    # Tracking
    current_phase: int = 0
    hitl_approvals: dict = field(default_factory=dict)

    def summary_for_next_agent(self) -> str:
        """
        CAPSTONE: Token Optimization + Lost in the Middle

        Instead of appending raw conversation history to every new agent call
        (which makes the context window grow O(n) across phases), we extract
        only the structured outputs and compress them into a summary.

        Critical context (feature name, classification) is placed FIRST —
        not in the middle — because attention is strongest at the start and end
        of a prompt (Lost in the Middle pattern).
        """
        # ── START: most critical context goes here ──
        parts = [
            f"FEATURE: {self.feature_name}",
            f"USER STORY:\n{self.user_story}",
        ]

        if self.phase_0_classification:
            c = self.phase_0_classification
            parts.append(
                f"\n[PHASE 0 — Classification COMPLETE]\n"
                f"  Type: {c['test_type']}  |  Risk: {c['risk_level']}  |  "
                f"Approach: {c['test_approach']}  |  Priority: {c['priority']}\n"
                f"  Rationale: {c['rationale']}"
            )

        if self.phase_1_test_plan:
            p = self.phase_1_test_plan
            scenarios_text = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(p["test_scenarios"]))
            parts.append(
                f"\n[PHASE 1 — Test Plan COMPLETE]\n"
                f"  Objectives: {'; '.join(p['objectives'])}\n"
                f"  In Scope: {', '.join(p['in_scope'])}\n"
                f"  Scenarios:\n{scenarios_text}\n"
                f"  Entry: {'; '.join(p['entry_criteria'])}\n"
                f"  Exit: {'; '.join(p['exit_criteria'])}"
            )

        if self.phase_2_test_cases:
            tc_titles = [tc.get("title", f"TC-{i+1:03}") for i, tc in enumerate(self.phase_2_test_cases)]
            parts.append(
                f"\n[PHASE 2 — Test Cases COMPLETE]\n"
                f"  {len(self.phase_2_test_cases)} cases generated:\n"
                + "\n".join(f"  - {t}" for t in tc_titles)
            )

        if self.phase_3_review:
            r = self.phase_3_review
            parts.append(
                f"\n[PHASE 3 — Review COMPLETE]\n"
                f"  Coverage: {r.get('coverage_score', '?')}  |  "
                f"Approved: {r.get('approved', '?')}\n"
                f"  Notes: {r.get('overall_notes', '')}"
            )
        # ── END: critical context also benefits from being near the end ──

        return "\n".join(parts)

    def to_dict(self) -> dict:
        return {
            "feature_name":            self.feature_name,
            "user_story":              self.user_story,
            "phase_0_classification":  self.phase_0_classification,
            "phase_1_test_plan":       self.phase_1_test_plan,
            "phase_2_test_cases":      self.phase_2_test_cases,
            "phase_3_review":          self.phase_3_review,
            "phase_4_automation":      self.phase_4_automation,
            "phase_5_automation_review": self.phase_5_automation_review,
            "phase_6_fix":             self.phase_6_fix,
            "phase_7_ptr":             self.phase_7_ptr,
            "github_pr_url":           self.github_pr_url,
            "current_phase":           self.current_phase,
            "hitl_approvals":          self.hitl_approvals,
        }
