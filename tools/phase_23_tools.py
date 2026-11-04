"""
Tools for Phase 2 (Test Case Generation) and Phase 3 (Test Case Review).
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any

OUTPUT_DIR = Path(__file__).parent.parent / "output"

PHASE_23_TOOLS: list[dict] = [
    {
        "name": "save_test_cases",
        "description": (
            "Persist all generated test cases for Phase 2. "
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
                            "id":           {"type": "string", "description": "e.g. TC-001"},
                            "title":        {"type": "string", "description": "Action + expected outcome"},
                            "scenario_ref": {"type": "string", "description": "Which Phase 1 scenario this covers"},
                            "preconditions":{"type": "array", "items": {"type": "string"}},
                            "steps":        {"type": "array", "items": {"type": "string"}, "description": "Numbered, executable steps"},
                            "expected_result": {"type": "string"},
                            "test_data":    {"type": "object", "description": "Specific values to use (not placeholders)"},
                            "test_type":    {"type": "string", "enum": ["Positive", "Negative", "Edge Case", "Security", "Performance"]},
                            "priority":     {"type": "string", "enum": ["P1", "P2", "P3"]},
                            "automation_feasibility": {"type": "string", "enum": ["High", "Medium", "Low"]},
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
            "Persist Phase 3 review of the generated test cases. "
            "Review all test cases against the Phase 1 plan before calling."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "feature_name": {"type": "string"},
                "coverage_score": {
                    "type": "string",
                    "description": "e.g. '8/10' — how well test cases cover Phase 1 scenarios",
                },
                "scenarios_covered": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Phase 1 scenarios that have at least one test case",
                },
                "gaps": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Phase 1 scenarios with no test case coverage",
                },
                "issues": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "test_case_id": {"type": "string"},
                            "issue":        {"type": "string"},
                        },
                    },
                    "description": "Specific test cases with quality problems",
                },
                "additions_recommended": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "New test cases to add for better coverage",
                },
                "approved": {
                    "type": "boolean",
                    "description": "true if coverage_score >= 7/10 and no blocking issues",
                },
                "overall_notes": {"type": "string"},
            },
            "required": ["feature_name", "coverage_score", "gaps", "approved", "overall_notes"],
        },
    },
]


def handle_phase_23_tool(name: str, tool_input: dict) -> tuple[dict, Any]:
    """Returns (tool_result_for_api, captured_output)."""
    if name == "save_test_cases":
        result = _save_json(tool_input, "phase02")
        return result, ("phase_2", tool_input.get("test_cases", []))
    if name == "save_review":
        result = _save_json(tool_input, "phase03")
        return result, ("phase_3", tool_input)
    return {"error": f"Unknown tool: {name}"}, None


def _save_json(data: dict, phase_tag: str) -> dict:
    OUTPUT_DIR.mkdir(exist_ok=True)
    slug = _slugify(data.get("feature_name", "unknown"))
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"{slug}_{phase_tag}_{ts}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"  [tool] saved → {path.name}")
    return {"status": "success", "file": str(path)}


def _slugify(text: str) -> str:
    slug = text.lower().replace(" ", "_").replace("—", "").replace("-", "_")
    return "".join(c for c in slug if c.isalnum() or c == "_")
