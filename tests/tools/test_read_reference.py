"""Tests for the async read_reference tool."""

import pytest

from adk_skills_agent import SkillsRegistry
from adk_skills_agent.exceptions import SkillExecutionError, SkillNotFoundError
from adk_skills_agent.tools.read_reference import create_read_reference_tool


class TestCreateReadReferenceTool:
    """Tests for create_read_reference_tool."""

    def test_tool_creation(self):
        registry = SkillsRegistry()
        tool = create_read_reference_tool(registry)

        assert callable(tool)

    async def test_read_reference_success(self, tmp_path):
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test"
        )

        refs_dir = skill_dir / "references"
        refs_dir.mkdir()
        ref_file = refs_dir / "guide.md"
        ref_file.write_text("# Reference Guide\n\nThis is a guide.")

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        tool = create_read_reference_tool(registry)
        result = await tool("test-skill", "guide.md")

        assert result["content"] == "# Reference Guide\n\nThis is a guide."
        assert result["filename"] == "guide.md"
        # Locator is skill-root-relative, not an on-disk path.
        assert result["path"] == "references/guide.md"

    async def test_read_reference_skill_not_found(self):
        registry = SkillsRegistry()
        tool = create_read_reference_tool(registry)

        with pytest.raises(SkillNotFoundError):
            await tool("nonexistent-skill", "guide.md")

    async def test_read_reference_no_references_dir(self, tmp_path):
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test"
        )

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        tool = create_read_reference_tool(registry)

        # With generalized read_reference, a bare filename maps to
        # ``references/guide.md`` and the error is just "not found".
        with pytest.raises(SkillExecutionError, match="not found"):
            await tool("test-skill", "guide.md")

    async def test_read_reference_file_not_found(self, tmp_path):
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

        tool = create_read_reference_tool(registry)

        with pytest.raises(SkillExecutionError, match="guide.md"):
            await tool("test-skill", "nonexistent.md")

    async def test_read_reference_path_traversal_prevention(self, tmp_path):
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test"
        )
        refs_dir = skill_dir / "references"
        refs_dir.mkdir()

        outside_file = tmp_path / "secret.txt"
        outside_file.write_text("secret data")

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        tool = create_read_reference_tool(registry)

        with pytest.raises(SkillExecutionError, match="escapes skill directory"):
            await tool("test-skill", "../../secret.txt")

    async def test_read_reference_nested_path(self, tmp_path):
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test"
        )

        refs_dir = skill_dir / "references"
        nested_dir = refs_dir / "guides"
        nested_dir.mkdir(parents=True)
        nested_file = nested_dir / "intro.md"
        nested_file.write_text("Nested guide content")

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        tool = create_read_reference_tool(registry)
        result = await tool("test-skill", "guides/intro.md")

        assert result["content"] == "Nested guide content"
        assert result["filename"] == "intro.md"

    async def test_read_reference_from_registry_method(self, tmp_path):
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

        tool = registry.create_read_reference_tool()

        result = await tool("test-skill", "guide.md")
        assert result["content"] == "Guide content"
