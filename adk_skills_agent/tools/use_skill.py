"""Use skill tool - activate a skill on-demand."""

from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from adk_skills_agent.registry import SkillsRegistry


def generate_available_skills_xml(registry: "SkillsRegistry") -> str:
    """Generate <available_skills> XML block from registry metadata.

    Args:
        registry: SkillsRegistry instance with discovered skills

    Returns:
        XML string listing all available skills
    """
    skills_metadata = registry.list_metadata()

    if not skills_metadata:
        return "<available_skills>\nNo skills available.\n</available_skills>"

    xml_parts = ["<available_skills>"]

    for metadata in skills_metadata:
        xml_parts.append("  <skill>")
        xml_parts.append(f"    <name>{metadata.name}</name>")
        # Escape description for XML
        description = (
            metadata.description.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )
        xml_parts.append(f"    <description>{description}</description>")
        xml_parts.append("  </skill>")

    xml_parts.append("</available_skills>")

    return "\n".join(xml_parts)


def create_use_skill_tool(
    registry: "SkillsRegistry", include_skills_listing: bool = True
) -> Callable[[str], dict[str, Any]]:
    """Create ADK tool for skill activation.

    This tool enables on-demand skill activation. When include_skills_listing is True
    (default), the tool description contains an <available_skills> block listing all
    discovered skills. When False, the listing is omitted (useful when skills are
    injected into the system prompt instead).

    Args:
        registry: SkillsRegistry instance with discovered skills
        include_skills_listing: Whether to include <available_skills> XML in tool
            description (default: True). Set to False when using prompt injection.

    Returns:
        Callable tool function with optional skill listing in docstring

    Example:
        >>> registry = SkillsRegistry()
        >>> registry.discover(["./skills"])
        >>>
        >>> # Pattern 1: Tool-based (default) - skills in tool description
        >>> use_skill = create_use_skill_tool(registry)
        >>>
        >>> # Pattern 2: Prompt-based - skills in system prompt, not in tool
        >>> prompt = registry.to_prompt_xml()
        >>> use_skill = create_use_skill_tool(registry, include_skills_listing=False)
        >>> agent = Agent(instruction=f"...\\n{prompt}", tools=[use_skill])
    """

    def use_skill(name: str) -> dict[str, Any]:
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
            - base_directory: Path to the skill directory
            - has_scripts: Whether the skill has a scripts/ directory
            - has_references: Whether the skill has a references/ directory
            - has_assets: Whether the skill has an assets/ directory
        """
        # Load full skill on-demand
        skill = registry.load_skill(name)

        return {
            "skill_name": skill.name,
            "instructions": skill.instructions,
            "base_directory": str(skill.skill_dir),
            "has_scripts": skill.scripts_dir is not None,
            "has_references": skill.references_dir is not None,
            "has_assets": skill.assets_dir is not None,
        }

    # Generate XML and inject into docstring if requested
    if include_skills_listing:
        available_skills_xml = generate_available_skills_xml(registry)
    else:
        available_skills_xml = ""

    if use_skill.__doc__:
        use_skill.__doc__ = use_skill.__doc__.format(available_skills_xml=available_skills_xml)

    # Set function name for better debugging
    use_skill.__name__ = "use_skill"

    return use_skill
