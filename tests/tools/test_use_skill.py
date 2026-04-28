"""Tests for the async use_skill tool."""

import pytest

from adk_skills_agent import SkillsRegistry
from adk_skills_agent.exceptions import SkillNotFoundError
from adk_skills_agent.tools.use_skill import (
    create_use_skill_tool,
    generate_available_skills_xml,
)


class TestGenerateAvailableSkillsXml:
    """Tests for generate_available_skills_xml function."""

    async def test_empty_registry(self, tmp_path):
        registry = SkillsRegistry()
        xml = await generate_available_skills_xml(registry)

        assert "<available_skills>" in xml
        assert "No skills available" in xml
        assert "</available_skills>" in xml

    async def test_single_skill(self, tmp_path):
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test Skill"
        )

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        xml = await generate_available_skills_xml(registry)

        assert "<available_skills>" in xml
        assert "<skill>" in xml
        assert "<name>test-skill</name>" in xml
        assert "<description>A test skill</description>" in xml
        assert "</skill>" in xml
        assert "</available_skills>" in xml

    async def test_multiple_skills(self, tmp_path):
        skill1_dir = tmp_path / "skill-one"
        skill1_dir.mkdir()
        (skill1_dir / "SKILL.md").write_text(
            "---\nname: skill-one\ndescription: First skill\n---\n\n# Skill One"
        )

        skill2_dir = tmp_path / "skill-two"
        skill2_dir.mkdir()
        (skill2_dir / "SKILL.md").write_text(
            "---\nname: skill-two\ndescription: Second skill\n---\n\n# Skill Two"
        )

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        xml = await generate_available_skills_xml(registry)

        assert xml.count("<skill>") == 2
        assert "<name>skill-one</name>" in xml
        assert "<name>skill-two</name>" in xml
        assert "<description>First skill</description>" in xml
        assert "<description>Second skill</description>" in xml

    async def test_xml_escaping(self, tmp_path):
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: Test <tag> & special\n---\n\n# Test"
        )

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        xml = await generate_available_skills_xml(registry)

        assert "&lt;tag&gt;" in xml
        assert "&amp;" in xml
        assert "<tag>" not in xml


class TestCreateUseSkillTool:
    """Tests for the create_use_skill_tool factory."""

    def test_tool_creation(self, tmp_path):
        registry = SkillsRegistry()
        tool = create_use_skill_tool(registry)

        assert callable(tool)
        assert tool.__name__ == "use_skill"
        assert tool.__doc__ is not None

    async def test_tool_docstring_can_embed_pre_computed_listing(self, tmp_path):
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test"
        )

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        listing = await registry.to_prompt_xml()
        tool = create_use_skill_tool(registry, available_skills_xml=listing)

        assert "<available_skills>" in tool.__doc__
        assert "test-skill" in tool.__doc__
        assert "A test skill" in tool.__doc__

    async def test_tool_activates_skill(self, tmp_path):
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test Instructions"
        )

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        tool = create_use_skill_tool(registry)
        result = await tool("test-skill")

        assert result["skill_name"] == "test-skill"
        assert "Test Instructions" in result["instructions"]
        assert result["base_directory"] == str(skill_dir)
        assert result["has_scripts"] is False
        assert result["has_references"] is False
        assert result["has_assets"] is False

    async def test_tool_with_directories(self, tmp_path):
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "scripts").mkdir()
        (skill_dir / "references").mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test"
        )

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        tool = create_use_skill_tool(registry)
        result = await tool("test-skill")

        assert result["has_scripts"] is True
        assert result["has_references"] is True
        assert result["has_assets"] is False

    async def test_tool_raises_on_nonexistent_skill(self, tmp_path):
        registry = SkillsRegistry()

        tool = create_use_skill_tool(registry)

        with pytest.raises(SkillNotFoundError):
            await tool("nonexistent-skill")

    async def test_tool_from_registry_method(self, tmp_path):
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test"
        )

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        tool = registry.create_use_skill_tool()

        result = await tool("test-skill")
        assert result["skill_name"] == "test-skill"

    async def test_tool_without_listing_when_no_xml_passed(self, tmp_path):
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test"
        )

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        tool = create_use_skill_tool(registry)

        # No listing was passed, so the docstring shouldn't carry it.
        assert "<available_skills>" not in tool.__doc__
        assert "test-skill" not in tool.__doc__

        result = await tool("test-skill")
        assert result["skill_name"] == "test-skill"

    async def test_tool_listing_via_registry_method(self, tmp_path):
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test"
        )

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        listing = await registry.to_prompt_xml()
        tool_with = registry.create_use_skill_tool(available_skills_xml=listing)
        assert "<available_skills>" in tool_with.__doc__

        tool_without = registry.create_use_skill_tool()
        assert "<available_skills>" not in tool_without.__doc__
