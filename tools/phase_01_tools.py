"""
Tools for Phase 0 (Classification) and Phase 1 (Test Plan).

Output strategy:
  Tools CAPTURE only — no file writing during execution.
  On success: orchestrator writes output/<ID>/stlc_summary_*.md  (one file)
  On failure: orchestrator writes output/<ID>/debug_phase<N>_*.json  (one file)
"""
import json
from typing import Any

PHASE_01_TOOLS: list[dict] = [
    {
        "name": "save_test_plan",
        "description": (
            "Persist Phase 0 classification and Phase 1 test plan to disk. "
            "Both phases must be fully completed before calling this tool."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "feature_name": {"type": "string"},
                "phase_0_classification": {
                    "type": "object",
                    "properties": {
                        "test_type":      {"type": "string", "enum": ["API", "UI", "Mobile", "Integration", "Performance", "Security", "E2E"]},
                        "risk_level":     {"type": "string", "enum": ["High", "Medium", "Low"]},
                        "test_approach":  {"type": "string", "enum": ["Automated", "Manual", "Both"]},
                        "priority":       {"type": "string", "enum": ["P1", "P2", "P3"]},
                        "rationale":      {"type": "string"},
                    },
                    "required": ["test_type", "risk_level", "test_approach", "priority", "rationale"],
                },
                "phase_1_test_plan": {
                    "type": "object",
                    "properties": {
                        "objectives":      {"type": "array", "items": {"type": "string"}},
                        "in_scope":        {"type": "array", "items": {"type": "string"}},
                        "out_of_scope":    {"type": "array", "items": {"type": "string"}},
                        "test_scenarios":  {"type": "array", "items": {"type": "string"}},
                        "entry_criteria":  {"type": "array", "items": {"type": "string"}},
                        "exit_criteria":   {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["objectives", "in_scope", "out_of_scope", "test_scenarios", "entry_criteria", "exit_criteria"],
                },
            },
            "required": ["feature_name", "phase_0_classification", "phase_1_test_plan"],
        },
    }
]


def handle_phase_01_tool(name: str, tool_input: dict) -> tuple[dict, Any]:
    """
    Captures Phase 0+1 data WITHOUT writing any files.
    Files are written only by the orchestrator:
      - One summary MD on successful pipeline completion
      - One debug JSON if the pipeline aborts or hits a hardstop
    """
    if name == "save_test_plan":
        normalized_input = _normalize_tool_input(tool_input)
        if normalized_input is None:
            return {"error": "phase_1_test_plan must be an object or valid JSON"}, None
        # Return success to the agent — no file written yet
        return {"status": "captured", "message": "Test plan captured. Pipeline will save on completion."}, normalized_input
    return {"error": f"Unknown tool: {name}"}, None


def _normalize_tool_input(tool_input: dict) -> dict | None:
    phase_1_test_plan = tool_input.get("phase_1_test_plan")
    if isinstance(phase_1_test_plan, str):
        try:
            phase_1_test_plan = json.loads(phase_1_test_plan)
        except json.JSONDecodeError:
            return None
        if not isinstance(phase_1_test_plan, dict):
            return None
        normalized_input = dict(tool_input)
        normalized_input["phase_1_test_plan"] = phase_1_test_plan
        return normalized_input
    if isinstance(phase_1_test_plan, dict):
        return tool_input
    return None


# All file writing removed. Data flows:
#   tool call → handle_phase_01_tool (capture) → PipelineState → summary_writer.py
