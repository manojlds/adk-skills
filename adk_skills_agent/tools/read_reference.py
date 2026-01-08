"""Read reference tool - read reference files from activated skills."""

from typing import TYPE_CHECKING, Any, Callable

from adk_skills_agent.exceptions import SkillExecutionError, SkillNotFoundError

if TYPE_CHECKING:
    from adk_skills_agent.registry import SkillsRegistry


def create_read_reference_tool(
    registry: "SkillsRegistry",
) -> Callable[[str, str], dict[str, Any]]:
    """Create ADK tool for reading skill reference files.

    Args:
        registry: SkillsRegistry instance with discovered skills

    Returns:
        Callable tool function for reading references

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
            skill: Name of the skill containing the reference
            reference: Name of the reference file to read (e.g., "api_docs.md", "guide.txt")

        Returns:
            Dict containing:
            - content: Contents of the reference file
            - path: Full path to the reference file
            - filename: Name of the reference file

        Raises:
            SkillNotFoundError: If skill doesn't exist
            SkillExecutionError: If reference file cannot be read
        """
        # Load the skill to get its directory structure
        try:
            skill_obj = registry.load_skill(skill)
        except SkillNotFoundError as e:
            raise SkillNotFoundError(f"Skill '{skill}' not found. Cannot read reference.") from e

        # Check if skill has references directory
        if skill_obj.references_dir is None:
            raise SkillExecutionError(f"Skill '{skill}' has no references/ directory")

        # Validate reference exists
        reference_path = skill_obj.references_dir / reference

        # Prevent path traversal attacks
        try:
            reference_path = reference_path.resolve()
            if not reference_path.is_relative_to(skill_obj.references_dir.resolve()):
                raise SkillExecutionError("Access denied: reference path escapes skill directory")
        except (ValueError, OSError) as e:
            raise SkillExecutionError(f"Invalid reference path: {e}") from e

        if not reference_path.exists():
            available_refs = list(skill_obj.references_dir.glob("*"))
            raise SkillExecutionError(
                f"Reference '{reference}' not found in skill '{skill}'. "
                f"Available references: {[r.name for r in available_refs]}"
            )

        if not reference_path.is_file():
            raise SkillExecutionError(f"Reference '{reference}' is not a file")

        # Read the reference file
        try:
            content = reference_path.read_text(encoding="utf-8")
            return {
                "content": content,
                "path": str(reference_path),
                "filename": reference_path.name,
            }
        except Exception as e:
            raise SkillExecutionError(f"Failed to read reference '{reference}': {e}") from e

    return read_reference
