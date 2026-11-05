"""
CAPSTONE CONCEPT: MCP Knowledge

MCP (Model Context Protocol) is the standard for connecting agents to external
tools and data. This module implements the Jira integration layer:

  Without MCP:  python main.py --story "paste full story text here..."
  With MCP:     python main.py --ticket KAN-14
                → pipeline fetches live story from Jira automatically

Two things demonstrate MCP in this project:
  1. This client   — fetches Jira data and feeds it into the agent pipeline
  2. .vscode/mcp.json — registers @sooperset/mcp-atlassian as a VS Code MCP
     server so GitHub Copilot can also call Jira tools natively

The Jira REST API v3 is called directly here. In a full MCP setup, the
orchestrator would call a `get_jira_story` tool on the MCP server instead
of this direct client — the result to the pipeline is identical.
"""
import base64
import json
import urllib.request
import urllib.error
from pathlib import Path
from dotenv import load_dotenv
import os


load_dotenv()


class JiraClient:
    """Fetches a single Jira issue and formats it as a pipeline-ready user story."""

    def __init__(self):
        self.base_url = os.getenv("JIRA_INSTANCE_URL", "").rstrip("/")
        self.email    = os.getenv("JIRA_USER_EMAIL", "")
        self.token    = os.getenv("JIRA_API_TOKEN", "")

        if not all([self.base_url, self.email, self.token]):
            raise EnvironmentError(
                "Missing Jira credentials. Add to .env:\n"
                "  JIRA_INSTANCE_URL=https://yourcompany.atlassian.net\n"
                "  JIRA_USER_EMAIL=your@email.com\n"
                "  JIRA_API_TOKEN=your_token_here"
            )

        self._auth = base64.b64encode(
            f"{self.email}:{self.token}".encode()
        ).decode()

    def fetch_story(self, ticket_key: str) -> dict:
        """
        Fetch a Jira ticket and return:
          {
            "feature_name": "KAN-14: Story summary",
            "user_story":   "Full description + acceptance criteria as text"
          }

        Raises:
          ValueError if the ticket is not found or credentials are wrong.
        """
        url  = f"{self.base_url}/rest/api/3/issue/{ticket_key}"
        data = self._get(url)

        fields  = data.get("fields", {})
        summary = fields.get("summary", ticket_key)

        description_text = _parse_adf(fields.get("description") or {})
        ac_text          = _extract_acceptance_criteria(fields)

        user_story = description_text
        if ac_text:
            user_story += f"\n\nAcceptance Criteria:\n{ac_text}"

        if not user_story.strip():
            user_story = f"Story: {summary}\n(No description in Jira — add details to the ticket.)"

        print(f"  [jira] fetched {ticket_key}: {summary}")

        return {
            "feature_name": f"{ticket_key}: {summary}",
            "user_story":   user_story.strip(),
        }

    def _get(self, url: str) -> dict:
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Basic {self._auth}",
                "Accept":        "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise ValueError("Jira authentication failed — check JIRA_USER_EMAIL and JIRA_API_TOKEN")
            if e.code == 404:
                raise ValueError(f"Ticket not found: {url.split('/')[-1]}")
            raise ValueError(f"Jira API error {e.code}: {e.reason}")


# ── ADF (Atlassian Document Format) parser ────────────────────────────────────

def _parse_adf(node: dict, depth: int = 0) -> str:
    """
    Recursively extract plain text from Jira's Atlassian Document Format.
    ADF is a JSON tree — text lives in leaf nodes of type 'text'.
    """
    if not node:
        return ""

    node_type = node.get("type", "")
    content   = node.get("content", [])
    text      = node.get("text", "")

    if node_type == "text":
        return text

    if node_type in ("paragraph", "heading"):
        inner = "".join(_parse_adf(c) for c in content)
        return inner + "\n"

    if node_type == "bulletList":
        lines = []
        for item in content:
            item_text = "".join(_parse_adf(c) for c in item.get("content", []))
            lines.append(f"- {item_text.strip()}")
        return "\n".join(lines) + "\n"

    if node_type == "orderedList":
        lines = []
        for i, item in enumerate(content, 1):
            item_text = "".join(_parse_adf(c) for c in item.get("content", []))
            lines.append(f"{i}. {item_text.strip()}")
        return "\n".join(lines) + "\n"

    # For any other node type, recurse into children
    return "".join(_parse_adf(c) for c in content)


def _extract_acceptance_criteria(fields: dict) -> str:
    """
    Try to find acceptance criteria from common Jira field names.
    Different Jira projects store AC in different custom fields.
    """
    # Common custom field names for AC
    for key, value in fields.items():
        if not isinstance(value, dict):
            continue
        field_name = key.lower()
        if any(kw in field_name for kw in ("acceptance", "criteria", "ac_")):
            return _parse_adf(value)

    # Also try to find AC markers in the description text
    return ""
