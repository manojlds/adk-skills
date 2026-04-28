"""Helper functions for common skills operations.

This module provides convenience functions for common tasks like adding
skills support to existing agents. The runtime helpers
(:func:`with_skills`, :func:`create_skills_agent`,
:func:`inject_skills_prompt`) are async because the underlying
:class:`SkillsRegistry` API is async.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from adk_skills_agent.core.models import SkillsConfig
from adk_skills_agent.registry import SkillsRegistry


async def with_skills(
    agent: Any,
    directories: Sequence[str | Path],
    config: SkillsConfig | None = None,
    include_reference_tool: bool = True,
    auto_inject_prompt: bool = False,
    prompt_format: str = "xml",
) -> Any:
    """Add skills support to an existing ADK agent.

    Discovers skills synchronously, then awaits the registry's async
    helpers to build the ``use_skill`` tool description (and optionally
    inject the listing into the agent's instruction).

    Args:
        agent: Existing ``google.adk.agents.Agent`` instance.
        directories: List of directories to discover skills from.
        config: Optional ``SkillsConfig`` for customization.
        include_reference_tool: Include the ``read_reference`` tool
            (default: True).
        auto_inject_prompt: When ``True``, the discovered skills are
            appended to ``agent.instruction`` and the ``use_skill`` tool
            description omits the listing to avoid duplication.
        prompt_format: Format for prompt injection (``"xml"`` or
            ``"text"``).

    Returns:
        The agent with skills tools added.

    Example:
        >>> from google.adk.agents import Agent
        >>> from adk_skills_agent import with_skills
        >>>
        >>> agent = Agent(
        ...     name="assistant",
        ...     model="gemini-2.5-flash",
        ...     instruction="You are a helpful assistant.",
        ... )
        >>> agent = await with_skills(agent, ["./skills", "~/.adk/skills"])
    """
    registry = SkillsRegistry(config=config or SkillsConfig())
    registry.discover(directories)

    available_skills_xml: str | None = None
    if not auto_inject_prompt:
        available_skills_xml = await registry.to_prompt_xml()

    tools: list[Any] = [registry.create_use_skill_tool(available_skills_xml=available_skills_xml)]
    if include_reference_tool:
        tools.append(registry.create_read_reference_tool())

    if not hasattr(agent, "tools"):
        raise AttributeError(
            "Agent does not have a 'tools' attribute. Use SkillsRegistry directly to create tools."
        )

    if auto_inject_prompt and hasattr(agent, "instruction"):
        agent.instruction = await registry.inject_skills_prompt(
            agent.instruction or "", format=prompt_format
        )

    if agent.tools is None:
        agent.tools = tools
    else:
        agent.tools.extend(tools)

    return agent


async def create_skills_agent(
    name: str,
    model: str,
    instruction: str = "",
    skills_directories: Sequence[str | Path] | None = None,
    **kwargs: Any,
) -> Any:
    """Create an ADK agent with skills support in one async call.

    Args:
        name: Agent name.
        model: Model identifier (e.g., ``"gemini-2.5-flash"``).
        instruction: System instruction/prompt.
        skills_directories: Directories to discover skills from.
        **kwargs: Additional arguments passed to :class:`SkillsAgent`.

    Returns:
        Configured ``google.adk.agents.Agent`` with skills support.

    Example:
        >>> from adk_skills_agent import create_skills_agent
        >>>
        >>> agent = await create_skills_agent(
        ...     name="assistant",
        ...     model="gemini-2.5-flash",
        ...     instruction="You are a helpful assistant.",
        ...     skills_directories=["./skills"],
        ... )

    Note:
        Requires ``google.adk`` to be installed.
    """
    from adk_skills_agent.agent import SkillsAgent

    skills_agent = SkillsAgent(
        name=name,
        model=model,
        instruction=instruction,
        skills_directories=skills_directories,
        **kwargs,
    )
    return await skills_agent.build()


async def inject_skills_prompt(
    instruction: str,
    directories: Sequence[str | Path] | None = None,
    format: str = "xml",
    config: SkillsConfig | None = None,
    registry: SkillsRegistry | None = None,
) -> str:
    """Inject skills listing into an instruction/system prompt.

    Two usage patterns:

    1. Directory-based: Pass ``directories`` to discover skills (creates
       a temporary registry).
    2. Registry-based: Pass an existing :class:`SkillsRegistry` instance
       (more efficient).

    Args:
        instruction: Base instruction/system prompt.
        directories: Directories to discover skills from. Mutually
            exclusive with ``registry``.
        format: Output format - ``"xml"`` or ``"text"`` (default: ``"xml"``).
        config: Optional ``SkillsConfig`` (only used with ``directories``).
        registry: Optional existing :class:`SkillsRegistry` instance.
            Mutually exclusive with ``directories``.

    Returns:
        Instruction with skills listing appended.

    Raises:
        ValueError: If both or neither of ``directories`` / ``registry``
            are provided.
    """
    if directories is not None and registry is not None:
        raise ValueError("Cannot specify both 'directories' and 'registry'. Choose one.")
    if directories is None and registry is None:
        raise ValueError("Must specify either 'directories' or 'registry'.")

    if registry is not None:
        return await registry.inject_skills_prompt(instruction, format=format)

    assert directories is not None
    temp_registry = SkillsRegistry(config=config or SkillsConfig())
    temp_registry.discover(directories)
    return await temp_registry.inject_skills_prompt(instruction, format=format)
