"""SkillsRegistry - main interface for managing skills in ADK."""

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Optional, Union

from adk_skills_agent.core.discovery import discover_skills
from adk_skills_agent.core.models import Skill, SkillMetadata, SkillsConfig, ValidationResult
from adk_skills_agent.core.parser import parse_full
from adk_skills_agent.core.validator import validate_skill_metadata
from adk_skills_agent.exceptions import SkillNotFoundError


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

    def create_use_skill_tool(self, include_skills_listing: bool = True) -> Any:
        """Create ADK tool for skill activation.

        The tool description includes an <available_skills> block listing
        all discovered skills (when include_skills_listing=True). When called,
        it loads and returns the full skill instructions.

        Args:
            include_skills_listing: Whether to include <available_skills> XML in
                tool description (default: True). Set to False when using prompt
                injection to avoid duplication.

        Returns:
            Callable tool function for use with ADK agents

        Example:
            >>> registry = SkillsRegistry()
            >>> registry.discover(["./skills"])
            >>>
            >>> # Pattern 1: Tool-based (default)
            >>> agent = Agent(
            ...     name="assistant",
            ...     model="gemini-2.5-flash",
            ...     tools=[registry.create_use_skill_tool()]
            ... )
            >>>
            >>> # Pattern 2: Prompt-based
            >>> prompt = registry.to_prompt_xml()
            >>> agent = Agent(
            ...     instruction=f"You are helpful.\\n{prompt}",
            ...     tools=[registry.create_use_skill_tool(include_skills_listing=False)]
            ... )
        """
        from adk_skills_agent.tools.use_skill import create_use_skill_tool

        return create_use_skill_tool(self, include_skills_listing=include_skills_listing)

    def create_run_script_tool(self) -> Any:
        """Create ADK tool for executing skill scripts.

        Returns:
            Callable tool function for script execution

        Example:
            >>> registry = SkillsRegistry()
            >>> registry.discover(["./skills"])
            >>> agent = Agent(
            ...     name="assistant",
            ...     model="gemini-2.5-flash",
            ...     tools=[
            ...         registry.create_use_skill_tool(),
            ...         registry.create_run_script_tool(),
            ...     ]
            ... )
        """
        from adk_skills_agent.tools.run_script import create_run_script_tool

        return create_run_script_tool(self)

    def create_read_reference_tool(self) -> Any:
        """Create ADK tool for reading skill reference files.

        Returns:
            Callable tool function for reading references

        Example:
            >>> registry = SkillsRegistry()
            >>> registry.discover(["./skills"])
            >>> agent = Agent(
            ...     name="assistant",
            ...     model="gemini-2.5-flash",
            ...     tools=[
            ...         registry.create_use_skill_tool(),
            ...         registry.create_read_reference_tool(),
            ...     ]
            ... )
        """
        from adk_skills_agent.tools.read_reference import create_read_reference_tool

        return create_read_reference_tool(self)

    # Prompt injection utilities

    def to_prompt_xml(self) -> str:
        """Generate XML representation of skills for system prompt injection.

        Returns XML block listing all available skills with name and description.
        This can be injected into an agent's system prompt to make skills
        available without using tools.

        Returns:
            XML string with <available_skills> block

        Example:
            >>> registry = SkillsRegistry()
            >>> registry.discover(["./skills"])
            >>> prompt = registry.to_prompt_xml()
            >>> print(prompt)
            <available_skills>
              <skill>
                <name>calculator</name>
                <description>Perform calculations</description>
              </skill>
            </available_skills>
        """
        from adk_skills_agent.tools.use_skill import generate_available_skills_xml

        return generate_available_skills_xml(self)

    def to_prompt_text(self) -> str:
        """Generate plain text representation of skills for system prompt injection.

        Returns a human-readable list of available skills with descriptions.

        Returns:
            Plain text string listing skills

        Example:
            >>> registry = SkillsRegistry()
            >>> registry.discover(["./skills"])
            >>> print(registry.to_prompt_text())
            Available Skills:
            - calculator: Perform calculations
            - hello-world: Simple greeting skill
        """
        skills_metadata = self.list_metadata()

        if not skills_metadata:
            return "No skills available."

        lines = ["Available Skills:"]
        for metadata in skills_metadata:
            lines.append(f"- {metadata.name}: {metadata.description}")

        return "\n".join(lines)

    def get_skills_prompt(self, format: str = "xml") -> str:
        """Get skills as formatted prompt text for injection.

        Convenience method that supports multiple output formats.

        Args:
            format: Output format - "xml" or "text" (default: "xml")

        Returns:
            Formatted string representation of skills

        Raises:
            ValueError: If format is not supported

        Example:
            >>> registry = SkillsRegistry()
            >>> registry.discover(["./skills"])
            >>> xml_prompt = registry.get_skills_prompt("xml")
            >>> text_prompt = registry.get_skills_prompt("text")
        """
        if format == "xml":
            return self.to_prompt_xml()
        elif format == "text":
            return self.to_prompt_text()
        else:
            raise ValueError(f"Unsupported format: {format}. Use 'xml' or 'text'.")

    # Validation utilities

    def validate_all(self, strict: bool = True) -> dict[str, ValidationResult]:
        """Validate all discovered skills.

        Runs validation on all skills in the registry and returns results.

        Args:
            strict: If True, enforce strict validation (warnings for missing optional fields)

        Returns:
            Dictionary mapping skill names to ValidationResult objects

        Example:
            >>> registry = SkillsRegistry()
            >>> registry.discover(["./skills"])
            >>> results = registry.validate_all(strict=True)
            >>> for name, result in results.items():
            ...     if not result.valid:
            ...         print(f"{name}: {result.errors}")
        """
        results = {}
        for metadata in self.list_metadata():
            results[metadata.name] = validate_skill_metadata(metadata, strict=strict)
        return results

    def validate_skill_by_name(self, name: str, strict: bool = True) -> ValidationResult:
        """Validate a specific skill by name.

        Args:
            name: Skill name to validate
            strict: If True, enforce strict validation

        Returns:
            ValidationResult for the skill

        Raises:
            SkillNotFoundError: If skill not found

        Example:
            >>> registry = SkillsRegistry()
            >>> registry.discover(["./skills"])
            >>> result = registry.validate_skill_by_name("calculator")
            >>> if result.valid:
            ...     print("Skill is valid!")
        """
        metadata = self.get_metadata(name)
        if metadata is None:
            raise SkillNotFoundError(
                f"Skill '{name}' not found. Available skills: {list(self._metadata_registry.keys())}"
            )
        return validate_skill_metadata(metadata, strict=strict)
