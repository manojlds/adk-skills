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
        self.load_calls = 0

    def add(self, skill: Skill) -> None:
        self._skills[skill.name] = skill

    def add_file(self, skill_name: str, file: SkillFile) -> None:
        self._files[(skill_name, file.relative_path)] = file

    async def list_metadata(self) -> list[SkillMetadata]:
        return [skill.to_metadata() for skill in self._skills.values()]

    async def load_skill(self, name: str) -> Skill:
        self.load_calls += 1
        if name not in self._skills:
            raise SkillNotFoundError(name)
        return self._skills[name]

    async def has_skill(self, name: str) -> bool:
        return name in self._skills

    async def list_files(self, skill_name: str) -> list[SkillFile]:
        return [file for (s, _), file in self._files.items() if s == skill_name]

    async def read_file(self, skill_name: str, relative_path: str) -> SkillFile:
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
    async def test_add_source_registers_with_registry(self, memory_skill: Skill) -> None:
        registry = SkillsRegistry()
        source = _InMemorySource({memory_skill.name: memory_skill})
        registry.add_source(source)

        names = [meta.name for meta in await registry.list_metadata()]
        assert "memory-one" in names
        assert await registry.has_skill("memory-one")
        assert (await registry.load_skill("memory-one")).instructions == "Memory instructions"

    async def test_add_source_idempotent(self, memory_skill: Skill) -> None:
        registry = SkillsRegistry()
        source = _InMemorySource({memory_skill.name: memory_skill})

        registry.add_source(source)
        registry.add_source(source)

        assert [s for s in registry.sources if s is source] == [source]

    async def test_load_skill_delegates_to_source_each_time(self, memory_skill: Skill) -> None:
        registry = SkillsRegistry()
        source = _InMemorySource({memory_skill.name: memory_skill})
        registry.add_source(source)

        assert (await registry.load_skill("memory-one")).instructions == "Memory instructions"

        source.add(
            Skill(
                name="memory-one",
                description="An in-memory skill",
                location=Path("/__mem__/memory-one"),
                skill_dir=Path("/__mem__/memory-one"),
                instructions="Updated instructions",
            )
        )

        assert (await registry.load_skill("memory-one")).instructions == "Updated instructions"
        assert source.load_calls == 2

    def test_add_source_rejects_non_source(self) -> None:
        registry = SkillsRegistry()
        with pytest.raises(TypeError):
            registry.add_source("not a source")  # type: ignore[arg-type]

    def test_remove_filesystem_source_is_rejected(self) -> None:
        registry = SkillsRegistry()
        filesystem_source = registry.sources[0]
        with pytest.raises(ValueError):
            registry.remove_source(filesystem_source)

    async def test_remove_custom_source_drops_skill(self, memory_skill: Skill) -> None:
        registry = SkillsRegistry()
        source = _InMemorySource({memory_skill.name: memory_skill})
        registry.add_source(source)
        await registry.load_skill("memory-one")

        registry.remove_source(source)

        assert not await registry.has_skill("memory-one")
        with pytest.raises(SkillNotFoundError):
            await registry.load_skill("memory-one")

    async def test_add_source_surfaces_collisions(self, tmp_path: Path) -> None:
        _write_skill(tmp_path, "dup")
        registry = SkillsRegistry()
        registry.discover([tmp_path])

        await registry.load_skill("dup")

        other = Skill(
            name="dup",
            description="duplicate",
            location=Path("/__mem__/dup"),
            skill_dir=Path("/__mem__/dup"),
            instructions="other",
        )
        registry.add_source(_InMemorySource({"dup": other}))

        with pytest.raises(SkillSourceCollisionError):
            await registry.load_skill("dup")


class TestCollisionDetection:
    async def test_list_metadata_raises_on_collision(
        self, tmp_path: Path, memory_skill: Skill
    ) -> None:
        _write_skill(tmp_path, "memory-one")
        registry = SkillsRegistry()
        registry.discover([tmp_path])
        registry.add_source(_InMemorySource({memory_skill.name: memory_skill}))

        with pytest.raises(SkillSourceCollisionError):
            await registry.list_metadata()

    async def test_load_skill_raises_on_collision(
        self, tmp_path: Path, memory_skill: Skill
    ) -> None:
        _write_skill(tmp_path, "memory-one")
        registry = SkillsRegistry()
        registry.discover([tmp_path])
        registry.add_source(_InMemorySource({memory_skill.name: memory_skill}))

        with pytest.raises(SkillSourceCollisionError):
            await registry.load_skill("memory-one")

    async def test_collision_error_mentions_source_names(
        self, tmp_path: Path, memory_skill: Skill
    ) -> None:
        _write_skill(tmp_path, "memory-one")
        registry = SkillsRegistry()
        registry.discover([tmp_path])
        registry.add_source(_InMemorySource({memory_skill.name: memory_skill}))

        with pytest.raises(SkillSourceCollisionError) as exc:
            await registry.list_metadata()

        msg = str(exc.value)
        assert "filesystem" in msg
        assert "memory" in msg

    async def test_collision_error_disambiguates_sources_with_same_name(self) -> None:
        class _DefaultNamedSource(SkillSource):
            # Intentionally keep default SkillSource.name == "source"
            def __init__(self, skill: Skill) -> None:
                self._skill = skill

            async def list_metadata(self) -> list[SkillMetadata]:
                return [self._skill.to_metadata()]

            async def load_skill(self, name: str) -> Skill:
                if name != self._skill.name:
                    raise SkillNotFoundError(name)
                return self._skill

        skill_a = Skill(
            name="dup",
            description="dup a",
            location=Path("/__mem__/a/SKILL.md"),
            skill_dir=Path("/__mem__/a"),
            instructions="a",
        )
        skill_b = Skill(
            name="dup",
            description="dup b",
            location=Path("/__mem__/b/SKILL.md"),
            skill_dir=Path("/__mem__/b"),
            instructions="b",
        )

        registry = SkillsRegistry()
        registry.add_source(_DefaultNamedSource(skill_a))
        registry.add_source(_DefaultNamedSource(skill_b))

        with pytest.raises(SkillSourceCollisionError) as exc:
            await registry.load_skill("dup")

        msg = str(exc.value)
        assert "source<_DefaultNamedSource>@1" in msg
        assert "source<_DefaultNamedSource>@2" in msg

    async def test_available_names_use_iter_names_without_materializing_metadata(
        self,
    ) -> None:
        class _NamesOnlySource(SkillSource):
            name = "names-only"

            async def list_metadata(self) -> list[SkillMetadata]:
                raise AssertionError("list_metadata should not be called by missing-skill error")

            async def iter_names(self) -> list[str]:
                return ["alpha", "beta"]

            async def load_skill(self, name: str) -> Skill:
                raise SkillNotFoundError(name)

        registry = SkillsRegistry()
        registry.add_source(_NamesOnlySource())

        with pytest.raises(SkillNotFoundError, match="Available skills"):
            await registry.load_skill("missing")

    async def test_missing_skill_error_is_not_masked_by_collision(
        self, tmp_path: Path, memory_skill: Skill
    ) -> None:
        _write_skill(tmp_path, "memory-one")
        registry = SkillsRegistry()
        registry.discover([tmp_path])
        registry.add_source(_InMemorySource({memory_skill.name: memory_skill}))

        with pytest.raises(SkillNotFoundError):
            await registry.load_skill("not-here")

    async def test_validate_missing_skill_error_is_not_masked_by_collision(
        self, tmp_path: Path, memory_skill: Skill
    ) -> None:
        _write_skill(tmp_path, "memory-one")
        registry = SkillsRegistry()
        registry.discover([tmp_path])
        registry.add_source(_InMemorySource({memory_skill.name: memory_skill}))

        with pytest.raises(SkillNotFoundError):
            await registry.validate_skill_by_name("not-here")


class TestRouting:
    async def test_read_reference_routes_to_owning_source(self, memory_skill: Skill) -> None:
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

        result = await registry.read_reference("memory-one", "note.md")

        assert result.content == "Hello"
        assert result.path == "references/note.md"
        assert result.filename == "note.md"

    async def test_read_reference_via_tool_routes_through_source(self, memory_skill: Skill) -> None:
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
        result = await tool("memory-one", "note.md")

        assert result == {
            "content": "Tool routing",
            "path": "references/note.md",
            "filename": "note.md",
        }

    async def test_read_reference_rejects_path_escape_before_source(
        self, memory_skill: Skill
    ) -> None:
        registry = SkillsRegistry()
        registry.add_source(_InMemorySource({memory_skill.name: memory_skill}))

        with pytest.raises(SkillExecutionError, match="escapes skill directory"):
            await registry.read_reference("memory-one", "../../secret.txt")

    async def test_read_reference_errors_when_source_returns_no_content(
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
            await registry.read_reference("memory-one", "empty.md")

    async def test_read_reference_preserves_primary_error_when_hinting_fails(
        self, memory_skill: Skill
    ) -> None:
        class _HintCrashSource(_InMemorySource):
            async def read_file(self, skill_name: str, relative_path: str) -> SkillFile:
                raise SkillExecutionError("primary read failure")

            async def list_files(self, skill_name: str) -> list[SkillFile]:
                # Simulate a secondary backend failure while computing the
                # optional "Available: [...]" hint.
                raise RuntimeError("hint backend unavailable")

        registry = SkillsRegistry()
        registry.add_source(_HintCrashSource({memory_skill.name: memory_skill}))

        with pytest.raises(SkillExecutionError, match="primary read failure"):
            await registry.read_reference("memory-one", "note.md")

    async def test_list_files_routes_to_filesystem_source(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "pkg"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: pkg\ndescription: d\n---\n\nBody.\n")
        (skill_dir / "assets").mkdir()
        (skill_dir / "assets" / "template.json").write_text('{"a": 1}')

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        files = await registry.list_files("pkg")
        paths = {f.relative_path for f in files}
        assert paths == {"SKILL.md", "assets/template.json"}

    async def test_read_file_routes_to_filesystem_source(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "pkg"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: pkg\ndescription: d\n---\n\nBody.\n")
        (skill_dir / "assets").mkdir()
        (skill_dir / "assets" / "template.json").write_text('{"a": 1}')

        registry = SkillsRegistry()
        registry.discover([tmp_path])

        file = await registry.read_file("pkg", "assets/template.json")
        assert file.text_content == '{"a": 1}'
        assert file.mime_type == "application/json"

    async def test_list_files_routes_to_custom_source(self, memory_skill: Skill) -> None:
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

        files = await registry.list_files("memory-one")
        assert len(files) == 1
        assert files[0].relative_path == "references/guide.md"

    async def test_read_file_routes_to_custom_source(self, memory_skill: Skill) -> None:
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

        file = await registry.read_file("memory-one", "assets/data.json")
        assert file.text_content == '{"x": 1}'

    async def test_list_files_surfaces_not_implemented_as_execution_error(
        self,
    ) -> None:
        class _NoFilesSource(_InMemorySource):
            async def list_files(self, skill_name: str) -> list[SkillFile]:
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
            await registry.list_files("memory-one")

    async def test_read_file_surfaces_not_implemented_as_execution_error(
        self,
    ) -> None:
        class _NoFilesSource(_InMemorySource):
            async def read_file(self, skill_name: str, relative_path: str) -> SkillFile:
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
            await registry.read_file("memory-one", "whatever.md")


class TestRefreshSemantics:
    async def test_refresh_delegates_to_sources_and_returns_whether_any_changed(
        self, memory_skill: Skill
    ) -> None:
        class _RefreshableSource(_InMemorySource):
            def __init__(self, *, changed: bool) -> None:
                super().__init__({memory_skill.name: memory_skill})
                self.changed = changed
                self.refresh_calls = 0

            async def refresh(self) -> bool:
                self.refresh_calls += 1
                return self.changed

        changed = _RefreshableSource(changed=True)
        unchanged = _RefreshableSource(changed=False)
        registry = SkillsRegistry()
        registry.add_source(changed)
        registry.add_source(unchanged)

        assert await registry.refresh() is True
        assert changed.refresh_calls == 1
        assert unchanged.refresh_calls == 1

    async def test_clear_cache_delegates_to_sources(self, memory_skill: Skill) -> None:
        class _CacheableSource(_InMemorySource):
            def __init__(self) -> None:
                super().__init__({memory_skill.name: memory_skill})
                self.clear_cache_calls = 0

            async def clear_cache(self) -> None:
                self.clear_cache_calls += 1

        source = _CacheableSource()
        registry = SkillsRegistry()
        registry.add_source(source)

        await registry.clear_cache()

        assert source.clear_cache_calls == 1


class TestClearSemantics:
    async def test_clear_only_resets_filesystem_source(
        self, tmp_path: Path, memory_skill: Skill
    ) -> None:
        _write_skill(tmp_path, "filesystem-only")
        registry = SkillsRegistry()
        registry.discover([tmp_path])
        registry.add_source(_InMemorySource({memory_skill.name: memory_skill}))

        await registry.clear()

        names = {meta.name for meta in await registry.list_metadata()}
        assert names == {"memory-one"}


class TestRegistryDiscoverDelegates:
    async def test_discover_goes_through_builtin_filesystem_source(self, tmp_path: Path) -> None:
        _write_skill(tmp_path, "alpha")
        registry = SkillsRegistry()
        registry.discover([tmp_path])

        filesystem_source = registry.sources[0]
        assert isinstance(filesystem_source, FilesystemSkillSource)
        assert await filesystem_source.has_skill("alpha")

    async def test_discover_surfaces_collisions(self, tmp_path: Path) -> None:
        registry = SkillsRegistry()
        memory_skill = Skill(
            name="dup",
            description="memory copy",
            location=Path("/__mem__/dup/SKILL.md"),
            skill_dir=Path("/__mem__/dup"),
            instructions="Memory instructions",
        )
        registry.add_source(_InMemorySource({"dup": memory_skill}))

        await registry.load_skill("dup")
        _write_skill(tmp_path, "dup")
        registry.discover([tmp_path])

        with pytest.raises(SkillSourceCollisionError):
            await registry.load_skill("dup")
