"""ADK Skills - Agent Skills support for Google's Agent Development Kit.

This library enables ADK agents to discover and activate skills on-demand
using the standard Agent Skills format (agentskills.io).

Starting in 0.2.0, the library ships a pluggable
:class:`~adk_skills_agent.core.source.SkillSource` abstraction. The registry
composes one or more sources; the built-in
:class:`~adk_skills_agent.sources.filesystem.FilesystemSkillSource` covers
directory-based skills, and applications plug in their own sources (database
schemas, remote registries, object storage, …) via
:meth:`SkillsRegistry.add_source`. Any source can implement
:meth:`SkillSource.list_files` / :meth:`SkillSource.read_file` to surface
references, assets, and any other files in a skill package (text or binary).
Reference-path normalisation and the text-only ``read_reference`` wrapper
live on the registry, so custom sources only need to implement raw
:meth:`SkillSource.read_file`.

Starting in 0.4.0, all runtime read methods on :class:`SkillSource` and
:class:`SkillsRegistry` are coroutines, so I/O-bound sources (databases,
remote registries) can perform real non-blocking I/O. Construction and
filesystem discovery remain synchronous setup-time helpers; only runtime
catalog/file access requires ``await``.
"""

__version__ = "0.4.0"

from .agent import SkillsAgent
from .core.models import Skill, SkillMetadata, SkillsConfig, ValidationResult
from .core.paths import normalize_skill_reference, validate_skill_root_relative_path
from .core.source import ReferenceFile, SkillFile, SkillSource
from .core.validator import validate_skill
from .exceptions import (
    SkillConfigError,
    SkillError,
    SkillExecutionError,
    SkillNotFoundError,
    SkillParseError,
    SkillSourceCollisionError,
    SkillValidationError,
)
from .helpers import create_skills_agent, inject_skills_prompt, with_skills
from .registry import SkillsRegistry
from .sources.filesystem import FilesystemSkillSource

__all__ = [
    "__version__",
    # Core classes
    "SkillsRegistry",
    "Skill",
    "SkillMetadata",
    "SkillsConfig",
    "ValidationResult",
    # Source abstraction
    "SkillSource",
    "ReferenceFile",
    "SkillFile",
    "FilesystemSkillSource",
    # Path helpers for custom source authors
    "normalize_skill_reference",
    "validate_skill_root_relative_path",
    # Agent integration
    "SkillsAgent",
    # Helper functions
    "with_skills",
    "create_skills_agent",
    "inject_skills_prompt",
    "validate_skill",
    # Exceptions
    "SkillError",
    "SkillNotFoundError",
    "SkillValidationError",
    "SkillParseError",
    "SkillExecutionError",
    "SkillConfigError",
    "SkillSourceCollisionError",
]
