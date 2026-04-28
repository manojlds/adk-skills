"""Custom agent class with tight skills integration for Google ADK.

This module provides SkillsAgent, a convenience builder that wires a
:class:`~adk_skills_agent.registry.SkillsRegistry` into an ADK
``LlmAgent``/``Agent``. Discovery (:meth:`SkillsAgent.discover_skills`) is
synchronous because it only walks the local filesystem, but
:meth:`SkillsAgent.build` is asynchronous so it can call into the
async :class:`SkillsRegistry` API for validation, prompt injection, and
tool wiring.
"""

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Optional, Union

from adk_skills_agent.core.models import SkillsConfig
from adk_skills_agent.exceptions import SkillConfigError
from adk_skills_agent.registry import SkillsRegistry


class SkillsAgent:
    """Convenience builder that pairs an ADK agent with a skills registry.

    Construction is synchronous and only does setup-time work (filesystem
    discovery via the registry). The async :meth:`build` method runs
    validation, optional prompt injection, and tool creation against the
    registry's async API and returns a fully wired
    :class:`google.adk.agents.Agent`.

    Example:
        >>> from adk_skills_agent import SkillsAgent
        >>>
        >>> skills_agent = SkillsAgent(
        ...     name="assistant",
        ...     model="gemini-2.5-flash",
        ...     instruction="You are a helpful assistant.",
        ...     skills_directories=["./skills"],
        ... )
        >>> agent = await skills_agent.build()

    Attributes:
        registry: The SkillsRegistry managing discovered skills
    """

    def __init__(
        self,
        name: str,
        model: str,
        instruction: str = "",
        skills_directories: Optional[Sequence[Union[str, Path]]] = None,
        skills_config: Optional[SkillsConfig] = None,
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
            include_reference_tool: Include read_reference tool (default: True)
            validate_skills: Validate skills during :meth:`build` (default: True)
            auto_inject_prompt: Inject skills into the system prompt during
                :meth:`build` (default: False). When True, the use_skill tool
                description omits the listing to avoid duplication.
            prompt_format: Format for prompt injection - "xml" or "text"
                (default: "xml")
            **agent_kwargs: Additional arguments to pass to the ADK Agent
                constructor.
        """
        self.name = name
        self.model = model
        self.instruction = instruction
        self.skills_directories = skills_directories or []
        self.include_reference_tool = include_reference_tool
        self.validate_skills = validate_skills
        self.auto_inject_prompt = auto_inject_prompt
        self.prompt_format = prompt_format
        self.agent_kwargs = agent_kwargs

        # Always disable strict_validation in registry so we can discover all
        # skills and validate them in build() if requested.
        if skills_config is None:
            skills_config = SkillsConfig(strict_validation=False)

        self.registry = SkillsRegistry(config=skills_config)

        if self.skills_directories:
            self.discover_skills(self.skills_directories)

    def discover_skills(self, directories: Sequence[Union[str, Path]]) -> int:
        """Discover skills from directories.

        This is the synchronous filesystem walk; runtime/validation work
        happens later in :meth:`build`.

        Args:
            directories: List of directories to scan.

        Returns:
            Number of skills discovered.
        """
        return self.registry.discover(directories)

    async def get_tools(self) -> list[Any]:
        """Get the configured tools for this agent.

        When ``auto_inject_prompt`` is ``True``, the ``use_skill`` tool's
        description omits the ``<available_skills>`` listing because it is
        already in the system prompt.

        Returns:
            List of async tool callables (use_skill, read_reference).
        """
        available_skills_xml: str | None = None
        if not self.auto_inject_prompt:
            available_skills_xml = await self.registry.to_prompt_xml()

        tools: list[Any] = [
            self.registry.create_use_skill_tool(available_skills_xml=available_skills_xml)
        ]
        if self.include_reference_tool:
            tools.append(self.registry.create_read_reference_tool())
        return tools

    async def get_instruction(self) -> str:
        """Get the instruction/system prompt for the agent.

        If ``auto_inject_prompt`` is ``True``, appends the skills listing.
        """
        if not self.auto_inject_prompt:
            return self.instruction
        return await self.registry.inject_skills_prompt(self.instruction, format=self.prompt_format)

    async def build(self) -> Any:
        """Build and return an ADK Agent with skills support.

        Performs validation (if requested), prompt injection (if requested),
        and tool wiring against the async registry API.

        Returns:
            Configured ``google.adk.agents.Agent`` instance.

        Raises:
            ImportError: If ``google.adk`` is not installed.
            SkillConfigError: If validation fails and ``validate_skills`` is
                ``True``.
        """
        if self.validate_skills:
            results = await self.registry.validate_all(strict=True)
            invalid = [name for name, result in results.items() if not result.valid]
            if invalid:
                raise SkillConfigError(
                    f"Invalid skills found: {invalid}. "
                    "Set validate_skills=False to skip validation."
                )

        try:
            from google.adk.agents import Agent  # type: ignore
        except ImportError as e:
            raise ImportError(
                "google.adk is required to build agents. Install it with: pip install google-adk"
            ) from e

        instruction = await self.get_instruction()
        tools = await self.get_tools()

        return Agent(
            name=self.name,
            model=self.model,
            instruction=instruction,
            tools=tools,
            **self.agent_kwargs,
        )

    def __repr__(self) -> str:
        """String representation."""
        return f"SkillsAgent(name={self.name!r}, model={self.model!r})"
