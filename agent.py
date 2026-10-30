"""
STLC Pipeline Agent — Intermediate Capstone
Single agent | Phase 0: Classification → Phase 1: Test Plan | ONE tool: save_test_plan
"""
import json
import os
import anthropic
from tools import TOOLS, handle_tool_call

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are a senior QA architect running a 2-phase STLC pipeline.

## PHASE 0 — CLASSIFICATION
Analyze the feature/user story and determine:
- test_type: primary type (API | UI | Mobile | Integration | Performance | Security | E2E)
- risk_level: High | Medium | Low — based on business impact × technical complexity
- test_approach: Automated | Manual | Both — based on ROI and feasibility
- priority: P1 | P2 | P3 — P1 means release is blocked without this testing
- rationale: 1-2 sentences explaining your classification decisions

## PHASE 1 — TEST PLAN
Using Phase 0 output to inform depth and focus, generate:
- objectives: 2-3 specific, measurable testing goals
- in_scope: behaviors and areas that WILL be tested
- out_of_scope: explicitly excluded areas (no ambiguity)
- test_scenarios: 5-7 concrete scenarios — mix of positive, negative, and edge cases
- entry_criteria: pre-conditions that must be true before testing begins
- exit_criteria: measurable conditions that define testing as done

## RULES
1. Reason through Phase 0 first — state your classification with justification
2. Let Phase 0 risk level and test type drive scope in Phase 1
3. High risk → broader scope, more edge cases; Low risk → focused scope
4. Only call save_test_plan after both phases are fully completed"""


def run_pipeline(feature_name: str, user_story: str) -> dict | None:
    """
    Agentic loop: agent reasons (Phase 0 + Phase 1) then calls save_test_plan once.
    Returns the structured output dict, or None if the agent didn't call the tool.
    """
    client = anthropic.Anthropic()

    messages = [
        {
            "role": "user",
            "content": (
                f"Feature: {feature_name}\n\n"
                f"User Story:\n{user_story}\n\n"
                "Run the STLC pipeline: Phase 0 (Classification) then Phase 1 (Test Plan)."
            ),
        }
    ]

    result = None
    iteration = 0
    max_iterations = 8  # safety cap

    print(f"\n{'=' * 60}")
    print(f"  STLC PIPELINE AGENT")
    print(f"  Feature: {feature_name}")
    print(f"{'=' * 60}\n")

    while iteration < max_iterations:
        iteration += 1

        response = client.messages.create(
            model=MODEL,
            max_tokens=3000,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # Print agent's reasoning text
        for block in response.content:
            if hasattr(block, "text") and block.text.strip():
                print(f"[Agent Reasoning]\n{block.text}\n")

        if response.stop_reason == "end_turn":
            # Agent confirmed completion (post-tool) or stopped without calling tool
            if result:
                print("[Pipeline] Complete.\n")
            else:
                print("[Pipeline] Agent ended without calling save_test_plan.")
            break

        if response.stop_reason == "tool_use":
            tool_block = next(b for b in response.content if b.type == "tool_use")
            print(f"[Tool Call] {tool_block.name}")

            tool_result = handle_tool_call(tool_block.name, tool_block.input)

            if tool_block.name == "save_test_plan" and tool_result.get("status") == "success":
                result = tool_block.input

            messages.append({"role": "assistant", "content": response.content})
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_block.id,
                        "content": json.dumps(tool_result),
                    }
                ],
            })

    return result
