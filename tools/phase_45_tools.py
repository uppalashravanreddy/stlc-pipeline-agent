"""
Tools for Phase 4 (Automation Generate) and Phase 5 (Automation Review).
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any

OUTPUT_DIR = Path(__file__).parent.parent / "output"

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
    """Returns (tool_result_for_api, captured_output)."""
    if name == "save_automation":
        result = _save_automation_code(tool_input)
        return result, ("phase_4", tool_input)
    if name == "save_automation_review":
        result = _save_json(tool_input, "phase05")
        return result, ("phase_5", tool_input)
    return {"error": f"Unknown tool: {name}"}, None


def _save_automation_code(data: dict) -> dict:
    OUTPUT_DIR.mkdir(exist_ok=True)
    slug = _slugify(data.get("feature_name", "unknown"))
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save JSON metadata
    json_path = OUTPUT_DIR / f"{slug}_phase04_{ts}.json"
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # Write actual Python test file
    py_path = OUTPUT_DIR / data.get("test_file_name", f"{slug}_test_{ts}.py")
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
    print(f"  [tool] saved → {json_path.name}")
    print(f"  [tool] saved → {py_path.name}")
    return {"status": "success", "json_file": str(json_path), "py_file": str(py_path)}


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
