"""Core data models for Agent Skills."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class SkillMetadata:
    """Lightweight metadata for skill discovery (~50-100 tokens).

    This is parsed during discovery from SKILL.md frontmatter only.
    Used to populate <available_skills> in tool descriptions.

    Attributes:
        name: Skill identifier (required, lowercase, hyphens, max 64 chars)
        description: What the skill does and when to use it (required, max 1024 chars)
        location: Absolute path to the SKILL.md file
        license: License information (optional)
        compatibility: Environment requirements (optional, max 500 chars)
        allowed_tools: Space-delimited list of pre-approved tools (optional, experimental)
        metadata: Additional key-value metadata (optional)
    """

    name: str
    description: str
    location: Path

    # Optional frontmatter fields
    license: Optional[str] = None
    compatibility: Optional[str] = None
    allowed_tools: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        result: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "location": str(self.location),
        }
        if self.license is not None:
            result["license"] = self.license
        if self.compatibility is not None:
            result["compatibility"] = self.compatibility
        if self.allowed_tools is not None:
            result["allowed_tools"] = self.allowed_tools
        if self.metadata:
            result["metadata"] = self.metadata
        return result


@dataclass
class Skill:
    """Full skill with content (loaded on-demand when activated).

    This is parsed when an agent activates a skill via use_skill tool.
    Contains complete instructions and directory structure.

    Attributes:
        name: Skill identifier
        description: What the skill does
        location: Path to SKILL.md file
        skill_dir: Base directory of the skill
        instructions: Full markdown body content (from SKILL.md)

        # Optional frontmatter fields
        license: License information
        compatibility: Environment requirements
        allowed_tools: Pre-approved tools list
        metadata: Additional metadata

        # Directory structure (discovered lazily)
        scripts_dir: Path to scripts/ directory if it exists
        references_dir: Path to references/ directory if it exists
        assets_dir: Path to assets/ directory if it exists
    """

    # Required fields
    name: str
    description: str
    location: Path
    skill_dir: Path
    instructions: str

    # Optional frontmatter fields
    license: Optional[str] = None
    compatibility: Optional[str] = None
    allowed_tools: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # Directory structure (lazy-loaded)
    scripts_dir: Optional[Path] = None
    references_dir: Optional[Path] = None
    assets_dir: Optional[Path] = None

    def to_metadata(self) -> SkillMetadata:
        """Convert to lightweight metadata representation."""
        return SkillMetadata(
            name=self.name,
            description=self.description,
            location=self.location,
            license=self.license,
            compatibility=self.compatibility,
            allowed_tools=self.allowed_tools,
            metadata=self.metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "location": str(self.location),
            "skill_dir": str(self.skill_dir),
            "instructions": self.instructions,
        }
        if self.license is not None:
            result["license"] = self.license
        if self.compatibility is not None:
            result["compatibility"] = self.compatibility
        if self.allowed_tools is not None:
            result["allowed_tools"] = self.allowed_tools
        if self.metadata:
            result["metadata"] = self.metadata
        if self.scripts_dir is not None:
            result["scripts_dir"] = str(self.scripts_dir)
        if self.references_dir is not None:
            result["references_dir"] = str(self.references_dir)
        if self.assets_dir is not None:
            result["assets_dir"] = str(self.assets_dir)
        return result


@dataclass
class SkillsConfig:
    """Configuration for skills system.

    Attributes:
        skills_directories: List of directories to scan for skills
        auto_discover: Automatically discover skills on initialization
        enable_scripts: Allow script execution
        script_timeout: Maximum script execution time in seconds
        sandbox_mode: Run scripts in sandboxed environment
        strict_validation: Enforce strict spec validation
        allow_experimental: Allow experimental features (e.g., allowed-tools)
    """

    skills_directories: list[Path] = field(default_factory=list)
    auto_discover: bool = True
    enable_scripts: bool = True
    script_timeout: int = 30
    sandbox_mode: bool = True
    strict_validation: bool = True
    allow_experimental: bool = False


@dataclass
class ValidationResult:
    """Result of skill validation.

    Attributes:
        valid: Whether the skill passed validation
        skill_path: Path to the validated skill
        errors: List of validation errors
        warnings: List of validation warnings
    """

    valid: bool
    skill_path: Path
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        """Add a validation error."""
        self.errors.append(message)
        self.valid = False

    def add_warning(self, message: str) -> None:
        """Add a validation warning."""
        self.warnings.append(message)

    def __bool__(self) -> bool:
        """Return True if validation passed."""
        return self.valid
