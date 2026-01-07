"""Tests for skill discovery module."""

from adk_skills_agent.core.discovery import discover_skills
from adk_skills_agent.core.models import SkillMetadata


def test_discover_skills_empty_directory(tmp_path):
    """Test discovery in empty directory."""
    result = discover_skills([tmp_path])
    assert result == []


def test_discover_skills_no_skill_md(tmp_path):
    """Test discovery when no SKILL.md files exist."""
    # Create some random files
    (tmp_path / "README.md").write_text("# README")
    (tmp_path / "script.py").write_text("print('hello')")

    result = discover_skills([tmp_path])
    assert result == []


def test_discover_single_skill(tmp_path):
    """Test discovery of a single valid skill."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()

    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        """---
name: my-skill
description: A test skill
---

# My Skill
Test instructions.
"""
    )

    result = discover_skills([tmp_path])

    assert len(result) == 1
    assert isinstance(result[0], SkillMetadata)
    assert result[0].name == "my-skill"
    assert result[0].description == "A test skill"
    assert result[0].location == skill_md


def test_discover_multiple_skills(tmp_path):
    """Test discovery of multiple skills."""
    # Create first skill
    skill1_dir = tmp_path / "skill-one"
    skill1_dir.mkdir()
    (skill1_dir / "SKILL.md").write_text(
        """---
name: skill-one
description: First skill
---

Instructions for skill one.
"""
    )

    # Create second skill
    skill2_dir = tmp_path / "skill-two"
    skill2_dir.mkdir()
    (skill2_dir / "SKILL.md").write_text(
        """---
name: skill-two
description: Second skill
---

Instructions for skill two.
"""
    )

    result = discover_skills([tmp_path])

    assert len(result) == 2
    names = {skill.name for skill in result}
    assert names == {"skill-one", "skill-two"}


def test_discover_nested_skills(tmp_path):
    """Test discovery of skills in nested directories."""
    # Create nested structure
    nested_dir = tmp_path / "category" / "subcategory" / "my-skill"
    nested_dir.mkdir(parents=True)

    (nested_dir / "SKILL.md").write_text(
        """---
name: nested-skill
description: A nested skill
---

Nested skill instructions.
"""
    )

    result = discover_skills([tmp_path])

    assert len(result) == 1
    assert result[0].name == "nested-skill"


def test_discover_lowercase_skill_md(tmp_path):
    """Test discovery of skill.md (lowercase) files."""
    skill_dir = tmp_path / "lowercase-skill"
    skill_dir.mkdir()

    # Use lowercase skill.md instead of SKILL.md
    (skill_dir / "skill.md").write_text(
        """---
name: lowercase-skill
description: Skill with lowercase filename
---

Instructions.
"""
    )

    result = discover_skills([tmp_path])

    assert len(result) == 1
    assert result[0].name == "lowercase-skill"


def test_discover_prefers_uppercase_skill_md(tmp_path):
    """Test that SKILL.md is preferred over skill.md."""
    skill_dir = tmp_path / "both-files"
    skill_dir.mkdir()

    # Create both uppercase and lowercase
    (skill_dir / "SKILL.md").write_text(
        """---
name: uppercase-skill
description: From SKILL.md
---

Uppercase.
"""
    )

    (skill_dir / "skill.md").write_text(
        """---
name: lowercase-skill
description: From skill.md
---

Lowercase.
"""
    )

    result = discover_skills([tmp_path])

    # Should only find one skill (uppercase preferred)
    assert len(result) == 1
    assert result[0].name == "uppercase-skill"


def test_discover_multiple_directories(tmp_path):
    """Test discovery from multiple directories."""
    dir1 = tmp_path / "dir1"
    dir1.mkdir()
    dir1_skill = dir1 / "skill-1"
    dir1_skill.mkdir()
    (dir1_skill / "SKILL.md").write_text(
        """---
name: skill-1
description: Skill from dir1
---

Instructions.
"""
    )

    dir2 = tmp_path / "dir2"
    dir2.mkdir()
    dir2_skill = dir2 / "skill-2"
    dir2_skill.mkdir()
    (dir2_skill / "SKILL.md").write_text(
        """---
name: skill-2
description: Skill from dir2
---

Instructions.
"""
    )

    result = discover_skills([dir1, dir2])

    assert len(result) == 2
    names = {skill.name for skill in result}
    assert names == {"skill-1", "skill-2"}


def test_discover_skips_duplicate_names(tmp_path):
    """Test that duplicate skill names are skipped."""
    # Create first skill
    skill1_dir = tmp_path / "dir1" / "duplicate-skill"
    skill1_dir.mkdir(parents=True)
    (skill1_dir / "SKILL.md").write_text(
        """---
name: duplicate-skill
description: First instance
---

First.
"""
    )

    # Create second skill with same name
    skill2_dir = tmp_path / "dir2" / "duplicate-skill"
    skill2_dir.mkdir(parents=True)
    (skill2_dir / "SKILL.md").write_text(
        """---
name: duplicate-skill
description: Second instance
---

Second.
"""
    )

    result = discover_skills([tmp_path])

    # Should only find one (glob order not deterministic)
    assert len(result) == 1
    assert result[0].name == "duplicate-skill"
    # Description could be from either instance depending on glob order
    assert result[0].description in ["First instance", "Second instance"]


def test_discover_skips_invalid_skills(tmp_path):
    """Test that invalid skills are skipped during discovery."""
    # Valid skill
    valid_dir = tmp_path / "valid-skill"
    valid_dir.mkdir()
    (valid_dir / "SKILL.md").write_text(
        """---
name: valid-skill
description: Valid skill
---

Instructions.
"""
    )

    # Invalid skill (missing name)
    invalid_dir = tmp_path / "invalid-skill"
    invalid_dir.mkdir()
    (invalid_dir / "SKILL.md").write_text(
        """---
description: Missing name field
---

Instructions.
"""
    )

    result = discover_skills([tmp_path])

    # Should only find the valid skill
    assert len(result) == 1
    assert result[0].name == "valid-skill"


def test_discover_with_optional_fields(tmp_path):
    """Test discovery of skill with all optional fields."""
    skill_dir = tmp_path / "full-skill"
    skill_dir.mkdir()

    (skill_dir / "SKILL.md").write_text(
        """---
name: full-skill
description: Skill with all fields
license: MIT
compatibility: Python 3.9+
allowed-tools: bash python
metadata:
  author: Test Author
  version: 1.0.0
---

Instructions.
"""
    )

    result = discover_skills([tmp_path])

    assert len(result) == 1
    skill = result[0]
    assert skill.name == "full-skill"
    assert skill.license == "MIT"
    assert skill.compatibility == "Python 3.9+"
    assert skill.allowed_tools == "bash python"
    assert skill.metadata == {"author": "Test Author", "version": "1.0.0"}


def test_discover_nonexistent_directory(tmp_path):
    """Test discovery with nonexistent directory."""
    nonexistent = tmp_path / "does-not-exist"

    # Should not raise error, just return empty list
    result = discover_skills([nonexistent])
    assert result == []


def test_discover_empty_directories_list():
    """Test discovery with empty directories list."""
    result = discover_skills([])
    assert result == []
