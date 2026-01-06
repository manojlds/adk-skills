"""SkillsRegistry - main interface for managing skills in ADK."""

from collections.abc import Sequence
from pathlib import Path
from typing import Optional, Union

from adk_skills.core.discovery import discover_skills
from adk_skills.core.models import Skill, SkillMetadata, SkillsConfig
from adk_skills.core.parser import parse_full
from adk_skills.core.validator import validate_skill_metadata
from adk_skills.exceptions import SkillNotFoundError


class SkillsRegistry:
    """Main registry for managing Agent Skills in ADK.

    This is the primary interface for:
    - Discovering skills from directories (metadata-only, fast)
    - Loading full skills on-demand (when activated)
    - Listing available skills
    - Creating tools for ADK agents

    Example:
        >>> registry = SkillsRegistry()
        >>> registry.discover(["./skills", "~/.adk/skills"])
        >>> metadata = registry.list_metadata()
        >>> skill = registry.load_skill("pdf-processing")
    """

    def __init__(self, config: Optional[SkillsConfig] = None):
        """Initialize skills registry.

        Args:
            config: Optional configuration. Uses defaults if not provided.
        """
        self.config = config or SkillsConfig()
        self._metadata_registry: dict[str, SkillMetadata] = {}
        self._skill_cache: dict[str, Skill] = {}

        # Auto-discover if configured
        if self.config.auto_discover and self.config.skills_directories:
            self.discover(self.config.skills_directories)

    def discover(self, directories: Sequence[Union[str, Path]]) -> int:
        """Discover skills from directories.

        This performs fast metadata-only parsing of SKILL.md files.

        Args:
            directories: List of directory paths to scan

        Returns:
            Number of skills discovered

        Example:
            >>> registry = SkillsRegistry()
            >>> count = registry.discover(["./skills"])
            >>> print(f"Found {count} skills")
        """
        # Convert string paths to Path objects
        paths = [Path(d).expanduser().resolve() for d in directories]

        # Discover skills (metadata only)
        discovered = discover_skills(paths)

        # Validate and add to registry
        for metadata in discovered:
            if self.config.strict_validation:
                result = validate_skill_metadata(metadata, strict=True)
                if not result.valid:
                    # Skip invalid skills in strict mode
                    continue

            # Add to registry (skip duplicates)
            if metadata.name not in self._metadata_registry:
                self._metadata_registry[metadata.name] = metadata

        return len(self._metadata_registry)

    def list_metadata(self) -> list[SkillMetadata]:
        """List all discovered skills (lightweight metadata).

        Returns:
            List of SkillMetadata for all discovered skills
        """
        return list(self._metadata_registry.values())

    def get_metadata(self, name: str) -> Optional[SkillMetadata]:
        """Get metadata for a specific skill.

        Args:
            name: Skill name

        Returns:
            SkillMetadata if found, None otherwise
        """
        return self._metadata_registry.get(name)

    def load_skill(self, name: str) -> Skill:
        """Load full skill content on-demand.

        This parses the complete SKILL.md including instructions.

        Args:
            name: Skill name to load

        Returns:
            Full Skill object with instructions

        Raises:
            SkillNotFoundError: If skill not found in registry

        Example:
            >>> skill = registry.load_skill("pdf-processing")
            >>> print(skill.instructions)
        """
        # Check cache first
        if name in self._skill_cache:
            return self._skill_cache[name]

        # Get metadata
        metadata = self.get_metadata(name)
        if metadata is None:
            raise SkillNotFoundError(
                f"Skill '{name}' not found. Available skills: {list(self._metadata_registry.keys())}"
            )

        # Parse full skill
        skill = parse_full(metadata.location)

        # Cache for future use
        self._skill_cache[name] = skill

        return skill

    def has_skill(self, name: str) -> bool:
        """Check if skill exists in registry.

        Args:
            name: Skill name

        Returns:
            True if skill exists
        """
        return name in self._metadata_registry

    def clear_cache(self) -> None:
        """Clear the skill cache.

        Useful for reloading skills that may have changed.
        """
        self._skill_cache.clear()

    def clear(self) -> None:
        """Clear all discovered skills and cache."""
        self._metadata_registry.clear()
        self._skill_cache.clear()

    def __len__(self) -> int:
        """Return number of discovered skills."""
        return len(self._metadata_registry)

    def __contains__(self, name: str) -> bool:
        """Check if skill exists (supports 'in' operator)."""
        return name in self._metadata_registry

    def __repr__(self) -> str:
        """String representation."""
        return f"SkillsRegistry(skills={len(self._metadata_registry)})"
