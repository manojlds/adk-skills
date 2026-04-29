# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.1] - 2026-04-29

### Fixed
- Removed the broken `adk-skills` console script declaration so installs no
  longer expose a CLI entry point that imports a missing module.
- Updated README and examples to use the async-only `0.4.x` APIs consistently.
- Prevented `FilesystemSkillSource.load_skill()` from recaching stale parsed
  skills after a concurrent refresh clears the cache.
- Made `FilesystemSkillSource` state mutations thread-safe and bounded retry
  loops for catalogs that keep changing during refresh or load operations.

## [0.4.0] - 2026-04-28

### Changed (breaking)
- **All runtime read methods on `SkillSource` and `SkillsRegistry` are now
  coroutines.** I/O-bound sources (databases, remote registries, object
  storage) can now perform real non-blocking I/O end-to-end, instead of
  forcing every consumer to wrap a synchronous source with `asyncio.to_thread`
  at the call site.
  - `SkillSource.list_metadata`, `load_skill`, `iter_names`, `has_skill`,
    `get_metadata`, `refresh`, `clear_cache`, `list_files`, and `read_file`
    are now `async def`.
  - `SkillsRegistry.list_metadata`, `load_skill`, `read_reference`,
    `list_files`, `read_file`, `validate_all`, `refresh`, `clear_cache`,
    `to_prompt_xml`, `to_prompt_text`, `get_skills_prompt`, `iter_names`,
    `has_skill`, and `get_metadata` are now `async def`.
  - `SkillsAgent.get_tools`, `get_instruction`, and `build` are now
    `async def`.
  - The `with_skills`, `create_skills_agent`, and `inject_skills_prompt`
    helpers in `adk_skills_agent.helpers` are now `async def`.
  - The callables produced by `create_use_skill_tool` and
    `create_read_reference_tool` are now `async def`. ADK already supports
    async tool callables, so no agent-side change is required.
- `create_use_skill_tool` no longer takes `include_skills_listing`. Callers
  that want the available-skills listing in the tool description should pass
  the pre-rendered XML via the new `available_skills_xml` argument:
  `xml = await registry.to_prompt_xml(); create_use_skill_tool(registry, available_skills_xml=xml)`.
  This avoids duplicating the async listing step inside the tool factory.
- `SkillsRegistry.__len__` and `SkillsRegistry.__contains__` were removed
  because the underlying lookups are now async (`__len__` and `__contains__`
  cannot be coroutines). Replace `len(registry)` with
  `len(await registry.list_metadata())` and `name in registry` with
  `await registry.has_skill(name)`.
- `SkillSource.iter_names` now returns a `list[str]` (rather than yielding an
  iterator) so it can be implemented as a single coroutine.

### Removed
- Removed the broken `adk-skills` console script declaration. This project does
  not currently ship a CLI module.
- Removed the legacy script-execution API (`run_script`, `ScriptResult`, and
  `create_run_script_tool`). Applications should expose script execution through
  their own ADK tools when they need it.

### Added
- Module-level `_format_metadata_xml` / `_format_metadata_text` helpers in
  `adk_skills_agent.registry` so prompt-shape utilities can be reused without
  re-running the metadata gather.
- `pytest-asyncio>=0.23` dev dependency, with `asyncio_mode = "auto"` in
  `pyproject.toml` so async tests do not need explicit decorators.

### Migration notes
- `with_skills(...)`, `create_skills_agent(...)`, and `SkillsAgent.build(...)`
  are now coroutines. Wherever you build agents at module top-level, switch
  the call site to `asyncio.run(create_skills_agent(...))` (or `await ...`
  from inside another async context).
- ADK's `before_agent_callback` and tool callables already support `async
  def`, so wiring the new async tools into an ADK agent does not require any
  additional adapter — return them directly from your tool list.
- Custom `SkillSource` implementations must change their method signatures
  from `def` to `async def` for the runtime methods listed above. Sources
  whose underlying I/O is synchronous (filesystem, in-memory, sqlite3) can
  wrap blocking calls with `asyncio.to_thread(...)`; sources backed by
  asyncio-aware drivers (`asyncpg`, `aiomysql`, `httpx.AsyncClient`, …) can
  call into them directly.

## [0.3.0] - 2026-04-27

### Changed
- Skill freshness is now owned by each source. `SkillsRegistry.refresh()`
  delegates to every registered source's own `refresh()` and returns whether
  any source reported a change. Sources that maintain caches (filesystem,
  database, …) are responsible for invalidating just the entries that became
  stale, instead of clearing the registry-wide cache wholesale.
- `FilesystemSkillSource.refresh()` is now rollback-safe: if rediscovery
  raises, the previously discovered metadata and skill cache are preserved
  unchanged so callers continue to see a consistent view.

### Added
- Documentation of the new source-owned refresh contract in the `SkillSource`
  base class so custom source authors know what `refresh()` is expected to
  return and which caches they own.

## [0.2.0] - 2026-04-22

### Added
- New `SkillSource` abstract base class (`adk_skills_agent.core.source.SkillSource`)
  defining a pluggable interface for skill providers. Implementations are expected
  to provide `list_metadata()` and `load_skill()` at minimum, and may optionally
  implement `list_files()` / `read_file()` / `run_script()` when their underlying
  storage supports those operations.
- `FilesystemSkillSource` (`adk_skills_agent.sources.filesystem`) — the built-in
  source backing `SkillsRegistry.discover(...)`. Encapsulates the existing
  filesystem discovery, file access, and script-execution logic.
- `ReferenceFile` and `ScriptResult` dataclasses returned by
  `SkillsRegistry.read_reference()` / `SkillsRegistry.run_script()`.
- New `SkillFile` dataclass and generic file-access API
  (`SkillSource.list_files(skill_name)` and
  `SkillSource.read_file(skill_name, relative_path)`) that lets a source expose
  any file in a skill package — `SKILL.md`, references, assets, and any other
  files — as text or binary. The `FilesystemSkillSource` implements both; the
  registry exposes matching `SkillsRegistry.list_files` / `read_file` wrappers
  that route through the owning source.
- New public path helpers in `adk_skills_agent.core.paths` (also re-exported
  from the top-level package): `normalize_skill_reference(reference)` and
  `validate_skill_root_relative_path(path)`. Custom source authors can reuse
  them when implementing `read_file`, but the registry normally handles
  normalisation on their behalf.
- `SkillsRegistry.add_source(...)` / `remove_source(...)` for registering custom
  skill sources (e.g. remote services, databases, object storage).
- New `SkillSourceCollisionError` raised when multiple registered sources
  advertise a skill with the same name.
- New end-to-end integration test
  (`tests/integration/test_sqlite_skill_source.py`) showing how to plug a
  multi-file SQLite-backed source into the registry — doubles as the
  reference implementation for writing a custom database source.

### Changed
- `SkillsRegistry` is now composed of one or more `SkillSource` instances
  instead of maintaining a private metadata dictionary directly. The public API
  (`discover`, `list_metadata`, `load_skill`, `read_reference`, `list_files`,
  `read_file`, `run_script`, `validate_all`, prompt/tool helpers) is preserved.
- `read_reference` is now implemented at the registry level on top of
  `SkillSource.read_file`. The registry owns reference-path normalisation
  (a bare filename with no `/` is still resolved under `references/`;
  `assets/…`, `scripts/…`, and `SKILL.md` pass through), text-only
  enforcement, and the `Available: […]` hint that fires when a reference is
  missing. Sources never need to reimplement any of this logic — providing
  `read_file(skill_name, skill_root_relative_path)` is sufficient to make
  `read_reference` work end-to-end.
- `ReferenceFile.path` is now a **skill-root-relative locator**
  (`"references/guide.md"`, `"assets/template.json"`, …) rather than an
  opaque, source-specific string. Callers that previously relied on the
  filesystem source returning an on-disk path can reconstruct it with
  `Skill.skill_dir / reference.path`.
- Skill lookups now fail with `SkillSourceCollisionError` when two sources
  expose the same skill name, instead of silently preferring one source.
- `create_read_reference_tool` and `create_run_script_tool` delegate to
  `SkillsRegistry.read_reference()` / `SkillsRegistry.run_script()`, which in
  turn route to the source that owns the skill.
- `SkillsRegistry.clear()` now only clears the built-in filesystem source and
  the internal skill cache; any custom sources registered via `add_source(...)`
  are left untouched. Use `remove_source(...)` to unregister them explicitly.

### Removed
- **Lowercase ``skill.md`` is no longer accepted.** The agentskills.io
  specification mandates the uppercase filename ``SKILL.md``; the parser,
  discovery scan, and reference-path normaliser now accept only the
  uppercase form. Skills stored as ``skill.md`` will no longer be
  discovered — rename them to ``SKILL.md`` to keep them working.
- **Built-in database support is gone.** The following symbols and modules
  have been deleted:
  - `adk_skills_agent.db` package (SQLAlchemy models, `SkillsStore`, Alembic
    metadata helper).
  - `adk_skills_agent.sources.database.DatabaseSkillSource` (the prompt-only
    wrapper around `SkillsStore`).
  - `SkillsConfig.db_enabled`, `db_session`, `db_auto_create`, and `app_name`
    fields.
  - `SkillsRegistry.save_skill_to_db`, `delete_skill_from_db`,
    `import_skill_to_db`, `import_all_to_db`, `list_skill_versions`, and
    `skill_exists_in_db`.
  - The `[db]` optional extra and the SQLAlchemy dependency.

  The built-in store was prompt-only and never matched what serious DB-backed
  deployments need (references, assets, binary content, versioning semantics).
  The new `SkillSource` abstraction lets applications bring their own
  database-backed source that fits their schema exactly. See
  `tests/integration/test_sqlite_skill_source.py` for a worked multi-file
  example.
- `SkillSource.read_reference` is no longer part of the abstract base class.
  Custom sources should implement `SkillSource.read_file` instead; the
  registry provides the text-only `read_reference` wrapper on top.

### Migration notes
- **Rename any ``skill.md`` to ``SKILL.md``.** Rename the files in place
  (on case-insensitive filesystems such as macOS's default APFS, use
  ``git mv -f skill.md SKILL.md`` so the rename is recorded). No other
  changes are needed.
- **Migrating off built-in DB support.** Anyone on 0.1.x who set
  `db_enabled=True` / `db_session=...` in `SkillsConfig`, or called
  `registry.save_skill_to_db(...)` / `import_skill_to_db(...)` etc., needs to
  subclass `SkillSource` against their chosen storage layer and register it
  with `registry.add_source(...)`. The SQLite integration test in
  `tests/integration/test_sqlite_skill_source.py` is a short,
  copy-pasteable starting point; it implements `list_metadata`, `load_skill`,
  `list_files`, and `read_file` against stdlib `sqlite3`. Reference-path
  normalisation and the text-only `read_reference` wrapper are handled by the
  registry, so your source only needs raw `read_file` (and optional
  `list_files`) to support multi-file skill packages.
- Code that relied on the old private `_metadata_registry` /
  `_db_metadata_registry` attributes must be updated to go through
  `list_metadata()`, `get_metadata()`, or `load_skill()`.
- Applications that previously had a skill with the same name in both the
  filesystem source and another source will now hit
  `SkillSourceCollisionError`; rename or remove one of the two copies to
  resolve.
- Anyone who was calling `read_reference(skill, "../something.md")` or similar
  to read outside `references/` should switch to the new relative-path form
  (e.g. `read_reference(skill, "assets/something.json")`) or use `read_file`.
- Custom `SkillSource` implementations that previously overrode
  `read_reference` should move that logic into `read_file` and drop the
  override. The registry-level wrapper will handle normalisation, text-only
  enforcement, and the available-files hint.
- Callers that parsed `ReferenceFile.path` as an on-disk path should join it
  with `Skill.skill_dir` (for filesystem-backed skills) or treat it as a
  source-agnostic locator.

## [0.1.0]

Initial release.
