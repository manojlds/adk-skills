# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-04-22

### Added
- New `SkillSource` abstract base class (`adk_skills_agent.core.source.SkillSource`)
  defining a pluggable interface for skill providers. Implementations are expected
  to provide `list_metadata()` and `load_skill()` at minimum, and may optionally
  implement `list_files()` / `read_file()` when their underlying storage supports
  those operations.
- `FilesystemSkillSource` (`adk_skills_agent.sources.filesystem`) — the built-in
  source backing `SkillsRegistry.discover(...)`. Encapsulates the existing
  filesystem discovery and file-access logic.
- `ReferenceFile` dataclass returned by `SkillsRegistry.read_reference()`.
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
  `read_file`, `validate_all`, prompt/tool helpers) is preserved.
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
- `create_read_reference_tool` delegates to `SkillsRegistry.read_reference()`,
  which routes to the source that owns the skill.
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
- `run_script` support has been removed for now. The following symbols and
  methods no longer exist:
  - `SkillSource.run_script`
  - `SkillsRegistry.run_script`
  - `SkillsRegistry.create_run_script_tool`
  - `adk_skills_agent.tools.run_script`
  - `ScriptResult`
  - `SkillsConfig.enable_scripts`, `SkillsConfig.script_timeout`, and
    `SkillsConfig.sandbox_mode`

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
