"""
Entry point for the STLC Pipeline Agent — Advanced Capstone (Phases 0–5).

Usage:
  python main.py                              # default User Authentication story
  python main.py --ticket KAN-14             # fetch story from Jira via MCP
  python main.py --feature "X" --story "Y"  # pass story text directly

CAPSTONE: MCP Knowledge
  --ticket mode connects to Jira via the MCP integration in .vscode/mcp.json.
  The JiraClient fetches the live story so you never need to copy-paste text.
  This is what MCP enables: agents consuming live external data by ID, not text.
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
    parser.add_argument("--ticket",  default=None,           help="Jira ticket ID (e.g. KAN-14) — fetches story via MCP")
    parser.add_argument("--feature", default=DEFAULT_FEATURE, help="Feature name (used when --ticket not provided)")
    parser.add_argument("--story",   default=DEFAULT_STORY,   help="User story text (used when --ticket not provided)")
    args = parser.parse_args()

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("[Error] ANTHROPIC_API_KEY not set. Add it to .env")
        sys.exit(1)

    # ── CAPSTONE: MCP — fetch story from Jira by ticket ID ───────────────────
    if args.ticket:
        try:
            from tools.jira_client import JiraClient
            print(f"\n[MCP] Fetching {args.ticket} from Jira...")
            jira    = JiraClient()
            story   = jira.fetch_story(args.ticket)
            feature = story["feature_name"]
            text    = story["user_story"]
            print(f"[MCP] Story loaded: {feature}\n")
        except (EnvironmentError, ValueError) as e:
            print(f"[Error] Jira fetch failed: {e}")
            print("Add JIRA_INSTANCE_URL, JIRA_USER_EMAIL, JIRA_API_TOKEN to .env")
            sys.exit(1)
    else:
        feature = args.feature
        text    = args.story
    # ─────────────────────────────────────────────────────────────────────────

    orchestrator = Orchestrator()
    state = orchestrator.run(feature_name=feature, user_story=text)

    if state is None:
        print("\n[Error] Pipeline failed at Phase 0+1.")
        sys.exit(1)

    completed = state.current_phase
    print(f"\nDone. Completed through Phase {completed}. Check ./output/ for all artifacts.")


if __name__ == "__main__":
    main()
