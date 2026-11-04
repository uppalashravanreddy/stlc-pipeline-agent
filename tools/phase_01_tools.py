"""
Tools for Phase 0 (Classification) and Phase 1 (Test Plan).
Moved from tools.py — same schema, restructured for multi-agent use.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any

OUTPUT_DIR = Path(__file__).parent.parent / "output"

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
        result = _save_test_plan(tool_input)
        return result, tool_input   # captured = the full structured input
    return {"error": f"Unknown tool: {name}"}, None


def _save_test_plan(data: dict) -> dict:
    OUTPUT_DIR.mkdir(exist_ok=True)
    slug = _slugify(data["feature_name"])
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = OUTPUT_DIR / f"{slug}_phase01_{ts}.json"
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"  [tool] saved → {json_path.name}")
    return {"status": "success", "file": str(json_path)}


def _slugify(text: str) -> str:
    slug = text.lower().replace(" ", "_").replace("—", "").replace("-", "_")
    return "".join(c for c in slug if c.isalnum() or c == "_")
