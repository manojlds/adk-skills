"""Registry-level integration tests for the new source abstraction."""

from __future__ import annotations

from pathlib import Path

import pytest

from adk_skills_agent import SkillsRegistry
from adk_skills_agent.core.models import Skill, SkillMetadata
from adk_skills_agent.core.source import SkillFile, SkillSource
from adk_skills_agent.exceptions import (
    SkillExecutionError,
    SkillNotFoundError,
    SkillSourceCollisionError,
)
from adk_skills_agent.sources.filesystem import FilesystemSkillSource


def _write_skill(tmp_path: Path, name: str) -> Path:
    skill_dir = tmp_path / name
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Test skill {name}\n---\n\nBody.\n"
    )
    return skill_dir


class _InMemorySource(SkillSource):
    """Minimal SkillSource for tests — lives entirely in memory.

    Only implements the mandatory ``SkillSource`` surface
    (``list_metadata`` / ``load_skill`` / ``has_skill``) plus ``list_files``
    / ``read_file``. ``read_reference`` is handled at the registry level
    by delegating to ``read_file``, so the source does not need to know
    about reference-path normalisation.
    """

    name = "memory"

    def __init__(self, skills: dict[str, Skill] | None = None) -> None:
        self._skills = dict(skills or {})
        self._files: dict[tuple[str, str], SkillFile] = {}

    def add(self, skill: Skill) -> None:
        self._skills[skill.name] = skill

    def add_file(self, skill_name: str, file: SkillFile) -> None:
        self._files[(skill_name, file.relative_path)] = file

    def list_metadata(self) -> list[SkillMetadata]:
        return [skill.to_metadata() for skill in self._skills.values()]

    def load_skill(self, name: str) -> Skill:
        if name not in self._skills:
            raise SkillNotFoundError(name)
        return self._skills[name]

    def has_skill(self, name: str) -> bool:
        return name in self._skills

    def list_files(self, skill_name: str) -> list[SkillFile]:
        return [file for (s, _), file in self._files.items() if s == skill_name]

    def read_file(self, skill_name: str, relative_path: str) -> SkillFile:
        key = (skill_name, relative_path)
        if key not in self._files:
            raise SkillExecutionError(f"File '{relative_path}' not found in skill '{skill_name}'.")
        return self._files[key]


@pytest.fixture
def memory_skill() -> Skill:
    return Skill(
        name="memory-one",
        description="An in-memory skill",
        location=Path("/__mem__/memory-one"),
        skill_dir=Path("/__mem__/memory-one"),
        instructions="Memory instructions",
    )


class TestAddSource:
    def test_add_source_registers_with_registry(self, memory_skill: Skill) -> None:
        registry = SkillsRegistry()
        source = _InMemorySource({memory_skill.name: memory_skill})
        registry.add_source(source)

        names = [meta.name for meta in registry.list_metadata()]
        assert "memory-one" in names
        assert registry.has_skill("memory-one")
        assert registry.load_skill("memory-one").instructions == "Memory instructions"

    def test_add_source_idempotent(self, memory_skill: Skill) -> None:
        registry = SkillsRegistry()
        source = _InMemorySource({memory_skill.name: memory_skill})

        registry.add_source(source)
        registry.add_source(source)

        assert [s for s in registry.sources if s is source] == [source]

    def test_add_source_rejects_non_source(self) -> None:
        registry = SkillsRegistry()
        with pytest.raises(TypeError):
            registry.add_source("not a source")  # type: ignore[arg-type]

    def test_remove_filesystem_source_is_rejected(self) -> None:
        registry = SkillsRegistry()
        filesystem_source = registry.sources[0]
        with pytest.raises(ValueError):
            registry.remove_source(filesystem_source)

    def test_remove_custom_source_clears_cache(self, memory_skill: Skill) -> None:
        registry = SkillsRegistry()
        source = _InMemorySource({memory_skill.name: memory_skill})
        registry.add_source(source)
        registry.load_skill("memory-one")  # warm the cache

        registry.remove_source(source)

        assert not registry.has_skill("memory-one")
        with pytest.raises(SkillNotFoundError):
            registry.load_skill("memory-one")


class TestCollisionDetection:
    def test_list_metadata_raises_on_collision(self, tmp_path: Path, memory_skill: Skill) -> None:
        _write_skill(tmp_path, "memory-one")
        registry = SkillsRegistry()
        registry.discover([tmp_path])
        registry.add_source(_InMemorySource({memory_skill.name: memory_skill}))

        with pytest.raises(SkillSourceCollisionError):
            registry.list_metadata()

    def test_load_skill_raises_on_collision(self, tmp_path: Path, memory_skill: Skill) -> None:
        _write_skill(tmp_path, "memory-one")
        registry = SkillsRegistry()
        registry.discover([tmp_path])
        registry.add_source(_InMemorySource({memory_skill.name: memory_skill}))

        with pytest.raises(SkillSourceCollisionError):
            registry.load_skill("memory-one")

    def test_collision_error_mentions_source_names(
        self, tmp_path: Path, memory_skill: Skill
    ) -> None:
        _write_skill(tmp_path, "memory-one")
        registry = SkillsRegistry()
        registry.discover([tmp_path])
        registry.add_source(_InMemorySource({memory_skill.name: memory_skill}))

        with pytest.raises(SkillSourceCollisionError) as exc:
            registry.list_metadata()

        msg = str(exc.value)
        assert "filesystem" in msg
        assert "memory" in msg

    def test_len_tolerates_collision(self, tmp_path: Path, memory_skill: Skill) -> None:
        _write_skill(tmp_path, "memory-one")
        registry = SkillsRegistry()
        registry.discover([tmp_path])
        registry.add_source(_InMemorySource({memory_skill.name: memory_skill}))

        assert len(registry) == 1


class TestRouting:
    def test_read_reference_routes_to_owning_source(self, memory_skill: Skill) -> None:
        # The registry normalises ``"note.md"`` to ``"references/note.md"``
        # and delegates to ``source.read_file`` — the custom source only
        # stores raw files keyed by their skill-root-relative path.
        registry = SkillsRegistry()
        source = _InMemorySource({memory_skill.name: memory_skill})
        source.add_file(
            "memory-one",
            SkillFile(
                relative_path="references/note.md",
                mime_type="text/markdown",
                size_bytes=5,
                content_hash="h",
                text_content="Hello",
            ),
        )
        registry.add_source(source)

        result = registry.read_reference("memory-one", "note.md")

        assert result.content == "Hello"
        assert result.path == "references/note.md"
        assert result.filename == "note.md"

    def test_read_reference_via_tool_routes_through_source(self, memory_skill: Skill) -> None:
        registry = SkillsRegistry()
        source = _InMemorySource({memory_skill.name: memory_skill})
        source.add_file(
            "memory-one",
            SkillFile(
                relative_path="references/note.md",
                mime_type="text/markdown",
                size_bytes=12,
                content_hash="h",
                text_content="Tool routing",
            ),
        )
        registry.add_source(source)

        tool = registry.create_read_reference_tool()
        result = tool("memory-one", "note.md")

        assert result == {
            "content": "Tool routing",
            "path": "references/note.md",
            "filename": "note.md",
        }

    def test_read_reference_rejects_path_escape_before_source(self, memory_skill: Skill) -> None:
        registry = SkillsRegistry()
        registry.add_source(_InMemorySource({memory_skill.name: memory_skill}))

        with pytest.raises(SkillExecutionError, match="escapes skill directory"):
            registry.read_reference("memory-one", "../../secret.txt")

    def test_read_reference_errors_when_source_returns_no_content(
        self, memory_skill: Skill
    ) -> None:
        registry = SkillsRegistry()
        source = _InMemorySource({memory_skill.name: memory_skill})
        source.add_file(
            "memory-one",
            SkillFile(
                relative_path="references/empty.md",
                mime_type="text/markdown",
                size_bytes=0,
                content_hash="hash",
            ),
        )
        registry.add_source(source)

        with pytest.raises(SkillExecutionError, match="returned no content"):
            registry.read_reference("memory-one", "empty.md")

    def test_list_files_routes_to_filesystem_source(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "pkg"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: pkg\ndescription: d\n---\n\nBody.\n")
        (skill_dir / "assets").mkdir()
        (skill_dir / "assets" / "template.json").write_text('{"a": 1}')

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        files = registry.list_files("pkg")
        paths = {f.relative_path for f in files}
        assert paths == {"SKILL.md", "assets/template.json"}

    def test_read_file_routes_to_filesystem_source(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "pkg"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: pkg\ndescription: d\n---\n\nBody.\n")
        (skill_dir / "assets").mkdir()
        (skill_dir / "assets" / "template.json").write_text('{"a": 1}')

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        file = registry.read_file("pkg", "assets/template.json")
        assert file.text_content == '{"a": 1}'
        assert file.mime_type == "application/json"

    def test_list_files_routes_to_custom_source(self, memory_skill: Skill) -> None:
        registry = SkillsRegistry()
        source = _InMemorySource({memory_skill.name: memory_skill})
        source.add_file(
            "memory-one",
            SkillFile(
                relative_path="references/guide.md",
                mime_type="text/markdown",
                size_bytes=3,
                content_hash="abc",
            ),
        )
        registry.add_source(source)

        files = registry.list_files("memory-one")
        assert len(files) == 1
        assert files[0].relative_path == "references/guide.md"

    def test_read_file_routes_to_custom_source(self, memory_skill: Skill) -> None:
        registry = SkillsRegistry()
        source = _InMemorySource({memory_skill.name: memory_skill})
        source.add_file(
            "memory-one",
            SkillFile(
                relative_path="assets/data.json",
                mime_type="application/json",
                size_bytes=9,
                content_hash="hash",
                text_content='{"x": 1}',
            ),
        )
        registry.add_source(source)

        file = registry.read_file("memory-one", "assets/data.json")
        assert file.text_content == '{"x": 1}'

    def test_list_files_surfaces_not_implemented_as_execution_error(
        self,
    ) -> None:
        class _NoFilesSource(_InMemorySource):
            def list_files(self, skill_name: str) -> list[SkillFile]:
                raise NotImplementedError

        registry = SkillsRegistry()
        source = _NoFilesSource(
            {
                "memory-one": Skill(
                    name="memory-one",
                    description="d",
                    location=Path("/__m__/m.md"),
                    skill_dir=Path("/__m__"),
                    instructions="",
                )
            }
        )
        registry.add_source(source)

        with pytest.raises(SkillExecutionError, match="does not support listing skill files"):
            registry.list_files("memory-one")

    def test_read_file_surfaces_not_implemented_as_execution_error(
        self,
    ) -> None:
        class _NoFilesSource(_InMemorySource):
            def read_file(self, skill_name: str, relative_path: str) -> SkillFile:
                raise NotImplementedError

        registry = SkillsRegistry()
        source = _NoFilesSource(
            {
                "memory-one": Skill(
                    name="memory-one",
                    description="d",
                    location=Path("/__m__/m.md"),
                    skill_dir=Path("/__m__"),
                    instructions="",
                )
            }
        )
        registry.add_source(source)

        with pytest.raises(SkillExecutionError, match="does not support reading skill files"):
            registry.read_file("memory-one", "whatever.md")


class TestClearSemantics:
    def test_clear_only_resets_filesystem_source(self, tmp_path: Path, memory_skill: Skill) -> None:
        _write_skill(tmp_path, "filesystem-only")
        registry = SkillsRegistry()
        registry.discover([tmp_path])
        registry.add_source(_InMemorySource({memory_skill.name: memory_skill}))

        registry.clear()

        names = {meta.name for meta in registry.list_metadata()}
        assert names == {"memory-one"}


class TestRegistryDiscoverDelegates:
    def test_discover_goes_through_builtin_filesystem_source(self, tmp_path: Path) -> None:
        _write_skill(tmp_path, "alpha")
        registry = SkillsRegistry()
        registry.discover([tmp_path])

        filesystem_source = registry.sources[0]
        assert isinstance(filesystem_source, FilesystemSkillSource)
        assert filesystem_source.has_skill("alpha")
