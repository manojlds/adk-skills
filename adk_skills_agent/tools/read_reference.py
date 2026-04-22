"""Read reference tool - read reference files from activated skills."""

from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from adk_skills_agent.registry import SkillsRegistry


def create_read_reference_tool(
    registry: "SkillsRegistry",
) -> Callable[[str, str], dict[str, Any]]:
    """Create ADK tool for reading skill reference files.

    The tool delegates to :meth:`SkillsRegistry.read_reference`, which routes
    the request to whichever :class:`~adk_skills_agent.core.source.SkillSource`
    owns the named skill.

    Args:
        registry: Registry containing discovered skills.

    Returns:
        Callable tool function for reading references.

    Example:
        >>> registry = SkillsRegistry()
        >>> registry.discover(["./skills"])
        >>> read_reference = create_read_reference_tool(registry)
        >>> result = read_reference("web-scraper", "best_practices.md")
        >>> print(result["content"])
    """

    def read_reference(skill: str, reference: str) -> dict[str, Any]:
        """Read a reference document from a skill.

        Args:
            skill: Name of the skill containing the reference.
            reference: Name of the reference file to read (e.g. ``"api_docs.md"``).

        Returns:
            Dict containing:

            - ``content``: Contents of the reference file.
            - ``path``: Skill-root-relative path for the reference
              (for example, ``"references/guide.md"``), consistent across
              all source types.
            - ``filename``: Base filename of the reference.

        Raises:
            SkillNotFoundError: If the skill is not known to any source.
            SkillSourceCollisionError: If multiple sources expose the skill.
            SkillExecutionError: If the reference cannot be read.
        """
        result = registry.read_reference(skill, reference)
        return {
            "content": result.content,
            "path": result.path,
            "filename": result.filename,
        }

    return read_reference
