"""Tests for skill registry module."""

import pytest

from adk_skills_agent.core.models import SkillsConfig
from adk_skills_agent.exceptions import SkillNotFoundError
from adk_skills_agent.registry import SkillsRegistry


class TestSkillsRegistryInit:
    """Tests for SkillsRegistry initialization."""

    def test_init_default_config(self):
        """Test initialization with default config."""
        registry = SkillsRegistry()
        assert registry.config is not None
        assert isinstance(registry.config, SkillsConfig)

    def test_init_custom_config(self):
        """Test initialization with custom config."""
        config = SkillsConfig(strict_validation=True, auto_discover=False)
        registry = SkillsRegistry(config=config)
        assert registry.config == config
        assert registry.config.strict_validation is True

    def test_init_empty_registry(self):
        """Test that registry starts empty."""
        registry = SkillsRegistry()
        assert registry.list_metadata() == []


class TestSkillsRegistryDiscover:
    """Tests for skill discovery in registry."""

    def test_discover_empty_directory(self, tmp_path):
        """Test discovery in empty directory."""
        registry = SkillsRegistry()
        count = registry.discover([tmp_path])
        assert count == 0
        assert registry.list_metadata() == []

    def test_discover_single_skill(self, tmp_path):
        """Test discovery of a single skill."""
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

        registry = SkillsRegistry()
        count = registry.discover([tmp_path])

        assert count == 1
        assert len(registry.list_metadata()) == 1
        assert registry.list_metadata()[0].name == "my-skill"

    def test_discover_multiple_skills(self, tmp_path):
        """Test discovery of multiple skills."""
        for i in range(3):
            skill_dir = tmp_path / f"skill-{i}"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                f"""---
name: skill-{i}
description: Test skill {i}
---

Instructions.
"""
            )

        registry = SkillsRegistry()
        count = registry.discover([tmp_path])

        assert count == 3
        assert len(registry.list_metadata()) == 3
        names = {s.name for s in registry.list_metadata()}
        assert names == {"skill-0", "skill-1", "skill-2"}

    def test_discover_from_multiple_directories(self, tmp_path):
        """Test discovery from multiple directories."""
        dir1 = tmp_path / "dir1"
        dir1.mkdir()
        skill1 = dir1 / "skill-1"
        skill1.mkdir()
        (skill1 / "SKILL.md").write_text(
            """---
name: skill-1
description: Skill 1
---

Instructions.
"""
        )

        dir2 = tmp_path / "dir2"
        dir2.mkdir()
        skill2 = dir2 / "skill-2"
        skill2.mkdir()
        (skill2 / "SKILL.md").write_text(
            """---
name: skill-2
description: Skill 2
---

Instructions.
"""
        )

        registry = SkillsRegistry()
        count = registry.discover([dir1, dir2])

        assert count == 2
        names = {s.name for s in registry.list_metadata()}
        assert names == {"skill-1", "skill-2"}

    def test_discover_string_paths(self, tmp_path):
        """Test discovery with string paths instead of Path objects."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: my-skill
description: A skill
---

Instructions.
"""
        )

        registry = SkillsRegistry()
        count = registry.discover([str(tmp_path)])  # Pass string instead of Path

        assert count == 1
        assert registry.list_metadata()[0].name == "my-skill"

    def test_discover_with_home_expansion(self, tmp_path, monkeypatch):
        """Test discovery with ~ path expansion."""
        monkeypatch.setenv("HOME", str(tmp_path))

        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: my-skill
description: A skill
---

Instructions.
"""
        )

        registry = SkillsRegistry()
        count = registry.discover(["~"])

        assert count == 1

    def test_discover_accumulates_skills(self, tmp_path):
        """Test that multiple discover calls accumulate skills."""
        dir1 = tmp_path / "dir1"
        dir1.mkdir()
        skill1 = dir1 / "skill-1"
        skill1.mkdir()
        (skill1 / "SKILL.md").write_text(
            """---
name: skill-1
description: Skill 1
---

Instructions.
"""
        )

        dir2 = tmp_path / "dir2"
        dir2.mkdir()
        skill2 = dir2 / "skill-2"
        skill2.mkdir()
        (skill2 / "SKILL.md").write_text(
            """---
name: skill-2
description: Skill 2
---

Instructions.
"""
        )

        registry = SkillsRegistry()
        count1 = registry.discover([dir1])
        count2 = registry.discover([dir2])

        assert count1 == 1
        assert count2 == 2  # Total count
        assert len(registry.list_metadata()) == 2


class TestSkillsRegistryStrictValidation:
    """Tests for strict validation mode in registry."""

    def test_strict_validation_rejects_invalid_skills(self, tmp_path):
        """Test that strict validation rejects invalid skills."""
        skill_dir = tmp_path / "invalid-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: Invalid_Name
description: Invalid skill
---

Instructions.
"""
        )

        config = SkillsConfig(strict_validation=True)
        registry = SkillsRegistry(config=config)
        count = registry.discover([tmp_path])

        # Should reject invalid skill
        assert count == 0

    def test_non_strict_validation_accepts_invalid_skills(self, tmp_path):
        """Test that non-strict validation accepts invalid skills."""
        skill_dir = tmp_path / "invalid-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: Invalid_Name
description: Invalid skill
---

Instructions.
"""
        )

        config = SkillsConfig(strict_validation=False)
        registry = SkillsRegistry(config=config)
        count = registry.discover([tmp_path])

        # Should accept even invalid skill in non-strict mode
        assert count == 1


class TestSkillsRegistryGetMetadata:
    """Tests for getting skill metadata from registry."""

    def test_get_metadata_existing_skill(self, tmp_path):
        """Test getting metadata for existing skill."""
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

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        metadata = registry.get_metadata("my-skill")
        assert metadata is not None
        assert metadata.name == "my-skill"
        assert metadata.description == "A test skill"

    def test_get_metadata_nonexistent_skill(self):
        """Test getting metadata for nonexistent skill."""
        registry = SkillsRegistry()
        metadata = registry.get_metadata("nonexistent-skill")
        assert metadata is None


class TestSkillsRegistryLoadSkill:
    """Tests for loading full skills from registry."""

    def test_load_skill_existing(self, tmp_path):
        """Test loading an existing skill."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: my-skill
description: A test skill
---

# My Skill
These are the instructions.
"""
        )

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        skill = registry.load_skill("my-skill")
        assert skill.name == "my-skill"
        assert skill.description == "A test skill"
        assert skill.instructions == "# My Skill\nThese are the instructions."

    def test_load_skill_nonexistent(self):
        """Test loading a nonexistent skill raises error."""
        registry = SkillsRegistry()

        with pytest.raises(SkillNotFoundError):
            registry.load_skill("nonexistent-skill")

    def test_load_skill_caches_result(self, tmp_path):
        """Test that load_skill caches the result."""
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

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        skill1 = registry.load_skill("my-skill")
        skill2 = registry.load_skill("my-skill")

        # Should return the same cached object
        assert skill1 is skill2

    def test_load_skill_with_scripts(self, tmp_path):
        """Test loading skill with scripts directory."""
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

        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "test.py").write_text("print('hello')")

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        skill = registry.load_skill("my-skill")
        assert skill.scripts_dir is not None
        assert skill.scripts_dir.name == "scripts"

    def test_load_skill_with_references(self, tmp_path):
        """Test loading skill with references directory."""
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

        refs_dir = skill_dir / "references"
        refs_dir.mkdir()
        (refs_dir / "doc.md").write_text("# Documentation")

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        skill = registry.load_skill("my-skill")
        assert skill.references_dir is not None
        assert skill.references_dir.name == "references"


class TestSkillsRegistryHasSkill:
    """Tests for checking if skill exists in registry."""

    def test_has_skill_existing(self, tmp_path):
        """Test has_skill for existing skill."""
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

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        assert registry.has_skill("my-skill")

    def test_has_skill_nonexistent(self):
        """Test has_skill for nonexistent skill."""
        registry = SkillsRegistry()
        assert not registry.has_skill("nonexistent-skill")


class TestSkillsRegistryListSkills:
    """Tests for listing skills in registry."""

    def test_list_skills_empty(self):
        """Test listing skills when registry is empty."""
        registry = SkillsRegistry()
        assert registry.list_metadata() == []

    def test_list_skills_returns_metadata(self, tmp_path):
        """Test that list_skills returns SkillMetadata objects."""
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

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        skills = registry.list_metadata()
        assert len(skills) == 1
        from adk_skills_agent.core.models import SkillMetadata

        assert isinstance(skills[0], SkillMetadata)

    def test_list_skills_returns_copy(self, tmp_path):
        """Test that list_skills returns a copy, not the internal list."""
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

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        skills1 = registry.list_metadata()
        skills2 = registry.list_metadata()

        # Should be different list objects
        assert skills1 is not skills2


class TestSkillsRegistryCount:
    """Tests for counting skills in registry."""

    def test_count_empty(self):
        """Test count when registry is empty."""
        registry = SkillsRegistry()
        assert len(registry) == 0

    def test_count_after_discovery(self, tmp_path):
        """Test count after discovering skills."""
        for i in range(5):
            skill_dir = tmp_path / f"skill-{i}"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                f"""---
name: skill-{i}
description: Skill {i}
---

Instructions.
"""
            )

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        assert len(registry) == 5


class TestSkillsRegistryClear:
    """Tests for clearing the registry."""

    def test_clear_empty_registry(self):
        """Test clearing an empty registry."""
        registry = SkillsRegistry()
        registry.clear()
        assert len(registry) == 0

    def test_clear_populated_registry(self, tmp_path):
        """Test clearing a populated registry."""
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

        registry = SkillsRegistry()
        registry.discover([tmp_path])
        assert len(registry) == 1

        registry.clear()
        assert len(registry) == 0
        assert registry.list_metadata() == []

    def test_clear_clears_cache(self, tmp_path):
        """Test that clear also clears the skill cache."""
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

        registry = SkillsRegistry()
        registry.discover([tmp_path])
        registry.load_skill("my-skill")  # Load into cache

        registry.clear()

        # After clear, should need to rediscover
        with pytest.raises(SkillNotFoundError):
            registry.load_skill("my-skill")


class TestSkillsRegistryPromptInjection:
    """Tests for prompt injection utilities."""

    def test_to_prompt_xml_empty_registry(self):
        """Test XML prompt generation with empty registry."""
        registry = SkillsRegistry()
        xml = registry.to_prompt_xml()
        assert "<available_skills>" in xml
        assert "No skills available" in xml

    def test_to_prompt_xml_with_skills(self, tmp_path):
        """Test XML prompt generation with skills."""
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

        registry = SkillsRegistry()
        registry.discover([tmp_path])
        xml = registry.to_prompt_xml()

        assert "<available_skills>" in xml
        assert "<skill>" in xml
        assert "<name>my-skill</name>" in xml
        assert "<description>A test skill</description>" in xml
        assert "</available_skills>" in xml

    def test_to_prompt_xml_escapes_special_chars(self, tmp_path):
        """Test that XML prompt escapes special characters."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: my-skill
description: A skill with <special> & chars
---

Instructions.
"""
        )

        registry = SkillsRegistry()
        registry.discover([tmp_path])
        xml = registry.to_prompt_xml()

        assert "&lt;special&gt;" in xml
        assert "&amp;" in xml

    def test_to_prompt_text_empty_registry(self):
        """Test text prompt generation with empty registry."""
        registry = SkillsRegistry()
        text = registry.to_prompt_text()
        assert text == "No skills available."

    def test_to_prompt_text_with_skills(self, tmp_path):
        """Test text prompt generation with skills."""
        for i in range(2):
            skill_dir = tmp_path / f"skill-{i}"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                f"""---
name: skill-{i}
description: Test skill {i}
---

Instructions.
"""
            )

        registry = SkillsRegistry()
        registry.discover([tmp_path])
        text = registry.to_prompt_text()

        assert "Available Skills:" in text
        assert "- skill-0: Test skill 0" in text
        assert "- skill-1: Test skill 1" in text

    def test_get_skills_prompt_xml_format(self, tmp_path):
        """Test get_skills_prompt with XML format."""
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

        registry = SkillsRegistry()
        registry.discover([tmp_path])
        prompt = registry.get_skills_prompt(format="xml")

        assert "<available_skills>" in prompt
        assert "<name>my-skill</name>" in prompt

    def test_get_skills_prompt_text_format(self, tmp_path):
        """Test get_skills_prompt with text format."""
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

        registry = SkillsRegistry()
        registry.discover([tmp_path])
        prompt = registry.get_skills_prompt(format="text")

        assert "Available Skills:" in prompt
        assert "- my-skill: A test skill" in prompt

    def test_get_skills_prompt_invalid_format(self):
        """Test get_skills_prompt with invalid format."""
        registry = SkillsRegistry()

        with pytest.raises(ValueError, match="Unsupported format"):
            registry.get_skills_prompt(format="invalid")


class TestSkillsRegistryValidation:
    """Tests for validation utilities."""

    def test_validate_all_empty_registry(self):
        """Test validate_all with empty registry."""
        registry = SkillsRegistry()
        results = registry.validate_all()
        assert results == {}

    def test_validate_all_with_valid_skills(self, tmp_path):
        """Test validate_all with valid skills."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: my-skill
description: A test skill
license: MIT
---

Instructions.
"""
        )

        registry = SkillsRegistry()
        registry.discover([tmp_path])
        results = registry.validate_all(strict=True)

        assert "my-skill" in results
        assert results["my-skill"].valid is True

    def test_validate_all_with_invalid_skills(self, tmp_path):
        """Test validate_all with invalid skills."""
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

        config = SkillsConfig(strict_validation=False)
        registry = SkillsRegistry(config=config)
        registry.discover([tmp_path])
        results = registry.validate_all(strict=True)

        assert "Invalid_Name" in results
        assert results["Invalid_Name"].valid is False
        assert len(results["Invalid_Name"].errors) > 0

    def test_validate_skill_by_name_existing(self, tmp_path):
        """Test validate_skill_by_name for existing skill."""
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

        registry = SkillsRegistry()
        registry.discover([tmp_path])
        result = registry.validate_skill_by_name("my-skill")

        assert result.valid is True

    def test_validate_skill_by_name_nonexistent(self):
        """Test validate_skill_by_name for nonexistent skill."""
        registry = SkillsRegistry()

        with pytest.raises(SkillNotFoundError):
            registry.validate_skill_by_name("nonexistent-skill")

    def test_validate_skill_by_name_with_warnings(self, tmp_path):
        """Test validate_skill_by_name shows warnings in strict mode."""
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

        registry = SkillsRegistry()
        registry.discover([tmp_path])
        result = registry.validate_skill_by_name("my-skill", strict=True)

        assert result.valid is True
        assert len(result.warnings) > 0  # Should warn about missing license
