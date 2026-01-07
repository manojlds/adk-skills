"""Custom agent class with tight skills integration for Google ADK.

This module provides SkillsAgent, a custom agent class that integrates
skills discovery, validation, and tools into a single convenient interface.
"""

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Optional, Union

from adk_skills_agent.core.models import SkillsConfig
from adk_skills_agent.exceptions import SkillConfigError
from adk_skills_agent.registry import SkillsRegistry


class SkillsAgent:
    """Custom agent wrapper with tight skills integration.

    This class provides a convenient way to create ADK agents with skills
    support built-in. It manages skills discovery, validation, and tool
    creation automatically.

    Example:
        >>> from google.adk.agents import Agent
        >>> from adk_skills_agent import SkillsAgent
        >>>
        >>> # Create agent with skills
        >>> skills_agent = SkillsAgent(
        ...     name="assistant",
        ...     model="gemini-2.5-flash",
        ...     instruction="You are a helpful assistant.",
        ...     skills_directories=["./skills"],
        ... )
        >>>
        >>> # Get the configured ADK agent
        >>> agent = skills_agent.build()

    Attributes:
        registry: The SkillsRegistry managing discovered skills
        agent_config: Configuration dict for the ADK agent
    """

    def __init__(
        self,
        name: str,
        model: str,
        instruction: str = "",
        skills_directories: Optional[Sequence[Union[str, Path]]] = None,
        skills_config: Optional[SkillsConfig] = None,
        include_script_tool: bool = True,
        include_reference_tool: bool = True,
        validate_skills: bool = True,
        auto_inject_prompt: bool = False,
        prompt_format: str = "xml",
        **agent_kwargs: Any,
    ):
        """Initialize SkillsAgent.

        Args:
            name: Agent name
            model: Model identifier (e.g., "gemini-2.5-flash")
            instruction: System instruction/prompt for the agent
            skills_directories: Directories to discover skills from
            skills_config: Optional SkillsConfig for customization
            include_script_tool: Include run_script tool (default: True)
            include_reference_tool: Include read_reference tool (default: True)
            validate_skills: Validate skills on discovery (default: True)
            auto_inject_prompt: Inject skills into system prompt (default: False)
            prompt_format: Format for prompt injection - "xml" or "text" (default: "xml")
            **agent_kwargs: Additional arguments to pass to Agent constructor

        Example:
            >>> agent = SkillsAgent(
            ...     name="assistant",
            ...     model="gemini-2.5-flash",
            ...     instruction="You are a helpful assistant.",
            ...     skills_directories=["./skills", "~/.adk/skills"],
            ...     validate_skills=True,
            ... )
        """
        self.name = name
        self.model = model
        self.instruction = instruction
        self.skills_directories = skills_directories or []
        self.include_script_tool = include_script_tool
        self.include_reference_tool = include_reference_tool
        self.validate_skills = validate_skills
        self.auto_inject_prompt = auto_inject_prompt
        self.prompt_format = prompt_format
        self.agent_kwargs = agent_kwargs

        # Create registry config
        # Always disable strict_validation in registry so we can discover all skills
        # and validate them in the agent if needed
        if skills_config is None:
            skills_config = SkillsConfig(strict_validation=False)

        self.registry = SkillsRegistry(config=skills_config)

        if self.skills_directories:
            self.discover_skills(self.skills_directories)

    def discover_skills(self, directories: Sequence[Union[str, Path]]) -> int:
        """Discover skills from directories.

        Args:
            directories: List of directories to scan

        Returns:
            Number of skills discovered

        Raises:
            SkillConfigError: If validation fails and validate_skills is True
        """
        count = self.registry.discover(directories)

        if self.validate_skills:
            results = self.registry.validate_all(strict=True)
            invalid = [name for name, result in results.items() if not result.valid]
            if invalid:
                raise SkillConfigError(
                    f"Invalid skills found: {invalid}. "
                    "Set validate_skills=False to skip validation."
                )

        return count

    def get_tools(self) -> list[Any]:
        """Get all configured tools for this agent.

        When auto_inject_prompt is True, the use_skill tool will not include
        the <available_skills> listing in its description to avoid duplication.

        Returns:
            List of tool functions (use_skill, run_script, read_reference)

        Example:
            >>> agent = SkillsAgent(name="assistant", model="gemini-2.5-flash")
            >>> tools = agent.get_tools()
            >>> print(f"Created {len(tools)} tools")
        """
        # Don't include skills listing in tool if we're injecting it into prompt
        include_listing = not self.auto_inject_prompt

        tools = [self.registry.create_use_skill_tool(include_skills_listing=include_listing)]

        if self.include_script_tool:
            tools.append(self.registry.create_run_script_tool())

        if self.include_reference_tool:
            tools.append(self.registry.create_read_reference_tool())

        return tools

    def get_instruction(self) -> str:
        """Get the instruction/system prompt for the agent.

        If auto_inject_prompt is True, appends skills listing to the instruction.

        Returns:
            Complete instruction string

        Example:
            >>> agent = SkillsAgent(
            ...     name="assistant",
            ...     model="gemini-2.5-flash",
            ...     instruction="You are helpful.",
            ...     auto_inject_prompt=True,
            ... )
            >>> print(agent.get_instruction())
        """
        instruction = self.instruction

        if self.auto_inject_prompt and len(self.registry) > 0:
            skills_prompt = self.registry.get_skills_prompt(format=self.prompt_format)
            instruction = f"{instruction}\n\n{skills_prompt}"

        return instruction

    def build(self) -> Any:
        """Build and return an ADK Agent with skills support.

        Returns:
            Configured google.adk.agents.Agent instance

        Raises:
            ImportError: If google.adk is not installed

        Example:
            >>> from adk_skills_agent import SkillsAgent
            >>> skills_agent = SkillsAgent(
            ...     name="assistant",
            ...     model="gemini-2.5-flash",
            ...     skills_directories=["./skills"],
            ... )
            >>> agent = skills_agent.build()
            >>> # Use agent normally with ADK
        """
        try:
            from google.adk.agents import Agent  # type: ignore
        except ImportError as e:
            raise ImportError(
                "google.adk is required to build agents. " "Install it with: pip install google-adk"
            ) from e

        return Agent(
            name=self.name,
            model=self.model,
            instruction=self.get_instruction(),
            tools=self.get_tools(),
            **self.agent_kwargs,
        )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"SkillsAgent(name={self.name!r}, model={self.model!r}, "
            f"skills={len(self.registry)})"
        )
