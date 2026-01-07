"""Tests for run_script tool."""

import pytest

from adk_skills_agent import SkillsRegistry
from adk_skills_agent.exceptions import SkillExecutionError, SkillNotFoundError
from adk_skills_agent.tools.run_script import create_run_script_tool


class TestCreateRunScriptTool:
    """Tests for create_run_script_tool function."""

    def test_tool_creation(self):
        """Test that tool is created successfully."""
        registry = SkillsRegistry()
        tool = create_run_script_tool(registry)

        assert callable(tool)

    def test_run_script_skill_not_found(self):
        """Test error when skill doesn't exist."""
        registry = SkillsRegistry()
        tool = create_run_script_tool(registry)

        with pytest.raises(SkillNotFoundError):
            tool("nonexistent-skill", "script.py")

    def test_run_script_no_scripts_dir(self, tmp_path):
        """Test error when skill has no scripts directory."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test"
        )

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        tool = create_run_script_tool(registry)

        with pytest.raises(SkillExecutionError, match="no scripts/"):
            tool("test-skill", "script.py")

    def test_run_script_script_not_found(self, tmp_path):
        """Test error when script doesn't exist."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test"
        )
        (skill_dir / "scripts").mkdir()

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        tool = create_run_script_tool(registry)

        with pytest.raises(SkillExecutionError, match="not found"):
            tool("test-skill", "nonexistent.py")

    def test_run_script_success(self, tmp_path):
        """Test successful script execution."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test"
        )

        # Create scripts directory with a simple script
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        script_file = scripts_dir / "hello.sh"
        script_file.write_text("#!/bin/bash\necho 'Hello World'")
        script_file.chmod(0o755)

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        tool = create_run_script_tool(registry)
        result = tool("test-skill", "hello.sh")

        assert result["success"] is True
        assert result["returncode"] == 0
        assert "Hello World" in result["stdout"]

    def test_run_script_from_registry_method(self, tmp_path):
        """Test creating tool via registry method."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test"
        )

        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        script_file = scripts_dir / "test.sh"
        script_file.write_text("#!/bin/bash\necho 'test'")
        script_file.chmod(0o755)

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        # Create tool via registry method
        tool = registry.create_run_script_tool()

        result = tool("test-skill", "test.sh")
        assert result["success"] is True
