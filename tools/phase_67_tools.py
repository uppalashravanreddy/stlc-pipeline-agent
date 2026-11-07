"""
Tools for Phase 6 (Fix Review Comments) and Phase 7 (PTR + Create MR).
Capture-only — no file writing. Orchestrator writes stlc_summary_*.md on success.
"""
from typing import Any

PHASE_6_TOOLS: list[dict] = [
    {
        "name": "save_fixed_automation",
        "description": (
            "Capture the fixed automation code after addressing Phase 5 review comments. "
            "Fix ALL blocking and major issues before calling. Include a fix manifest."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "feature_name":  {"type": "string"},
                "test_functions": {
                    "type": "array",
                    "description": "Updated test functions with all issues resolved",
                    "items": {
                        "type": "object",
                        "properties": {
                            "test_case_id":   {"type": "string"},
                            "function_name":  {"type": "string"},
                            "code":           {"type": "string"},
                            "docstring":      {"type": "string"},
                        },
                        "required": ["test_case_id", "function_name", "code"],
                    },
                },
                "fix_manifest": {
                    "type": "array",
                    "description": "What was changed and why — one entry per fix",
                    "items": {
                        "type": "object",
                        "properties": {
                            "function_name": {"type": "string"},
                            "issue":         {"type": "string"},
                            "fix_applied":   {"type": "string"},
                            "severity":      {"type": "string"},
                        },
                        "required": ["function_name", "issue", "fix_applied"],
                    },
                },
                "quality_score_after_fix": {
                    "type": "string",
                    "description": "Estimated quality score after fixes e.g. '9/10'",
                },
            },
            "required": ["feature_name", "test_functions", "fix_manifest"],
        },
    }
]

PHASE_7_TOOLS: list[dict] = [
    {
        "name": "save_ptr",
        "description": (
            "Capture the Project Test Report summarising all STLC phases. "
            "This becomes the GitHub PR description."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "feature_name":      {"type": "string"},
                "pr_title":          {"type": "string", "description": "GitHub PR title"},
                "executive_summary": {"type": "string", "description": "2-3 sentence summary for reviewers"},
                "phase_summary": {
                    "type": "object",
                    "description": "One-line outcome per phase",
                    "properties": {
                        "phase_0": {"type": "string"},
                        "phase_1": {"type": "string"},
                        "phase_2": {"type": "string"},
                        "phase_3": {"type": "string"},
                        "phase_4": {"type": "string"},
                        "phase_5": {"type": "string"},
                        "phase_6": {"type": "string"},
                    },
                },
                "test_case_count":     {"type": "integer"},
                "automation_count":    {"type": "integer"},
                "coverage_score":      {"type": "string"},
                "quality_score":       {"type": "string"},
                "open_risks": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Known risks or gaps that reviewers should be aware of",
                },
                "recommendation":      {"type": "string", "enum": ["APPROVE", "APPROVE_WITH_CONDITIONS", "REQUEST_CHANGES"]},
                "conditions":          {"type": "array", "items": {"type": "string"}},
            },
            "required": ["feature_name", "pr_title", "executive_summary", "recommendation"],
        },
    }
]


def handle_phase_6_tool(name: str, tool_input: dict) -> tuple[dict, Any]:
    if name == "save_fixed_automation":
        fix_count = len(tool_input.get("fix_manifest", []))
        return {"status": "captured", "fixes": fix_count}, ("phase_6", tool_input)
    return {"error": f"Unknown tool: {name}"}, None


def handle_phase_7_tool(name: str, tool_input: dict) -> tuple[dict, Any]:
    if name == "save_ptr":
        return {"status": "captured", "recommendation": tool_input.get("recommendation")}, ("phase_7", tool_input)
    return {"error": f"Unknown tool: {name}"}, None
