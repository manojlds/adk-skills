"""Helper functions for common skills operations.

This module provides convenience functions for common tasks like adding
skills support to existing agents.
"""

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Optional, Union

from adk_skills_agent.core.models import SkillsConfig
from adk_skills_agent.registry import SkillsRegistry


def with_skills(
    agent: Any,
    directories: Sequence[Union[str, Path]],
    config: Optional[SkillsConfig] = None,
    include_script_tool: bool = True,
    include_reference_tool: bool = True,
) -> Any:
    """Add skills support to an existing ADK agent.

    This is a convenience function that:
    1. Creates a SkillsRegistry
    2. Discovers skills from the specified directories
    3. Creates and adds skill tools to the agent

    Args:
        agent: Existing google.adk.agents.Agent instance
        directories: List of directories to discover skills from
        config: Optional SkillsConfig for customization
        include_script_tool: Include run_script tool (default: True)
        include_reference_tool: Include read_reference tool (default: True)

    Returns:
        The agent with skills tools added

    Example:
        >>> from google.adk.agents import Agent
        >>> from adk_skills_agent import with_skills
        >>>
        >>> # Create a standard ADK agent
        >>> agent = Agent(
        ...     name="assistant",
        ...     model="gemini-2.5-flash",
        ...     instruction="You are a helpful assistant.",
        ... )
        >>>
        >>> # Add skills support
        >>> agent = with_skills(agent, ["./skills", "~/.adk/skills"])

    Note:
        This function assumes the agent has a `tools` attribute that can be
        modified. If your agent implementation differs, you may need to use
        SkillsRegistry directly.
    """
    # Create registry and discover skills
    registry = SkillsRegistry(config=config or SkillsConfig())
    registry.discover(directories)

    # Create tools
    tools = [registry.create_use_skill_tool()]

    if include_script_tool:
        tools.append(registry.create_run_script_tool())

    if include_reference_tool:
        tools.append(registry.create_read_reference_tool())

    # Add tools to agent
    if hasattr(agent, "tools"):
        if agent.tools is None:
            agent.tools = tools
        else:
            agent.tools.extend(tools)
    else:
        raise AttributeError(
            "Agent does not have a 'tools' attribute. "
            "Use SkillsRegistry directly to create tools."
        )

    return agent


def create_skills_agent(
    name: str,
    model: str,
    instruction: str = "",
    skills_directories: Optional[Sequence[Union[str, Path]]] = None,
    **kwargs: Any,
) -> Any:
    """Create an ADK agent with skills support in one call.

    This is a convenience function that combines agent creation with skills
    discovery. It's equivalent to creating a SkillsAgent and calling build().

    Args:
        name: Agent name
        model: Model identifier (e.g., "gemini-2.5-flash")
        instruction: System instruction/prompt
        skills_directories: Directories to discover skills from
        **kwargs: Additional arguments passed to SkillsAgent

    Returns:
        Configured google.adk.agents.Agent with skills support

    Example:
        >>> from adk_skills_agent import create_skills_agent
        >>>
        >>> agent = create_skills_agent(
        ...     name="assistant",
        ...     model="gemini-2.5-flash",
        ...     instruction="You are a helpful assistant.",
        ...     skills_directories=["./skills"],
        ... )

    Note:
        This requires google.adk to be installed.
    """
    from adk_skills_agent.agent import SkillsAgent

    skills_agent = SkillsAgent(
        name=name,
        model=model,
        instruction=instruction,
        skills_directories=skills_directories,
        **kwargs,
    )

    return skills_agent.build()


def inject_skills_prompt(
    instruction: str,
    directories: Sequence[Union[str, Path]],
    format: str = "xml",
    config: Optional[SkillsConfig] = None,
) -> str:
    """Inject skills listing into an instruction/system prompt.

    This helper discovers skills and appends them to an instruction string.
    Useful when you want to include skills in the system prompt rather than
    using the tool-based approach.

    Args:
        instruction: Base instruction/system prompt
        directories: Directories to discover skills from
        format: Output format - "xml" or "text" (default: "xml")
        config: Optional SkillsConfig for customization

    Returns:
        Instruction with skills listing appended

    Example:
        >>> from adk_skills_agent import inject_skills_prompt
        >>>
        >>> instruction = "You are a helpful assistant."
        >>> full_instruction = inject_skills_prompt(
        ...     instruction,
        ...     ["./skills"],
        ...     format="xml",
        ... )
        >>> print(full_instruction)
        You are a helpful assistant.

        <available_skills>
        ...
        </available_skills>
    """
    registry = SkillsRegistry(config=config or SkillsConfig())
    registry.discover(directories)

    if len(registry) == 0:
        return instruction

    skills_prompt = registry.get_skills_prompt(format=format)
    return f"{instruction}\n\n{skills_prompt}"
