"""Tests for the filesystem-backed skill source.

The source only implements raw file I/O (:meth:`list_files`,
:meth:`read_file`). Reference-path normalisation and the text-only
``read_reference`` wrapper live at the :class:`SkillsRegistry` level, so tests
that exercise the reference UX go through a registry here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from adk_skills_agent import SkillsRegistry
from adk_skills_agent.core.source import ReferenceFile, SkillFile
from adk_skills_agent.exceptions import SkillExecutionError, SkillNotFoundError
from adk_skills_agent.sources.filesystem import FilesystemSkillSource


def _registry_for(tmp_path: Path) -> SkillsRegistry:
    registry = SkillsRegistry()
    registry.discover([tmp_path])
    return registry


def _write_skill(tmp_path: Path, name: str, body: str = "Instructions.\n") -> Path:
    skill_dir = tmp_path / name
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Test skill {name}\n---\n\n{body}"
    )
    return skill_dir


class TestFilesystemSourceDiscovery:
    def test_construct_without_directories(self) -> None:
        source = FilesystemSkillSource()
        assert source.list_metadata() == []
        assert source.directories == []

    def test_construct_with_directories_discovers_skills(self, tmp_path: Path) -> None:
        _write_skill(tmp_path, "alpha")
        _write_skill(tmp_path, "beta")

        source = FilesystemSkillSource([tmp_path])

        names = sorted(meta.name for meta in source.list_metadata())
        assert names == ["alpha", "beta"]
        assert source.has_skill("alpha")
        assert not source.has_skill("ghost")

    def test_add_directories_accumulates(self, tmp_path: Path) -> None:
        dir_a = tmp_path / "dir-a"
        dir_a.mkdir()
        _write_skill(dir_a, "alpha")

        dir_b = tmp_path / "dir-b"
        dir_b.mkdir()
        _write_skill(dir_b, "beta")

        source = FilesystemSkillSource()
        assert source.add_directories([dir_a]) == 1
        assert source.add_directories([dir_b]) == 2
        assert {meta.name for meta in source.list_metadata()} == {"alpha", "beta"}

    def test_first_directory_wins_on_same_source_duplicates(self, tmp_path: Path) -> None:
        first = tmp_path / "first"
        first.mkdir()
        _write_skill(first, "dup", body="original")

        second = tmp_path / "second"
        second.mkdir()
        _write_skill(second, "dup", body="override")

        source = FilesystemSkillSource([first, second])
        skill = source.load_skill("dup")
        assert "original" in skill.instructions


class TestFilesystemSourceLoading:
    def test_load_skill_populates_cache(self, tmp_path: Path) -> None:
        _write_skill(tmp_path, "alpha")
        source = FilesystemSkillSource([tmp_path])

        first = source.load_skill("alpha")
        second = source.load_skill("alpha")
        assert first is second

    def test_load_skill_missing_raises(self, tmp_path: Path) -> None:
        source = FilesystemSkillSource([tmp_path])
        with pytest.raises(SkillNotFoundError):
            source.load_skill("ghost")

    def test_clear_resets_state(self, tmp_path: Path) -> None:
        _write_skill(tmp_path, "alpha")
        source = FilesystemSkillSource([tmp_path])
        source.load_skill("alpha")

        source.clear()

        assert source.list_metadata() == []
        assert source.directories == []
        with pytest.raises(SkillNotFoundError):
            source.load_skill("alpha")


class TestFilesystemSourceReferencesViaRegistry:
    """``read_reference`` lives on the registry, not the source.

    These tests drive a real :class:`SkillsRegistry` wired to a
    :class:`FilesystemSkillSource` and exercise the reference UX end-to-end:
    path normalisation, binary rejection, path-escape prevention, and the
    ``Available: [...]`` hint that fires when a reference is missing.
    """

    def test_read_reference_returns_dataclass(self, tmp_path: Path) -> None:
        skill_dir = _write_skill(tmp_path, "docs")
        refs = skill_dir / "references"
        refs.mkdir()
        (refs / "guide.md").write_text("# Guide")

        result = _registry_for(tmp_path).read_reference("docs", "guide.md")

        assert isinstance(result, ReferenceFile)
        assert result.content == "# Guide"
        assert result.filename == "guide.md"
        # The locator is skill-root-relative, source-agnostic.
        assert result.path == "references/guide.md"

    def test_read_reference_rejects_path_escape(self, tmp_path: Path) -> None:
        skill_dir = _write_skill(tmp_path, "docs")
        (skill_dir / "references").mkdir()
        (tmp_path / "secret.txt").write_text("shh")

        with pytest.raises(SkillExecutionError, match="escapes skill directory"):
            _registry_for(tmp_path).read_reference("docs", "../../secret.txt")

    def test_read_reference_when_file_missing(self, tmp_path: Path) -> None:
        # The ``references/`` directory not existing is the same case as the
        # file simply not existing.
        _write_skill(tmp_path, "docs")

        with pytest.raises(SkillExecutionError, match="not found"):
            _registry_for(tmp_path).read_reference("docs", "guide.md")

    def test_read_reference_nested_path_prefixes_references(self, tmp_path: Path) -> None:
        # Matches the legacy call shape: nested paths like ``"guides/intro.md"``
        # should still resolve under ``references/`` for backwards compatibility.
        skill_dir = _write_skill(tmp_path, "docs")
        nested = skill_dir / "references" / "guides"
        nested.mkdir(parents=True)
        (nested / "intro.md").write_text("# Intro")

        result = _registry_for(tmp_path).read_reference("docs", "guides/intro.md")
        assert result.content == "# Intro"
        assert result.filename == "intro.md"
        assert result.path == "references/guides/intro.md"

    def test_read_reference_error_includes_available_hint(self, tmp_path: Path) -> None:
        skill_dir = _write_skill(tmp_path, "docs")
        refs = skill_dir / "references"
        refs.mkdir()
        (refs / "known.md").write_text("known")

        with pytest.raises(SkillExecutionError, match="known.md"):
            _registry_for(tmp_path).read_reference("docs", "missing.md")

    def test_read_reference_accepts_explicit_references_prefix(self, tmp_path: Path) -> None:
        skill_dir = _write_skill(tmp_path, "docs")
        refs = skill_dir / "references"
        refs.mkdir()
        (refs / "guide.md").write_text("# Guide")

        result = _registry_for(tmp_path).read_reference("docs", "references/guide.md")

        assert result.content == "# Guide"
        assert result.filename == "guide.md"
        assert result.path == "references/guide.md"

    def test_read_reference_accepts_asset_path(self, tmp_path: Path) -> None:
        skill_dir = _write_skill(tmp_path, "schema")
        assets = skill_dir / "assets"
        assets.mkdir()
        (assets / "template.json").write_text('{"a": 1}')

        result = _registry_for(tmp_path).read_reference("schema", "assets/template.json")

        assert result.content == '{"a": 1}'
        assert result.filename == "template.json"
        assert result.path == "assets/template.json"

    def test_read_reference_refuses_binary_asset(self, tmp_path: Path) -> None:
        skill_dir = _write_skill(tmp_path, "bins")
        assets = skill_dir / "assets"
        assets.mkdir()
        (assets / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\nbinary\x00data")

        with pytest.raises(SkillExecutionError, match="not a text file"):
            _registry_for(tmp_path).read_reference("bins", "assets/logo.png")

    def test_read_reference_empty_reference_rejected(self, tmp_path: Path) -> None:
        _write_skill(tmp_path, "docs")
        with pytest.raises(SkillExecutionError, match="Empty reference"):
            _registry_for(tmp_path).read_reference("docs", "")


class TestFilesystemSourceFiles:
    def test_list_files_returns_every_file(self, tmp_path: Path) -> None:
        skill_dir = _write_skill(tmp_path, "pkg")
        (skill_dir / "references").mkdir()
        (skill_dir / "references" / "guide.md").write_text("# Guide")
        (skill_dir / "assets").mkdir()
        (skill_dir / "assets" / "template.json").write_text('{"a": 1}')
        (skill_dir / "assets" / "logo.png").write_bytes(b"\x89PNG\x00data")

        source = FilesystemSkillSource([tmp_path])
        files = source.list_files("pkg")

        paths = {f.relative_path for f in files}
        assert paths == {
            "SKILL.md",
            "references/guide.md",
            "assets/template.json",
            "assets/logo.png",
        }
        for file in files:
            assert isinstance(file, SkillFile)
            # Listing does not populate content.
            assert file.text_content is None
            assert file.binary_content is None
            assert file.size_bytes > 0

    def test_list_files_skips_pycache_and_dsstore(self, tmp_path: Path) -> None:
        skill_dir = _write_skill(tmp_path, "pkg")
        pycache = skill_dir / "__pycache__"
        pycache.mkdir()
        (pycache / "foo.cpython-312.pyc").write_bytes(b"\x00\x01")
        (skill_dir / ".DS_Store").write_bytes(b"mac-noise")

        source = FilesystemSkillSource([tmp_path])
        files = source.list_files("pkg")
        paths = {f.relative_path for f in files}
        assert paths == {"SKILL.md"}

    def test_list_files_raises_for_unknown_skill(self, tmp_path: Path) -> None:
        source = FilesystemSkillSource([tmp_path])
        with pytest.raises(SkillNotFoundError):
            source.list_files("ghost")

    def test_read_file_text(self, tmp_path: Path) -> None:
        skill_dir = _write_skill(tmp_path, "pkg")
        (skill_dir / "assets").mkdir()
        (skill_dir / "assets" / "template.json").write_text('{"a": 1}')

        source = FilesystemSkillSource([tmp_path])
        file = source.read_file("pkg", "assets/template.json")

        assert file.relative_path == "assets/template.json"
        assert file.text_content == '{"a": 1}'
        assert file.binary_content is None
        assert file.size_bytes == len('{"a": 1}')
        assert file.mime_type == "application/json"
        assert file.content_hash is not None and len(file.content_hash) == 64
        assert file.is_text is True
        assert file.is_binary is False

    def test_read_file_binary(self, tmp_path: Path) -> None:
        skill_dir = _write_skill(tmp_path, "pkg")
        (skill_dir / "assets").mkdir()
        raw = b"\x89PNG\r\n\x1a\nbinary\x00data"
        (skill_dir / "assets" / "logo.png").write_bytes(raw)

        source = FilesystemSkillSource([tmp_path])
        file = source.read_file("pkg", "assets/logo.png")

        assert file.binary_content == raw
        assert file.text_content is None
        assert file.is_binary is True
        assert file.is_text is False
        assert file.mime_type == "image/png"

    def test_read_file_skill_md(self, tmp_path: Path) -> None:
        _write_skill(tmp_path, "pkg", body="Hello")
        source = FilesystemSkillSource([tmp_path])

        file = source.read_file("pkg", "SKILL.md")
        assert file.text_content is not None
        assert "Hello" in file.text_content

    def test_read_file_rejects_path_escape(self, tmp_path: Path) -> None:
        skill_dir = _write_skill(tmp_path, "pkg")
        (tmp_path / "secret.txt").write_text("shh")
        assert skill_dir.exists()

        source = FilesystemSkillSource([tmp_path])
        with pytest.raises(SkillExecutionError, match="escapes skill directory"):
            source.read_file("pkg", "../secret.txt")

    def test_read_file_rejects_absolute_path(self, tmp_path: Path) -> None:
        _write_skill(tmp_path, "pkg")
        source = FilesystemSkillSource([tmp_path])

        with pytest.raises(SkillExecutionError, match="Absolute"):
            source.read_file("pkg", "/etc/hosts")

    def test_read_file_missing_returns_error(self, tmp_path: Path) -> None:
        _write_skill(tmp_path, "pkg")
        source = FilesystemSkillSource([tmp_path])

        with pytest.raises(SkillExecutionError, match="not found"):
            source.read_file("pkg", "missing.md")

    def test_read_file_not_a_file(self, tmp_path: Path) -> None:
        skill_dir = _write_skill(tmp_path, "pkg")
        (skill_dir / "references").mkdir()

        source = FilesystemSkillSource([tmp_path])
        with pytest.raises(SkillExecutionError, match="is not a file"):
            source.read_file("pkg", "references")
