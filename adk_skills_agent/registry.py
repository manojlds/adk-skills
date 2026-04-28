"""SkillsRegistry - main interface for managing skills in ADK.

The registry composes one or more :class:`~adk_skills_agent.core.source.SkillSource`
instances. By default it installs a built-in
:class:`~adk_skills_agent.sources.filesystem.FilesystemSkillSource` for the
``discover([...])`` workflow.

Applications bring their own sources (remote registries, object storage,
database schemas, ...) via :meth:`SkillsRegistry.add_source`. All read
operations (``list_metadata``, ``load_skill``, ``read_reference``) are routed
through the registered sources.

All runtime read methods on :class:`SkillsRegistry` are coroutines because
their underlying :class:`SkillSource` methods are coroutines. Construction,
source management, and discovery (which only walks the local filesystem
once at setup time) remain synchronous so that wiring code outside an event
loop continues to work unchanged.

Collisions
    If two sources expose the same skill name, the registry raises
    :class:`~adk_skills_agent.exceptions.SkillSourceCollisionError` instead of
    silently picking a winner. Rename one of the skills or scope your sources
    to avoid overlap.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from adk_skills_agent.core.models import Skill, SkillMetadata, SkillsConfig, ValidationResult
from adk_skills_agent.core.paths import normalize_skill_reference, validate_skill_root_relative_path
from adk_skills_agent.core.source import ReferenceFile, SkillFile, SkillSource
from adk_skills_agent.core.validator import validate_skill_metadata
from adk_skills_agent.exceptions import (
    SkillExecutionError,
    SkillNotFoundError,
    SkillSourceCollisionError,
)
from adk_skills_agent.sources.filesystem import FilesystemSkillSource


class SkillsRegistry:
    """Main registry for managing Agent Skills in ADK.

    The registry is the primary entry point for:

    * Discovering skills from directories (synchronous setup-time helper)
    * Loading full skills on-demand (when activated by an agent, async)
    * Listing available skills across one or more sources (async)
    * Creating tools for ADK agents (:meth:`create_use_skill_tool`, etc.)
    * Reading references and files via the owning source (async)

    Example:
        >>> registry = SkillsRegistry()
        >>> registry.discover(["./skills", "~/.adk/skills"])
        >>> metadata = await registry.list_metadata()
        >>> skill = await registry.load_skill("pdf-processing")
    """

    def __init__(self, config: SkillsConfig | None = None):
        """Initialize skills registry.

        Args:
            config: Optional configuration. Uses defaults if not provided.
        """
        self.config = config or SkillsConfig()
        self._sources: list[SkillSource] = []

        # Built-in filesystem source: receives anything passed to discover().
        self._filesystem_source = FilesystemSkillSource(
            strict_validation=self.config.strict_validation,
        )
        self._sources.append(self._filesystem_source)

        if self.config.auto_discover and self.config.skills_directories:
            self.discover(self.config.skills_directories)

    # Source management ------------------------------------------------------

    def add_source(self, source: SkillSource) -> None:
        """Register an additional :class:`SkillSource` with the registry.

        Sources are consulted in registration order when resolving a skill;
        however the registry hard-fails on name collisions across sources, so
        order is never used to pick a "winner".
        """
        if not isinstance(source, SkillSource):
            raise TypeError(f"Expected a SkillSource subclass, got {type(source).__name__}")
        if source in self._sources:
            return
        self._sources.append(source)

    def remove_source(self, source: SkillSource) -> None:
        """Unregister a previously added source. No-op if absent."""
        if source is self._filesystem_source:
            raise ValueError("Cannot remove the built-in filesystem source.")
        try:
            self._sources.remove(source)
        except ValueError:
            return

    @property
    def sources(self) -> list[SkillSource]:
        """Return a copy of the registered sources (ordered)."""
        return list(self._sources)

    # Discovery --------------------------------------------------------------

    def discover(self, directories: Sequence[str | Path]) -> int:
        """Discover skills from directories using the built-in filesystem source.

        This is a synchronous helper intended for setup-time use. It scans
        the local filesystem once and returns immediately.

        Args:
            directories: List of directory paths to scan.

        Returns:
            Total number of skills the filesystem source currently indexes.

        Example:
            >>> registry = SkillsRegistry()
            >>> count = registry.discover(["./skills"])
            >>> print(f"Found {count} skills")
        """
        return self._filesystem_source.add_directories(directories)

    # Core reads -------------------------------------------------------------

    async def list_metadata(self) -> list[SkillMetadata]:
        """List metadata for every known skill across all sources.

        Raises:
            SkillSourceCollisionError: If two or more sources expose the same
                skill name.
        """
        seen: dict[str, tuple[SkillSource, SkillMetadata]] = {}
        collisions: list[tuple[str, str, str]] = []

        for source in self._sources:
            for metadata in await source.list_metadata():
                previous = seen.get(metadata.name)
                if previous is None:
                    seen[metadata.name] = (source, metadata)
                    continue
                previous_source, _ = previous
                if previous_source is source:
                    # Within-source duplicates are the source's own concern.
                    continue
                collisions.append(
                    (
                        metadata.name,
                        self._describe_source(previous_source),
                        self._describe_source(source),
                    )
                )

        if collisions:
            detail = ", ".join(
                f"'{name}' (in sources {a!r} and {b!r})" for name, a, b in collisions
            )
            raise SkillSourceCollisionError(
                "Skill name collisions detected across sources: " + detail
            )

        return [metadata for _, metadata in seen.values()]

    async def get_metadata(self, name: str) -> SkillMetadata | None:
        """Return metadata for ``name`` or ``None`` if unknown.

        Raises:
            SkillSourceCollisionError: If two or more sources expose ``name``.
        """
        source = await self._find_source(name)
        if source is None:
            return None
        return await source.get_metadata(name)

    async def load_skill(self, name: str) -> Skill:
        """Load full skill content on-demand, consulting every source.

        Args:
            name: Skill name to load.

        Returns:
            Full :class:`Skill` object with instructions. The registry delegates
            each call to the owning source and does not cache loaded
            :class:`Skill` instances; callers should not rely on object
            identity being stable across repeated calls.

        Raises:
            SkillNotFoundError: If no source provides the skill.
            SkillSourceCollisionError: If two or more sources expose ``name``.
        """
        source = await self._resolve_source(name)
        return await source.load_skill(name)

    async def has_skill(self, name: str) -> bool:
        """Check if any source provides ``name``.

        Note:
            Returns ``True`` even when multiple sources provide the same name;
            call :meth:`load_skill` (or :meth:`list_metadata`) to surface the
            collision.
        """
        for source in self._sources:
            if await source.has_skill(name):
                return True
        return False

    # File / reference access ------------------------------------------------

    async def list_files(self, skill_name: str) -> list[SkillFile]:
        """List the files belonging to ``skill_name``.

        Delegates to the source that owns the skill. Sources that cannot
        enumerate their files raise :class:`SkillExecutionError`.
        """
        source = await self._resolve_source(skill_name)
        try:
            return await source.list_files(skill_name)
        except NotImplementedError as e:
            raise SkillExecutionError(
                f"Source '{source.name}' does not support listing skill files"
            ) from e

    async def read_file(self, skill_name: str, relative_path: str) -> SkillFile:
        """Read a single file from ``skill_name`` via its owning source.

        ``relative_path`` is interpreted relative to the skill root. The
        returned :class:`SkillFile` has exactly one of ``text_content`` /
        ``binary_content`` populated.
        """
        source = await self._resolve_source(skill_name)
        try:
            return await source.read_file(skill_name, relative_path)
        except NotImplementedError as e:
            raise SkillExecutionError(
                f"Source '{source.name}' does not support reading skill files"
            ) from e

    async def read_reference(self, skill_name: str, reference: str) -> ReferenceFile:
        """Read a *text* reference file from the source that owns ``skill_name``.

        ``reference`` is interpreted as a path relative to the skill root; a
        bare filename (no ``/``) is resolved under ``references/`` for
        backwards compatibility (see
        :func:`adk_skills_agent.core.paths.normalize_skill_reference`).

        The registry normalises the path, delegates to
        :meth:`SkillSource.read_file` on the owning source, and enforces that
        the payload is text. Binary files raise a :class:`SkillExecutionError`
        suggesting :meth:`read_file` instead. Sources only need to implement
        :meth:`SkillSource.read_file` — they never see reference-path
        normalisation.
        """
        source = await self._resolve_source(skill_name)
        normalized = normalize_skill_reference(reference)
        validated = validate_skill_root_relative_path(normalized)

        try:
            file = await source.read_file(skill_name, validated)
        except NotImplementedError as e:
            raise SkillExecutionError(
                f"Source '{source.name}' does not support reading references"
            ) from e
        except SkillExecutionError as e:
            hint = await self._format_available_hint(source, skill_name, validated)
            if hint and hint not in str(e):
                raise SkillExecutionError(f"{e}{hint}") from e
            raise

        if file.text_content is None:
            if file.binary_content is not None:
                raise SkillExecutionError(
                    f"Reference '{reference}' in skill '{skill_name}' is not a text "
                    "file; use read_file() for binary assets."
                )
            raise SkillExecutionError(
                f"Source '{source.name}' returned no content for '{validated}' "
                f"in skill '{skill_name}'."
            )

        return ReferenceFile(
            content=file.text_content,
            path=validated,
            filename=Path(validated).name,
        )

    @staticmethod
    async def _format_available_hint(
        source: SkillSource, skill_name: str, normalized_path: str
    ) -> str:
        """Return ``" Available: [...]"`` listing sibling files, or ``""``.

        Walks :meth:`SkillSource.list_files` and filters to entries sharing a
        parent directory with ``normalized_path``. Silently returns ``""`` if
        the source does not support ``list_files`` or the listing fails —
        callers treat the hint as best-effort UX, never as a contract.
        """
        try:
            files = await source.list_files(skill_name)
        except Exception:
            # Best-effort UX only: hint failures must never mask the primary
            # read_reference/read_file error.
            return ""
        parent = normalized_path.rsplit("/", 1)[0] if "/" in normalized_path else ""
        siblings = sorted(
            f.relative_path
            for f in files
            if (f.relative_path.rsplit("/", 1)[0] if "/" in f.relative_path else "") == parent
        )
        if not siblings:
            return ""
        return f" Available: {siblings}"

    # Cache / lifecycle ------------------------------------------------------

    async def refresh(self) -> bool:
        """Refresh all sources and return whether any source changed.

        The registry owns source composition, while each source owns its own
        freshness and caching policy. Dynamic sources should override
        :meth:`SkillSource.refresh` to update their catalogs and invalidate
        any source-local loaded-skill caches.
        """
        changed = False
        for source in self._sources:
            changed = (await source.refresh()) or changed
        return changed

    async def clear_cache(self) -> None:
        """Drop source-owned loaded-skill/content caches.

        Kept for compatibility with existing applications. Loaded skill
        freshness is source-owned; the registry delegates cache invalidation to
        each registered source.
        """
        for source in self._sources:
            await source.clear_cache()

    async def clear(self) -> None:
        """Reset the registry's view of skills.

        Clears the built-in filesystem source and source-owned caches. Any
        additional sources registered via :meth:`add_source` are preserved —
        clearing them would be destructive. Callers who want a full reset
        should reconstruct the registry or remove custom sources explicitly.
        """
        self._filesystem_source.clear()
        await self.clear_cache()

    def __repr__(self) -> str:
        return f"SkillsRegistry(sources={[source.name for source in self._sources]})"

    # Tool factories ---------------------------------------------------------

    def create_use_skill_tool(self, *, available_skills_xml: str | None = None) -> Any:
        """Create the async ADK tool for skill activation.

        The returned tool is an ``async def`` coroutine that ADK awaits on
        each invocation; it loads the requested skill from the owning source
        and returns the full instructions plus directory hints.

        Args:
            available_skills_xml: Optional pre-computed ``<available_skills>``
                XML block to embed in the tool description. Callers that want
                this listing should obtain it once via
                ``await registry.to_prompt_xml()`` and pass it here. When
                ``None`` (default), no listing is embedded — pair this with
                prompt injection (:meth:`inject_skills_prompt`) to surface
                skills to the model.

        Returns:
            Async callable tool function for use with ADK agents.
        """
        from adk_skills_agent.tools.use_skill import create_use_skill_tool

        return create_use_skill_tool(self, available_skills_xml=available_skills_xml)

    def create_read_reference_tool(self) -> Any:
        """Create the async ADK tool for reading skill reference files."""
        from adk_skills_agent.tools.read_reference import create_read_reference_tool

        return create_read_reference_tool(self)

    # Prompt injection utilities --------------------------------------------

    async def to_prompt_xml(self) -> str:
        """Generate XML representation of skills for prompt injection."""
        return _format_metadata_xml(await self.list_metadata())

    async def to_prompt_text(self) -> str:
        """Generate plain-text representation of skills for prompt injection."""
        return _format_metadata_text(await self.list_metadata())

    async def get_skills_prompt(self, format: str = "xml") -> str:
        """Return a formatted skills prompt.

        Args:
            format: ``"xml"`` or ``"text"``.

        Raises:
            ValueError: For any unsupported format.
        """
        metadata = await self.list_metadata()
        return _format_metadata(metadata, format=format)

    async def inject_skills_prompt(self, instruction: str, format: str = "xml") -> str:
        """Inject the skills listing into ``instruction``.

        Returns ``instruction`` unchanged when no skills are known.
        """
        metadata = await self.list_metadata()
        if not metadata:
            return instruction
        return f"{instruction}\n\n{_format_metadata(metadata, format=format)}"

    # Validation utilities --------------------------------------------------

    async def validate_all(self, strict: bool = True) -> dict[str, ValidationResult]:
        """Validate every known skill and return a per-name result map."""
        results: dict[str, ValidationResult] = {}
        for metadata in await self.list_metadata():
            results[metadata.name] = validate_skill_metadata(metadata, strict=strict)
        return results

    async def validate_skill_by_name(self, name: str, strict: bool = True) -> ValidationResult:
        """Validate a specific skill by name.

        Raises:
            SkillNotFoundError: If the skill is not known to any source.
        """
        metadata = await self.get_metadata(name)
        if metadata is None:
            available = await self._available_skill_names()
            raise SkillNotFoundError(f"Skill '{name}' not found. Available skills: {available}")
        return validate_skill_metadata(metadata, strict=strict)

    # Internals --------------------------------------------------------------

    async def _available_skill_names(self) -> list[str]:
        """Return sorted, collision-tolerant skill names across all sources."""
        return sorted(await self._available_skill_name_set())

    async def _available_skill_name_set(self) -> set[str]:
        """Return deduplicated skill names across all sources."""
        names: set[str] = set()
        for source in self._sources:
            names.update(await source.iter_names())
        return names

    async def _resolve_source(self, name: str) -> SkillSource:
        """Return the single source that provides ``name``.

        Raises:
            SkillNotFoundError: When no source claims ``name``.
            SkillSourceCollisionError: When two or more sources provide the
                skill.
        """
        source = await self._find_source(name)
        if source is None:
            available = await self._available_skill_names()
            raise SkillNotFoundError(f"Skill '{name}' not found. Available skills: {available}")
        return source

    async def _find_source(self, name: str) -> SkillSource | None:
        """Return the source that provides ``name`` or ``None`` if unknown.

        Raises:
            SkillSourceCollisionError: When two or more sources provide the
                skill.
        """
        owners: list[SkillSource] = []
        for source in self._sources:
            if await source.has_skill(name):
                owners.append(source)
        if not owners:
            return None
        if len(owners) > 1:
            names = [self._describe_source(source) for source in owners]
            raise SkillSourceCollisionError(
                f"Skill '{name}' is provided by multiple sources: {names}"
            )
        return owners[0]

    def _describe_source(self, source: SkillSource) -> str:
        """Return a disambiguated, human-readable source label.

        Includes the configured source name, class name, and registry index so
        collision messages remain actionable even when multiple sources share
        the same ``source.name``.
        """
        class_name = type(source).__name__
        try:
            index = self._sources.index(source)
        except ValueError:
            return f"{source.name}<{class_name}>"
        return f"{source.name}<{class_name}>@{index}"


# Module-level prompt formatters --------------------------------------------


def _format_metadata(metadata: list[SkillMetadata], *, format: str) -> str:
    """Render ``metadata`` according to ``format`` (``"xml"`` or ``"text"``)."""
    if format == "xml":
        return _format_metadata_xml(metadata)
    if format == "text":
        return _format_metadata_text(metadata)
    raise ValueError(f"Unsupported format: {format}. Use 'xml' or 'text'.")


def _format_metadata_xml(metadata: list[SkillMetadata]) -> str:
    """Render ``metadata`` as the legacy ``<available_skills>`` XML block."""
    if not metadata:
        return "<available_skills>\nNo skills available.\n</available_skills>"

    parts = ["<available_skills>"]
    for entry in metadata:
        description = (
            entry.description.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )
        parts.append("  <skill>")
        parts.append(f"    <name>{entry.name}</name>")
        parts.append(f"    <description>{description}</description>")
        parts.append("  </skill>")
    parts.append("</available_skills>")
    return "\n".join(parts)


def _format_metadata_text(metadata: list[SkillMetadata]) -> str:
    """Render ``metadata`` as a plain-text bullet list."""
    if not metadata:
        return "No skills available."
    lines = ["Available Skills:"]
    for entry in metadata:
        lines.append(f"- {entry.name}: {entry.description}")
    return "\n".join(lines)
