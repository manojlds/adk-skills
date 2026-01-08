"""SKILL.md parser with two-mode operation (metadata-only vs full)."""

from pathlib import Path
from typing import Optional

from adk_skills_agent.core.models import Skill, SkillMetadata
from adk_skills_agent.exceptions import SkillParseError
from adk_skills_agent.utils.yaml_parser import parse_frontmatter


def find_skill_md(skill_dir: Path) -> Optional[Path]:
    """Find the SKILL.md file in a skill directory.

    Prefers SKILL.md (uppercase) but accepts skill.md (lowercase).

    Args:
        skill_dir: Path to the skill directory

    Returns:
        Path to the SKILL.md file, or None if not found
    """
    for name in ("SKILL.md", "skill.md"):
        path = skill_dir / name
        if path.exists() and path.is_file():
            return path
    return None


def parse_metadata(skill_path: Path) -> SkillMetadata:
    """Parse only frontmatter metadata from SKILL.md (fast discovery).

    Args:
        skill_path: Path to SKILL.md file or skill directory

    Returns:
        SkillMetadata with parsed frontmatter

    Raises:
        SkillParseError: If SKILL.md not found or parsing fails
    """
    # Handle both file path and directory path
    if skill_path.is_dir():
        skill_md = find_skill_md(skill_path)
        if skill_md is None:
            raise SkillParseError(f"SKILL.md not found in {skill_path}")
        skill_path = skill_md

    try:
        content = skill_path.read_text(encoding="utf-8")
    except Exception as e:
        raise SkillParseError(f"Error reading {skill_path}: {e}") from e

    metadata, _ = parse_frontmatter(content)

    # Validate required fields
    if "name" not in metadata:
        raise SkillParseError(f"Missing required field 'name' in {skill_path}")
    if "description" not in metadata:
        raise SkillParseError(f"Missing required field 'description' in {skill_path}")

    name = metadata["name"]
    description = metadata["description"]

    if not isinstance(name, str) or not name.strip():
        raise SkillParseError(f"Field 'name' must be a non-empty string in {skill_path}")
    if not isinstance(description, str) or not description.strip():
        raise SkillParseError(f"Field 'description' must be a non-empty string in {skill_path}")

    return SkillMetadata(
        name=name.strip(),
        description=description.strip(),
        location=skill_path,
        license=metadata.get("license"),
        compatibility=metadata.get("compatibility"),
        allowed_tools=metadata.get("allowed-tools"),
        metadata=metadata.get("metadata", {}),
    )


def parse_full(skill_path: Path) -> Skill:
    """Parse complete SKILL.md with full content (on-demand activation).

    Args:
        skill_path: Path to SKILL.md file or skill directory

    Returns:
        Skill with full instructions and directory structure

    Raises:
        SkillParseError: If SKILL.md not found or parsing fails
    """
    # Handle both file path and directory path
    if skill_path.is_dir():
        skill_dir = skill_path
        skill_md = find_skill_md(skill_path)
        if skill_md is None:
            raise SkillParseError(f"SKILL.md not found in {skill_path}")
        skill_path = skill_md
    else:
        skill_dir = skill_path.parent

    try:
        content = skill_path.read_text(encoding="utf-8")
    except Exception as e:
        raise SkillParseError(f"Error reading {skill_path}: {e}") from e

    metadata, body = parse_frontmatter(content)

    # Validate required fields
    if "name" not in metadata:
        raise SkillParseError(f"Missing required field 'name' in {skill_path}")
    if "description" not in metadata:
        raise SkillParseError(f"Missing required field 'description' in {skill_path}")

    name = metadata["name"]
    description = metadata["description"]

    if not isinstance(name, str) or not name.strip():
        raise SkillParseError(f"Field 'name' must be a non-empty string in {skill_path}")
    if not isinstance(description, str) or not description.strip():
        raise SkillParseError(f"Field 'description' must be a non-empty string in {skill_path}")

    # Discover directory structure (lazy)
    scripts_dir = skill_dir / "scripts" if (skill_dir / "scripts").is_dir() else None
    references_dir = skill_dir / "references" if (skill_dir / "references").is_dir() else None
    assets_dir = skill_dir / "assets" if (skill_dir / "assets").is_dir() else None

    return Skill(
        name=name.strip(),
        description=description.strip(),
        location=skill_path,
        skill_dir=skill_dir,
        instructions=body,
        license=metadata.get("license"),
        compatibility=metadata.get("compatibility"),
        allowed_tools=metadata.get("allowed-tools"),
        metadata=metadata.get("metadata", {}),
        scripts_dir=scripts_dir,
        references_dir=references_dir,
        assets_dir=assets_dir,
    )
