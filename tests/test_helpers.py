"""Tests for helper functions."""

import pytest

from adk_skills_agent.core.models import SkillsConfig
from adk_skills_agent.helpers import (
    create_skills_agent,
    inject_skills_prompt,
    with_skills,
)


class MockAgent:
    """Mock agent for testing."""

    def __init__(self, name, model, **kwargs):
        self.name = name
        self.model = model
        self.tools = []
        self.kwargs = kwargs


class TestWithSkills:
    """Tests for the async with_skills helper."""

    async def test_with_skills_adds_tools(self, tmp_path):
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

        agent = MockAgent(name="test", model="gemini-2.5-flash")
        agent = await with_skills(agent, [tmp_path])

        assert len(agent.tools) == 2

    async def test_with_skills_without_reference_tool(self, tmp_path):
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

        agent = MockAgent(name="test", model="gemini-2.5-flash")
        agent = await with_skills(agent, [tmp_path], include_reference_tool=False)

        assert len(agent.tools) == 1

    async def test_with_skills_with_custom_config(self, tmp_path):
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

        config = SkillsConfig(strict_validation=False)
        agent = MockAgent(name="test", model="gemini-2.5-flash")
        agent = await with_skills(agent, [tmp_path], config=config)

        assert len(agent.tools) == 2

    async def test_with_skills_appends_to_existing_tools(self, tmp_path):
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

        agent = MockAgent(name="test", model="gemini-2.5-flash")
        agent.tools = [lambda: "existing"]

        agent = await with_skills(agent, [tmp_path])

        assert len(agent.tools) == 3

    async def test_with_skills_no_tools_attribute(self):
        class BadAgent:
            pass

        agent = BadAgent()

        with pytest.raises(AttributeError, match="does not have a 'tools' attribute"):
            await with_skills(agent, [])


class TestCreateSkillsAgent:
    """Tests for create_skills_agent."""

    async def test_create_skills_agent_requires_adk(self):
        with pytest.raises(ImportError, match="google.adk is required"):
            await create_skills_agent(
                name="test-agent",
                model="gemini-2.5-flash",
            )


class TestInjectSkillsPrompt:
    """Tests for the async inject_skills_prompt helper."""

    async def test_inject_skills_prompt_empty_directories(self, tmp_path):
        instruction = "You are helpful."
        result = await inject_skills_prompt(instruction, [tmp_path])

        assert result == instruction

    async def test_inject_skills_prompt_with_skills_xml(self, tmp_path):
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

        instruction = "You are helpful."
        result = await inject_skills_prompt(instruction, [tmp_path], format="xml")

        assert "You are helpful." in result
        assert "<available_skills>" in result
        assert "<name>my-skill</name>" in result

    async def test_inject_skills_prompt_with_skills_text(self, tmp_path):
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

        instruction = "You are helpful."
        result = await inject_skills_prompt(instruction, [tmp_path], format="text")

        assert "You are helpful." in result
        assert "Available Skills:" in result
        assert "- my-skill: A test skill" in result

    async def test_inject_skills_prompt_with_custom_config(self, tmp_path):
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

        config = SkillsConfig(strict_validation=False)
        instruction = "You are helpful."
        result = await inject_skills_prompt(instruction, [tmp_path], format="xml", config=config)

        assert "<available_skills>" in result

    async def test_inject_skills_prompt_with_registry(self, tmp_path):
        from adk_skills_agent.registry import SkillsRegistry

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

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        instruction = "You are helpful."
        result = await inject_skills_prompt(instruction, registry=registry, format="xml")

        assert "You are helpful." in result
        assert "<available_skills>" in result
        assert "<name>my-skill</name>" in result

    async def test_inject_skills_prompt_error_both_params(self, tmp_path):
        from adk_skills_agent.registry import SkillsRegistry

        registry = SkillsRegistry()
        instruction = "You are helpful."

        with pytest.raises(ValueError, match="Cannot specify both 'directories' and 'registry'"):
            await inject_skills_prompt(instruction, directories=[tmp_path], registry=registry)

    async def test_inject_skills_prompt_error_no_params(self):
        instruction = "You are helpful."

        with pytest.raises(ValueError, match="Must specify either 'directories' or 'registry'"):
            await inject_skills_prompt(instruction)
