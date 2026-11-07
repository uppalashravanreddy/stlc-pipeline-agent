"""
PR Orchestrator Runner — coordinates PR analysis and review.

CAPSTONE: Agent vs Sub-Agents (second demonstration)
  PROrchestrator is the coordinator — it knows the flow.
  PRAnalysisAgent and PRReviewAgent are specialists — each knows only their job.

CAPSTONE: Agent Model Mapping
  PRAnalysisAgent uses Haiku — reading PR metadata is simple
  PRReviewAgent uses Sonnet — writing review comments needs quality
"""
import re
import json
import anthropic
from tools.github_client import GitHubClient


class PROrchestrator:
    """
    Coordinates PR review pipeline:
      1. Fetch PR from GitHub
      2. PRAnalysisAgent — understand what changed
      3. PRReviewAgent   — apply checklist, write comments
      4. Post review to GitHub
    """

    def __init__(self):
        self.gh     = GitHubClient()
        self.client = anthropic.Anthropic()

    def run(self, pr_url: str, checklist: str = "pytest") -> dict | None:
        print(f"\n{'='*60}")
        print(f"  PR REVIEW ORCHESTRATOR")
        print(f"  PR  : {pr_url}")
        print(f"  Mode: {checklist} checklist")
        print(f"{'='*60}\n")

        # ── Parse PR URL ──────────────────────────────────────────────────────
        match = re.match(r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)", pr_url)
        if not match:
            print("[Error] Invalid GitHub PR URL")
            return None

        owner    = match.group(1)
        repo     = match.group(2)
        pr_num   = int(match.group(3))

        # ── Fetch PR details ─────────────────────────────────────────────────
        print("  Fetching PR details from GitHub...")
        try:
            pr_data = self.gh._get(f"/repos/{owner}/{repo}/pulls/{pr_num}")
            files   = self.gh._get(f"/repos/{owner}/{repo}/pulls/{pr_num}/files")
        except Exception as e:
            print(f"[Error] GitHub fetch failed: {e}")
            return None

        # ── PRAnalysisAgent: understand the PR ───────────────────────────────
        print("  PRAnalysisAgent — analysing PR content...\n")
        analysis = self._run_analysis_agent(pr_data, files)
        if not analysis:
            print("[Error] Analysis failed")
            return None

        # ── PRReviewAgent: apply checklist ───────────────────────────────────
        print("  PRReviewAgent — applying checklist...\n")
        review = self._run_review_agent(analysis, checklist)
        if not review:
            print("[Error] Review failed")
            return None

        # ── Post review to GitHub ─────────────────────────────────────────────
        print("  Posting review comments to GitHub...")
        self._post_review(owner, repo, pr_num, review)

        return review

    # ── PRAnalysisAgent ───────────────────────────────────────────────────────

    def _run_analysis_agent(self, pr_data: dict, files: list) -> dict | None:
        """
        CAPSTONE: Agent Model Mapping — Haiku for simple read/parse tasks.
        Reads the PR description and changed files, extracts key information.
        No QA framing — pure engineering perspective.
        """
        pr_title = pr_data.get("title", "")
        pr_body  = pr_data.get("body", "")[:2000]

        # Summarise changed files
        file_summary = []
        test_code    = []
        for f in files[:10]:   # limit to first 10 files
            fname = f.get("filename", "")
            patch = f.get("patch", "")[:800]
            file_summary.append(f"  {fname} (+{f.get('additions',0)} -{f.get('deletions',0)})")
            if "test_" in fname or fname.endswith(".py"):
                test_code.append(f"--- {fname} ---\n{patch}")

        prompt = f"""You are a code reviewer analysing a Pull Request.
Extract the key information needed for a quality review.

PR Title: {pr_title}
PR Description:
{pr_body}

Changed files:
{chr(10).join(file_summary)}

Test code changes:
{chr(10).join(test_code[:3])}

Return a JSON object with:
{{
  "pr_title": "...",
  "purpose": "one sentence — what this PR does",
  "test_files_changed": ["list of test file names"],
  "has_assertions": true/false,
  "has_fixtures": true/false,
  "estimated_test_count": number,
  "concerns": ["list of things that look wrong or missing"]
}}
Return JSON only."""

        response = self.client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )
        try:
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"): text = text[4:]
            return json.loads(text.strip())
        except Exception:
            return {"pr_title": pr_title, "purpose": "Could not parse", "concerns": []}

    # ── PRReviewAgent ─────────────────────────────────────────────────────────

    def _run_review_agent(self, analysis: dict, checklist: str) -> dict | None:
        """
        CAPSTONE: Agent Model Mapping — Sonnet for quality review writing.
        Applies the checklist and writes specific, actionable review comments.
        """
        checklist_text = _get_checklist(checklist)

        prompt = f"""You are a senior engineer reviewing a Pull Request.
You have NO QA bias — evaluate purely from a code quality and completeness perspective.

PR Analysis:
{json.dumps(analysis, indent=2)}

Apply this checklist:
{checklist_text}

Return a JSON object:
{{
  "decision": "APPROVE" | "REQUEST_CHANGES" | "COMMENT",
  "summary": "2-3 sentence overall assessment",
  "comments": [
    {{
      "type": "blocking" | "suggestion" | "praise",
      "topic": "short label",
      "body": "specific, actionable comment text"
    }}
  ],
  "checklist_results": {{
    "item_name": "pass" | "fail" | "na"
  }}
}}
Return JSON only."""

        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        try:
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"): text = text[4:]
            return json.loads(text.strip())
        except Exception:
            return None

    # ── Post to GitHub ────────────────────────────────────────────────────────

    def _post_review(self, owner: str, repo: str, pr_num: int, review: dict) -> None:
        """Post the review as a PR comment. MCP write demonstrated here."""
        decision = review.get("decision", "COMMENT")
        summary  = review.get("summary", "")
        comments = review.get("comments", [])
        results  = review.get("checklist_results", {})

        lines = [
            f"## PR Review — {decision}",
            "",
            f"**{summary}**",
            "",
            "---",
            "",
            "### Checklist Results",
            "",
        ]

        for item, status in results.items():
            emoji = {"pass": "✅", "fail": "❌", "na": "—"}.get(status, "—")
            lines.append(f"- {emoji} {item}")

        if comments:
            lines += ["", "### Review Comments", ""]
            for c in comments:
                tag = {"blocking": "🔴", "suggestion": "💡", "praise": "✅"}.get(c.get("type",""), "")
                lines.append(f"**{tag} {c.get('topic','')}**")
                lines.append(c.get("body", ""))
                lines.append("")

        lines += [
            "---",
            "*Review generated by PR Orchestrator — STLC Capstone*",
            "🤖 Generated with [Claude Code](https://claude.com/claude-code)",
        ]

        try:
            self.gh.add_pr_comment(owner, repo, pr_num, "\n".join(lines))
            print(f"  [github] Review posted → PR #{pr_num} | Decision: {decision}")
        except Exception as e:
            print(f"  [github] Could not post review: {e}")
            print(f"  Review content:\n{chr(10).join(lines[:20])}")


# ── Checklists ────────────────────────────────────────────────────────────────

def _get_checklist(checklist: str) -> str:
    checklists = {
        "pytest": """
PYTEST CODE REVIEW CHECKLIST:
1. Every test function has at least one assert statement
2. No hardcoded credentials or environment-specific values
3. Test names clearly describe what they test (test_<scenario>_<expected>)
4. Fixtures used for setup/teardown, not repeated setup in every test
5. Negative and edge cases present, not just happy-path tests
6. No duplicate tests (two tests doing identical assertions)
7. Expected results are specific (not "should work" or "assert result")
8. Test data uses realistic values, not placeholders like <email>
""",
        "playwright": """
PLAYWRIGHT TEST REVIEW CHECKLIST:
1. Page object model used — no raw selectors in test functions
2. Selectors are stable (data-testid preferred over CSS class or text)
3. Waits use expect().toBeVisible() not hardcoded sleep()
4. Screenshots captured on failure
5. Tests are independent — no shared state between tests
6. Environment URLs come from config, not hardcoded
7. Both happy path and error states tested
8. Mobile viewport tested where relevant
""",
    }
    return checklists.get(checklist, checklists["pytest"])
