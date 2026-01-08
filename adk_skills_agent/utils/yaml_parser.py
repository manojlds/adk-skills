"""YAML frontmatter parser for SKILL.md files."""

from pathlib import Path
from typing import Any

import yaml

from adk_skills_agent.exceptions import SkillParseError


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from SKILL.md content.

    Args:
        content: Raw content of SKILL.md file

    Returns:
        Tuple of (metadata dict, markdown body)

    Raises:
        SkillParseError: If frontmatter is missing or invalid
    """
    if not content.strip():
        raise SkillParseError("SKILL.md file is empty")

    if not content.startswith("---"):
        raise SkillParseError("SKILL.md must start with YAML frontmatter (---)")

    # Split on --- delimiters
    parts = content.split("---", 2)
    if len(parts) < 3:
        raise SkillParseError("SKILL.md frontmatter not properly closed with ---")

    frontmatter_str = parts[1]
    body = parts[2].strip()

    # Parse YAML
    try:
        metadata = yaml.safe_load(frontmatter_str)
    except yaml.YAMLError as e:
        raise SkillParseError(f"Invalid YAML in frontmatter: {e}") from e

    if metadata is None:
        raise SkillParseError("SKILL.md frontmatter is empty")

    if not isinstance(metadata, dict):
        raise SkillParseError("SKILL.md frontmatter must be a YAML mapping")

    # Ensure metadata.metadata is a dict if present
    if "metadata" in metadata and isinstance(metadata["metadata"], dict):
        metadata["metadata"] = {str(k): str(v) for k, v in metadata["metadata"].items()}

    return metadata, body


def extract_frontmatter(file_path: Path) -> dict[str, Any]:
    """Extract only the YAML frontmatter from a SKILL.md file.

    This is a fast operation used during skills discovery.

    Args:
        file_path: Path to SKILL.md file

    Returns:
        Parsed frontmatter as dictionary

    Raises:
        SkillParseError: If file cannot be read or parsed
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        raise SkillParseError(f"SKILL.md not found: {file_path}") from e
    except Exception as e:
        raise SkillParseError(f"Error reading {file_path}: {e}") from e

    metadata, _ = parse_frontmatter(content)
    return metadata
