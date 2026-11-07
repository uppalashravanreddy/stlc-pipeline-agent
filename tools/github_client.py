"""
CAPSTONE CONCEPT: MCP Knowledge — MCP write, not just read

The Jira client demonstrated MCP read (fetch a story by ticket ID).
This GitHub client demonstrates MCP write (create a PR, post comments).

Two layers of GitHub integration:
  1. .vscode/mcp.json  — registers @modelcontextprotocol/server-github
     so VS Code and GitHub Copilot can call GitHub tools natively
  2. This file        — direct GitHub REST API for the Python pipeline
     Creates PRs, posts comments, reads repo info

The GitHub personal access token is read from .env:
  GITHUB_PERSONAL_ACCESS_TOKEN=ghp_...
"""
import os
import json
import urllib.request
import urllib.error
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

GITHUB_API = "https://api.github.com"


class GitHubClient:
    """Creates pull requests and posts comments via GitHub REST API."""

    def __init__(self):
        self.token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", "")
        if not self.token:
            raise EnvironmentError(
                "GITHUB_PERSONAL_ACCESS_TOKEN not set in .env\n"
                "Create one at: https://github.com/settings/tokens"
            )
        self._headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept":        "application/vnd.github+json",
            "Content-Type":  "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def get_repo_info(self, owner: str, repo: str) -> dict:
        """Fetch basic repo info — confirms token works."""
        return self._get(f"/repos/{owner}/{repo}")

    def create_pull_request(
        self,
        owner:      str,
        repo:       str,
        title:      str,
        body:       str,
        head:       str,   # source branch (e.g. "feat/KAN-28-stlc-automation")
        base:       str = "main",
        draft:      bool = True,
    ) -> dict:
        """
        Create a Pull Request.

        Returns the PR dict including: number, html_url, title, state.
        draft=True means reviewers are not auto-requested — good default
        for AI-generated PRs that need human review first.
        """
        payload = {
            "title": title,
            "body":  body,
            "head":  head,
            "base":  base,
            "draft": draft,
        }
        result = self._post(f"/repos/{owner}/{repo}/pulls", payload)
        print(f"  [github] PR created → {result.get('html_url')}")
        return result

    def add_pr_comment(self, owner: str, repo: str, pr_number: int, body: str) -> dict:
        """Post a review comment on the PR body (not inline on a line)."""
        result = self._post(
            f"/repos/{owner}/{repo}/issues/{pr_number}/comments",
            {"body": body}
        )
        print(f"  [github] Comment posted → PR #{pr_number}")
        return result

    def get_repo_from_remote(self) -> tuple[str, str]:
        """
        Read the GitHub owner/repo from .git/config in the workspace root.
        Returns (owner, repo) or raises ValueError if not found.
        """
        import re
        git_config = Path(__file__).parent.parent / ".git" / "config"
        if not git_config.exists():
            raise ValueError("No .git/config found. Is this a git repo?")

        content = git_config.read_text()
        match = re.search(r'url\s*=\s*.*github\.com[:/]([^/\n]+)/([^\n.]+)', content)
        if not match:
            raise ValueError("Could not parse GitHub remote URL from .git/config")

        owner = match.group(1).strip()
        repo  = match.group(2).strip().removesuffix(".git")
        return owner, repo

    def _get(self, path: str) -> dict:
        req = urllib.request.Request(
            f"{GITHUB_API}{path}", headers=self._headers
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())

    def _post(self, path: str, payload: dict) -> dict:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{GITHUB_API}{path}",
            data=data,
            headers=self._headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            raise ValueError(f"GitHub API {e.code}: {body[:200]}")
