"""
CAPSTONE CONCEPT: Skills — reusable instruction packages

Skills live in .claude/skills/*.md.
This loader reads skill files and returns their content so agents can
inject them into system prompts at runtime.

Why this matters:
  - QA methodology lives in skill files, not buried in Python strings
  - Update a skill file → agent behaviour changes, no Python edit needed
  - Skills vs Instructions: skills are loaded on demand per agent/phase;
    instructions (system prompts) are always active

Called by:
  - analysis_agent.py  → classify-requirement + generate-test-plan
  - generation_agent.py → generate-test-cases + review-test-artifacts
  - main.py            → fetch-user-story (when --ticket flag is used)
"""
from pathlib import Path

SKILLS_DIR = Path(__file__).parent.parent / ".claude" / "skills"


def load_skill(skill_name: str) -> str:
    """
    Load a skill file and return its content.
    Strips the YAML frontmatter (--- ... ---) so only the instructions remain.
    Returns empty string if skill file not found.
    """
    skill_path = SKILLS_DIR / f"{skill_name}.md"
    if not skill_path.exists():
        print(f"  [skills] WARNING: skill '{skill_name}' not found at {skill_path}")
        return ""

    content = skill_path.read_text(encoding="utf-8")

    # Strip YAML frontmatter if present
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            content = parts[2].strip()

    return content


def load_skills(*skill_names: str) -> str:
    """Load multiple skills and join them as one block."""
    parts = []
    for name in skill_names:
        skill_content = load_skill(name)
        if skill_content:
            parts.append(skill_content)
    return "\n\n---\n\n".join(parts)
