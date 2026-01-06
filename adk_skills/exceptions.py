"""Custom exceptions for adk-skills."""


class SkillError(Exception):
    """Base exception for all skill-related errors."""

    pass


class SkillNotFoundError(SkillError):
    """Raised when a requested skill cannot be found."""

    pass


class SkillValidationError(SkillError):
    """Raised when skill validation fails."""

    pass


class SkillParseError(SkillError):
    """Raised when skill parsing fails."""

    pass


class SkillExecutionError(SkillError):
    """Raised when skill script execution fails."""

    pass


class SkillConfigError(SkillError):
    """Raised when skill configuration is invalid."""

    pass
