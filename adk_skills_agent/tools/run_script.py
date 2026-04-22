"""Run script tool - execute scripts from activated skills."""

from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from adk_skills_agent.registry import SkillsRegistry


def create_run_script_tool(
    registry: "SkillsRegistry",
) -> Callable[[str, str, Optional[dict[str, Any]]], dict[str, Any]]:
    """Create ADK tool for executing skill scripts.

    The tool delegates to :meth:`SkillsRegistry.run_script`, which dispatches
    to whichever :class:`~adk_skills_agent.core.source.SkillSource` owns the
    named skill. Sources that do not support script execution (anything that
    cannot materialise scripts on disk — most database- or object-storage-
    backed sources) surface a
    :class:`~adk_skills_agent.exceptions.SkillExecutionError`.

    Args:
        registry: Registry containing discovered skills.

    Returns:
        Callable tool function for script execution.

    Example:
        >>> registry = SkillsRegistry()
        >>> registry.discover(["./skills"])
        >>> run_script = create_run_script_tool(registry)
        >>> result = run_script("calculator", "calculate.py", {"a": 5, "b": 3})
    """

    def run_script(
        skill: str,
        script: str,
        args: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Execute a script from an activated skill.

        Args:
            skill: Name of the skill containing the script.
            script: Name of the script file to execute.
            args: Dictionary of arguments to pass to the script (optional).

        Returns:
            Dict containing:

            - ``stdout``: Standard output from the script.
            - ``stderr``: Standard error from the script.
            - ``returncode``: Exit code of the script.
            - ``success``: Whether the script executed successfully.

        Raises:
            SkillNotFoundError: If the skill is not known to any source.
            SkillSourceCollisionError: If multiple sources expose the skill.
            SkillExecutionError: If the owning source cannot execute the script.
        """
        result = registry.run_script(skill, script, args)
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "success": result.success,
        }

    return run_script
