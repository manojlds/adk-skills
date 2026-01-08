"""Tests for SkillsAgent class."""

import pytest

from adk_skills_agent.agent import SkillsAgent
from adk_skills_agent.core.models import SkillsConfig
from adk_skills_agent.exceptions import SkillConfigError


class TestSkillsAgentInit:
    """Tests for SkillsAgent initialization."""

    def test_init_minimal(self):
        """Test initialization with minimal parameters."""
        agent = SkillsAgent(
            name="test-agent",
            model="gemini-2.5-flash",
        )

        assert agent.name == "test-agent"
        assert agent.model == "gemini-2.5-flash"
        assert agent.instruction == ""
        assert len(agent.registry) == 0

    def test_init_with_instruction(self):
        """Test initialization with instruction."""
        agent = SkillsAgent(
            name="test-agent",
            model="gemini-2.5-flash",
            instruction="You are helpful.",
        )

        assert agent.instruction == "You are helpful."

    def test_init_with_skills_directories(self, tmp_path):
        """Test initialization with skills directories."""
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

        assert len(agent.registry) == 1

    def test_init_with_custom_config(self):
        """Test initialization with custom skills config."""
        config = SkillsConfig(strict_validation=False)
        agent = SkillsAgent(
            name="test-agent",
            model="gemini-2.5-flash",
            skills_config=config,
        )

        assert agent.registry.config == config


class TestSkillsAgentDiscoverSkills:
    """Tests for discover_skills method."""

    def test_discover_skills(self, tmp_path):
        """Test discovering skills."""
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
        assert len(agent.registry) == 1

    def test_discover_skills_with_validation_error(self, tmp_path):
        """Test that validation errors raise SkillConfigError."""
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
            validate_skills=True,
        )

        with pytest.raises(SkillConfigError):
            agent.discover_skills([tmp_path])

    def test_discover_skills_without_validation(self, tmp_path):
        """Test discovering skills without validation."""
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
            validate_skills=False,
        )

        count = agent.discover_skills([tmp_path])
        assert count == 1


class TestSkillsAgentGetTools:
    """Tests for get_tools method."""

    def test_get_tools_default(self, tmp_path):
        """Test getting tools with default configuration."""
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

        tools = agent.get_tools()
        assert len(tools) == 3  # use_skill, run_script, read_reference

    def test_get_tools_without_script_tool(self, tmp_path):
        """Test getting tools without script tool."""
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
            include_script_tool=False,
        )

        tools = agent.get_tools()
        assert len(tools) == 2  # use_skill, read_reference

    def test_get_tools_without_reference_tool(self, tmp_path):
        """Test getting tools without reference tool."""
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

        tools = agent.get_tools()
        assert len(tools) == 2  # use_skill, run_script

    def test_get_tools_minimal(self):
        """Test getting tools with minimal tools."""
        agent = SkillsAgent(
            name="test-agent",
            model="gemini-2.5-flash",
            include_script_tool=False,
            include_reference_tool=False,
        )

        tools = agent.get_tools()
        assert len(tools) == 1  # only use_skill

    def test_get_tools_without_listing_when_auto_inject(self, tmp_path):
        """Test that use_skill tool doesn't include listing when auto_inject_prompt=True."""
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

        # Without auto_inject_prompt (default) - should have listing
        agent_without = SkillsAgent(
            name="test-agent",
            model="gemini-2.5-flash",
            skills_directories=[tmp_path],
            auto_inject_prompt=False,
        )
        tools_without = agent_without.get_tools()
        assert "<available_skills>" in tools_without[0].__doc__

        # With auto_inject_prompt - should NOT have listing
        agent_with = SkillsAgent(
            name="test-agent",
            model="gemini-2.5-flash",
            skills_directories=[tmp_path],
            auto_inject_prompt=True,
        )
        tools_with = agent_with.get_tools()
        assert "<available_skills>" not in tools_with[0].__doc__


class TestSkillsAgentGetInstruction:
    """Tests for get_instruction method."""

    def test_get_instruction_basic(self):
        """Test getting basic instruction."""
        agent = SkillsAgent(
            name="test-agent",
            model="gemini-2.5-flash",
            instruction="You are helpful.",
        )

        instruction = agent.get_instruction()
        assert instruction == "You are helpful."

    def test_get_instruction_with_auto_inject(self, tmp_path):
        """Test getting instruction with auto prompt injection."""
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

        instruction = agent.get_instruction()
        assert "You are helpful." in instruction
        assert "<available_skills>" in instruction

    def test_get_instruction_with_text_format(self, tmp_path):
        """Test getting instruction with text format injection."""
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

        instruction = agent.get_instruction()
        assert "Available Skills:" in instruction

    def test_get_instruction_no_injection_without_skills(self):
        """Test that instruction doesn't include injection without skills."""
        agent = SkillsAgent(
            name="test-agent",
            model="gemini-2.5-flash",
            instruction="You are helpful.",
            auto_inject_prompt=True,
        )

        instruction = agent.get_instruction()
        assert instruction == "You are helpful."


class TestSkillsAgentBuild:
    """Tests for build method."""

    def test_build_requires_adk(self):
        """Test that build raises ImportError without google.adk."""
        agent = SkillsAgent(
            name="test-agent",
            model="gemini-2.5-flash",
        )

        # This will raise ImportError since google.adk is not installed in tests
        with pytest.raises(ImportError, match="google.adk is required"):
            agent.build()


class TestSkillsAgentRepr:
    """Tests for string representation."""

    def test_repr_without_skills(self):
        """Test string representation without skills."""
        agent = SkillsAgent(
            name="test-agent",
            model="gemini-2.5-flash",
        )

        repr_str = repr(agent)
        assert "test-agent" in repr_str
        assert "gemini-2.5-flash" in repr_str
        assert "skills=0" in repr_str

    def test_repr_with_skills(self, tmp_path):
        """Test string representation with skills."""
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

        repr_str = repr(agent)
        assert "skills=1" in repr_str
