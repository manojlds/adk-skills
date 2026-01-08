"""Tests for SKILL.md parser."""

from pathlib import Path

import pytest

from adk_skills_agent.core.models import Skill, SkillMetadata
from adk_skills_agent.core.parser import find_skill_md, parse_full, parse_metadata
from adk_skills_agent.exceptions import SkillParseError


class TestFindSkillMd:
    """Tests for find_skill_md function."""

    def test_find_uppercase_skill_md(self, skills_dir: Path) -> None:
        """Test finding SKILL.md (uppercase)."""
        skill_path = find_skill_md(skills_dir / "valid-skill")
        assert skill_path is not None
        assert skill_path.name == "SKILL.md"

    def test_find_lowercase_skill_md(self, tmp_path: Path) -> None:
        """Test finding skill.md (lowercase)."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "skill.md").write_text("---\nname: test\n---\n\nBody")

        skill_path = find_skill_md(skill_dir)
        assert skill_path is not None
        assert skill_path.name == "skill.md"

    def test_prefer_uppercase(self, tmp_path: Path) -> None:
        """Test preference for SKILL.md over skill.md."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: test1\n---\n\nBody1")
        (skill_dir / "skill.md").write_text("---\nname: test2\n---\n\nBody2")

        skill_path = find_skill_md(skill_dir)
        assert skill_path is not None
        assert skill_path.name == "SKILL.md"

    def test_not_found(self, tmp_path: Path) -> None:
        """Test returning None when SKILL.md not found."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()

        skill_path = find_skill_md(skill_dir)
        assert skill_path is None


class TestParseMetadata:
    """Tests for parse_metadata function."""

    def test_parse_from_file(self, skills_dir: Path) -> None:
        """Test parsing metadata from SKILL.md file path."""
        skill_path = skills_dir / "valid-skill" / "SKILL.md"
        metadata = parse_metadata(skill_path)

        assert isinstance(metadata, SkillMetadata)
        assert metadata.name == "valid-skill"
        assert metadata.description == "A valid test skill with all optional fields"
        assert metadata.license == "MIT"
        assert metadata.compatibility == "Requires Python 3.9+"
        assert metadata.allowed_tools == "bash python"
        assert metadata.location == skill_path

    def test_parse_from_directory(self, skills_dir: Path) -> None:
        """Test parsing metadata from skill directory."""
        skill_dir = skills_dir / "valid-skill"
        metadata = parse_metadata(skill_dir)

        assert isinstance(metadata, SkillMetadata)
        assert metadata.name == "valid-skill"
        assert metadata.location.name == "SKILL.md"

    def test_parse_minimal(self, skills_dir: Path) -> None:
        """Test parsing minimal metadata."""
        skill_path = skills_dir / "minimal-skill" / "SKILL.md"
        metadata = parse_metadata(skill_path)

        assert metadata.name == "minimal-skill"
        assert metadata.description == "A minimal test skill with only required fields"
        assert metadata.license is None
        assert metadata.compatibility is None

    def test_missing_name(self, tmp_path: Path) -> None:
        """Test error when name field is missing."""
        skill_path = tmp_path / "SKILL.md"
        skill_path.write_text("---\ndescription: Test\n---\n\nBody")

        with pytest.raises(SkillParseError, match="Missing required field 'name'"):
            parse_metadata(skill_path)

    def test_missing_description(self, tmp_path: Path) -> None:
        """Test error when description field is missing."""
        skill_path = tmp_path / "SKILL.md"
        skill_path.write_text("---\nname: test\n---\n\nBody")

        with pytest.raises(SkillParseError, match="Missing required field 'description'"):
            parse_metadata(skill_path)

    def test_empty_name(self, tmp_path: Path) -> None:
        """Test error when name is empty."""
        skill_path = tmp_path / "SKILL.md"
        skill_path.write_text("---\nname: ''\ndescription: Test\n---\n\nBody")

        with pytest.raises(SkillParseError, match="must be a non-empty string"):
            parse_metadata(skill_path)

    def test_skill_md_not_found(self, tmp_path: Path) -> None:
        """Test error when SKILL.md not found in directory."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()

        with pytest.raises(SkillParseError, match="SKILL.md not found"):
            parse_metadata(skill_dir)


class TestParseFull:
    """Tests for parse_full function."""

    def test_parse_full_from_file(self, skills_dir: Path) -> None:
        """Test parsing full skill from SKILL.md file path."""
        skill_path = skills_dir / "valid-skill" / "SKILL.md"
        skill = parse_full(skill_path)

        assert isinstance(skill, Skill)
        assert skill.name == "valid-skill"
        assert skill.description == "A valid test skill with all optional fields"
        assert skill.license == "MIT"
        assert skill.location == skill_path
        assert skill.skill_dir == skill_path.parent
        assert "# Valid Skill" in skill.instructions
        assert "## When to Use" in skill.instructions

    def test_parse_full_from_directory(self, skills_dir: Path) -> None:
        """Test parsing full skill from skill directory."""
        skill_dir = skills_dir / "valid-skill"
        skill = parse_full(skill_dir)

        assert skill.name == "valid-skill"
        assert skill.skill_dir == skill_dir
        assert skill.location.name == "SKILL.md"

    def test_parse_full_minimal(self, skills_dir: Path) -> None:
        """Test parsing minimal full skill."""
        skill_path = skills_dir / "minimal-skill" / "SKILL.md"
        skill = parse_full(skill_path)

        assert skill.name == "minimal-skill"
        assert (
            skill.instructions
            == "# Minimal Skill\n\nThis skill has only the required frontmatter fields."
        )
        assert skill.scripts_dir is None
        assert skill.references_dir is None
        assert skill.assets_dir is None

    def test_discover_directories(self, tmp_path: Path) -> None:
        """Test discovery of scripts/references/assets directories."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()

        # Create SKILL.md
        (skill_dir / "SKILL.md").write_text("---\nname: test\ndescription: Test\n---\n\nBody")

        # Create directories
        (skill_dir / "scripts").mkdir()
        (skill_dir / "references").mkdir()
        (skill_dir / "assets").mkdir()

        skill = parse_full(skill_dir)

        assert skill.scripts_dir == skill_dir / "scripts"
        assert skill.references_dir == skill_dir / "references"
        assert skill.assets_dir == skill_dir / "assets"

    def test_no_directories(self, skills_dir: Path) -> None:
        """Test skill without scripts/references/assets directories."""
        skill = parse_full(skills_dir / "minimal-skill")

        assert skill.scripts_dir is None
        assert skill.references_dir is None
        assert skill.assets_dir is None

    def test_convert_to_metadata(self, skills_dir: Path) -> None:
        """Test converting full skill to metadata."""
        skill = parse_full(skills_dir / "valid-skill")
        metadata = skill.to_metadata()

        assert isinstance(metadata, SkillMetadata)
        assert metadata.name == skill.name
        assert metadata.description == skill.description
        assert metadata.location == skill.location
        assert metadata.license == skill.license
