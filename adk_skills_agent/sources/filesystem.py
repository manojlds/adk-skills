"""Filesystem-backed skill source.

The original adk-skills behaviour: scan one or more directories for ``SKILL.md``
files, parse metadata up-front, and resolve full skill bodies lazily.
"""

from __future__ import annotations

import hashlib
import mimetypes
from collections.abc import Iterator, Sequence
from pathlib import Path

from adk_skills_agent.core.discovery import discover_skills
from adk_skills_agent.core.models import Skill, SkillMetadata
from adk_skills_agent.core.parser import parse_full
from adk_skills_agent.core.paths import validate_skill_root_relative_path
from adk_skills_agent.core.source import SkillFile, SkillSource
from adk_skills_agent.core.validator import validate_skill_metadata
from adk_skills_agent.exceptions import SkillExecutionError, SkillNotFoundError


class FilesystemSkillSource(SkillSource):
    """Skill source backed by ``SKILL.md`` files on the local filesystem.

    Discovery is eager (metadata is parsed at construction / :meth:`add_directories`
    time) and skill loading is lazy. Full skill bodies are cached in-process so
    parsing happens at most once per skill.

    Attributes:
        name: ``"filesystem"`` — used by the registry when reporting collisions.
    """

    name = "filesystem"

    def __init__(
        self,
        directories: Sequence[str | Path] | None = None,
        *,
        strict_validation: bool = True,
    ):
        """Construct a filesystem source.

        Args:
            directories: Optional initial set of directories to scan. Each entry
                may be a string or :class:`Path`; ``~`` is expanded and relative
                paths are resolved to absolute.
            strict_validation: When ``True``, invalid skills are silently
                dropped during discovery (matches the legacy registry
                behaviour).
        """
        self._directories: list[Path] = []
        self._metadata: dict[str, SkillMetadata] = {}
        self._skill_cache: dict[str, Skill] = {}
        self._strict_validation = strict_validation

        if directories:
            self.add_directories(directories)

    @property
    def directories(self) -> list[Path]:
        """Return a copy of the directories this source has scanned."""
        return list(self._directories)

    def add_directories(self, directories: Sequence[str | Path]) -> int:
        """Scan additional directories and index any skills found.

        Args:
            directories: Directories to scan. ``~`` expansion and resolution
                mirrors the legacy :meth:`SkillsRegistry.discover` behaviour.

        Returns:
            The total number of unique skills currently known to this source
            (matches the legacy ``registry.discover`` return value).
        """
        paths = [Path(d).expanduser().resolve() for d in directories]
        self._directories.extend(paths)

        for metadata in discover_skills(paths):
            if self._strict_validation:
                result = validate_skill_metadata(metadata, strict=True)
                if not result.valid:
                    continue

            # Within a single filesystem source we silently skip duplicates
            # (first directory wins). Collisions across sources are handled
            # by the registry, which hard-fails.
            self._metadata.setdefault(metadata.name, metadata)

        return len(self._metadata)

    def list_metadata(self) -> list[SkillMetadata]:
        return list(self._metadata.values())

    def has_skill(self, name: str) -> bool:
        return name in self._metadata

    def iter_names(self) -> Iterator[str]:
        return iter(self._metadata)

    def get_metadata(self, name: str) -> SkillMetadata | None:
        return self._metadata.get(name)

    def refresh(self) -> bool:
        previous_metadata = dict(self._metadata)
        had_cached_skills = bool(self._skill_cache)

        if self._directories:
            directories = list(self._directories)
            self._metadata.clear()
            self._directories.clear()
            self.add_directories(directories)

        self.clear_cache()
        return had_cached_skills or self._metadata != previous_metadata

    def load_skill(self, name: str) -> Skill:
        if name in self._skill_cache:
            return self._skill_cache[name]

        metadata = self._metadata.get(name)
        if metadata is None:
            raise SkillNotFoundError(
                f"Skill '{name}' not found in filesystem source. "
                f"Available skills: {list(self._metadata)}"
            )

        skill = parse_full(metadata.location)
        self._skill_cache[name] = skill
        return skill

    def list_files(self, skill_name: str) -> list[SkillFile]:
        try:
            skill_obj = self.load_skill(skill_name)
        except SkillNotFoundError as e:
            raise SkillNotFoundError(f"Skill '{skill_name}' not found. Cannot list files.") from e

        skill_dir = skill_obj.skill_dir.resolve()
        files: list[SkillFile] = []
        for candidate in sorted(skill_dir.rglob("*")):
            if not candidate.is_file():
                continue
            # Skip common noise; callers can still address them via read_file
            # if they really want, but they should not pollute listings.
            if "__pycache__" in candidate.parts:
                continue
            if candidate.name == ".DS_Store":
                continue

            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            try:
                rel = resolved.relative_to(skill_dir)
            except ValueError:
                # Ignore symlinks/files that resolve outside the skill root.
                continue
            try:
                stat = candidate.stat()
            except OSError:
                continue
            mime_type = mimetypes.guess_type(candidate.name)[0]
            files.append(
                SkillFile(
                    relative_path=rel.as_posix(),
                    mime_type=mime_type,
                    size_bytes=stat.st_size,
                    content_hash=None,
                )
            )
        return files

    def read_file(self, skill_name: str, relative_path: str) -> SkillFile:
        try:
            skill_obj = self.load_skill(skill_name)
        except SkillNotFoundError as e:
            raise SkillNotFoundError(f"Skill '{skill_name}' not found. Cannot read file.") from e

        resolved = self._resolve_under_skill(skill_obj.skill_dir, relative_path)
        if not resolved.exists():
            raise SkillExecutionError(f"File '{relative_path}' not found in skill '{skill_name}'.")
        if not resolved.is_file():
            raise SkillExecutionError(
                f"Path '{relative_path}' in skill '{skill_name}' is not a file"
            )

        try:
            raw_bytes = resolved.read_bytes()
        except OSError as e:
            raise SkillExecutionError(f"Failed to read file '{relative_path}': {e}") from e

        rel = resolved.relative_to(skill_obj.skill_dir.resolve()).as_posix()
        mime_type = mimetypes.guess_type(resolved.name)[0]
        content_hash = hashlib.sha256(raw_bytes).hexdigest()

        text_content, binary_content = _classify_bytes(raw_bytes)

        return SkillFile(
            relative_path=rel,
            mime_type=mime_type,
            size_bytes=len(raw_bytes),
            content_hash=content_hash,
            text_content=text_content,
            binary_content=binary_content,
        )

    def _resolve_under_skill(self, skill_dir: Path, relative_path: str) -> Path:
        """Resolve ``relative_path`` safely under ``skill_dir``.

        Delegates syntactic validation (empty, absolute, ``..``) to the
        shared :func:`validate_skill_root_relative_path` helper, then adds
        filesystem-specific symlink escape protection by resolving the
        candidate and confirming it still lives under ``skill_dir``.
        """
        normalized = validate_skill_root_relative_path(relative_path)

        skill_root = skill_dir.resolve()
        target = skill_root / normalized
        try:
            target_resolved = target.resolve()
        except OSError as e:
            raise SkillExecutionError(f"Invalid path: {e}") from e

        if not target_resolved.is_relative_to(skill_root):
            raise SkillExecutionError(
                f"Access denied: path escapes skill directory: {relative_path!r}"
            )
        return target_resolved

    def clear_cache(self) -> None:
        """Drop any cached fully-loaded skills."""
        self._skill_cache.clear()

    def clear(self) -> None:
        """Forget all discovered skills and directories."""
        self._metadata.clear()
        self._skill_cache.clear()
        self._directories.clear()


def _classify_bytes(data: bytes) -> tuple[str | None, bytes | None]:
    """Split raw bytes into (text_content, binary_content).

    A file is treated as text iff (a) it decodes as UTF-8 without errors and
    (b) it does not contain a NUL byte. The NUL check mirrors the classic
    heuristic used by ``file(1)`` for binary detection. Exactly one of the two
    elements in the returned tuple is non-None.
    """
    if b"\x00" in data:
        return (None, data)
    try:
        return (data.decode("utf-8"), None)
    except UnicodeDecodeError:
        return (None, data)
