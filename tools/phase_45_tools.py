"""
Tools for Phase 4 (Automation Generate) and Phase 5 (Automation Review).
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from tools.output_utils import get_story_dir

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


def _save_automation_code(data: dict) -> dict:
    story_dir = get_story_dir(data.get("feature_name", "unknown"))
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = story_dir / f"04_automation_{ts}.json"
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    py_path = story_dir / data.get("test_file_name", f"04_automation_{ts}.py")
    lines = []
    for imp in data.get("imports", []):
        lines.append(imp)
    if lines:
        lines.append("")

    for fixture in data.get("fixtures", []):
        lines.append(f"@pytest.fixture(scope=\"{fixture['scope']}\")")
        lines.append(fixture["code"])
        lines.append("")

    for fn in data.get("test_functions", []):
        if fn.get("docstring"):
            lines.append(f'def {fn["function_name"]}():')
            lines.append(f'    """{fn["docstring"]}"""')
        else:
            lines.append(f'def {fn["function_name"]}():')
        lines.append(fn["code"])
        lines.append("")

    py_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  [tool] saved → {story_dir.name}/{py_path.name}")
    print(f"  [tool] saved → {story_dir.name}/{json_path.name}")
    return {"status": "success", "json_file": str(json_path), "py_file": str(py_path)}


def _save_phase05(data: dict) -> dict:
    story_dir = get_story_dir(data.get("feature_name", "unknown"))
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = story_dir / f"05_automation_review_{ts}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"  [tool] saved → {story_dir.name}/{path.name}")
    return {"status": "success", "file": str(path)}


def _slugify(text: str) -> str:
    slug = text.lower().replace(" ", "_").replace("—", "").replace("-", "_")
    return "".join(c for c in slug if c.isalnum() or c == "_")
