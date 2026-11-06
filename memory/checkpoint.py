"""
CAPSTONE CONCEPT: Memory Types — External Memory + Pipeline Resumption

Checks output/ for existing phase artifacts from a prior run of the same feature.
If found, loads them into PipelineState so the pipeline resumes from where it
stopped rather than re-running completed phases.

This demonstrates External Memory:
  - Completed phase outputs persist on disk between runs
  - Next run reads them back and skips to the first incomplete phase
  - No work is wasted when a later phase fails
"""
import json
from pathlib import Path
from memory.pipeline_state import PipelineState

from tools.output_utils import get_story_dir
BASE_OUTPUT = Path(__file__).parent.parent / "output"


def find_existing_checkpoint(feature_name: str) -> dict:
    """
    Look inside output/<STORY-ID>/ for existing phase output files.
    Returns {phase_num: latest_file_path} for phases that have output.
    """
    import re
    match = re.match(r"^([A-Z]+-\d+)", feature_name.strip())
    folder = match.group(1) if match else feature_name[:25]
    story_dir = BASE_OUTPUT / folder

    if not story_dir.exists():
        return {}

    found = {}
    for phase_tag, phase_num in [("test_plan", 1), ("test_cases", 2), ("test_case_review", 3), ("automation", 4), ("automation_review", 5)]:
        matches = sorted(
            story_dir.glob(f"{phase_tag}*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if matches:
            found[phase_num] = matches[0]

    return found


def load_checkpoint(feature_name: str, user_story: str) -> tuple[PipelineState, int]:
    """
    Build a PipelineState from existing output files.
    Returns (state, resume_from_phase) where resume_from_phase is the
    first phase that has no saved output.

    resume_from_phase:
      0 = no checkpoint, start from beginning
      2 = Phase 1 done, start from Phase 2
      4 = Phases 1-3 done, start from Phase 4
    """
    checkpoint = find_existing_checkpoint(feature_name)

    if not checkpoint:
        return PipelineState(feature_name=feature_name, user_story=user_story), 0

    state = PipelineState(feature_name=feature_name, user_story=user_story)
    resume_from = 0

    # Load Phase 1
    if 1 in checkpoint:
        try:
            data = json.loads(checkpoint[1].read_text(encoding="utf-8"))
            state.phase_0_classification = data.get("phase_0_classification")
            state.phase_1_test_plan      = data.get("phase_1_test_plan")
            state.current_phase = 1
            resume_from = 2
        except Exception:
            pass

    # Load Phase 2
    if 2 in checkpoint and resume_from >= 2:
        try:
            data = json.loads(checkpoint[2].read_text(encoding="utf-8"))
            state.phase_2_test_cases = data.get("test_cases", [])
            state.current_phase = 2
            resume_from = 4
        except Exception:
            pass

    # Load Phase 3
    if 3 in checkpoint and resume_from >= 4:
        try:
            data = json.loads(checkpoint[3].read_text(encoding="utf-8"))
            state.phase_3_review = data
            state.current_phase = 3
        except Exception:
            pass

    # Load Phase 4
    if 4 in checkpoint and resume_from >= 4:
        try:
            data = json.loads(checkpoint[4].read_text(encoding="utf-8"))
            state.phase_4_automation = data
            state.current_phase = 4
            resume_from = 6   # skip to after Phase 5
        except Exception:
            pass

    return state, resume_from


def describe_checkpoint(checkpoint: dict) -> str:
    """Human-readable summary of what's already saved."""
    if not checkpoint:
        return "No existing work found."
    lines = ["Existing work found:"]
    phase_names = {1: "Test Plan", 2: "Test Cases",
                   3: "Test Case Review", 4: "Automation", 5: "Automation Review"}
    for p, path in sorted(checkpoint.items()):
        lines.append(f"  ✓ {phase_names.get(p, f'Phase {p}')} — {path.name}")
    return "\n".join(lines)
