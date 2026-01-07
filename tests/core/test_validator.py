"""Tests for skill validator module."""

import pytest

from adk_skills_agent.core.models import Skill, SkillMetadata, ValidationResult
from adk_skills_agent.core.validator import (
    validate_skill,
    validate_skill_compatibility,
    validate_skill_description,
    validate_skill_directory,
    validate_skill_metadata,
    validate_skill_name,
)


class TestValidateSkillName:
    """Tests for validate_skill_name function."""

    def test_valid_name(self):
        """Test validation of valid skill names."""
        valid_names = [
            "my-skill",
            "skill-123",
            "test",
            "a",
            "skill-with-many-hyphens",
            "123-numbers",
        ]
        for name in valid_names:
            errors = validate_skill_name(name)
            assert errors == [], f"Expected '{name}' to be valid"

    def test_empty_name(self):
        """Test validation of empty name."""
        errors = validate_skill_name("")
        assert len(errors) == 1
        assert "cannot be empty" in errors[0]

    def test_name_too_long(self):
        """Test validation of name exceeding 64 characters."""
        long_name = "a" * 65
        errors = validate_skill_name(long_name)
        assert len(errors) == 1
        assert "too long" in errors[0]
        assert "64" in errors[0]

    def test_name_starts_with_hyphen(self):
        """Test validation of name starting with hyphen."""
        errors = validate_skill_name("-invalid")
        assert any("cannot start or end with hyphen" in err for err in errors)

    def test_name_ends_with_hyphen(self):
        """Test validation of name ending with hyphen."""
        errors = validate_skill_name("invalid-")
        assert any("cannot start or end with hyphen" in err for err in errors)

    def test_name_with_uppercase(self):
        """Test validation of name with uppercase letters."""
        errors = validate_skill_name("MySkill")
        assert any("lowercase" in err for err in errors)

    def test_name_with_spaces(self):
        """Test validation of name with spaces."""
        errors = validate_skill_name("my skill")
        assert any("lowercase letters, numbers, and hyphens" in err for err in errors)

    def test_name_with_underscores(self):
        """Test validation of name with underscores."""
        errors = validate_skill_name("my_skill")
        assert any("lowercase letters, numbers, and hyphens" in err for err in errors)

    def test_name_with_special_characters(self):
        """Test validation of name with special characters."""
        invalid_names = ["my@skill", "skill!", "test.skill", "skill/name"]
        for name in invalid_names:
            errors = validate_skill_name(name)
            assert len(errors) > 0, f"Expected '{name}' to be invalid"


class TestValidateSkillDescription:
    """Tests for validate_skill_description function."""

    def test_valid_description(self):
        """Test validation of valid descriptions."""
        valid_descriptions = [
            "A simple description",
            "Description with numbers 123",
            "A" * 1024,  # Max length
        ]
        for desc in valid_descriptions:
            errors = validate_skill_description(desc)
            assert errors == [], "Expected description to be valid"

    def test_empty_description(self):
        """Test validation of empty description."""
        errors = validate_skill_description("")
        assert len(errors) == 1
        assert "cannot be empty" in errors[0]

    def test_whitespace_only_description(self):
        """Test validation of whitespace-only description."""
        errors = validate_skill_description("   \n\t  ")
        assert len(errors) == 1
        assert "cannot be empty" in errors[0]

    def test_description_too_long(self):
        """Test validation of description exceeding 1024 characters."""
        long_desc = "a" * 1025
        errors = validate_skill_description(long_desc)
        assert len(errors) == 1
        assert "too long" in errors[0]
        assert "1024" in errors[0]


class TestValidateSkillCompatibility:
    """Tests for validate_skill_compatibility function."""

    def test_valid_compatibility(self):
        """Test validation of valid compatibility strings."""
        valid_compat = [
            "Python 3.9+",
            "Requires Docker",
            "A" * 500,  # Max length
        ]
        for compat in valid_compat:
            errors = validate_skill_compatibility(compat)
            assert errors == []

    def test_empty_compatibility(self):
        """Test validation of empty compatibility (should be valid)."""
        errors = validate_skill_compatibility("")
        assert errors == []

    def test_none_compatibility(self):
        """Test validation of None compatibility (should be valid)."""
        errors = validate_skill_compatibility("")
        assert errors == []

    def test_compatibility_too_long(self):
        """Test validation of compatibility exceeding 500 characters."""
        long_compat = "a" * 501
        errors = validate_skill_compatibility(long_compat)
        assert len(errors) == 1
        assert "too long" in errors[0]
        assert "500" in errors[0]


class TestValidateSkillMetadata:
    """Tests for validate_skill_metadata function."""

    def test_valid_metadata(self, tmp_path):
        """Test validation of valid metadata."""
        metadata = SkillMetadata(
            name="valid-skill",
            description="A valid skill",
            location=tmp_path / "SKILL.md",
        )

        result = validate_skill_metadata(metadata, strict=False)
        assert result.valid
        assert len(result.errors) == 0

    def test_metadata_with_invalid_name(self, tmp_path):
        """Test validation of metadata with invalid name."""
        metadata = SkillMetadata(
            name="Invalid_Name",
            description="A skill",
            location=tmp_path / "SKILL.md",
        )

        result = validate_skill_metadata(metadata, strict=False)
        assert not result.valid
        assert len(result.errors) > 0
        assert any("lowercase" in err for err in result.errors)

    def test_metadata_with_invalid_description(self, tmp_path):
        """Test validation of metadata with invalid description."""
        metadata = SkillMetadata(
            name="valid-skill",
            description="",
            location=tmp_path / "SKILL.md",
        )

        result = validate_skill_metadata(metadata, strict=False)
        assert not result.valid
        assert any("description" in err.lower() for err in result.errors)

    def test_metadata_with_invalid_compatibility(self, tmp_path):
        """Test validation of metadata with invalid compatibility."""
        metadata = SkillMetadata(
            name="valid-skill",
            description="A skill",
            location=tmp_path / "SKILL.md",
            compatibility="a" * 501,
        )

        result = validate_skill_metadata(metadata, strict=False)
        assert not result.valid
        assert any("compatibility" in err.lower() for err in result.errors)

    def test_strict_mode_warns_missing_license(self, tmp_path):
        """Test strict mode warns about missing license."""
        metadata = SkillMetadata(
            name="valid-skill",
            description="A skill",
            location=tmp_path / "SKILL.md",
        )

        result = validate_skill_metadata(metadata, strict=True)
        assert result.valid  # Still valid, just warnings
        assert any("license" in warn.lower() for warn in result.warnings)

    def test_strict_mode_warns_missing_compatibility(self, tmp_path):
        """Test strict mode warns about missing compatibility."""
        metadata = SkillMetadata(
            name="valid-skill",
            description="A skill",
            location=tmp_path / "SKILL.md",
        )

        result = validate_skill_metadata(metadata, strict=True)
        assert result.valid
        assert any("compatibility" in warn.lower() for warn in result.warnings)

    def test_non_strict_mode_no_warnings(self, tmp_path):
        """Test non-strict mode doesn't warn about missing optional fields."""
        metadata = SkillMetadata(
            name="valid-skill",
            description="A skill",
            location=tmp_path / "SKILL.md",
        )

        result = validate_skill_metadata(metadata, strict=False)
        assert result.valid
        assert len(result.warnings) == 0


class TestValidateSkillDirectory:
    """Tests for validate_skill_directory function."""

    def test_valid_skill_directory(self, tmp_path):
        """Test validation of valid skill directory."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            """---
name: my-skill
description: A valid skill
---

Instructions.
"""
        )

        result = validate_skill_directory(skill_dir, strict=False)
        assert result.valid
        assert len(result.errors) == 0

    def test_skill_directory_missing_skill_md(self, tmp_path):
        """Test validation when SKILL.md is missing."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()

        result = validate_skill_directory(skill_dir, strict=False)
        assert not result.valid
        assert any("SKILL.md not found" in err for err in result.errors)

    def test_skill_directory_warns_missing_scripts(self, tmp_path):
        """Test validation warns about missing scripts directory."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            """---
name: my-skill
description: A skill
---

Instructions.
"""
        )

        result = validate_skill_directory(skill_dir, strict=False)
        assert result.valid
        assert any("scripts" in warn.lower() for warn in result.warnings)

    def test_skill_directory_warns_missing_references(self, tmp_path):
        """Test validation warns about missing references directory."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            """---
name: my-skill
description: A skill
---

Instructions.
"""
        )

        result = validate_skill_directory(skill_dir, strict=False)
        assert result.valid
        assert any("references" in warn.lower() for warn in result.warnings)

    def test_skill_directory_with_complete_structure(self, tmp_path):
        """Test validation of directory with complete structure."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            """---
name: my-skill
description: A skill
---

Instructions.
"""
        )

        # Create recommended directories
        (skill_dir / "scripts").mkdir()
        (skill_dir / "references").mkdir()

        result = validate_skill_directory(skill_dir, strict=False)
        assert result.valid
        assert len(result.warnings) == 0

    def test_validate_skill_md_file_directly(self, tmp_path):
        """Test validation passing SKILL.md file directly."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            """---
name: my-skill
description: A skill
---

Instructions.
"""
        )

        # Pass file path instead of directory
        result = validate_skill_directory(skill_md, strict=False)
        assert result.valid


class TestValidateSkill:
    """Tests for validate_skill convenience function."""

    def test_validate_path(self, tmp_path):
        """Test validating a Path object."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            """---
name: my-skill
description: A skill
---

Instructions.
"""
        )

        result = validate_skill(skill_dir, strict=False)
        assert result.valid

    def test_validate_metadata(self, tmp_path):
        """Test validating a SkillMetadata object."""
        metadata = SkillMetadata(
            name="valid-skill",
            description="A skill",
            location=tmp_path / "SKILL.md",
        )

        result = validate_skill(metadata, strict=False)
        assert result.valid

    def test_validate_skill_object(self, tmp_path):
        """Test validating a Skill object."""
        skill = Skill(
            name="valid-skill",
            description="A skill",
            location=tmp_path / "SKILL.md",
            skill_dir=tmp_path,
            instructions="Instructions here",
        )

        result = validate_skill(skill, strict=False)
        assert result.valid

    def test_validate_invalid_type(self):
        """Test validating an invalid type raises TypeError."""
        with pytest.raises(TypeError):
            validate_skill("not-a-valid-type")

    def test_validate_invalid_skill(self, tmp_path):
        """Test validating an invalid skill."""
        metadata = SkillMetadata(
            name="Invalid Name",
            description="",
            location=tmp_path / "SKILL.md",
        )

        result = validate_skill(metadata, strict=False)
        assert not result.valid
        assert len(result.errors) > 0


class TestValidationResult:
    """Tests for ValidationResult model."""

    def test_validation_result_defaults(self, tmp_path):
        """Test ValidationResult default values."""
        result = ValidationResult(valid=True, skill_path=tmp_path)
        assert result.valid
        assert result.skill_path == tmp_path
        assert result.errors == []
        assert result.warnings == []

    def test_add_error(self, tmp_path):
        """Test adding errors to ValidationResult."""
        result = ValidationResult(valid=True, skill_path=tmp_path)
        result.add_error("Test error")

        assert not result.valid
        assert "Test error" in result.errors

    def test_add_warning(self, tmp_path):
        """Test adding warnings to ValidationResult."""
        result = ValidationResult(valid=True, skill_path=tmp_path)
        result.add_warning("Test warning")

        assert result.valid  # Warnings don't affect validity
        assert "Test warning" in result.warnings
