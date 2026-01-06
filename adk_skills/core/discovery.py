"""Skills discovery system - scan directories for SKILL.md files."""

from pathlib import Path

from adk_skills.core.models import SkillMetadata
from adk_skills.core.parser import parse_metadata
from adk_skills.exceptions import SkillParseError


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
        - Uses glob pattern: {skill,skills}/**/SKILL.md
    """
    discovered: list[SkillMetadata] = []
    seen_names: set = set()

    for directory in directories:
        if not directory.exists():
            continue

        if not directory.is_dir():
            continue

        # Search for SKILL.md files recursively
        # Look in both skill/ and skills/ subdirectories
        for pattern in ["**/SKILL.md", "**/skill.md"]:
            for skill_path in directory.glob(pattern):
                try:
                    # Parse metadata only (fast)
                    metadata = parse_metadata(skill_path)

                    # Warn about duplicate names
                    if metadata.name in seen_names:
                        # Skip duplicate but could log warning
                        continue

                    discovered.append(metadata)
                    seen_names.add(metadata.name)

                except SkillParseError:
                    # Skip invalid skills
                    # Could log warning here
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
