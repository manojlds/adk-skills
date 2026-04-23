"""Tests for skill path normalization helpers."""

import pytest

from adk_skills_agent.core.paths import normalize_skill_reference, validate_skill_root_relative_path
from adk_skills_agent.exceptions import SkillExecutionError


def test_normalize_skill_reference_maps_bare_and_nested_paths() -> None:
    assert normalize_skill_reference("guide.md") == "references/guide.md"
    assert normalize_skill_reference("guides/intro.md") == "references/guides/intro.md"


def test_normalize_skill_reference_preserves_known_roots() -> None:
    assert normalize_skill_reference("references/guide.md") == "references/guide.md"
    assert normalize_skill_reference("assets/template.json") == "assets/template.json"
    assert normalize_skill_reference("scripts/run.sh") == "scripts/run.sh"
    assert normalize_skill_reference("SKILL.md") == "SKILL.md"


def test_validate_skill_root_relative_path_rejects_escape_and_absolute() -> None:
    with pytest.raises(SkillExecutionError, match="escapes skill directory"):
        validate_skill_root_relative_path("../secret.txt")
    with pytest.raises(SkillExecutionError, match="Absolute paths are not allowed"):
        validate_skill_root_relative_path("/etc/passwd")


def test_validate_skill_root_relative_path_strips_dot_segments() -> None:
    assert validate_skill_root_relative_path("assets/./template.json") == "assets/template.json"
    assert validate_skill_root_relative_path("./references/guide.md") == "references/guide.md"
    assert (
        validate_skill_root_relative_path("references/./guides/./intro.md")
        == "references/guides/intro.md"
    )


def test_validate_skill_root_relative_path_rejects_dot_only() -> None:
    with pytest.raises(SkillExecutionError, match="Empty path is not allowed"):
        validate_skill_root_relative_path(".")
