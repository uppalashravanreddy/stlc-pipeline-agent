"""
Peer Review Agent — single agent, separate from the STLC orchestrator.

Reviewer clarification:
  - Main orchestrator does its OWN self-review (Phase 5: Automation Review)
    then creates the MR and CLOSES.
  - This is a SEPARATE single agent (not an orchestrator) that accepts
    the MR URL and does a peer review — an independent second opinion.

Usage:
  python peer_review_agent.py --mr-url https://github.com/owner/repo/pull/42
  python peer_review_agent.py --mr-url <url> --checklist playwright

Flow (single agent, one loop):
  1. Fetch MR details + changed files from GitHub
  2. Single LLM call: review against the checklist
  3. Post review comments on the MR
  4. Done

CAPSTONE: Agent vs Sub-Agents
  Main orchestrator = multi-agent coordinator (Phases 0-7)
  This = single agent with one focused job (peer review)
  Both demonstrate different valid architectures.
"""
import argparse
import os
import re
import sys
import json
from dotenv import load_dotenv
import anthropic

load_dotenv()

CHECKLISTS = {
    "pytest": """
PEER REVIEW CHECKLIST — pytest automation:
1. Every test function has at least one assert or pytest.raises()
2. No hardcoded credentials — env vars or fixtures only
3. Function names clearly describe the scenario (test_<what>_<expected>)
4. Setup/teardown uses fixtures, not repeated code in each test
5. Negative and edge cases present alongside positive tests
6. Expected results are specific — not "assert result" or "assert True"
7. No duplicate tests doing identical assertions
8. Test data uses realistic values, not <email> or <password> placeholders
9. Low-feasibility cases have pytest.skip() with a reason
""",
    "playwright": """
PEER REVIEW CHECKLIST — Playwright automation:
1. Page object model used — no raw selectors in test functions
2. Selectors use data-testid, not fragile CSS classes or text content
3. Waits use expect(locator).toBeVisible(), not sleep()
4. Screenshots captured on failure via test hooks
5. Tests are independent — no shared mutable state between tests
6. Environment URLs from config/env, not hardcoded
7. Both happy path and error states covered
8. Mobile viewport tested where feature is responsive
9. No arbitrary timeouts — use expect() with reasonable timeout options
""",
}


def fetch_pr_data(gh_token: str, owner: str, repo: str, pr_num: int) -> tuple[dict, list]:
    """Fetch PR details and changed files from GitHub."""
    import urllib.request
    headers = {
        "Authorization": f"Bearer {gh_token}",
        "Accept":        "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    def get(path):
        req = urllib.request.Request(f"https://api.github.com{path}", headers=headers)
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())

    pr    = get(f"/repos/{owner}/{repo}/pulls/{pr_num}")
    files = get(f"/repos/{owner}/{repo}/pulls/{pr_num}/files")
    return pr, files


def post_review_comment(gh_token: str, owner: str, repo: str,
                        pr_num: int, body: str) -> None:
    """Post the review as a PR comment."""
    import urllib.request, urllib.error
    headers = {
        "Authorization": f"Bearer {gh_token}",
        "Accept":        "application/vnd.github+json",
        "Content-Type":  "application/json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    payload = json.dumps({"body": body}).encode()
    req = urllib.request.Request(
        f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_num}/comments",
        data=payload, headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15):
            print(f"  [github] Review comment posted on PR #{pr_num}")
    except urllib.error.HTTPError as e:
        print(f"  [github] Failed to post comment: {e.code} {e.read().decode()[:100]}")


def run_peer_review(mr_url: str, checklist: str = "pytest") -> dict | None:
    """
    Single-agent peer review.

    One LLM call reads the PR and produces structured review output.
    Then posts comments back to GitHub.
    """
    # Parse URL
    match = re.match(r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)", mr_url)
    if not match:
        print("[Error] Invalid GitHub MR URL — expected https://github.com/owner/repo/pull/N")
        return None

    owner, repo, pr_num = match.group(1), match.group(2), int(match.group(3))

    gh_token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", "")
    if not gh_token:
        print("[Error] GITHUB_PERSONAL_ACCESS_TOKEN not set"); return None

    # Fetch PR
    print(f"  Fetching MR #{pr_num} from GitHub...")
    try:
        pr_data, files = fetch_pr_data(gh_token, owner, repo, pr_num)
    except Exception as e:
        print(f"  [Error] GitHub fetch failed: {e}"); return None

    pr_title = pr_data.get("title", "")
    pr_body  = pr_data.get("body", "")[:3000]

    # Collect changed test files
    test_code = []
    for f in files[:8]:
        fname = f.get("filename", "")
        patch = f.get("patch", "")[:1000]
        if patch and ("test_" in fname or fname.endswith(".py")):
            test_code.append(f"=== {fname} ===\n{patch}")

    checklist_text = CHECKLISTS.get(checklist, CHECKLISTS["pytest"])

    # Single agent call
    client = anthropic.Anthropic()
    prompt = f"""You are conducting a peer review of a Pull Request for QA automation code.
You are a SEPARATE reviewer — give an independent opinion, not a repeat of any prior review.

PR Title: {pr_title}
PR Description:
{pr_body}

Code changes:
{chr(10).join(test_code) if test_code else "No Python test files changed."}

Apply this peer review checklist:
{checklist_text}

Return JSON only:
{{
  "decision": "APPROVE" | "REQUEST_CHANGES" | "COMMENT",
  "summary": "2-3 sentence independent assessment",
  "passed": ["checklist items that pass"],
  "failed": ["checklist items that fail"],
  "comments": [
    {{"type": "blocking"|"suggestion", "topic": "short label", "body": "specific feedback"}}
  ]
}}"""

    print("  Running peer review (single agent)...")
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"): text = text[4:]

    try:
        result = json.loads(text.strip())
    except Exception:
        print("  [Error] Could not parse review output"); return None

    # Format comment
    decision  = result.get("decision", "COMMENT")
    emoji_map = {"APPROVE": "✅", "REQUEST_CHANGES": "❌", "COMMENT": "💬"}
    emoji     = emoji_map.get(decision, "💬")

    lines = [
        f"## {emoji} Peer Review — {decision}",
        "",
        f"*Independent review by Peer Review Agent · checklist: {checklist}*",
        "",
        f"**{result.get('summary', '')}**",
        "",
    ]

    passed = result.get("passed", [])
    failed = result.get("failed", [])
    if passed or failed:
        lines += ["### Checklist", ""]
        for p in passed: lines.append(f"- ✅ {p}")
        for f in failed: lines.append(f"- ❌ {f}")
        lines.append("")

    for c in result.get("comments", []):
        tag = "🔴" if c.get("type") == "blocking" else "💡"
        lines += [f"**{tag} {c.get('topic','')}**", c.get("body",""), ""]

    lines += ["---", "*🤖 Generated with [Claude Code](https://claude.com/claude-code)*"]

    post_review_comment(gh_token, owner, repo, pr_num, "\n".join(lines))

    print(f"\n  Decision : {decision}")
    print(f"  Passed   : {len(passed)}  |  Failed: {len(failed)}")
    print(f"  MR       : {mr_url}")
    return result


def main():
    parser = argparse.ArgumentParser(description="Peer Review Agent — single agent")
    parser.add_argument("--mr-url",    required=True, help="GitHub MR/PR URL")
    parser.add_argument("--checklist", default="pytest", choices=["pytest", "playwright"])
    args = parser.parse_args()

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("[Error] ANTHROPIC_API_KEY not set"); sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  PEER REVIEW AGENT (single agent)")
    print(f"  MR  : {args.mr_url}")
    print(f"  Mode: {args.checklist} checklist")
    print(f"{'='*60}\n")

    result = run_peer_review(args.mr_url, args.checklist)
    if not result:
        sys.exit(1)


if __name__ == "__main__":
    main()
