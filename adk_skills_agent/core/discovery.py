"""Skills discovery system - scan directories for SKILL.md files."""

from pathlib import Path

from adk_skills_agent.core.models import SkillMetadata
from adk_skills_agent.core.parser import parse_metadata
from adk_skills_agent.exceptions import SkillParseError


def discover_skills(directories: list[Path]) -> list[SkillMetadata]:
    """Discover skills from directories by scanning for ``SKILL.md`` files.

    Performs fast metadata-only parsing for efficient discovery.

    Args:
        directories: List of directories to scan for skills.

    Returns:
        List of :class:`SkillMetadata` for all discovered skills.

    Note:
        - Scans recursively for ``SKILL.md`` (uppercase only, per the
          agentskills.io specification).
        - Parses only frontmatter (not full content).
        - Silently skips files that fail to parse.
    """
    discovered: list[SkillMetadata] = []
    seen_names: set = set()

    for directory in directories:
        if not directory.exists() or not directory.is_dir():
            continue

        for skill_path in directory.glob("**/SKILL.md"):
            try:
                metadata = parse_metadata(skill_path)
            except SkillParseError:
                continue

            if metadata.name in seen_names:
                continue

            discovered.append(metadata)
            seen_names.add(metadata.name)

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
