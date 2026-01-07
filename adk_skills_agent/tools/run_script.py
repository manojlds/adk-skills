"""Run script tool - execute scripts from activated skills."""

import subprocess
from typing import TYPE_CHECKING, Any, Callable, Optional

from adk_skills_agent.exceptions import SkillExecutionError, SkillNotFoundError

if TYPE_CHECKING:
    from adk_skills_agent.registry import SkillsRegistry


def create_run_script_tool(
    registry: "SkillsRegistry",
) -> Callable[[str, str, dict], dict[str, Any]]:
    """Create ADK tool for executing skill scripts.

    Args:
        registry: SkillsRegistry instance with discovered skills

    Returns:
        Callable tool function for script execution

    Example:
        >>> registry = SkillsRegistry()
        >>> registry.discover(["./skills"])
        >>> run_script = create_run_script_tool(registry)
        >>> result = run_script("calculator", "calculate.py", {"operation": "add", "a": 5, "b": 3})
    """

    def run_script(
        skill: str, script: str, args: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Execute a script from an activated skill.

        Args:
            skill: Name of the skill containing the script
            script: Name of the script file to execute (e.g., "process.py", "scrape.sh")
            args: Dictionary of arguments to pass to the script (optional)

        Returns:
            Dict containing:
            - stdout: Standard output from the script
            - stderr: Standard error from the script
            - returncode: Exit code of the script
            - success: Whether the script executed successfully

        Raises:
            SkillNotFoundError: If skill doesn't exist
            SkillExecutionError: If script execution fails
        """
        if args is None:
            args = {}

        # Load the skill to get its directory structure
        try:
            skill_obj = registry.load_skill(skill)
        except SkillNotFoundError as e:
            raise SkillNotFoundError(f"Skill '{skill}' not found. Cannot execute script.") from e

        # Check if skill has scripts directory
        if skill_obj.scripts_dir is None:
            raise SkillExecutionError(f"Skill '{skill}' has no scripts/ directory")

        # Validate script exists
        script_path = skill_obj.scripts_dir / script
        if not script_path.exists():
            available_scripts = list(skill_obj.scripts_dir.glob("*"))
            raise SkillExecutionError(
                f"Script '{script}' not found in skill '{skill}'. "
                f"Available scripts: {[s.name for s in available_scripts]}"
            )

        if not script_path.is_file():
            raise SkillExecutionError(f"Script '{script}' is not a file")

        # Get timeout from config
        timeout = registry.config.script_timeout

        try:
            # Execute the script
            # For Python scripts, pass args as JSON via stdin or environment
            # For now, use a simple subprocess call
            result = subprocess.run(
                [str(script_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=skill_obj.skill_dir,
            )

            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "success": result.returncode == 0,
            }

        except subprocess.TimeoutExpired as e:
            raise SkillExecutionError(f"Script '{script}' timed out after {timeout} seconds") from e
        except Exception as e:
            raise SkillExecutionError(f"Failed to execute script '{script}': {e}") from e

    return run_script
