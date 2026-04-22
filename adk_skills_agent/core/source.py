"""Pluggable skill source abstraction.

A :class:`SkillSource` is the backing store behind a :class:`SkillsRegistry`.
It owns discovery, loading, and content access for a group of skills. The
registry composes one or more sources and routes read operations to whichever
source provides the requested skill.

This package ships one first-party implementation:

* :class:`adk_skills_agent.sources.filesystem.FilesystemSkillSource` — scans
  directories of ``SKILL.md`` files.

Applications bring their own sources for everything else (database schemas,
remote registries, object storage, multi-file version stores, …) by
subclassing this abstract base class and plugging into a registry via
:meth:`SkillsRegistry.add_source`. See
``tests/integration/test_sqlite_skill_source.py`` in the source tree for a
worked multi-file SQLite-backed source.

Note:
    Not every source supports every capability. File access may or may not be
    available depending on how the source stores auxiliary content. Sources
    that cannot honour a capability should raise
    :class:`NotImplementedError` from the relevant method; the registry converts
    this into a
    :class:`~adk_skills_agent.exceptions.SkillExecutionError` with a helpful
    message. ``read_reference`` is implemented once at the registry level on
    top of :meth:`SkillSource.read_file`, so sources that store files never
    need to implement reference-path normalisation themselves.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass

from adk_skills_agent.core.models import Skill, SkillMetadata


@dataclass
class ReferenceFile:
    """Content of a reference file read from a skill.

    Attributes:
        content: The file's decoded UTF-8 text content.
        path: Skill-root-relative locator for the reference (for example
            ``"references/guide.md"`` or ``"assets/template.json"``). Always
            uses ``/`` as the separator and contains no leading slash or
            ``..`` segments. Callers that need an on-disk path for
            filesystem-backed skills can join with ``Skill.skill_dir``.
        filename: The leaf filename of the reference (``"guide.md"``).
    """

    content: str
    path: str
    filename: str


@dataclass
class SkillFile:
    """A single file belonging to a skill package.

    A :class:`SkillFile` is the generic currency of :meth:`SkillSource.list_files`
    and :meth:`SkillSource.read_file`. It can describe any file living inside a
    skill (the ``SKILL.md`` itself, anything under ``references/``, ``assets/``,
    or any other folder the skill author creates). Exactly one of
    :attr:`text_content` / :attr:`binary_content` is populated when the file is
    fully read; both may be ``None`` when returned from a metadata-only listing.

    Attributes:
        relative_path: Path relative to the skill root, using ``/`` as the
            separator (``"SKILL.md"``, ``"references/guide.md"``,
            ``"assets/template.json"``). Never contains ``..`` or a leading ``/``.
        mime_type: Best-effort MIME type; ``None`` if the source cannot determine
            one. Useful for callers that need to serve the file to the browser
            or pick a renderer.
        size_bytes: File size in bytes.
        content_hash: Opaque content hash (sources typically use a hex-encoded
            SHA-256 digest). ``None`` if the source does not track one.
        text_content: Decoded UTF-8 text content; ``None`` when the file is
            binary or when only metadata was requested.
        binary_content: Raw bytes; ``None`` when the file is text or when only
            metadata was requested.
    """

    relative_path: str
    mime_type: str | None
    size_bytes: int
    content_hash: str | None
    text_content: str | None = None
    binary_content: bytes | None = None

    @property
    def is_text(self) -> bool:
        """``True`` if :attr:`text_content` is populated."""
        return self.text_content is not None

    @property
    def is_binary(self) -> bool:
        """``True`` if :attr:`binary_content` is populated."""
        return self.binary_content is not None


class SkillSource(abc.ABC):
    """Abstract base class for pluggable skill sources.

    Subclasses must implement :meth:`list_metadata` and :meth:`load_skill`.
    Override :meth:`has_skill` for efficiency when the default linear scan is
    too expensive. :meth:`list_files` and :meth:`read_file` are optional; the
    defaults raise :class:`NotImplementedError` so that the registry can
    surface a clear error to callers.

    The registry exposes ``read_reference`` by normalising the caller's
    input and delegating to :meth:`read_file`, so individual sources do not
    need to reimplement the ``references/``-prefixing / path-escape logic.
    Implementing :meth:`read_file` is sufficient to make ``read_reference``
    work end-to-end.

    Subclasses should set :attr:`name` to a short, human-readable identifier
    (for example ``"filesystem"`` or ``"registry"``); it is used in error
    messages when multiple sources expose the same skill name.
    """

    name: str = "source"

    @abc.abstractmethod
    def list_metadata(self) -> list[SkillMetadata]:
        """Return metadata for every skill this source currently provides.

        The registry calls this method whenever it needs a fresh view of the
        source; implementations should return a new list on each call so
        callers can safely mutate the result.
        """

    @abc.abstractmethod
    def load_skill(self, name: str) -> Skill:
        """Return the fully loaded :class:`Skill` for ``name``.

        Raises:
            adk_skills_agent.exceptions.SkillNotFoundError: If ``name`` is not
                provided by this source.
        """

    def has_skill(self, name: str) -> bool:
        """Return ``True`` if this source provides a skill called ``name``.

        The default implementation iterates :meth:`list_metadata`. Subclasses
        should override this when a cheaper existence check is available
        (for example a ``SELECT 1`` against the database).
        """
        return any(meta.name == name for meta in self.list_metadata())

    def list_files(self, skill_name: str) -> list[SkillFile]:
        """Return metadata for every file belonging to ``skill_name``.

        Implementations should return a :class:`SkillFile` for each file in
        the skill package (``SKILL.md``, everything under ``references/`` and
        ``assets/``, and any other files the skill author includes). The
        returned :class:`SkillFile` instances carry path/size/mime info only;
        :attr:`SkillFile.text_content` and :attr:`SkillFile.binary_content`
        are typically ``None`` for listings.

        The default implementation raises :class:`NotImplementedError`. Sources
        that can enumerate their files should override this method; the
        registry surfaces a clear error when a source cannot honour the call.
        """
        raise NotImplementedError(f"{type(self).__name__} does not support listing skill files")

    def read_file(self, skill_name: str, relative_path: str) -> SkillFile:
        """Read a single file from a skill package.

        ``relative_path`` is interpreted relative to the skill root and should
        use ``/`` as the separator. Implementations must reject paths that
        attempt to escape the skill package (``..`` segments, absolute paths,
        symlinks that leave the package root). The returned :class:`SkillFile`
        must populate exactly one of :attr:`SkillFile.text_content` /
        :attr:`SkillFile.binary_content` so callers can tell text files from
        binaries.

        The default implementation raises :class:`NotImplementedError`.
        """
        raise NotImplementedError(f"{type(self).__name__} does not support reading skill files")
