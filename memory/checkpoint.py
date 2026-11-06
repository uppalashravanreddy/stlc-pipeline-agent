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

from memory.summary_writer import load_checkpoint_cache

CACHE_DIR = Path(__file__).parent.parent / ".cache"


def find_existing_checkpoint(feature_name: str) -> dict:
    """
    Looks in .cache/<STORY-ID>/checkpoint.json for prior run state.
    The cache is written after each phase (internal, not user output).
    Returns the cached state dict or empty dict if none found.
    """
    cached = load_checkpoint_cache(feature_name)
    if not cached:
        return {}
    # Return a simple signal dict — actual data is in the full cache
    found = {}
    if cached.get("phase_1_test_plan"):    found[1] = True
    if cached.get("phase_2_test_cases"):   found[2] = True
    if cached.get("phase_3_review"):       found[3] = True
    if cached.get("phase_4_automation"):   found[4] = True
    return found


def load_checkpoint(feature_name: str, user_story: str) -> "tuple[PipelineState, int]":
    """
    Build a PipelineState from existing output files.
    Returns (state, resume_from_phase) where resume_from_phase is the
    first phase that has no saved output.

    resume_from_phase:
      0 = no checkpoint, start from beginning
      2 = Phase 1 done, start from Phase 2
      4 = Phases 1-3 done, start from Phase 4
    """
    cached = load_checkpoint_cache(feature_name)
    if not cached:
        return PipelineState(feature_name=feature_name, user_story=user_story), 0

    state = PipelineState(feature_name=feature_name, user_story=user_story)
    state.phase_0_classification     = cached.get("phase_0_classification")
    state.phase_1_test_plan          = cached.get("phase_1_test_plan")
    state.phase_2_test_cases         = cached.get("phase_2_test_cases")
    state.phase_3_review             = cached.get("phase_3_review")
    state.phase_4_automation         = cached.get("phase_4_automation")
    state.phase_5_automation_review  = cached.get("phase_5_automation_review")
    state.current_phase              = cached.get("current_phase", 0)
    state.hitl_approvals             = cached.get("hitl_approvals", {})

    # Determine which phase to resume from
    if state.phase_4_automation:   resume_from = 6
    elif state.phase_2_test_cases: resume_from = 4
    elif state.phase_1_test_plan:  resume_from = 2
    else:                          resume_from = 0

    return state, resume_from


def describe_checkpoint(checkpoint: dict) -> str:
    """Human-readable summary of what's cached from a prior run."""
    if not checkpoint:
        return "No existing work found."
    phase_names = {1: "Phase 1 — Test Plan", 2: "Phase 2 — Test Cases",
                   3: "Phase 3 — Review", 4: "Phase 4 — Automation"}
    lines = ["Prior run found in cache:"]
    for p in sorted(checkpoint.keys()):
        lines.append(f"  ✓ {phase_names.get(p, f'Phase {p}')}")
    return "\n".join(lines)
