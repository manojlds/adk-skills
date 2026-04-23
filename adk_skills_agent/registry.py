"""SkillsRegistry - main interface for managing skills in ADK.

The registry composes one or more :class:`~adk_skills_agent.core.source.SkillSource`
instances. By default it installs a built-in
:class:`~adk_skills_agent.sources.filesystem.FilesystemSkillSource` for the
``discover([...])`` workflow.

Applications bring their own sources (remote registries, object storage,
database schemas, ...) via :meth:`SkillsRegistry.add_source`. All read
operations (``list_metadata``, ``load_skill``, ``read_reference``) are routed
through the registered sources.

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

    * Discovering skills from directories (metadata-only, fast)
    * Loading full skills on-demand (when activated by an agent)
    * Listing available skills across one or more sources
    * Creating tools for ADK agents (:meth:`create_use_skill_tool`, etc.)
    * Reading references and files via the owning source

    Example:
        >>> registry = SkillsRegistry()
        >>> registry.discover(["./skills", "~/.adk/skills"])
        >>> metadata = registry.list_metadata()
        >>> skill = registry.load_skill("pdf-processing")
    """

    def __init__(self, config: SkillsConfig | None = None):
        """Initialize skills registry.

        Args:
            config: Optional configuration. Uses defaults if not provided.
        """
        self.config = config or SkillsConfig()
        self._sources: list[SkillSource] = []
        self._skill_cache: dict[str, Skill] = {}

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
        self._skill_cache.clear()

    def remove_source(self, source: SkillSource) -> None:
        """Unregister a previously added source. No-op if absent."""
        if source is self._filesystem_source:
            raise ValueError("Cannot remove the built-in filesystem source.")
        try:
            self._sources.remove(source)
        except ValueError:
            return
        self._skill_cache.clear()

    @property
    def sources(self) -> list[SkillSource]:
        """Return a copy of the registered sources (ordered)."""
        return list(self._sources)

    # Discovery --------------------------------------------------------------

    def discover(self, directories: Sequence[str | Path]) -> int:
        """Discover skills from directories using the built-in filesystem source.

        Args:
            directories: List of directory paths to scan.

        Returns:
            Total number of skills the filesystem source currently indexes.

        Example:
            >>> registry = SkillsRegistry()
            >>> count = registry.discover(["./skills"])
            >>> print(f"Found {count} skills")
        """
        count = self._filesystem_source.add_directories(directories)
        # Filesystem discovery can introduce new names/collisions, so cached
        # skills loaded before this call may no longer be valid.
        self._skill_cache.clear()
        return count

    # Core reads -------------------------------------------------------------

    def list_metadata(self) -> list[SkillMetadata]:
        """List metadata for every known skill across all sources.

        Raises:
            SkillSourceCollisionError: If two or more sources expose the same
                skill name.
        """
        seen: dict[str, tuple[SkillSource, SkillMetadata]] = {}
        collisions: list[tuple[str, str, str]] = []

        for source in self._sources:
            for metadata in source.list_metadata():
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

    def get_metadata(self, name: str) -> SkillMetadata | None:
        """Return metadata for ``name`` or ``None`` if unknown.

        Raises:
            SkillSourceCollisionError: If two or more sources expose ``name``.
        """
        source = self._find_source(name)
        if source is None:
            return None
        return source.get_metadata(name)

    def load_skill(self, name: str) -> Skill:
        """Load full skill content on-demand, consulting every source.

        Args:
            name: Skill name to load.

        Returns:
            Full :class:`Skill` object with instructions.

        Raises:
            SkillNotFoundError: If no source provides the skill.
            SkillSourceCollisionError: If two or more sources expose ``name``.
        """
        if name in self._skill_cache:
            return self._skill_cache[name]

        source = self._resolve_source(name)
        skill = source.load_skill(name)
        self._skill_cache[name] = skill
        return skill

    def has_skill(self, name: str) -> bool:
        """Check if any source provides ``name``.

        Note:
            Returns ``True`` even when multiple sources provide the same name;
            call :meth:`load_skill` (or :meth:`list_metadata`) to surface the
            collision.
        """
        return any(source.has_skill(name) for source in self._sources)

    # File / reference access ------------------------------------------------

    def list_files(self, skill_name: str) -> list[SkillFile]:
        """List the files belonging to ``skill_name``.

        Delegates to the source that owns the skill. Sources that cannot
        enumerate their files raise :class:`SkillExecutionError`.
        """
        source = self._resolve_source(skill_name)
        try:
            return source.list_files(skill_name)
        except NotImplementedError as e:
            raise SkillExecutionError(
                f"Source '{source.name}' does not support listing skill files"
            ) from e

    def read_file(self, skill_name: str, relative_path: str) -> SkillFile:
        """Read a single file from ``skill_name`` via its owning source.

        ``relative_path`` is interpreted relative to the skill root. The
        returned :class:`SkillFile` has exactly one of ``text_content`` /
        ``binary_content`` populated.
        """
        source = self._resolve_source(skill_name)
        try:
            return source.read_file(skill_name, relative_path)
        except NotImplementedError as e:
            raise SkillExecutionError(
                f"Source '{source.name}' does not support reading skill files"
            ) from e

    def read_reference(self, skill_name: str, reference: str) -> ReferenceFile:
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
        source = self._resolve_source(skill_name)
        normalized = normalize_skill_reference(reference)
        validated = validate_skill_root_relative_path(normalized)

        try:
            file = source.read_file(skill_name, validated)
        except NotImplementedError as e:
            raise SkillExecutionError(
                f"Source '{source.name}' does not support reading references"
            ) from e
        except SkillExecutionError as e:
            hint = self._format_available_hint(source, skill_name, validated)
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
    def _format_available_hint(source: SkillSource, skill_name: str, normalized_path: str) -> str:
        """Return ``" Available: [...]"`` listing sibling files, or ``""``.

        Walks :meth:`SkillSource.list_files` and filters to entries sharing a
        parent directory with ``normalized_path``. Silently returns ``""`` if
        the source does not support ``list_files`` or the listing fails —
        callers treat the hint as best-effort UX, never as a contract.
        """
        try:
            files = source.list_files(skill_name)
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

    def clear_cache(self) -> None:
        """Drop the registry's loaded-skill cache."""
        self._skill_cache.clear()

    def clear(self) -> None:
        """Reset the registry's view of skills.

        Clears the built-in filesystem source and the registry's cache. Any
        additional sources registered via :meth:`add_source` are preserved —
        clearing them would be destructive. Callers who want a full reset
        should reconstruct the registry or remove custom sources explicitly.
        """
        self._filesystem_source.clear()
        self._skill_cache.clear()

    def __len__(self) -> int:
        """Return the number of unique skill names across all sources.

        Unlike :meth:`list_metadata`, this method is collision-tolerant and
        de-duplicates names when multiple sources expose the same skill.
        """
        return len(self._available_skill_name_set())

    def __contains__(self, name: str) -> bool:
        """Return whether any source exposes ``name``.

        This method is collision-tolerant; use :meth:`load_skill` or
        :meth:`list_metadata` to surface :class:`SkillSourceCollisionError`.
        """
        return self.has_skill(name)

    def __repr__(self) -> str:
        return f"SkillsRegistry(sources={[source.name for source in self._sources]})"

    # Tool factories ---------------------------------------------------------

    def create_use_skill_tool(self, include_skills_listing: bool = True) -> Any:
        """Create ADK tool for skill activation.

        The tool description includes an ``<available_skills>`` block listing
        all discovered skills (when ``include_skills_listing=True``). When
        called, the tool loads and returns the full skill instructions.

        Args:
            include_skills_listing: Whether to include the ``<available_skills>``
                XML in the tool description (default: True). Set to False when
                using prompt injection to avoid duplication.

        Returns:
            Callable tool function for use with ADK agents.
        """
        from adk_skills_agent.tools.use_skill import create_use_skill_tool

        return create_use_skill_tool(self, include_skills_listing=include_skills_listing)

    def create_read_reference_tool(self) -> Any:
        """Create ADK tool for reading skill reference files."""
        from adk_skills_agent.tools.read_reference import create_read_reference_tool

        return create_read_reference_tool(self)

    # Prompt injection utilities --------------------------------------------

    def to_prompt_xml(self) -> str:
        """Generate XML representation of skills for prompt injection."""
        from adk_skills_agent.tools.use_skill import generate_available_skills_xml

        return generate_available_skills_xml(self)

    def to_prompt_text(self) -> str:
        """Generate plain-text representation of skills for prompt injection."""
        skills_metadata = self.list_metadata()
        if not skills_metadata:
            return "No skills available."
        lines = ["Available Skills:"]
        for metadata in skills_metadata:
            lines.append(f"- {metadata.name}: {metadata.description}")
        return "\n".join(lines)

    def get_skills_prompt(self, format: str = "xml") -> str:
        """Return a formatted skills prompt.

        Args:
            format: ``"xml"`` or ``"text"``.

        Raises:
            ValueError: For any unsupported format.
        """
        if format == "xml":
            return self.to_prompt_xml()
        if format == "text":
            return self.to_prompt_text()
        raise ValueError(f"Unsupported format: {format}. Use 'xml' or 'text'.")

    def inject_skills_prompt(self, instruction: str, format: str = "xml") -> str:
        """Inject the skills listing into ``instruction``.

        Returns ``instruction`` unchanged when no skills are known.
        """
        if len(self) == 0:
            return instruction
        skills_prompt = self.get_skills_prompt(format=format)
        return f"{instruction}\n\n{skills_prompt}"

    # Validation utilities --------------------------------------------------

    def validate_all(self, strict: bool = True) -> dict[str, ValidationResult]:
        """Validate every known skill and return a per-name result map."""
        results: dict[str, ValidationResult] = {}
        for metadata in self.list_metadata():
            results[metadata.name] = validate_skill_metadata(metadata, strict=strict)
        return results

    def validate_skill_by_name(self, name: str, strict: bool = True) -> ValidationResult:
        """Validate a specific skill by name.

        Raises:
            SkillNotFoundError: If the skill is not known to any source.
        """
        metadata = self.get_metadata(name)
        if metadata is None:
            raise SkillNotFoundError(
                f"Skill '{name}' not found. Available skills: {self._available_skill_names()}"
            )
        return validate_skill_metadata(metadata, strict=strict)

    # Internals --------------------------------------------------------------

    def _available_skill_names(self) -> list[str]:
        """Return sorted, collision-tolerant skill names across all sources."""
        return sorted(self._available_skill_name_set())

    def _available_skill_name_set(self) -> set[str]:
        """Return deduplicated skill names across all sources."""
        names: set[str] = set()
        for source in self._sources:
            names.update(source.iter_names())
        return names

    def _resolve_source(self, name: str) -> SkillSource:
        """Return the single source that provides ``name``.

        Raises:
            SkillNotFoundError: When no source claims ``name``.
            SkillSourceCollisionError: When two or more sources provide the
                skill.
        """
        source = self._find_source(name)
        if source is None:
            raise SkillNotFoundError(
                f"Skill '{name}' not found. Available skills: {self._available_skill_names()}"
            )
        return source

    def _find_source(self, name: str) -> SkillSource | None:
        """Return the source that provides ``name`` or ``None`` if unknown.

        Raises:
            SkillSourceCollisionError: When two or more sources provide the
                skill.
        """
        owners = [source for source in self._sources if source.has_skill(name)]
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
