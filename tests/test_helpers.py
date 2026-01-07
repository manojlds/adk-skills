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
    """Tests for with_skills helper function."""

    def test_with_skills_adds_tools(self, tmp_path):
        """Test that with_skills adds tools to agent."""
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
        agent = with_skills(agent, [tmp_path])

        assert len(agent.tools) == 3  # use_skill, run_script, read_reference

    def test_with_skills_without_script_tool(self, tmp_path):
        """Test with_skills without script tool."""
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
        agent = with_skills(agent, [tmp_path], include_script_tool=False)

        assert len(agent.tools) == 2

    def test_with_skills_without_reference_tool(self, tmp_path):
        """Test with_skills without reference tool."""
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
        agent = with_skills(agent, [tmp_path], include_reference_tool=False)

        assert len(agent.tools) == 2

    def test_with_skills_with_custom_config(self, tmp_path):
        """Test with_skills with custom config."""
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
        agent = with_skills(agent, [tmp_path], config=config)

        assert len(agent.tools) == 3

    def test_with_skills_appends_to_existing_tools(self, tmp_path):
        """Test that with_skills appends to existing tools."""
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
        agent.tools = [lambda: "existing"]  # Add an existing tool

        agent = with_skills(agent, [tmp_path])

        assert len(agent.tools) == 4  # 1 existing + 3 new

    def test_with_skills_no_tools_attribute(self):
        """Test with_skills raises error for agent without tools attribute."""

        class BadAgent:
            pass

        agent = BadAgent()

        with pytest.raises(AttributeError, match="does not have a 'tools' attribute"):
            with_skills(agent, [])


class TestCreateSkillsAgent:
    """Tests for create_skills_agent helper function."""

    def test_create_skills_agent_requires_adk(self):
        """Test that create_skills_agent requires google.adk."""
        # This will raise ImportError since google.adk is not installed
        with pytest.raises(ImportError, match="google.adk is required"):
            create_skills_agent(
                name="test-agent",
                model="gemini-2.5-flash",
            )


class TestInjectSkillsPrompt:
    """Tests for inject_skills_prompt helper function."""

    def test_inject_skills_prompt_empty_directories(self, tmp_path):
        """Test inject_skills_prompt with no skills."""
        instruction = "You are helpful."
        result = inject_skills_prompt(instruction, [tmp_path])

        # Should not inject anything if no skills found
        assert result == instruction

    def test_inject_skills_prompt_with_skills_xml(self, tmp_path):
        """Test inject_skills_prompt with skills in XML format."""
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
        result = inject_skills_prompt(instruction, [tmp_path], format="xml")

        assert "You are helpful." in result
        assert "<available_skills>" in result
        assert "<name>my-skill</name>" in result

    def test_inject_skills_prompt_with_skills_text(self, tmp_path):
        """Test inject_skills_prompt with skills in text format."""
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
        result = inject_skills_prompt(instruction, [tmp_path], format="text")

        assert "You are helpful." in result
        assert "Available Skills:" in result
        assert "- my-skill: A test skill" in result

    def test_inject_skills_prompt_with_custom_config(self, tmp_path):
        """Test inject_skills_prompt with custom config."""
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
        result = inject_skills_prompt(instruction, [tmp_path], format="xml", config=config)

        assert "<available_skills>" in result
