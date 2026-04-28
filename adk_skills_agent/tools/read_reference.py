"""Read reference tool - read reference files from activated skills.

The factory returns an ``async def`` tool that ADK awaits on each invocation.
"""

from collections.abc import Awaitable
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from adk_skills_agent.registry import SkillsRegistry


def create_read_reference_tool(
    registry: "SkillsRegistry",
) -> Callable[[str, str], Awaitable[dict[str, Any]]]:
    """Create the async ADK tool for reading skill reference files.

    The tool delegates to :meth:`SkillsRegistry.read_reference`, which routes
    the request to whichever :class:`~adk_skills_agent.core.source.SkillSource`
    owns the named skill.

    Args:
        registry: Registry containing discovered skills.

    Returns:
        Async callable tool function for reading references.

    Example:
        >>> registry = SkillsRegistry()
        >>> registry.discover(["./skills"])
        >>> read_reference = registry.create_read_reference_tool()
        >>> result = await read_reference("web-scraper", "best_practices.md")
        >>> print(result["content"])
    """

    async def read_reference(skill: str, reference: str) -> dict[str, Any]:
        """Read a reference document from a skill.

        Args:
            skill: Name of the skill containing the reference.
            reference: Name of the reference file to read (e.g. ``"api_docs.md"``).

        Returns:
            Dict containing:

            - ``content``: Contents of the reference file.
            - ``path``: Opaque locator for the reference. For filesystem-backed
              skills this is the absolute path on disk; for other sources it
              may be a source-specific identifier.
            - ``filename``: Base filename of the reference.

        Raises:
            SkillNotFoundError: If the skill is not known to any source.
            SkillSourceCollisionError: If multiple sources expose the skill.
            SkillExecutionError: If the reference cannot be read.
        """
        result = await registry.read_reference(skill, reference)
        return {
            "content": result.content,
            "path": result.path,
            "filename": result.filename,
        }

    return read_reference
