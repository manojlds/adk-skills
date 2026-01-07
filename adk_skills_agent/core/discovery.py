"""Skills discovery system - scan directories for SKILL.md files."""

from pathlib import Path

from adk_skills_agent.core.models import SkillMetadata
from adk_skills_agent.core.parser import parse_metadata
from adk_skills_agent.exceptions import SkillParseError


def discover_skills(directories: list[Path]) -> list[SkillMetadata]:
    """Discover skills from directories by scanning for SKILL.md files.

    This performs fast metadata-only parsing for efficient discovery.

    Args:
        directories: List of directories to scan for skills

    Returns:
        List of SkillMetadata for all discovered skills

    Note:
        - Scans recursively for SKILL.md files
        - Parses only frontmatter (not full content)
        - Skips invalid skills with warnings
        - Prefers SKILL.md over skill.md if both exist in same directory
    """
    discovered: list[SkillMetadata] = []
    seen_names: set = set()
    seen_dirs: set = set()

    for directory in directories:
        if not directory.exists():
            continue

        if not directory.is_dir():
            continue

        # First pass: Find all SKILL.md files (uppercase preferred)
        for skill_path in directory.glob("**/SKILL.md"):
            skill_dir = skill_path.parent
            seen_dirs.add(skill_dir)

            try:
                # Parse metadata only (fast)
                metadata = parse_metadata(skill_path)

                # Skip duplicate names
                if metadata.name in seen_names:
                    continue

                discovered.append(metadata)
                seen_names.add(metadata.name)

            except SkillParseError:
                # Skip invalid skills
                continue

        # Second pass: Find skill.md files (lowercase) only if no SKILL.md in same dir
        for skill_path in directory.glob("**/skill.md"):
            skill_dir = skill_path.parent

            # Skip if we already found SKILL.md in this directory
            if skill_dir in seen_dirs:
                continue

            try:
                # Parse metadata only (fast)
                metadata = parse_metadata(skill_path)

                # Skip duplicate names
                if metadata.name in seen_names:
                    continue

                discovered.append(metadata)
                seen_names.add(metadata.name)

            except SkillParseError:
                # Skip invalid skills
                continue

    return discovered


def discover_skills_in_directory(directory: Path) -> list[SkillMetadata]:
    """Discover skills in a single directory.

    Convenience wrapper for discover_skills with single directory.

    Args:
        directory: Directory to scan

    Returns:
        List of discovered skills
    """
    return discover_skills([directory])
