"""
Entry point — runs the STLC pipeline on a sample user story.
Usage: python main.py
       python main.py --feature "Checkout" --story "As a user..."
"""
import argparse
import os
import sys
from dotenv import load_dotenv
from agent import run_pipeline

load_dotenv()

# Default sample — User Authentication (security risk, API + UI, rich AC)
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


def main():
    parser = argparse.ArgumentParser(description="STLC Pipeline Agent — Phase 0 + Phase 1")
    parser.add_argument("--feature", default=DEFAULT_FEATURE, help="Feature name")
    parser.add_argument("--story", default=DEFAULT_STORY, help="User story text")
    args = parser.parse_args()

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("[Error] ANTHROPIC_API_KEY not set. Add it to .env or your environment.")
        sys.exit(1)

    result = run_pipeline(feature_name=args.feature, user_story=args.story)

    if result:
        c = result["phase_0_classification"]
        print("=" * 60)
        print("  PIPELINE SUMMARY")
        print("=" * 60)
        print(f"  Feature  : {result['feature_name']}")
        print(f"  Type     : {c['test_type']}")
        print(f"  Risk     : {c['risk_level']}")
        print(f"  Approach : {c['test_approach']}")
        print(f"  Priority : {c['priority']}")
        print(f"\n  Output saved to ./output/")
        print("=" * 60)
    else:
        print("[Error] Pipeline produced no output. Check agent reasoning above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
