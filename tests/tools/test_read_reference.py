"""Tests for read_reference tool."""

import pytest

from adk_skills_agent import SkillsRegistry
from adk_skills_agent.exceptions import SkillExecutionError, SkillNotFoundError
from adk_skills_agent.tools.read_reference import create_read_reference_tool


class TestCreateReadReferenceTool:
    """Tests for create_read_reference_tool function."""

    def test_tool_creation(self):
        """Test that tool is created successfully."""
        registry = SkillsRegistry()
        tool = create_read_reference_tool(registry)

        assert callable(tool)

    def test_read_reference_success(self, tmp_path):
        """Test reading a reference file."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test"
        )

        # Create references directory with a file
        refs_dir = skill_dir / "references"
        refs_dir.mkdir()
        ref_file = refs_dir / "guide.md"
        ref_file.write_text("# Reference Guide\n\nThis is a guide.")

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        tool = create_read_reference_tool(registry)
        result = tool("test-skill", "guide.md")

        assert result["content"] == "# Reference Guide\n\nThis is a guide."
        assert result["filename"] == "guide.md"
        assert result["path"] == str(ref_file)

    def test_read_reference_skill_not_found(self):
        """Test error when skill doesn't exist."""
        registry = SkillsRegistry()
        tool = create_read_reference_tool(registry)

        with pytest.raises(SkillNotFoundError):
            tool("nonexistent-skill", "guide.md")

    def test_read_reference_no_references_dir(self, tmp_path):
        """Test error when skill has no references directory."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test"
        )

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        tool = create_read_reference_tool(registry)

        with pytest.raises(SkillExecutionError, match="no references/"):
            tool("test-skill", "guide.md")

    def test_read_reference_file_not_found(self, tmp_path):
        """Test error when reference file doesn't exist."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test"
        )
        (skill_dir / "references").mkdir()

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        tool = create_read_reference_tool(registry)

        with pytest.raises(SkillExecutionError, match="not found"):
            tool("test-skill", "nonexistent.md")

    def test_read_reference_path_traversal_prevention(self, tmp_path):
        """Test that path traversal is prevented."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test"
        )
        refs_dir = skill_dir / "references"
        refs_dir.mkdir()

        # Create a file outside the references directory
        outside_file = tmp_path / "secret.txt"
        outside_file.write_text("secret data")

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        tool = create_read_reference_tool(registry)

        # Try to access file outside references directory
        with pytest.raises(SkillExecutionError, match="escapes skill directory"):
            tool("test-skill", "../../secret.txt")

    def test_read_reference_from_registry_method(self, tmp_path):
        """Test creating tool via registry method."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test"
        )

        refs_dir = skill_dir / "references"
        refs_dir.mkdir()
        (refs_dir / "guide.md").write_text("Guide content")

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        # Create tool via registry method
        tool = registry.create_read_reference_tool()

        result = tool("test-skill", "guide.md")
        assert result["content"] == "Guide content"
