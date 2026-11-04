"""
Entry point for the STLC Pipeline Agent — Advanced Capstone (Phases 0–5).

Usage:
  python main.py                         # runs default User Authentication story
  python main.py --feature "X" --story "Y"
  python main.py --phases 01             # run only Phase 0+1 (Intermediate eval)
  python main.py --phases 0123           # run through Phase 3 (no automation)

CAPSTONE: Agent vs Sub-Agents — this file only creates the Orchestrator.
  The orchestrator decides which sub-agents run and in what order.
"""
import argparse
import os
import sys
from dotenv import load_dotenv
from agents.orchestrator import Orchestrator

load_dotenv()

DEFAULT_FEATURE = "User Authentication — Login"
DEFAULT_STORY = """\
As a registered user, I want to securely log in to the application
with my email and password so that I can access my account and features.

Acceptance Criteria:
- Valid credentials grant access and redirect to the user dashboard
- Invalid credentials display a user-friendly error without revealing which field is wrong
- Account locks after 5 consecutive failed login attempts; unlocks after 30 minutes
- Session expires after 30 minutes of inactivity and requires re-login
- Passwords are never transmitted or stored in plaintext
- A "Remember me" option extends session persistence to 7 days on trusted devices"""


def main() -> None:
    parser = argparse.ArgumentParser(description="STLC Pipeline Agent — Advanced Capstone")
    parser.add_argument("--feature", default=DEFAULT_FEATURE, help="Feature name")
    parser.add_argument("--story",   default=DEFAULT_STORY,   help="User story text")
    args = parser.parse_args()

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("[Error] ANTHROPIC_API_KEY not set. Add it to .env")
        sys.exit(1)

    orchestrator = Orchestrator()
    state = orchestrator.run(feature_name=args.feature, user_story=args.story)

    if state is None:
        print("\n[Error] Pipeline failed at Phase 0+1.")
        sys.exit(1)

    completed = state.current_phase
    print(f"\nDone. Completed through Phase {completed}. Check ./output/ for all artifacts.")


if __name__ == "__main__":
    main()
