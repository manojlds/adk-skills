"""ADK Skills - Agent Skills support for Google's Agent Development Kit.

This library enables ADK agents to discover and activate skills on-demand
using the standard Agent Skills format (agentskills.io).
"""

__version__ = "0.1.0"

# Core imports
# Agent and helpers
from .agent import SkillsAgent
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
from .helpers import create_skills_agent, inject_skills_prompt, with_skills
from .registry import SkillsRegistry

__all__ = [
    "__version__",
    # Core classes
    "SkillsRegistry",
    "Skill",
    "SkillMetadata",
    "SkillsConfig",
    "ValidationResult",
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
]
