"""
Tools for Phase 2 (Test Case Generation) and Phase 3 (Test Case Review).
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from tools.output_utils import get_story_dir

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
        result = _save_test_cases(tool_input)
        return result, ("phase_2", tool_input.get("test_cases", []))
    if name == "save_review":
        result = _save_review(tool_input)
        return result, ("phase_3", tool_input)
    return {"error": f"Unknown tool: {name}"}, None


def _save_test_cases(data: dict) -> dict:
    story_dir = get_story_dir(data.get("feature_name", "unknown"))
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    json_path = story_dir / f"phase02_{ts}.json"
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    md_path = story_dir / f"phase02_{ts}.md"
    md_path.write_text(_build_test_cases_md(data), encoding="utf-8")

    print(f"  [tool] saved → {story_dir.name}/{md_path.name}")
    print(f"  [tool] saved → {story_dir.name}/{json_path.name}")
    return {"status": "success", "markdown": str(md_path), "json": str(json_path)}


def _save_review(data: dict) -> dict:
    story_dir = get_story_dir(data.get("feature_name", "unknown"))
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    json_path = story_dir / f"phase03_{ts}.json"
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    md_path = story_dir / f"phase03_{ts}.md"
    md_path.write_text(_build_review_md(data), encoding="utf-8")

    print(f"  [tool] saved → {story_dir.name}/{md_path.name}")
    print(f"  [tool] saved → {story_dir.name}/{json_path.name}")
    return {"status": "success", "markdown": str(md_path), "json": str(json_path)}


def _build_test_cases_md(data: dict) -> str:
    ts  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tcs = data.get("test_cases", [])
    lines = [
        f"# Test Cases: {data.get('feature_name', '')}",
        f"_Generated: {ts} | {len(tcs)} test cases_",
        "",
        "---",
        "",
        "## Summary",
        "",
        "| ID | Title | Type | Priority | Automation |",
        "|---|---|---|---|---|",
    ]
    for tc in tcs:
        lines.append(
            f"| `{tc.get('id','')}` | {tc.get('title','')[:60]} | "
            f"{tc.get('test_type','')} | {tc.get('priority','')} | "
            f"{tc.get('automation_feasibility','')} |"
        )

    lines += ["", "---", ""]
    for tc in tcs:
        lines += [
            f"## {tc.get('id','')} — {tc.get('title','')}",
            "",
            f"**Scenario:** {tc.get('scenario_ref','')}  ",
            f"**Type:** {tc.get('test_type','')}  |  "
            f"**Priority:** {tc.get('priority','')}  |  "
            f"**Automation:** {tc.get('automation_feasibility','')}",
            "",
            "**Preconditions:**",
        ]
        for p in tc.get("preconditions", []):
            lines.append(f"- {p}")

        lines += ["", "**Steps:**"]
        for i, s in enumerate(tc.get("steps", []), 1):
            lines.append(f"{i}. {s}")

        lines += ["", f"**Expected Result:** {tc.get('expected_result','')}"]

        td = tc.get("test_data", {})
        if td:
            lines += ["", "**Test Data:**", "```json", json.dumps(td, indent=2), "```"]

        lines += ["", "---", ""]

    return "\n".join(lines)


def _build_review_md(data: dict) -> str:
    ts       = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    approved = data.get("approved", False)
    score    = data.get("coverage_score", "?")
    status   = "✅ APPROVED" if approved else "❌ NOT APPROVED"

    lines = [
        f"# Test Case Review: {data.get('feature_name', '')}",
        f"_Generated: {ts}_",
        "",
        "---",
        "",
        f"## Verdict: {status}",
        "",
        f"| Coverage Score | Approved |",
        f"|---|---|",
        f"| **{score}** | {'Yes ✅' if approved else 'No ❌'} |",
        "",
        f"**Overall Notes:** {data.get('overall_notes', '')}",
        "",
        "---",
    ]

    covered = data.get("scenarios_covered", [])
    if covered:
        lines += ["", "## Scenarios Covered"]
        for s in covered:
            lines.append(f"- ✓ {s}")

    gaps = data.get("gaps", [])
    if gaps:
        lines += ["", "## Coverage Gaps"]
        for g in gaps:
            lines.append(f"- ⚠️ {g}")

    issues = data.get("issues", [])
    if issues:
        lines += ["", "## Issues Found", "", "| Test Case | Severity | Issue |", "|---|---|---|"]
        for iss in issues:
            lines.append(
                f"| {iss.get('test_case_id','')} | {iss.get('severity','')} | {iss.get('issue','')} |"
            )

    additions = data.get("additions_recommended", [])
    if additions:
        lines += ["", "## Recommended Additions"]
        for a in additions:
            lines.append(f"- {a}")

    return "\n".join(lines)


def _slugify(text: str) -> str:
    slug = text.lower().replace(" ", "_").replace("—", "").replace("-", "_")
    return "".join(c for c in slug if c.isalnum() or c == "_")


def _slugify(text: str) -> str:
    slug = text.lower().replace(" ", "_").replace("—", "").replace("-", "_")
    return "".join(c for c in slug if c.isalnum() or c == "_")
