"""Tests for SkillsAgent class."""

import pytest

from adk_skills_agent.agent import SkillsAgent
from adk_skills_agent.core.models import SkillsConfig
from adk_skills_agent.exceptions import SkillConfigError


class TestSkillsAgentInit:
    """Tests for SkillsAgent initialization."""

    def test_init_minimal(self):
        agent = SkillsAgent(
            name="test-agent",
            model="gemini-2.5-flash",
        )

        assert agent.name == "test-agent"
        assert agent.model == "gemini-2.5-flash"
        assert agent.instruction == ""

    def test_init_with_instruction(self):
        agent = SkillsAgent(
            name="test-agent",
            model="gemini-2.5-flash",
            instruction="You are helpful.",
        )

        assert agent.instruction == "You are helpful."

    async def test_init_with_skills_directories(self, tmp_path):
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: my-skill
description: A test skill
---

Instructions.
"""
        )

        agent = SkillsAgent(
            name="test-agent",
            model="gemini-2.5-flash",
            skills_directories=[tmp_path],
        )

        names = [meta.name for meta in await agent.registry.list_metadata()]
        assert names == ["my-skill"]

    def test_init_with_custom_config(self):
        config = SkillsConfig(strict_validation=True)
        agent = SkillsAgent(
            name="test-agent",
            model="gemini-2.5-flash",
            skills_config=config,
        )

        assert agent.registry.config == config


class TestSkillsAgentDiscoverSkills:
    """Tests for discover_skills method."""

    async def test_discover_skills(self, tmp_path):
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: my-skill
description: A test skill
---

Instructions.
"""
        )

        agent = SkillsAgent(
            name="test-agent",
            model="gemini-2.5-flash",
        )

        count = agent.discover_skills([tmp_path])
        assert count == 1
        names = [meta.name for meta in await agent.registry.list_metadata()]
        assert names == ["my-skill"]

    async def test_build_raises_validation_error(self, tmp_path):
        # Validation now runs during build(), so the discover step itself
        # is permissive. Build surfaces the failure.
        skill_dir = tmp_path / "invalid-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: Invalid_Name
description: A test skill
---

Instructions.
"""
        )

        agent = SkillsAgent(
            name="test-agent",
            model="gemini-2.5-flash",
            skills_directories=[tmp_path],
            validate_skills=True,
        )

        # build() raises when google.adk is not installed in tests, but the
        # validation error fires first.
        with pytest.raises(SkillConfigError):
            await agent.build()

    async def test_build_skips_validation_when_disabled(self, tmp_path):
        skill_dir = tmp_path / "invalid-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: Invalid_Name
description: A test skill
---

Instructions.
"""
        )

        agent = SkillsAgent(
            name="test-agent",
            model="gemini-2.5-flash",
            skills_directories=[tmp_path],
            validate_skills=False,
        )

        # No SkillConfigError; we hit the ImportError because google.adk is
        # not installed in the test environment.
        with pytest.raises(ImportError, match="google.adk is required"):
            await agent.build()


class TestSkillsAgentGetTools:
    """Tests for get_tools method."""

    async def test_get_tools_default(self, tmp_path):
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: my-skill
description: A test skill
---

Instructions.
"""
        )

        agent = SkillsAgent(
            name="test-agent",
            model="gemini-2.5-flash",
            skills_directories=[tmp_path],
        )

        tools = await agent.get_tools()
        assert len(tools) == 2

    async def test_get_tools_without_reference_tool(self, tmp_path):
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: my-skill
description: A test skill
---

Instructions.
"""
        )

        agent = SkillsAgent(
            name="test-agent",
            model="gemini-2.5-flash",
            skills_directories=[tmp_path],
            include_reference_tool=False,
        )

        tools = await agent.get_tools()
        assert len(tools) == 1

    async def test_get_tools_minimal(self):
        agent = SkillsAgent(
            name="test-agent",
            model="gemini-2.5-flash",
            include_reference_tool=False,
        )

        tools = await agent.get_tools()
        assert len(tools) == 1

    async def test_get_tools_listing_swap_when_auto_inject(self, tmp_path):
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: my-skill
description: A test skill
---

Instructions.
"""
        )

        agent_without = SkillsAgent(
            name="test-agent",
            model="gemini-2.5-flash",
            skills_directories=[tmp_path],
            auto_inject_prompt=False,
        )
        tools_without = await agent_without.get_tools()
        assert "<available_skills>" in tools_without[0].__doc__

        agent_with = SkillsAgent(
            name="test-agent",
            model="gemini-2.5-flash",
            skills_directories=[tmp_path],
            auto_inject_prompt=True,
        )
        tools_with = await agent_with.get_tools()
        assert "<available_skills>" not in tools_with[0].__doc__


class TestSkillsAgentGetInstruction:
    """Tests for get_instruction method."""

    async def test_get_instruction_basic(self):
        agent = SkillsAgent(
            name="test-agent",
            model="gemini-2.5-flash",
            instruction="You are helpful.",
        )

        instruction = await agent.get_instruction()
        assert instruction == "You are helpful."

    async def test_get_instruction_with_auto_inject(self, tmp_path):
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: my-skill
description: A test skill
---

Instructions.
"""
        )

        agent = SkillsAgent(
            name="test-agent",
            model="gemini-2.5-flash",
            instruction="You are helpful.",
            skills_directories=[tmp_path],
            auto_inject_prompt=True,
        )

        instruction = await agent.get_instruction()
        assert "You are helpful." in instruction
        assert "<available_skills>" in instruction

    async def test_get_instruction_with_text_format(self, tmp_path):
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: my-skill
description: A test skill
---

Instructions.
"""
        )

        agent = SkillsAgent(
            name="test-agent",
            model="gemini-2.5-flash",
            instruction="You are helpful.",
            skills_directories=[tmp_path],
            auto_inject_prompt=True,
            prompt_format="text",
        )

        instruction = await agent.get_instruction()
        assert "Available Skills:" in instruction

    async def test_get_instruction_no_injection_without_skills(self):
        agent = SkillsAgent(
            name="test-agent",
            model="gemini-2.5-flash",
            instruction="You are helpful.",
            auto_inject_prompt=True,
        )

        instruction = await agent.get_instruction()
        assert instruction == "You are helpful."


class TestSkillsAgentBuild:
    """Tests for build method."""

    async def test_build_requires_adk(self):
        agent = SkillsAgent(
            name="test-agent",
            model="gemini-2.5-flash",
        )

        with pytest.raises(ImportError, match="google.adk is required"):
            await agent.build()


class TestSkillsAgentRepr:
    """Tests for string representation."""

    def test_repr_includes_name_and_model(self):
        agent = SkillsAgent(
            name="test-agent",
            model="gemini-2.5-flash",
        )

        repr_str = repr(agent)
        assert "test-agent" in repr_str
        assert "gemini-2.5-flash" in repr_str
