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


class SkillSourceCollisionError(SkillError):
    """Raised when multiple skill sources expose the same skill name.

    Collisions are treated as configuration errors: the registry refuses to
    resolve them silently because the "winner" would otherwise depend on the
    order in which sources were registered. Callers should rename one of the
    conflicting skills or restrict the sources they compose.
    """

    pass
