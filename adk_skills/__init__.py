"""ADK Skills - Agent Skills support for Google's Agent Development Kit.

This library enables ADK agents to discover and activate skills on-demand
using the standard Agent Skills format (agentskills.io).
"""

__version__ = "0.1.0"

# Core imports
from .core.models import Skill, SkillMetadata, SkillsConfig, ValidationResult
from .core.validator import validate_skill
from .exceptions import (
    SkillConfigError,
    SkillError,
    SkillExecutionError,
    SkillNotFoundError,
    SkillParseError,
    SkillValidationError,
)
from .registry import SkillsRegistry

__all__ = [
    "__version__",
    # Core classes
    "SkillsRegistry",
    "Skill",
    "SkillMetadata",
    "SkillsConfig",
    "ValidationResult",
    # Functions
    "validate_skill",
    # Exceptions
    "SkillError",
    "SkillNotFoundError",
    "SkillValidationError",
    "SkillParseError",
    "SkillExecutionError",
    "SkillConfigError",
]
