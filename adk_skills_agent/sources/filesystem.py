"""Filesystem-backed skill source.

The original adk-skills behaviour: scan one or more directories for ``SKILL.md``
files, parse metadata up-front, and resolve full skill bodies lazily.

Discovery (``__init__`` / :meth:`add_directories`) is synchronous because it
runs once at setup time. Runtime methods are ``async`` to satisfy the
:class:`~adk_skills_agent.core.source.SkillSource` contract; blocking parsing
and file I/O are pushed off the event loop with :func:`asyncio.to_thread`.
"""

from __future__ import annotations

import asyncio
import hashlib
import mimetypes
import threading
from collections.abc import Sequence
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
    _MAX_REFRESH_RETRIES = 10
    _MAX_LOAD_RETRIES = 10

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
        self._state_lock = threading.RLock()
        self._generation = 0
        self._strict_validation = strict_validation

        if directories:
            self.add_directories(directories)

    @property
    def directories(self) -> list[Path]:
        """Return a copy of the directories this source has scanned."""
        with self._state_lock:
            return list(self._directories)

    def add_directories(self, directories: Sequence[str | Path]) -> int:
        """Scan additional directories and index any skills found.

        This is a synchronous setup-time helper. Runtime reads are concurrency
        guarded, but callers should avoid mutating the discovered directory set
        from another OS thread while async reads are active.

        Args:
            directories: Directories to scan. ``~`` expansion and resolution
                mirrors the legacy :meth:`SkillsRegistry.discover` behaviour.

        Returns:
            The total number of unique skills currently known to this source
            (matches the legacy ``registry.discover`` return value).
        """
        paths = [Path(d).expanduser().resolve() for d in directories]
        discovered = self._discover_metadata(paths)

        with self._state_lock:
            self._directories.extend(paths)
            for metadata in discovered.values():
                self._metadata.setdefault(metadata.name, metadata)

            self._generation += 1
            return len(self._metadata)

    def _discover_metadata(self, paths: Sequence[Path]) -> dict[str, SkillMetadata]:
        metadata_by_name: dict[str, SkillMetadata] = {}
        for metadata in discover_skills(list(paths)):
            if self._strict_validation:
                result = validate_skill_metadata(metadata, strict=True)
                if not result.valid:
                    continue

            # Within a single filesystem source we silently skip duplicates
            # (first directory wins). Collisions across sources are handled
            # by the registry, which hard-fails.
            metadata_by_name.setdefault(metadata.name, metadata)
        return metadata_by_name

    async def list_metadata(self) -> list[SkillMetadata]:
        with self._state_lock:
            return list(self._metadata.values())

    async def has_skill(self, name: str) -> bool:
        with self._state_lock:
            return name in self._metadata

    async def iter_names(self) -> list[str]:
        with self._state_lock:
            return list(self._metadata)

    async def get_metadata(self, name: str) -> SkillMetadata | None:
        with self._state_lock:
            return self._metadata.get(name)

    async def refresh(self) -> bool:
        for _attempt in range(self._MAX_REFRESH_RETRIES):
            with self._state_lock:
                directories = list(self._directories)

            refreshed_metadata = await asyncio.to_thread(self._discover_metadata, directories)

            with self._state_lock:
                if self._directories != directories:
                    # discover()/add_directories() ran while we were scanning.
                    # Retry against the new full directory set rather than
                    # overwriting those additions with the stale snapshot.
                    continue

                previous_metadata = dict(self._metadata)
                had_cached_skills = bool(self._skill_cache)

                self._metadata = refreshed_metadata
                self._skill_cache.clear()
                self._generation += 1
                return had_cached_skills or self._metadata != previous_metadata

        raise SkillExecutionError(
            "Filesystem skill refresh could not stabilize because directories "
            "changed repeatedly during discovery. Retry refresh after discovery "
            "updates finish."
        )

    async def load_skill(self, name: str) -> Skill:
        for _attempt in range(self._MAX_LOAD_RETRIES):
            with self._state_lock:
                cached = self._skill_cache.get(name)
                if cached is not None:
                    return cached

                metadata = self._metadata.get(name)
                generation = self._generation
                available = list(self._metadata)

            if metadata is None:
                raise SkillNotFoundError(
                    f"Skill '{name}' not found in filesystem source. Available skills: {available}"
                )

            skill = await asyncio.to_thread(parse_full, metadata.location)

            with self._state_lock:
                cached = self._skill_cache.get(name)
                if cached is not None:
                    return cached
                # Refresh/cache-clear may have landed while parse_full was in
                # a worker thread; never cache a result from an older catalog.
                if generation != self._generation or self._metadata.get(name) != metadata:
                    continue
                self._skill_cache[name] = skill
                return skill

        raise SkillExecutionError(
            f"Skill '{name}' could not be loaded because the filesystem catalog "
            "changed repeatedly during parsing. Retry after discovery updates finish."
        )

    async def list_files(self, skill_name: str) -> list[SkillFile]:
        try:
            skill_obj = await self.load_skill(skill_name)
        except SkillNotFoundError as e:
            raise SkillNotFoundError(f"Skill '{skill_name}' not found. Cannot list files.") from e

        return await asyncio.to_thread(self._list_files_sync, skill_obj)

    @staticmethod
    def _list_files_sync(skill_obj: Skill) -> list[SkillFile]:
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

    async def read_file(self, skill_name: str, relative_path: str) -> SkillFile:
        try:
            skill_obj = await self.load_skill(skill_name)
        except SkillNotFoundError as e:
            raise SkillNotFoundError(f"Skill '{skill_name}' not found. Cannot read file.") from e

        return await asyncio.to_thread(self._read_file_sync, skill_obj, skill_name, relative_path)

    def _read_file_sync(self, skill_obj: Skill, skill_name: str, relative_path: str) -> SkillFile:
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

    async def clear_cache(self) -> None:
        """Drop any cached fully-loaded skills."""
        with self._state_lock:
            self._skill_cache.clear()
            self._generation += 1

    def clear(self) -> None:
        """Forget all discovered skills and directories.

        This synchronous setup-time helper should not be called from another OS
        thread while async runtime reads are active.
        """
        with self._state_lock:
            self._metadata.clear()
            self._skill_cache.clear()
            self._directories.clear()
            self._generation += 1


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
