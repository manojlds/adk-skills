"""Tests for skill registry module."""

import pytest

from adk_skills_agent.core.models import SkillsConfig
from adk_skills_agent.exceptions import SkillNotFoundError
from adk_skills_agent.registry import SkillsRegistry


class TestSkillsRegistryInit:
    def test_init_default_config(self):
        registry = SkillsRegistry()
        assert registry.config is not None
        assert isinstance(registry.config, SkillsConfig)

    def test_init_custom_config(self):
        config = SkillsConfig(strict_validation=True, auto_discover=False)
        registry = SkillsRegistry(config=config)
        assert registry.config == config
        assert registry.config.strict_validation is True

    async def test_init_empty_registry(self):
        registry = SkillsRegistry()
        assert await registry.list_metadata() == []


class TestSkillsRegistryDiscover:
    async def test_discover_empty_directory(self, tmp_path):
        registry = SkillsRegistry()
        count = registry.discover([tmp_path])
        assert count == 0
        assert await registry.list_metadata() == []

    async def test_discover_single_skill(self, tmp_path):
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
        metadata = await registry.list_metadata()
        assert len(metadata) == 1
        assert metadata[0].name == "my-skill"

    async def test_discover_multiple_skills(self, tmp_path):
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
        names = {meta.name for meta in await registry.list_metadata()}
        assert names == {"skill-0", "skill-1", "skill-2"}

    async def test_discover_from_multiple_directories(self, tmp_path):
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
        names = {meta.name for meta in await registry.list_metadata()}
        assert names == {"skill-1", "skill-2"}

    async def test_discover_string_paths(self, tmp_path):
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
        count = registry.discover([str(tmp_path)])

        assert count == 1
        metadata = await registry.list_metadata()
        assert metadata[0].name == "my-skill"

    async def test_discover_with_home_expansion(self, tmp_path, monkeypatch):
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

    async def test_discover_accumulates_skills(self, tmp_path):
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
        assert count2 == 2
        assert len(await registry.list_metadata()) == 2


class TestSkillsRegistryStrictValidation:
    async def test_strict_validation_rejects_invalid_skills(self, tmp_path):
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

        assert count == 0

    async def test_non_strict_validation_accepts_invalid_skills(self, tmp_path):
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

        assert count == 1


class TestSkillsRegistryGetMetadata:
    async def test_get_metadata_existing_skill(self, tmp_path):
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

        metadata = await registry.get_metadata("my-skill")
        assert metadata is not None
        assert metadata.name == "my-skill"
        assert metadata.description == "A test skill"

    async def test_get_metadata_nonexistent_skill(self):
        registry = SkillsRegistry()
        metadata = await registry.get_metadata("nonexistent-skill")
        assert metadata is None


class TestSkillsRegistryLoadSkill:
    async def test_load_skill_existing(self, tmp_path):
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

        skill = await registry.load_skill("my-skill")
        assert skill.name == "my-skill"
        assert skill.description == "A test skill"
        assert skill.instructions == "# My Skill\nThese are the instructions."

    async def test_load_skill_nonexistent(self):
        registry = SkillsRegistry()

        with pytest.raises(SkillNotFoundError):
            await registry.load_skill("nonexistent-skill")

    async def test_load_skill_caches_in_source(self, tmp_path):
        # The registry no longer caches loaded skills directly, but the
        # filesystem source caches its own ``Skill`` objects so identity
        # is stable across awaits.
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

        skill1 = await registry.load_skill("my-skill")
        skill2 = await registry.load_skill("my-skill")

        assert skill1 is skill2

    async def test_load_skill_with_scripts(self, tmp_path):
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

        skill = await registry.load_skill("my-skill")
        assert skill.scripts_dir is not None
        assert skill.scripts_dir.name == "scripts"

    async def test_load_skill_with_references(self, tmp_path):
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

        skill = await registry.load_skill("my-skill")
        assert skill.references_dir is not None
        assert skill.references_dir.name == "references"


class TestSkillsRegistryHasSkill:
    async def test_has_skill_existing(self, tmp_path):
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

        assert await registry.has_skill("my-skill")

    async def test_has_skill_nonexistent(self):
        registry = SkillsRegistry()
        assert not await registry.has_skill("nonexistent-skill")


class TestSkillsRegistryListSkills:
    async def test_list_skills_empty(self):
        registry = SkillsRegistry()
        assert await registry.list_metadata() == []

    async def test_list_skills_returns_metadata(self, tmp_path):
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

        skills = await registry.list_metadata()
        assert len(skills) == 1
        from adk_skills_agent.core.models import SkillMetadata

        assert isinstance(skills[0], SkillMetadata)

    async def test_list_skills_returns_copy(self, tmp_path):
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

        skills1 = await registry.list_metadata()
        skills2 = await registry.list_metadata()

        assert skills1 is not skills2


class TestSkillsRegistryClear:
    async def test_clear_empty_registry(self):
        registry = SkillsRegistry()
        await registry.clear()
        assert await registry.list_metadata() == []

    async def test_clear_populated_registry(self, tmp_path):
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
        assert len(await registry.list_metadata()) == 1

        await registry.clear()
        assert await registry.list_metadata() == []

    async def test_clear_clears_cache(self, tmp_path):
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
        await registry.load_skill("my-skill")

        await registry.clear()

        with pytest.raises(SkillNotFoundError):
            await registry.load_skill("my-skill")


class TestSkillsRegistryPromptInjection:
    async def test_to_prompt_xml_empty_registry(self):
        registry = SkillsRegistry()
        xml = await registry.to_prompt_xml()
        assert "<available_skills>" in xml
        assert "No skills available" in xml

    async def test_to_prompt_xml_with_skills(self, tmp_path):
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
        xml = await registry.to_prompt_xml()

        assert "<available_skills>" in xml
        assert "<skill>" in xml
        assert "<name>my-skill</name>" in xml
        assert "<description>A test skill</description>" in xml
        assert "</available_skills>" in xml

    async def test_to_prompt_xml_escapes_special_chars(self, tmp_path):
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
        xml = await registry.to_prompt_xml()

        assert "&lt;special&gt;" in xml
        assert "&amp;" in xml

    async def test_to_prompt_text_empty_registry(self):
        registry = SkillsRegistry()
        text = await registry.to_prompt_text()
        assert text == "No skills available."

    async def test_to_prompt_text_with_skills(self, tmp_path):
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
        text = await registry.to_prompt_text()

        assert "Available Skills:" in text
        assert "- skill-0: Test skill 0" in text
        assert "- skill-1: Test skill 1" in text

    async def test_get_skills_prompt_xml_format(self, tmp_path):
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
        prompt = await registry.get_skills_prompt(format="xml")

        assert "<available_skills>" in prompt
        assert "<name>my-skill</name>" in prompt

    async def test_get_skills_prompt_text_format(self, tmp_path):
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
        prompt = await registry.get_skills_prompt(format="text")

        assert "Available Skills:" in prompt
        assert "- my-skill: A test skill" in prompt

    async def test_get_skills_prompt_invalid_format(self):
        registry = SkillsRegistry()

        with pytest.raises(ValueError, match="Unsupported format"):
            await registry.get_skills_prompt(format="invalid")

    async def test_inject_skills_prompt_with_empty_registry(self):
        registry = SkillsRegistry()
        instruction = "You are a helpful assistant."
        result = await registry.inject_skills_prompt(instruction, format="xml")

        assert result == instruction

    async def test_inject_skills_prompt_xml_format(self, tmp_path):
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
        instruction = "You are a helpful assistant."
        result = await registry.inject_skills_prompt(instruction, format="xml")

        assert "You are a helpful assistant." in result
        assert "<available_skills>" in result
        assert "<name>my-skill</name>" in result

    async def test_inject_skills_prompt_text_format(self, tmp_path):
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
        instruction = "You are a helpful assistant."
        result = await registry.inject_skills_prompt(instruction, format="text")

        assert "You are a helpful assistant." in result
        assert "Available Skills:" in result
        assert "- my-skill: A test skill" in result


class TestSkillsRegistryValidation:
    async def test_validate_all_empty_registry(self):
        registry = SkillsRegistry()
        results = await registry.validate_all()
        assert results == {}

    async def test_validate_all_with_valid_skills(self, tmp_path):
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
        results = await registry.validate_all(strict=True)

        assert "my-skill" in results
        assert results["my-skill"].valid is True

    async def test_validate_all_with_invalid_skills(self, tmp_path):
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
        results = await registry.validate_all(strict=True)

        assert "Invalid_Name" in results
        assert results["Invalid_Name"].valid is False
        assert len(results["Invalid_Name"].errors) > 0

    async def test_validate_skill_by_name_existing(self, tmp_path):
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
        result = await registry.validate_skill_by_name("my-skill")

        assert result.valid is True

    async def test_validate_skill_by_name_nonexistent(self):
        registry = SkillsRegistry()

        with pytest.raises(SkillNotFoundError):
            await registry.validate_skill_by_name("nonexistent-skill")

    async def test_validate_skill_by_name_with_warnings(self, tmp_path):
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
        result = await registry.validate_skill_by_name("my-skill", strict=True)

        assert result.valid is True
        assert len(result.warnings) > 0
