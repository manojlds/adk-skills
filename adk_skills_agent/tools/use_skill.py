"""Use skill tool - activate a skill on-demand.

The factory returns an ``async def`` tool. ADK natively awaits async tool
callables, so registering it on an :class:`~google.adk.agents.LlmAgent`
yields a fully non-blocking skill-activation path.
"""

from collections.abc import Awaitable
from typing import TYPE_CHECKING, Any, Callable

from adk_skills_agent.registry import _format_metadata_xml

if TYPE_CHECKING:
    from adk_skills_agent.registry import SkillsRegistry


async def generate_available_skills_xml(registry: "SkillsRegistry") -> str:
    """Generate the ``<available_skills>`` XML block from registry metadata.

    Use this once at agent setup if you want to bake the listing into the
    ``use_skill`` tool description::

        listing = await registry.to_prompt_xml()
        tool = registry.create_use_skill_tool(available_skills_xml=listing)

    or pair it with prompt injection (:meth:`SkillsRegistry.inject_skills_prompt`)
    and leave ``available_skills_xml=None`` so the listing is sourced from the
    system prompt instead.

    Args:
        registry: SkillsRegistry instance with discovered skills.

    Returns:
        XML string listing all available skills.
    """
    return _format_metadata_xml(await registry.list_metadata())


def create_use_skill_tool(
    registry: "SkillsRegistry",
    *,
    available_skills_xml: str | None = None,
) -> Callable[[str], Awaitable[dict[str, Any]]]:
    """Create the async ADK tool for skill activation.

    The returned tool is an ``async def`` coroutine. When invoked, it loads
    the requested skill from whichever :class:`SkillSource` owns it and
    returns the full instructions plus directory hints.

    Args:
        registry: SkillsRegistry instance with discovered skills.
        available_skills_xml: Optional pre-computed listing block to embed in
            the tool docstring. Pass the result of
            ``await registry.to_prompt_xml()`` if you want the listing inside
            the tool description; pass ``None`` (default) when relying on
            prompt injection so the listing isn't duplicated.

    Returns:
        Async callable tool function with optional skill listing in docstring.

    Example:
        Pattern 1 — listing in the tool description::

            listing = await registry.to_prompt_xml()
            use_skill = registry.create_use_skill_tool(available_skills_xml=listing)

        Pattern 2 — listing in the system prompt::

            prompt = await registry.inject_skills_prompt(base_prompt)
            use_skill = registry.create_use_skill_tool()
            agent = LlmAgent(instruction=prompt, tools=[use_skill])
    """

    async def use_skill(name: str) -> dict[str, Any]:
        """Load a skill to get detailed instructions for a specific task.

        Skills provide specialized knowledge and step-by-step guidance.
        Use this when a task matches an available skill's description.

        {available_skills_xml}

        Args:
            name: The skill identifier to activate

        Returns:
            Dict containing:
            - skill_name: Name of the activated skill
            - instructions: Full markdown instructions from SKILL.md
            - base_directory: Path to the skill directory (resolve references/, scripts/, assets/)
            - has_scripts: Whether the skill has a scripts/ directory
            - has_references: Whether the skill has a references/ directory
            - has_assets: Whether the skill has an assets/ directory
        """
        skill = await registry.load_skill(name)

        return {
            "skill_name": skill.name,
            "instructions": skill.instructions,
            "base_directory": str(skill.skill_dir),
            "has_scripts": skill.scripts_dir is not None,
            "has_references": skill.references_dir is not None,
            "has_assets": skill.assets_dir is not None,
        }

    if use_skill.__doc__:
        use_skill.__doc__ = use_skill.__doc__.format(
            available_skills_xml=available_skills_xml or ""
        )

    use_skill.__name__ = "use_skill"

    return use_skill
