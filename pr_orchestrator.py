"""
PR Review Orchestrator — SEPARATE from the STLC pipeline.

CAPSTONE NOTE (mentor feedback):
  The STLC orchestrator has QA bias — it thinks in terms of test plans,
  risk levels, and coverage scores. A PR reviewer needs a different lens:
  code quality, completeness, standards compliance.
  This is why the PR Orchestrator is a separate entry point.

Usage:
  python pr_orchestrator.py --pr-url https://github.com/owner/repo/pull/42
  python pr_orchestrator.py --pr-url <url> --checklist playwright

Flow:
  1. Fetch PR details + changed files from GitHub (MCP write demonstrated here too)
  2. PRAnalysisAgent  — understand what the PR contains
  3. PRReviewAgent    — apply the checklist, identify issues
  4. Post review comments on the PR via GitHub API
  5. Approve or Request Changes
"""
import argparse
import os
import sys
import json
from dotenv import load_dotenv

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="PR Review Orchestrator — STLC Capstone")
    parser.add_argument("--pr-url",   required=True, help="GitHub PR URL e.g. https://github.com/owner/repo/pull/42")
    parser.add_argument("--checklist", default="pytest", choices=["pytest", "playwright"],
                        help="Review checklist to apply (default: pytest)")
    args = parser.parse_args()

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("[Error] ANTHROPIC_API_KEY not set"); sys.exit(1)
    if not os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"):
        print("[Error] GITHUB_PERSONAL_ACCESS_TOKEN not set"); sys.exit(1)

    from pr_agents.pr_orchestrator_runner import PROrchestrator
    orchestrator = PROrchestrator()
    result = orchestrator.run(pr_url=args.pr_url, checklist=args.checklist)

    if result:
        print(f"\n  Review posted → {args.pr_url}")
        print(f"  Decision     : {result.get('decision')}")
    else:
        print("\n  PR review failed — check logs")
        sys.exit(1)


if __name__ == "__main__":
    main()
