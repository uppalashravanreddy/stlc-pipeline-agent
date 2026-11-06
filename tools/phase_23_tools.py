"""
Tools for Phase 2 (Test Case Generation) and Phase 3 (Test Case Review).

Output strategy:
  Tools CAPTURE only — no file writing during execution.
  On success: orchestrator calls memory/summary_writer.py → one stlc_summary_*.md
  On failure: orchestrator calls memory/summary_writer.py → one debug_*.json
"""
from typing import Any

PHASE_23_TOOLS: list[dict] = [
    {
        "name": "save_test_cases",
        "description": (
            "Capture all generated test cases for Phase 2. "
            "Generate ALL test cases before calling this — do not call per test case."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "feature_name": {"type": "string"},
                "test_cases": {
                    "type": "array",
                    "description": "All generated test cases",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id":                     {"type": "string",  "description": "e.g. TC-001"},
                            "title":                  {"type": "string",  "description": "Action + expected outcome"},
                            "scenario_ref":            {"type": "string",  "description": "Which Phase 1 scenario this covers"},
                            "preconditions":           {"type": "array",   "items": {"type": "string"}},
                            "steps":                   {"type": "array",   "items": {"type": "string"}},
                            "expected_result":         {"type": "string"},
                            "test_data":               {"type": "object"},
                            "test_type":               {"type": "string",  "enum": ["Positive", "Negative", "Edge Case", "Security", "Performance"]},
                            "priority":                {"type": "string",  "enum": ["P1", "P2", "P3"]},
                            "automation_feasibility":  {"type": "string",  "enum": ["High", "Medium", "Low"]},
                        },
                        "required": ["id", "title", "scenario_ref", "preconditions", "steps", "expected_result", "test_type", "priority"],
                    },
                },
            },
            "required": ["feature_name", "test_cases"],
        },
    },
    {
        "name": "save_review",
        "description": (
            "Capture Phase 3 review results. "
            "Complete the full review before calling."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "feature_name":          {"type": "string"},
                "coverage_score":        {"type": "string", "description": "e.g. '8/10'"},
                "scenarios_covered":     {"type": "array",  "items": {"type": "string"}},
                "gaps":                  {"type": "array",  "items": {"type": "string"}},
                "issues":                {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "test_case_id": {"type": "string"},
                            "issue":        {"type": "string"},
                        },
                    },
                },
                "additions_recommended": {"type": "array",  "items": {"type": "string"}},
                "approved":              {"type": "boolean"},
                "overall_notes":         {"type": "string"},
            },
            "required": ["feature_name", "coverage_score", "gaps", "approved", "overall_notes"],
        },
    },
]


def handle_phase_23_tool(name: str, tool_input: dict) -> tuple[dict, Any]:
    """
    Captures Phase 2+3 data in memory — no files written.
    Data flows: tool call → PipelineState → summary_writer on completion.
    """
    if name == "save_test_cases":
        count = len(tool_input.get("test_cases", []))
        return {"status": "captured", "count": count}, ("phase_2", tool_input.get("test_cases", []))
    if name == "save_review":
        return {"status": "captured", "approved": tool_input.get("approved")}, ("phase_3", tool_input)
    return {"error": f"Unknown tool: {name}"}, None
