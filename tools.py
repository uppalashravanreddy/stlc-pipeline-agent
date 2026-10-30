"""
ONE tool: save_test_plan
Forces the agent to structure both Phase 0 and Phase 1 output before persisting.
"""
import json
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "output"

TOOLS = [
    {
        "name": "save_test_plan",
        "description": (
            "Persist the completed STLC pipeline output to a Markdown file. "
            "Phase 0 classification and Phase 1 test plan must both be fully completed "
            "before calling this tool. Do not call prematurely."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "feature_name": {
                    "type": "string",
                    "description": "Name of the feature under test"
                },
                "phase_0_classification": {
                    "type": "object",
                    "description": "Phase 0 output: feature classification",
                    "properties": {
                        "test_type": {
                            "type": "string",
                            "enum": ["API", "UI", "Mobile", "Integration", "Performance", "Security", "E2E"],
                            "description": "Primary test type"
                        },
                        "risk_level": {
                            "type": "string",
                            "enum": ["High", "Medium", "Low"],
                            "description": "Risk level based on business impact and complexity"
                        },
                        "test_approach": {
                            "type": "string",
                            "enum": ["Automated", "Manual", "Both"],
                            "description": "Recommended approach based on ROI and feasibility"
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["P1", "P2", "P3"],
                            "description": "P1 = release blocker, P2 = important, P3 = nice-to-have"
                        },
                        "rationale": {
                            "type": "string",
                            "description": "Brief explanation for the classification decisions"
                        }
                    },
                    "required": ["test_type", "risk_level", "test_approach", "priority", "rationale"]
                },
                "phase_1_test_plan": {
                    "type": "object",
                    "description": "Phase 1 output: structured test plan",
                    "properties": {
                        "objectives": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "2-3 specific, measurable testing objectives"
                        },
                        "in_scope": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Behaviors and areas that will be tested"
                        },
                        "out_of_scope": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Explicitly excluded areas (avoids ambiguity)"
                        },
                        "test_scenarios": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "5-7 concrete scenarios: positive, negative, edge cases"
                        },
                        "entry_criteria": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Conditions that must be true before testing starts"
                        },
                        "exit_criteria": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Measurable conditions that define testing as complete"
                        }
                    },
                    "required": [
                        "objectives", "in_scope", "out_of_scope",
                        "test_scenarios", "entry_criteria", "exit_criteria"
                    ]
                }
            },
            "required": ["feature_name", "phase_0_classification", "phase_1_test_plan"]
        }
    }
]


def handle_tool_call(name: str, tool_input: dict) -> dict:
    if name == "save_test_plan":
        return _save_test_plan(tool_input)
    return {"error": f"Unknown tool: {name}"}


def _save_test_plan(data: dict) -> dict:
    OUTPUT_DIR.mkdir(exist_ok=True)

    slug = data["feature_name"].lower().replace(" ", "_").replace("—", "").replace("-", "_")
    slug = "".join(c for c in slug if c.isalnum() or c == "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = OUTPUT_DIR / f"{slug}_{timestamp}.md"
    json_path = OUTPUT_DIR / f"{slug}_{timestamp}.json"

    c = data["phase_0_classification"]
    p = data["phase_1_test_plan"]

    lines = [
        f"# Test Plan: {data['feature_name']}",
        f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_",
        "",
        "---",
        "",
        "## Phase 0 — Classification",
        "",
        "| Field | Value |",
        "|-------|-------|",
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
    for obj in p["objectives"]:
        lines.append(f"- {obj}")

    lines += ["", "### Scope", "", "**In Scope:**"]
    for item in p["in_scope"]:
        lines.append(f"- {item}")

    lines += ["", "**Out of Scope:**"]
    for item in p["out_of_scope"]:
        lines.append(f"- {item}")

    lines += ["", "### Test Scenarios", ""]
    for i, scenario in enumerate(p["test_scenarios"], start=1):
        lines.append(f"{i}. {scenario}")

    lines += ["", "### Entry Criteria"]
    for item in p["entry_criteria"]:
        lines.append(f"- {item}")

    lines += ["", "### Exit Criteria"]
    for item in p["exit_criteria"]:
        lines.append(f"- {item}")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    print(f"[Tool] Saved → {md_path.name}")
    print(f"[Tool] Saved → {json_path.name}")

    return {
        "status": "success",
        "markdown_file": str(md_path),
        "json_file": str(json_path),
    }
