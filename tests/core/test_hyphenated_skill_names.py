"""Tests for hyphenated skill name support.

This module tests that skills with hyphenated names are properly supported
throughout the system, including validation, discovery, and loading.
"""

from adk_skills_agent.core.discovery import discover_skills
from adk_skills_agent.core.models import SkillsConfig
from adk_skills_agent.core.validator import validate_skill_name
from adk_skills_agent.registry import SkillsRegistry


class TestHyphenatedSkillNameValidation:
    def test_single_hyphen_valid(self):
        errors = validate_skill_name("my-skill")
        assert errors == []

    def test_multiple_hyphens_valid(self):
        errors = validate_skill_name("my-multi-hyphen-skill-name")
        assert errors == []

    def test_hyphen_with_numbers_valid(self):
        errors = validate_skill_name("skill-123-test")
        assert errors == []

    def test_all_numbers_with_hyphens_valid(self):
        errors = validate_skill_name("123-456-789")
        assert errors == []

    def test_consecutive_hyphens_valid(self):
        errors = validate_skill_name("my--skill")
        assert errors == []

    def test_many_hyphens_valid(self):
        errors = validate_skill_name("a-b-c-d-e-f-g-h-i-j-k")
        assert errors == []

    def test_starts_with_hyphen_invalid(self):
        errors = validate_skill_name("-my-skill")
        assert len(errors) > 0
        assert any("cannot start or end with hyphen" in err for err in errors)

    def test_ends_with_hyphen_invalid(self):
        errors = validate_skill_name("my-skill-")
        assert len(errors) > 0
        assert any("cannot start or end with hyphen" in err for err in errors)

    def test_only_hyphens_invalid(self):
        errors = validate_skill_name("---")
        assert len(errors) > 0
        assert any("cannot start or end with hyphen" in err for err in errors)

    def test_64_char_with_hyphens_valid(self):
        name = "a" * 31 + "-" + "b" * 32  # Total: 64 chars
        assert len(name) == 64
        errors = validate_skill_name(name)
        assert errors == []

    def test_65_char_with_hyphens_invalid(self):
        name = "a" * 32 + "-" + "b" * 32  # Total: 65 chars
        assert len(name) == 65
        errors = validate_skill_name(name)
        assert len(errors) > 0
        assert any("too long" in err for err in errors)


class TestHyphenatedSkillNameDiscovery:
    def test_discover_hyphenated_skill(self, tmp_path):
        skill_dir = tmp_path / "my-hyphenated-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: my-hyphenated-skill
description: A skill with hyphens
---

Instructions.
"""
        )

        result = discover_skills([tmp_path])
        assert len(result) == 1
        assert result[0].name == "my-hyphenated-skill"

    def test_discover_multiple_hyphenated_skills(self, tmp_path):
        skill_names = ["skill-one", "skill-two-test", "my-multi-hyphen-skill"]

        for name in skill_names:
            skill_dir = tmp_path / name
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                f"""---
name: {name}
description: Test skill {name}
---

Instructions.
"""
            )

        result = discover_skills([tmp_path])
        assert len(result) == 3
        discovered_names = {skill.name for skill in result}
        assert discovered_names == set(skill_names)

    def test_discover_hyphenated_skill_from_fixture(self):
        import pathlib

        fixtures_dir = pathlib.Path(__file__).parent.parent / "fixtures" / "skills"
        result = discover_skills([fixtures_dir])

        skill_names = {skill.name for skill in result}
        assert "multi-hyphen-skill-name" in skill_names


class TestHyphenatedSkillNameRegistry:
    async def test_registry_discover_hyphenated_skill(self, tmp_path):
        skill_dir = tmp_path / "my-test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: my-test-skill
description: A test skill
---

Instructions.
"""
        )

        registry = SkillsRegistry()
        count = registry.discover([tmp_path])

        assert count == 1
        assert await registry.has_skill("my-test-skill")

    async def test_registry_load_hyphenated_skill(self, tmp_path):
        skill_dir = tmp_path / "load-test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: load-test-skill
description: A test skill for loading
---

# Load Test Skill
These are the instructions.
"""
        )

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        skill = await registry.load_skill("load-test-skill")
        assert skill.name == "load-test-skill"
        assert skill.description == "A test skill for loading"
        assert "Load Test Skill" in skill.instructions

    async def test_registry_get_metadata_hyphenated_skill(self, tmp_path):
        skill_dir = tmp_path / "metadata-test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: metadata-test-skill
description: Test metadata retrieval
license: MIT
---

Instructions.
"""
        )

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        metadata = await registry.get_metadata("metadata-test-skill")
        assert metadata is not None
        assert metadata.name == "metadata-test-skill"
        assert metadata.license == "MIT"

    async def test_registry_validates_hyphenated_skill_names(self, tmp_path):
        valid_dir = tmp_path / "valid-hyphenated-skill"
        valid_dir.mkdir()
        (valid_dir / "SKILL.md").write_text(
            """---
name: valid-hyphenated-skill
description: Valid skill
---

Instructions.
"""
        )

        invalid_dir = tmp_path / "invalid-skill"
        invalid_dir.mkdir()
        (invalid_dir / "SKILL.md").write_text(
            """---
name: -invalid-hyphen-start
description: Invalid skill
---

Instructions.
"""
        )

        config = SkillsConfig(strict_validation=True)
        registry = SkillsRegistry(config=config)
        count = registry.discover([tmp_path])

        assert count == 1
        assert await registry.has_skill("valid-hyphenated-skill")
        assert not await registry.has_skill("-invalid-hyphen-start")

    async def test_registry_multiple_hyphens_in_name(self, tmp_path):
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: this-is-a-skill-with-many-hyphens
description: Multiple hyphens test
---

Instructions.
"""
        )

        registry = SkillsRegistry()
        count = registry.discover([tmp_path])

        assert count == 1
        skill = await registry.load_skill("this-is-a-skill-with-many-hyphens")
        assert skill.name == "this-is-a-skill-with-many-hyphens"


class TestFolderNameVsFrontmatterName:
    """Tests for folder name vs frontmatter name matching.

    These tests document that folder names do NOT need to match frontmatter names.
    The skill system uses the frontmatter 'name' field as the canonical identifier.
    """

    def test_folder_name_can_differ_from_frontmatter(self, tmp_path):
        skill_dir = tmp_path / "folder-name-here"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: actual-skill-name
description: Folder and frontmatter names differ
---

Instructions.
"""
        )

        result = discover_skills([tmp_path])
        assert len(result) == 1
        assert result[0].name == "actual-skill-name"

    async def test_registry_uses_frontmatter_name_not_folder(self, tmp_path):
        skill_dir = tmp_path / "some-folder"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: my-skill-name
description: Test skill
---

Instructions.
"""
        )

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        assert await registry.has_skill("my-skill-name")
        assert not await registry.has_skill("some-folder")

        skill = await registry.load_skill("my-skill-name")
        assert skill.name == "my-skill-name"

    async def test_no_validation_for_folder_name_format(self, tmp_path):
        skill_dir = tmp_path / "Invalid_Folder_Name"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: valid-skill-name
description: Valid skill despite invalid folder name
---

Instructions.
"""
        )

        result = discover_skills([tmp_path])
        assert len(result) == 1
        assert result[0].name == "valid-skill-name"

        registry = SkillsRegistry()
        registry.discover([tmp_path])
        assert await registry.has_skill("valid-skill-name")

    async def test_multiple_skills_different_folder_naming(self, tmp_path):
        skills = [
            ("CamelCaseFolder", "skill-one"),
            ("snake_case_folder", "skill-two"),
            ("kebab-case-folder", "skill-three"),
            ("randomname123", "skill-four"),
        ]

        for folder_name, skill_name in skills:
            skill_dir = tmp_path / folder_name
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                f"""---
name: {skill_name}
description: Test skill {skill_name}
---

Instructions.
"""
            )

        registry = SkillsRegistry()
        count = registry.discover([tmp_path])

        assert count == 4
        for _, skill_name in skills:
            assert await registry.has_skill(skill_name)
            skill = await registry.load_skill(skill_name)
            assert skill.name == skill_name


class TestHyphenatedSkillNameEdgeCases:
    async def test_single_char_with_hyphens(self, tmp_path):
        skill_dir = tmp_path / "a-b-c"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: a-b-c
description: Single char segments
---

Instructions.
"""
        )

        registry = SkillsRegistry()
        count = registry.discover([tmp_path])
        assert count == 1
        skill = await registry.load_skill("a-b-c")
        assert skill.name == "a-b-c"

    async def test_numbers_only_with_hyphens(self, tmp_path):
        skill_dir = tmp_path / "123-456"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: 123-456
description: Numbers with hyphens
---

Instructions.
"""
        )

        registry = SkillsRegistry()
        count = registry.discover([tmp_path])
        assert count == 1
        skill = await registry.load_skill("123-456")
        assert skill.name == "123-456"

    async def test_hyphen_at_various_positions(self, tmp_path):
        positions = [
            "a-bcdefg",
            "abcd-efg",
            "abcdef-g",
            "a-b-c-d",
        ]

        for name in positions:
            skill_dir = tmp_path / name
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                f"""---
name: {name}
description: Test {name}
---

Instructions.
"""
            )

        registry = SkillsRegistry()
        count = registry.discover([tmp_path])
        assert count == len(positions)

        for name in positions:
            assert await registry.has_skill(name)

    async def test_long_hyphenated_name_near_limit(self, tmp_path):
        name = "skill-" + "a" * 29 + "-" + "b" * 28  # 6 + 29 + 1 + 28 = 64
        assert len(name) == 64

        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            f"""---
name: {name}
description: Long hyphenated name
---

Instructions.
"""
        )

        registry = SkillsRegistry()
        count = registry.discover([tmp_path])
        assert count == 1
        skill = await registry.load_skill(name)
        assert skill.name == name
        assert len(skill.name) == 64
