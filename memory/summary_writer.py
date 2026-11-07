"""
Writes pipeline output files. Strategy (from mentor review):

  SUCCESS  → ONE markdown summary in output/<STORY-ID>/
             Contains all phases — shareable for next-level approval
  ERROR    → ONE debug JSON in output/<STORY-ID>/
             Contains pipeline state at point of failure — for debugging only

No intermediate files are written during execution. Everything lives in
PipelineState (in-memory) until the pipeline either completes or fails.
This keeps output/ clean and reduces file I/O during the run.
"""
import json
from datetime import datetime
from pathlib import Path
from tools.output_utils import get_story_dir


def save_pipeline_summary(state) -> Path:
    """
    Called by orchestrator on SUCCESSFUL completion.
    Writes one comprehensive Markdown file covering all phases.
    This is the approval document shared with the next level.
    """
    story_dir = get_story_dir(state.feature_name)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = story_dir / f"stlc_summary_{ts}.md"
    md_path.write_text(_build_summary_md(state), encoding="utf-8")
    print(f"\n  [output] Summary → {story_dir.name}/stlc_summary_{ts}.md")
    return md_path


def save_debug_json(state, reason: str) -> Path:
    """
    Called by orchestrator on ERROR, ABORT, or HARDSTOP.
    Writes one JSON file with the pipeline state at the point of failure.
    Used for debugging and re-run analysis only.
    """
    story_dir = get_story_dir(state.feature_name)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    phase = state.current_phase
    json_path = story_dir / f"debug_phase{phase}_{ts}.json"
    debug_data = {
        "abort_reason": reason,
        "failed_at_phase": phase,
        "timestamp": datetime.now().isoformat(),
        "pipeline_state": state.to_dict(),
    }
    json_path.write_text(json.dumps(debug_data, indent=2), encoding="utf-8")
    print(f"\n  [output] Debug → {story_dir.name}/{json_path.name}")
    return json_path


# ── Checkpoint cache (internal — not user-facing) ─────────────────────────────

CACHE_DIR = Path(__file__).parent.parent / ".cache"


def save_checkpoint_cache(state) -> None:
    """
    Saves a lightweight checkpoint after each phase completes.
    Stored in .cache/<STORY-ID>/ — internal, not user output.
    Enables resume without cluttering output/.
    """
    import re
    match = re.match(r"^([A-Z]+-\d+)", state.feature_name.strip())
    folder = match.group(1) if match else state.feature_name[:20]
    cache_dir = CACHE_DIR / folder
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / "checkpoint.json"
    cache_path.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")


def load_checkpoint_cache(feature_name: str):
    """
    Loads checkpoint from .cache/<STORY-ID>/checkpoint.json if it exists.
    Returns the state dict or None.
    """
    import re
    match = re.match(r"^([A-Z]+-\d+)", feature_name.strip())
    folder = match.group(1) if match else feature_name[:20]
    cache_path = CACHE_DIR / folder / "checkpoint.json"
    if not cache_path.exists():
        return None
    try:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    except Exception:
        return None


# ── Summary Markdown builder ───────────────────────────────────────────────────

def _build_summary_md(state) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hitl = state.hitl_approvals or {}

    lines = [
        f"# STLC Pipeline Summary — {state.feature_name}",
        f"_Generated: {ts} | Phases completed: {state.current_phase} of 5_",
        "",
        "---",
        "",
        "## Pipeline Status",
        "",
        f"| Gate | Decision |",
        f"|---|---|",
        f"| HITL Gate 1 (Test Plan) | {'✅ Approved' if hitl.get('gate_1') == 'approved' else '—'} |",
        f"| HITL Gate 2 (Test Cases) | {'✅ Approved' if hitl.get('gate_2') == 'approved' else '—'} |",
        f"| HITL Gate 3 (Automation) | {'✅ Approved' if hitl.get('gate_3') == 'approved' else '—'} |",
        "",
        "---",
    ]

    # Phase 0+1
    if state.phase_0_classification and state.phase_1_test_plan:
        c = state.phase_0_classification
        p = state.phase_1_test_plan
        lines += [
            "",
            "## Phase 0 — Requirement Classification",
            "",
            "| Field | Value |",
            "|---|---|",
            f"| Test Type | `{c.get('test_type','')}` |",
            f"| Risk Level | `{c.get('risk_level','')}` |",
            f"| Test Approach | `{c.get('test_approach','')}` |",
            f"| Priority | `{c.get('priority','')}` |",
            "",
            f"**Rationale:** {c.get('rationale','')}",
            "",
            "---",
            "",
            "## Phase 1 — Test Plan",
            "",
            "### Objectives",
        ]
        for obj in p.get("objectives", []):
            lines.append(f"- {obj}")
        lines += ["", "**In Scope:**"]
        for item in p.get("in_scope", []):
            lines.append(f"- {item}")
        lines += ["", "**Out of Scope:**"]
        for item in p.get("out_of_scope", []):
            lines.append(f"- {item}")
        lines += ["", "### Test Scenarios"]
        for i, s in enumerate(p.get("test_scenarios", []), 1):
            lines.append(f"{i}. {s}")
        lines += ["", "**Entry Criteria:**"]
        for item in p.get("entry_criteria", []):
            lines.append(f"- {item}")
        lines += ["", "**Exit Criteria:**"]
        for item in p.get("exit_criteria", []):
            lines.append(f"- {item}")
        lines += ["", "---"]

    # Phase 2+3
    if state.phase_2_test_cases:
        tcs = state.phase_2_test_cases
        lines += [
            "",
            f"## Phase 2 — Test Cases ({len(tcs)} cases)",
            "",
            "| ID | Title | Type | Priority | Automation |",
            "|---|---|---|---|---|",
        ]
        for tc in tcs:
            lines.append(
                f"| `{tc.get('id','')}` | {tc.get('title','')[:55]} | "
                f"{tc.get('test_type','')} | {tc.get('priority','')} | "
                f"{tc.get('automation_feasibility','')} |"
            )
        lines += ["", "---"]

    if state.phase_3_review:
        r = state.phase_3_review
        approved = "✅ Yes" if r.get("approved") else "❌ No"
        lines += [
            "",
            "## Phase 3 — Test Case Review",
            "",
            f"| Coverage Score | Approved |",
            f"|---|---|",
            f"| **{r.get('coverage_score','?')}** | {approved} |",
            "",
            f"**Notes:** {r.get('overall_notes','')}",
        ]
        if r.get("gaps"):
            lines += ["", "**Gaps:**"]
            for g in r["gaps"]:
                lines.append(f"- ⚠️ {g}")
        lines += ["", "---"]

    # Phase 4+5
    if state.phase_4_automation:
        auto = state.phase_4_automation
        fns = auto.get("test_functions", [])
        lines += [
            "",
            f"## Phase 4 — Automation ({len(fns)} test functions)",
            "",
            f"**File:** `{auto.get('test_file_name','')}`",
            "",
            "| Function | Test Case |",
            "|---|---|",
        ]
        for fn in fns:
            lines.append(f"| `{fn.get('function_name','')}` | {fn.get('test_case_id','')} |")
        lines += ["", "---"]

    if state.phase_5_automation_review:
        rev = state.phase_5_automation_review
        approved = "✅ Yes" if rev.get("approved") else "❌ No"
        lines += [
            "",
            "## Phase 5 — Automation Review",
            "",
            f"| Quality Score | Approved |",
            f"|---|---|",
            f"| **{rev.get('quality_score','?')}** | {approved} |",
            "",
            f"**Notes:** {rev.get('overall_notes','')}",
            "",
            "---",
        ]

    lines += [
        "",
        "## Ready for Next Level",
        "",
        "_This summary covers all completed STLC phases. "
        "Share with the QA Lead / mentor for Advanced eval approval._",
    ]

    return "\n".join(lines)
