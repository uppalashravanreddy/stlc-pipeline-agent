"""
Tools for Phase 4 (Automation Generate) and Phase 5 (Automation Review).

Output strategy:
  Tools CAPTURE only — no file writing during execution.
  On success: orchestrator calls memory/summary_writer.py → one stlc_summary_*.md
  On failure: orchestrator calls memory/summary_writer.py → one debug_*.json
"""
from typing import Any

PHASE_45_TOOLS: list[dict] = [
    {
        "name": "save_automation",
        "description": (
            "Persist the generated pytest automation code for Phase 4. "
            "Generate automation for ALL test cases before calling this."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "feature_name": {"type": "string"},
                "test_file_name": {
                    "type": "string",
                    "description": "e.g. test_user_authentication.py",
                },
                "imports": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Required import statements",
                },
                "fixtures": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name":        {"type": "string"},
                            "scope":       {"type": "string", "enum": ["function", "class", "module", "session"]},
                            "description": {"type": "string"},
                            "code":        {"type": "string"},
                        },
                        "required": ["name", "scope", "code"],
                    },
                },
                "test_functions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "test_case_id": {"type": "string"},
                            "function_name":{"type": "string", "description": "e.g. test_valid_login_with_correct_credentials"},
                            "docstring":    {"type": "string"},
                            "code":         {"type": "string", "description": "Full test function body"},
                        },
                        "required": ["test_case_id", "function_name", "code"],
                    },
                },
                "automation_notes": {"type": "string"},
            },
            "required": ["feature_name", "test_file_name", "test_functions"],
        },
    },
    {
        "name": "save_automation_review",
        "description": (
            "Persist Phase 5 review of the generated automation code. "
            "Review all test functions before calling."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "feature_name":   {"type": "string"},
                "quality_score":  {"type": "string", "description": "e.g. '7/10'"},
                "issues": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "function_name": {"type": "string"},
                            "severity":      {"type": "string", "enum": ["blocking", "major", "minor"]},
                            "issue":         {"type": "string"},
                            "fix":           {"type": "string"},
                        },
                        "required": ["function_name", "severity", "issue"],
                    },
                },
                "missing_coverage": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Test cases from Phase 2 with no automation",
                },
                "approved":       {"type": "boolean"},
                "overall_notes":  {"type": "string"},
            },
            "required": ["feature_name", "quality_score", "approved", "overall_notes"],
        },
    },
]


def handle_phase_45_tool(name: str, tool_input: dict) -> tuple[dict, Any]:
    """
    Captures Phase 4+5 data WITHOUT writing files.
    Orchestrator writes the final summary MD on completion.
    """
    if name == "save_automation":
        fn_count = len(tool_input.get("test_functions", []))
        return {"status": "captured", "functions": fn_count}, ("phase_4", tool_input)
    if name == "save_automation_review":
        return {"status": "captured", "approved": tool_input.get("approved")}, ("phase_5", tool_input)
    return {"error": f"Unknown tool: {name}"}, None


# All file writing removed.
# Data flows: tool call → handle_phase_45_tool (capture) → PipelineState → summary_writer.py
