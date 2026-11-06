"""
Tools for Phase 0 (Classification) and Phase 1 (Test Plan).
Moved from tools.py — same schema, restructured for multi-agent use.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from tools.output_utils import get_story_dir

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
    Returns (tool_result_for_api, captured_output_or_None).
    BaseAgent passes tool_result_for_api back to the model.
    The orchestrator uses captured_output to update PipelineState.
    """
    if name == "save_test_plan":
        normalized_input = _normalize_tool_input(tool_input)
        if normalized_input is None:
            return {
                "error": "phase_1_test_plan must be an object or valid JSON object string"
            }, None
        result = _save_test_plan(normalized_input)
        return result, normalized_input   # captured = the full structured input
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


def _save_test_plan(data: dict) -> dict:
    story_dir = get_story_dir(data["feature_name"])
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    json_path = story_dir / f"test_plan_{ts}.json"
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    md_path = story_dir / f"test_plan_{ts}.md"
    md_path.write_text(_build_markdown(data), encoding="utf-8")

    print(f"  [tool] saved → {story_dir.name}/{md_path.name}")
    print(f"  [tool] saved → {story_dir.name}/{json_path.name}")
    return {"status": "success", "markdown": str(md_path), "json": str(json_path)}


def _build_markdown(data: dict) -> str:
    c = data["phase_0_classification"]
    p = data["phase_1_test_plan"]
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        f"# Test Plan: {data['feature_name']}",
        f"_Generated: {ts}_",
        "",
        "---",
        "",
        "## Phase 0 — Classification",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Test Type | `{c['test_type']}` |",
        f"| Risk Level | `{c['risk_level']}` |",
        f"| Test Approach | `{c['test_approach']}` |",
        f"| Priority | `{c['priority']}` |",
        "",
        f"**Rationale:** {c['rationale']}",
        "",
        "---",
        "",
        "## Phase 1 — Test Plan",
        "",
        "### Objectives",
    ]
    for obj in p.get("objectives", []):
        lines.append(f"- {obj}")

    lines += ["", "### Scope", "", "**In Scope:**"]
    for item in p.get("in_scope", []):
        lines.append(f"- {item}")

    lines += ["", "**Out of Scope:**"]
    for item in p.get("out_of_scope", []):
        lines.append(f"- {item}")

    lines += ["", "### Test Scenarios", ""]
    for i, scenario in enumerate(p.get("test_scenarios", []), start=1):
        lines.append(f"{i}. {scenario}")

    lines += ["", "### Entry Criteria"]
    for item in p.get("entry_criteria", []):
        lines.append(f"- {item}")

    lines += ["", "### Exit Criteria"]
    for item in p.get("exit_criteria", []):
        lines.append(f"- {item}")

    return "\n".join(lines)


def _slugify(text: str) -> str:  # kept for _build_markdown internal use
    slug = text.lower().replace(" ", "_").replace("—", "").replace("-", "_")
    return "".join(c for c in slug if c.isalnum() or c == "_")
