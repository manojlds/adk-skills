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
        self._db_metadata_registry: dict[str, SkillMetadata] = {}
        self._db_store = None

        if self.config.db_enabled:
            if self.config.db_session is None:
                raise ValueError("db_session is required when db_enabled is True.")
            from adk_skills_agent.db.store import SkillsStore

            self._db_store = SkillsStore(self.config.db_session)
            if self.config.db_auto_create:
                self._db_store.ensure_schema()
            self._refresh_db_metadata()

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
        if self._db_store is not None:
            self._refresh_db_metadata()
        merged = {**self._metadata_registry, **self._db_metadata_registry}
        return list(merged.values())

    def get_metadata(self, name: str) -> Optional[SkillMetadata]:
        """Get metadata for a specific skill.

        Args:
            name: Skill name

        Returns:
            SkillMetadata if found, None otherwise
        """
        if self._db_store is not None:
            self._refresh_db_metadata()
        if name in self._db_metadata_registry:
            return self._db_metadata_registry[name]
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
            available = {**self._metadata_registry, **self._db_metadata_registry}
            raise SkillNotFoundError(
                f"Skill '{name}' not found. Available skills: {list(available.keys())}"
            )

        if self._db_store is not None and name in self._db_metadata_registry:
            skill = self._db_store.get_skill(name, app_name=self.config.app_name)
            self._skill_cache[name] = skill
            return skill

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
        if self._db_store is not None:
            self._refresh_db_metadata()
        return name in self._metadata_registry or name in self._db_metadata_registry

    def clear_cache(self) -> None:
        """Clear the skill cache.

        Useful for reloading skills that may have changed.
        """
        self._skill_cache.clear()

    def clear(self) -> None:
        """Clear all discovered skills and cache."""
        self._metadata_registry.clear()
        self._db_metadata_registry.clear()
        self._skill_cache.clear()

    def __len__(self) -> int:
        """Return number of discovered skills."""
        if self._db_store is not None:
            self._refresh_db_metadata()
        # Merge to avoid double-counting skills in both registries
        merged = {**self._metadata_registry, **self._db_metadata_registry}
        return len(merged)

    def __contains__(self, name: str) -> bool:
        """Check if skill exists (supports 'in' operator)."""
        if self._db_store is not None:
            self._refresh_db_metadata()
        return name in self._metadata_registry or name in self._db_metadata_registry

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

    def inject_skills_prompt(self, instruction: str, format: str = "xml") -> str:
        """Inject skills listing into an instruction/system prompt.

        This method appends the skills listing to the provided instruction string,
        using the skills already discovered in this registry instance. This is more
        efficient than the standalone helper when you already have a registry.

        Args:
            instruction: Base instruction/system prompt
            format: Output format - "xml" or "text" (default: "xml")

        Returns:
            Instruction with skills listing appended, or unchanged if no skills

        Example:
            >>> registry = SkillsRegistry()
            >>> registry.discover(["./skills"])
            >>> instruction = "You are a helpful assistant."
            >>> full_instruction = registry.inject_skills_prompt(instruction, format="xml")
            >>> print(full_instruction)
            You are a helpful assistant.

            <available_skills>
            ...
            </available_skills>
        """
        if len(self) == 0:
            return instruction

        skills_prompt = self.get_skills_prompt(format=format)
        return f"{instruction}\n\n{skills_prompt}"

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
            available = {**self._metadata_registry, **self._db_metadata_registry}
            raise SkillNotFoundError(
                f"Skill '{name}' not found. Available skills: {list(available.keys())}"
            )
        return validate_skill_metadata(metadata, strict=strict)

    def _refresh_db_metadata(self) -> None:
        if self._db_store is None:
            return
        db_metadata = self._db_store.list_metadata(app_name=self.config.app_name)
        self._db_metadata_registry = {metadata.name: metadata for metadata in db_metadata}

    # Database operations

    def save_skill_to_db(self, skill: Skill, version: Optional[int] = None) -> None:
        """Save a skill to the database.

        Requires db_enabled=True in config.

        Args:
            skill: The skill to save
            version: Optional version number (auto-increments if None)

        Raises:
            RuntimeError: If database is not enabled

        Example:
            >>> registry = SkillsRegistry(config=SkillsConfig(
            ...     db_enabled=True, db_session=session
            ... ))
            >>> skill = registry.load_skill("my-skill")
            >>> registry.save_skill_to_db(skill)
        """
        if self._db_store is None:
            raise RuntimeError("Database not enabled. Set db_enabled=True in SkillsConfig.")

        self._db_store.save_skill(skill, app_name=self.config.app_name, version=version)
        self._refresh_db_metadata()
        # Invalidate cache for this skill
        self._skill_cache.pop(skill.name, None)

    def delete_skill_from_db(self, name: str, version: Optional[int] = None) -> int:
        """Delete a skill from the database.

        Args:
            name: Name of the skill to delete
            version: If specified, deletes only that version.
                    If None, deletes all versions.

        Returns:
            Number of records deleted

        Raises:
            RuntimeError: If database is not enabled

        Example:
            >>> registry.delete_skill_from_db("old-skill")  # Delete all versions
            >>> registry.delete_skill_from_db("my-skill", version=1)  # Delete v1 only
        """
        if self._db_store is None:
            raise RuntimeError("Database not enabled. Set db_enabled=True in SkillsConfig.")

        count = self._db_store.delete_skill(name, app_name=self.config.app_name, version=version)
        self._refresh_db_metadata()
        # Invalidate cache for this skill
        self._skill_cache.pop(name, None)
        return count

    def import_skill_to_db(self, name: str) -> None:
        """Import a file-based skill into the database.

        Loads the skill from file and saves it to the database,
        creating a new version.

        Args:
            name: Name of the file-based skill to import

        Raises:
            RuntimeError: If database is not enabled
            SkillNotFoundError: If skill not found in file registry

        Example:
            >>> registry = SkillsRegistry(config=SkillsConfig(
            ...     db_enabled=True, db_session=session
            ... ))
            >>> registry.discover(["./skills"])
            >>> registry.import_skill_to_db("my-skill")  # Now in DB
        """
        if self._db_store is None:
            raise RuntimeError("Database not enabled. Set db_enabled=True in SkillsConfig.")

        if name not in self._metadata_registry:
            raise SkillNotFoundError(
                f"Skill '{name}' not found in file registry. "
                f"Available: {list(self._metadata_registry.keys())}"
            )

        # Load from file
        metadata = self._metadata_registry[name]
        skill = parse_full(metadata.location)

        # Save to DB
        self._db_store.import_skill(skill, app_name=self.config.app_name)
        self._refresh_db_metadata()

    def list_skill_versions(self, name: str) -> list[int]:
        """List all versions of a skill in the database.

        Args:
            name: Skill name

        Returns:
            List of version numbers in ascending order

        Raises:
            RuntimeError: If database is not enabled

        Example:
            >>> versions = registry.list_skill_versions("my-skill")
            >>> print(versions)  # [1, 2, 3]
        """
        if self._db_store is None:
            raise RuntimeError("Database not enabled. Set db_enabled=True in SkillsConfig.")

        return self._db_store.list_versions(name, app_name=self.config.app_name)

    def skill_exists_in_db(self, name: str, version: Optional[int] = None) -> bool:
        """Check if a skill exists in the database.

        Args:
            name: Skill name to check
            version: Optional specific version to check

        Returns:
            True if skill exists in database

        Raises:
            RuntimeError: If database is not enabled
        """
        if self._db_store is None:
            raise RuntimeError("Database not enabled. Set db_enabled=True in SkillsConfig.")

        return self._db_store.skill_exists(name, app_name=self.config.app_name, version=version)
