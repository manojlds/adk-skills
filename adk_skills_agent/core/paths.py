"""Skill-root-relative path helpers.

The registry owns two small pieces of UX logic that every skill source used
to duplicate:

1. Mapping a ``read_reference`` input to a skill-root-relative path. Bare
   filenames (no ``/``) and legacy nested shapes like ``"guides/intro.md"``
   are resolved under ``references/`` for backwards compatibility; explicit
   prefixes (``references/``, ``assets/``, ``scripts/``) and the ``SKILL.md``
   filename pass through unchanged.
2. Rejecting paths that try to escape the skill package (absolute paths,
   ``..`` segments, leading slashes after normalisation, empty inputs).

Both pieces live here as stable, pure functions so downstream skill source
implementations (``ContentStudioRegistrySkillSource`` and friends) can reuse
them without reaching into the filesystem source.
"""

from __future__ import annotations

from adk_skills_agent.exceptions import SkillExecutionError

# Top-level entries that are honoured as skill-root-relative. Any reference
# path whose first segment is not one of these (and whose only segment is not
# ``SKILL.md``) is prefixed with ``references/`` for backwards compatibility
# with the classic ``read_reference("skill", "guide.md")`` / nested
# ``"guides/intro.md"`` call shapes.
_KNOWN_SKILL_ROOT_DIRS = frozenset({"references", "assets", "scripts"})
_KNOWN_SKILL_ROOT_FILES = frozenset({"SKILL.md"})


def normalize_skill_reference(reference: str) -> str:
    """Map a ``read_reference`` input to a skill-root-relative path.

    * ``"foo.md"`` -> ``"references/foo.md"`` (backwards compat)
    * ``"guides/intro.md"`` -> ``"references/guides/intro.md"`` (nested under references/)
    * ``"references/foo.md"`` -> unchanged
    * ``"assets/grammar.lark"`` -> unchanged
    * ``"scripts/run.sh"`` -> unchanged
    * ``"SKILL.md"`` -> unchanged
    * Backslashes are normalised to forward slashes; leading ``/`` stripped.

    Note:
        This function does **not** validate path safety. Call
        :func:`validate_skill_root_relative_path` on the returned value before
        reading files.

    Raises:
        SkillExecutionError: If ``reference`` is empty.
    """
    if not reference:
        raise SkillExecutionError("Empty reference is not allowed")

    normalized = reference.replace("\\", "/").lstrip("/")
    first_segment, _sep, _rest = normalized.partition("/")
    if first_segment in _KNOWN_SKILL_ROOT_DIRS:
        return normalized
    if normalized in _KNOWN_SKILL_ROOT_FILES:
        return normalized
    return f"references/{normalized}"


def validate_skill_root_relative_path(relative_path: str) -> str:
    """Validate ``relative_path`` and return it in canonical form.

    The returned path uses forward slashes and is guaranteed to contain no
    ``..`` segments or empty segments. ``.`` segments are removed. Callers
    that additionally need filesystem-level resolution (to follow symlinks,
    etc.) should layer their own checks on top.

    Raises:
        SkillExecutionError: If the path is empty, absolute (leading ``/`` or
            an OS-absolute form), or contains a ``..`` segment.
    """
    if not relative_path:
        raise SkillExecutionError("Empty path is not allowed")
    normalized = relative_path.replace("\\", "/")
    if normalized.startswith("/"):
        raise SkillExecutionError(f"Absolute paths are not allowed: {relative_path!r}")
    parts = normalized.split("/")
    if any(part in ("", "..") for part in parts):
        raise SkillExecutionError(f"Access denied: path escapes skill directory: {relative_path!r}")
    canonical_parts = [part for part in parts if part != "."]
    if not canonical_parts:
        raise SkillExecutionError("Empty path is not allowed")
    return "/".join(canonical_parts)


__all__ = [
    "normalize_skill_reference",
    "validate_skill_root_relative_path",
]
