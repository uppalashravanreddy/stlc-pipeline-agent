"""
Shared output directory helper for all phase tools.

Creates output/<STORY-ID>/ so every story's artifacts are grouped together.
If feature_name starts with a ticket ID (e.g. KAN-28, PROJ-14), that becomes
the folder name. Otherwise falls back to a slugified name.

  output/KAN-28/phase01_20261106_120000.md
  output/KAN-28/phase02_20261106_120500.md
  output/KAN-29/phase01_...
"""
import re
from pathlib import Path

BASE_OUTPUT = Path(__file__).parent.parent / "output"


def get_story_dir(feature_name: str) -> Path:
    """Return output/<story_id>/ and create it if it doesn't exist."""
    match = re.match(r"^([A-Z]+-\d+)", feature_name.strip())
    folder = match.group(1) if match else _slugify(feature_name)[:25]
    story_dir = BASE_OUTPUT / folder
    story_dir.mkdir(parents=True, exist_ok=True)
    return story_dir


def _slugify(text: str) -> str:
    slug = text.lower().replace(" ", "_").replace("—", "").replace("-", "_")
    return "".join(c for c in slug if c.isalnum() or c == "_")
