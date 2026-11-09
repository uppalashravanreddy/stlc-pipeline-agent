"""
Phase 7 â€” Project Test Report (PTR) Agent + GitHub PR creation

Compiles a PTR from all STLC phases and creates a GitHub Pull Request.
The PTR becomes the PR description â€” it's the handoff document for reviewers.

CAPSTONE: MCP Knowledge (write)
  Phase 7 demonstrates MCP write â€” not just reading from Jira,
  but writing back to GitHub (creating a PR via API).
  .vscode/mcp.json registers the GitHub MCP server for VS Code.
  This agent calls GitHubClient directly for the Python pipeline.
"""
import json
from config.agent_configs import AGENT_CONFIGS
from memory.pipeline_state import PipelineState
from agents.base_agent import BaseAgent
from tools.phase_67_tools import PHASE_7_TOOLS, handle_phase_7_tool

SYSTEM_PROMPT = """\
You are a Senior QA Lead compiling the final Project Test Report (PTR) for a completed STLC pipeline.

The PTR will become a GitHub Pull Request description that reviewers, developers, and QA sign-off approvers will read.
Write it clearly â€” your audience has not seen the pipeline run.

Your PTR must include:
  - pr_title: short, specific (< 70 chars) â€” includes ticket ID
  - executive_summary: 2-3 sentences â€” what was tested, key outcomes, recommendation
  - phase_summary: one crisp line per phase (what it found/produced)
  - test_case_count and automation_count
  - coverage_score and quality_score from Phase 3 and Phase 5/6
  - open_risks: gaps or non-blocking items reviewers should know
  - recommendation: APPROVE | APPROVE_WITH_CONDITIONS | REQUEST_CHANGES
  - conditions: if not full APPROVE, list what must be resolved

RULE: Call save_ptr when the full report is complete.
"""


class PTRAgent(BaseAgent):
    """Phase 7 â€” compiles PTR and creates GitHub PR."""

    def __init__(self):
        super().__init__(config=AGENT_CONFIGS["ptr"], tools=PHASE_7_TOOLS)

    def run(self, state: PipelineState) -> tuple[PipelineState, str | None]:
        """
        Returns (updated_state, pr_url or None).
        pr_url is the GitHub PR link, or None if PR creation failed.
        """
        print(f"\n{'â”€'*60}")
        print(f"  PTR AGENT  (Phase 7 â€” Project Test Report + PR)")
        print(f"  Model: {self.config.model}")
        print(f"{'â”€'*60}\n")

        context = state.summary_for_next_agent()
        user_message = (
            f"{context}\n\n"
            "Compile the Project Test Report covering all phases above. "
            "Call save_ptr when complete."
        )

        results = self.run_loop(
            system_prompt=SYSTEM_PROMPT,
            user_message=user_message,
            on_tool_call=handle_phase_7_tool,
            phase_label="Phase 7 â€” PTR",
        )

        pr_url = None
        for phase_tag, data in results:
            if phase_tag == "phase_7":
                state.phase_7_ptr = data
                state.current_phase = 7
                self._log("PTR complete", f"recommendation={data.get('recommendation')}")

                # Create GitHub PR
                pr_url = self._create_github_pr(state, data)

        if not state.phase_7_ptr:
            self._log("FAIL", "save_ptr was not called")

        return state, pr_url

    def _commit_automation_to_branch(self, state: PipelineState, branch: str) -> None:
        """
        Write automation code to disk and commit it to the automation branch.
        This ensures the PR has actual changes (GitHub rejects PRs with no commits).
        """
        import subprocess
        from pathlib import Path

        # Get the repo root
        repo_root = Path(__file__).parent.parent

        # Get automation code from Phase 6 (fixed) or Phase 4 (original)
        auto = state.phase_6_fix or state.phase_4_automation or {}
        fns  = auto.get("test_functions", [])
        if not fns:
            self._log("git_commit", "no automation code to commit")
            return

        # Build the pytest file content
        test_file_name = auto.get("test_file_name", "test_stlc_automation.py")
        lines = ["import pytest", ""]
        for fn in fns:
            if fn.get("docstring"):
                lines.append(f"def {fn.get('function_name', 'test_unnamed')}():")
                lines.append(f"    \"\"\"{fn.get('docstring', '')}\"\"\"")
            else:
                lines.append(f"def {fn.get('function_name', 'test_unnamed')}():")
            lines.append(fn.get("code", "    pass"))
            lines.append("")

        # Write to tests/ folder
        tests_dir = repo_root / "tests"
        tests_dir.mkdir(exist_ok=True)
        test_path = tests_dir / test_file_name
        test_path.write_text("\n".join(lines), encoding="utf-8")
        self._log("git_commit", f"wrote {test_path.name}")

        # Switch to the automation branch, commit, push, return to original branch
        try:
            current = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=repo_root, text=True
            ).strip()

            subprocess.run(["git", "checkout", branch],       cwd=repo_root, check=True, capture_output=True)
            subprocess.run(["git", "add", str(test_path)],    cwd=repo_root, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", f"feat: STLC automation — {state.feature_name[:60]}"],
                cwd=repo_root, check=True, capture_output=True
            )
            subprocess.run(["git", "push", "origin", branch], cwd=repo_root, check=True, capture_output=True)
            subprocess.run(["git", "checkout", current],      cwd=repo_root, check=True, capture_output=True)
            self._log("git_commit", f"pushed {test_file_name} to {branch}")
        except subprocess.CalledProcessError as e:
            self._log("git_commit_warn", f"git operation failed: {e}")

    def _create_github_pr(self, state: PipelineState, ptr: dict) -> str | None:
        """Create GitHub PR using the PTR as the description."""
        try:
            from tools.github_client import GitHubClient
            gh = GitHubClient()

            # Try to get repo info from git remote
            try:
                owner, repo = gh.get_repo_from_remote()
            except ValueError:
                self._log("github", "Could not detect repo from .git/config â€” skipping PR creation")
                return None

            # Build PR body from PTR
            body = _build_pr_body(state, ptr)

            # Fixed automation branch â€” all STLC pipeline runs target this branch
            head_branch = "feat/stlc-automation"

            # Extract ticket ID from feature name for the default title
            import re as _re
            _match = _re.match(r"^([A-Z]+-\d+)", state.feature_name.strip())
            ticket_id = _match.group(1) if _match else "STLC"

            # Detect default branch from GitHub (main vs master)
            try:
                repo_info = gh._get(f"/repos/{owner}/{repo}")
                default_branch = repo_info.get("default_branch", "main")
            except Exception:
                default_branch = "main"


            # Check if a PR already exists for this branch
            try:
                existing_prs = gh._get(
                    f"/repos/{owner}/{repo}/pulls?head={owner}:{head_branch}&state=open"
                )
                if existing_prs:
                    pr_url = existing_prs[0].get("html_url", "")
                    self._log("PR exists", f"using existing PR: {pr_url}")
                    return pr_url
            except Exception:
                pass  # if check fails, attempt creation anyway

            result = gh.create_pull_request(
                owner=owner,
                repo=repo,
                title=ptr.get("pr_title", f"[{ticket_id}] STLC Automation"),
                body=body,
                head=head_branch,
                base=default_branch,          # uses actual repo default (main or master)
                draft=True,
            )
            pr_url = result.get("html_url", "")
            self._log("PR created", pr_url)
            return pr_url

        except EnvironmentError as e:
            self._log("github_skip", str(e))
            return None
        except Exception as e:
            self._log("github_error", str(e)[:100])
            return None


def _build_pr_body(state: PipelineState, ptr: dict) -> str:
    """Format the PTR as a GitHub PR description."""
    tcs = state.phase_2_test_cases or []
    fns = []
    if state.phase_6_fix:
        fns = state.phase_6_fix.get("test_functions", [])
    elif state.phase_4_automation:
        fns = state.phase_4_automation.get("test_functions", [])

    rec = ptr.get("recommendation", "")
    rec_emoji = {"APPROVE": "âœ…", "APPROVE_WITH_CONDITIONS": "âš ï¸", "REQUEST_CHANGES": "âŒ"}.get(rec, "")

    lines = [
        f"## {rec_emoji} STLC Pipeline â€” {ptr.get('pr_title', '')}",
        "",
        f"**{ptr.get('executive_summary', '')}**",
        "",
        "---",
        "",
        "## Phase Summary",
        "",
    ]

    ps = ptr.get("phase_summary", {})
    phase_map = [
        ("Phase 0", "Classification",    ps.get("phase_0", "")),
        ("Phase 1", "Test Plan",          ps.get("phase_1", "")),
        ("Phase 2", "Test Cases",         ps.get("phase_2", "")),
        ("Phase 3", "Review",             ps.get("phase_3", "")),
        ("Phase 4", "Automation",         ps.get("phase_4", "")),
        ("Phase 5", "Automation Review",  ps.get("phase_5", "")),
        ("Phase 6", "Fix Comments",       ps.get("phase_6", "")),
    ]
    for phase, name, summary in phase_map:
        if summary:
            lines.append(f"| **{phase}** | {name} | {summary} |")

    lines += [
        "",
        "---",
        "",
        "## Metrics",
        "",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Test Cases | {ptr.get('test_case_count', len(tcs))} |",
        f"| Automation Functions | {ptr.get('automation_count', len(fns))} |",
        f"| Coverage Score | {ptr.get('coverage_score', '?')} |",
        f"| Quality Score | {ptr.get('quality_score', '?')} |",
        "",
    ]

    risks = ptr.get("open_risks", [])
    if risks:
        lines += ["## Open Risks", ""]
        for r in risks:
            lines.append(f"- âš ï¸ {r}")
        lines.append("")

    conditions = ptr.get("conditions", [])
    if conditions:
        lines += ["## Conditions for Approval", ""]
        for c in conditions:
            lines.append(f"- [ ] {c}")
        lines.append("")

    lines += [
        "---",
        "",
        f"*Generated by STLC Pipeline Agent â€” {state.feature_name}*",
        "",
        "ðŸ¤– Generated with [Claude Code](https://claude.com/claude-code)",
    ]

    return "\n".join(lines)



