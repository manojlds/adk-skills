"""Tests for use_skill tool."""

import pytest

from adk_skills_agent import SkillsRegistry
from adk_skills_agent.exceptions import SkillNotFoundError
from adk_skills_agent.tools.use_skill import create_use_skill_tool, generate_available_skills_xml


class TestGenerateAvailableSkillsXml:
    """Tests for generate_available_skills_xml function."""

    def test_empty_registry(self, tmp_path):
        """Test XML generation with no skills."""
        registry = SkillsRegistry()
        xml = generate_available_skills_xml(registry)

        assert "<available_skills>" in xml
        assert "No skills available" in xml
        assert "</available_skills>" in xml

    def test_single_skill(self, tmp_path):
        """Test XML generation with one skill."""
        # Create a skill
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("---\nname: test-skill\ndescription: A test skill\n---\n\n# Test Skill")

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        xml = generate_available_skills_xml(registry)

        assert "<available_skills>" in xml
        assert "<skill>" in xml
        assert "<name>test-skill</name>" in xml
        assert "<description>A test skill</description>" in xml
        assert "</skill>" in xml
        assert "</available_skills>" in xml

    def test_multiple_skills(self, tmp_path):
        """Test XML generation with multiple skills."""
        # Create first skill
        skill1_dir = tmp_path / "skill-one"
        skill1_dir.mkdir()
        (skill1_dir / "SKILL.md").write_text(
            "---\nname: skill-one\ndescription: First skill\n---\n\n# Skill One"
        )

        # Create second skill
        skill2_dir = tmp_path / "skill-two"
        skill2_dir.mkdir()
        (skill2_dir / "SKILL.md").write_text(
            "---\nname: skill-two\ndescription: Second skill\n---\n\n# Skill Two"
        )

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        xml = generate_available_skills_xml(registry)

        assert xml.count("<skill>") == 2
        assert "<name>skill-one</name>" in xml
        assert "<name>skill-two</name>" in xml
        assert "<description>First skill</description>" in xml
        assert "<description>Second skill</description>" in xml

    def test_xml_escaping(self, tmp_path):
        """Test that special characters are escaped in XML."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            "---\nname: test-skill\ndescription: Test <tag> & special\n---\n\n# Test"
        )

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        xml = generate_available_skills_xml(registry)

        # Check that <, >, and & are escaped
        assert "&lt;tag&gt;" in xml
        assert "&amp;" in xml
        assert "<tag>" not in xml


class TestCreateUseSkillTool:
    """Tests for create_use_skill_tool function."""

    def test_tool_creation(self, tmp_path):
        """Test that tool is created successfully."""
        registry = SkillsRegistry()
        tool = create_use_skill_tool(registry)

        assert callable(tool)
        assert tool.__name__ == "use_skill"
        assert tool.__doc__ is not None

    def test_tool_docstring_includes_skills(self, tmp_path):
        """Test that tool docstring includes available skills."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test"
        )

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        tool = create_use_skill_tool(registry)

        # Check docstring contains the skill listing
        assert "<available_skills>" in tool.__doc__
        assert "test-skill" in tool.__doc__
        assert "A test skill" in tool.__doc__

    def test_tool_activates_skill(self, tmp_path):
        """Test that tool can activate a skill."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test Instructions"
        )

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        tool = create_use_skill_tool(registry)
        result = tool("test-skill")

        assert result["skill_name"] == "test-skill"
        assert "Test Instructions" in result["instructions"]
        assert result["base_directory"] == str(skill_dir)
        assert result["has_scripts"] is False
        assert result["has_references"] is False
        assert result["has_assets"] is False

    def test_tool_with_directories(self, tmp_path):
        """Test tool correctly reports skill directories."""
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
        result = tool("test-skill")

        assert result["has_scripts"] is True
        assert result["has_references"] is True
        assert result["has_assets"] is False

    def test_tool_raises_on_nonexistent_skill(self, tmp_path):
        """Test that tool raises error for nonexistent skill."""
        registry = SkillsRegistry()

        tool = create_use_skill_tool(registry)

        with pytest.raises(SkillNotFoundError):
            tool("nonexistent-skill")

    def test_tool_from_registry_method(self, tmp_path):
        """Test creating tool via registry method."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test"
        )

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        # Create tool via registry method
        tool = registry.create_use_skill_tool()

        result = tool("test-skill")
        assert result["skill_name"] == "test-skill"

    def test_tool_without_skills_listing(self, tmp_path):
        """Test creating tool without skills listing (for prompt injection)."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test"
        )

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        # Create tool without skills listing
        tool = create_use_skill_tool(registry, include_skills_listing=False)

        # Docstring should NOT contain <available_skills>
        assert "<available_skills>" not in tool.__doc__
        assert "test-skill" not in tool.__doc__

        # Tool should still work for activation
        result = tool("test-skill")
        assert result["skill_name"] == "test-skill"

    def test_tool_with_skills_listing_via_registry(self, tmp_path):
        """Test registry method supports include_skills_listing parameter."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test"
        )

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        # With listing (default)
        tool_with = registry.create_use_skill_tool(include_skills_listing=True)
        assert "<available_skills>" in tool_with.__doc__

        # Without listing
        tool_without = registry.create_use_skill_tool(include_skills_listing=False)
        assert "<available_skills>" not in tool_without.__doc__
