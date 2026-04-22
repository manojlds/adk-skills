"""End-to-end integration test for a SQLite-backed ``SkillSource``.

Doubles as a worked example of how to implement a database-backed source on
top of the :class:`SkillSource` contract. It exercises the public
:class:`SkillsRegistry` surface against a minimal custom source that stores
every file of a multi-file skill package in SQLite - ``SKILL.md``,
references, text assets, and a binary asset - and verifies that:

* ``registry.list_metadata()`` / ``registry.load_skill()`` see the skill.
* The ``use_skill`` tool returns the correct instructions.
* ``registry.list_files()`` reports every file with sensible metadata.
* ``registry.read_file()`` round-trips both text and binary contents.
* ``registry.read_reference()`` (and the tool wrapper) honour the relaxed
  0.2.0 path shapes (bare filename -> ``references/``, explicit prefix,
  ``assets/``) and refuses binary files with a clear error.
* Path-traversal attempts are blocked.

The source itself is defined in this file and uses stdlib ``sqlite3`` so the
test has no SQLAlchemy coupling. Note how small it is now that the registry
owns reference-path normalisation: the source only implements raw file I/O
(``list_files`` / ``read_file``) and the registry does the rest.
"""

from __future__ import annotations

import hashlib
import mimetypes
import sqlite3
from collections.abc import Generator, Mapping
from dataclasses import dataclass
from pathlib import Path

import pytest

from adk_skills_agent import SkillsRegistry
from adk_skills_agent.core.models import Skill, SkillMetadata
from adk_skills_agent.core.paths import validate_skill_root_relative_path
from adk_skills_agent.core.source import ReferenceFile, SkillFile, SkillSource
from adk_skills_agent.exceptions import SkillExecutionError, SkillNotFoundError

# --- Test-only SQLite skill source -------------------------------------------


@dataclass
class _SqliteSkillPackage:
    """Convenience container for seeding :class:`_SqliteSkillSource`.

    ``files`` maps ``relative_path`` -> raw bytes or ``str``; ``str`` values are
    encoded as UTF-8 and persisted in ``text_content``, ``bytes`` values go to
    ``binary_content``.
    """

    name: str
    description: str
    instructions: str
    files: Mapping[str, str | bytes]


class _SqliteSkillSource(SkillSource):
    """Minimal SQLite-backed source that stores every skill file separately.

    Schema (two tables):

    * ``skills(name PK, description, instructions)``
    * ``skill_files(skill_name FK, relative_path, mime_type, size_bytes,
      content_hash, text_content, binary_content, PRIMARY KEY (skill_name,
      relative_path))``

    This is intentionally dumb and test-only; real implementations will layer
    versioning, ownership, and binding filters on top.
    """

    name = "sqlite-test"

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._conn = connection
        self._ensure_schema()

    # Storage API --------------------------------------------------------

    def _ensure_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS skills (
                name TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                instructions TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS skill_files (
                skill_name TEXT NOT NULL,
                relative_path TEXT NOT NULL,
                mime_type TEXT,
                size_bytes INTEGER NOT NULL,
                content_hash TEXT NOT NULL,
                text_content TEXT,
                binary_content BLOB,
                PRIMARY KEY (skill_name, relative_path),
                FOREIGN KEY (skill_name) REFERENCES skills(name)
            );
            """
        )
        self._conn.commit()

    def save_package(self, package: _SqliteSkillPackage) -> None:
        """Persist ``package`` (skill row + all files) in one transaction."""
        self._conn.execute(
            "INSERT OR REPLACE INTO skills(name, description, instructions) VALUES (?, ?, ?)",
            (package.name, package.description, package.instructions),
        )
        self._conn.execute("DELETE FROM skill_files WHERE skill_name = ?", (package.name,))
        for relative_path, raw in package.files.items():
            normalized = validate_skill_root_relative_path(relative_path)
            text_content: str | None
            binary_content: bytes | None
            if isinstance(raw, str):
                text_content = raw
                binary_content = None
                blob = raw.encode("utf-8")
            else:
                text_content = None
                binary_content = raw
                blob = raw
            self._conn.execute(
                "INSERT INTO skill_files(skill_name, relative_path, mime_type, "
                "size_bytes, content_hash, text_content, binary_content) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    package.name,
                    normalized,
                    mimetypes.guess_type(normalized)[0],
                    len(blob),
                    hashlib.sha256(blob).hexdigest(),
                    text_content,
                    binary_content,
                ),
            )
        self._conn.commit()

    # SkillSource contract ----------------------------------------------

    def list_metadata(self) -> list[SkillMetadata]:
        rows = self._conn.execute("SELECT name, description FROM skills ORDER BY name").fetchall()
        return [
            SkillMetadata(
                name=row[0],
                description=row[1],
                location=Path(f"sqlite://{row[0]}/SKILL.md"),
            )
            for row in rows
        ]

    def has_skill(self, name: str) -> bool:
        row = self._conn.execute("SELECT 1 FROM skills WHERE name = ? LIMIT 1", (name,)).fetchone()
        return row is not None

    def load_skill(self, name: str) -> Skill:
        row = self._conn.execute(
            "SELECT name, description, instructions FROM skills WHERE name = ?",
            (name,),
        ).fetchone()
        if row is None:
            raise SkillNotFoundError(f"Skill '{name}' not found in sqlite-test source")
        existing = {
            r[0]
            for r in self._conn.execute(
                "SELECT relative_path FROM skill_files WHERE skill_name = ?",
                (name,),
            ).fetchall()
        }
        base = Path(f"sqlite://{name}")
        return Skill(
            name=row[0],
            description=row[1],
            location=base / "SKILL.md",
            skill_dir=base,
            instructions=row[2],
            references_dir=base / "references"
            if any(p.startswith("references/") for p in existing)
            else None,
            assets_dir=base / "assets" if any(p.startswith("assets/") for p in existing) else None,
            scripts_dir=base / "scripts"
            if any(p.startswith("scripts/") for p in existing)
            else None,
        )

    def list_files(self, skill_name: str) -> list[SkillFile]:
        if not self.has_skill(skill_name):
            raise SkillNotFoundError(f"Skill '{skill_name}' not found in sqlite-test source")
        rows = self._conn.execute(
            "SELECT relative_path, mime_type, size_bytes, content_hash "
            "FROM skill_files WHERE skill_name = ? ORDER BY relative_path",
            (skill_name,),
        ).fetchall()
        return [
            SkillFile(
                relative_path=row[0],
                mime_type=row[1],
                size_bytes=row[2],
                content_hash=row[3],
            )
            for row in rows
        ]

    def read_file(self, skill_name: str, relative_path: str) -> SkillFile:
        if not self.has_skill(skill_name):
            raise SkillNotFoundError(f"Skill '{skill_name}' not found in sqlite-test source")
        normalized = validate_skill_root_relative_path(relative_path)
        row = self._conn.execute(
            "SELECT relative_path, mime_type, size_bytes, content_hash, "
            "text_content, binary_content FROM skill_files "
            "WHERE skill_name = ? AND relative_path = ?",
            (skill_name, normalized),
        ).fetchone()
        if row is None:
            raise SkillExecutionError(f"File '{relative_path}' not found in skill '{skill_name}'.")
        return SkillFile(
            relative_path=row[0],
            mime_type=row[1],
            size_bytes=row[2],
            content_hash=row[3],
            text_content=row[4],
            binary_content=row[5],
        )


# --- Example skill seed data -------------------------------------------------

_SKILL_NAME = "invoice-extraction"
_SKILL_MD = """\
---
name: invoice-extraction
description: Extract line items from PDF invoices into structured JSON.
---

# Invoice extraction

Use this skill when the user needs to extract structured data from PDF
invoices. Start by reading `references/guide.md` for the canonical
procedure, and use `assets/template.json` as the output schema.

Do not invent fields; if a field is missing, set it to `null` and note the
gap in `coverage_notes`.
"""

_GUIDE_MD = """\
# Extraction procedure

1. Parse the PDF page-by-page.
2. Classify lines against `assets/grammar.lark` (token order matters).
3. Emit one JSON record per line item, matching `assets/template.json`.
"""

_EXAMPLES_MD = """\
# Worked examples

See `assets/template.json` for the output schema. Boolean flags use
`TRUE`/`FALSE` (never `true`/`false`) to match the legacy consumer.
"""

_TEMPLATE_JSON = '{\n  "invoice_number": null,\n  "line_items": []\n}\n'

_GRAMMAR_LARK = """\
start: line+
line: amount_literal CURRENCY
amount_literal: /[0-9]+(\\.[0-9]+)?/
CURRENCY: "USD" | "EUR" | "INR"
"""

# A minimal PNG header so ``mimetypes`` returns image/png and we exercise
# the binary path end-to-end.
_LOGO_PNG = b"\x89PNG\r\n\x1a\nfake-binary-payload\x00\x01\x02\x03"


@pytest.fixture
def sqlite_connection(tmp_path: Path) -> Generator[sqlite3.Connection, None, None]:
    db_path = tmp_path / "skills.db"
    conn = sqlite3.connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def registry(sqlite_connection: sqlite3.Connection) -> SkillsRegistry:
    source = _SqliteSkillSource(sqlite_connection)
    source.save_package(
        _SqliteSkillPackage(
            name=_SKILL_NAME,
            description="Extract line items from PDF invoices into structured JSON.",
            instructions=_SKILL_MD,
            files={
                "SKILL.md": _SKILL_MD,
                "references/guide.md": _GUIDE_MD,
                "references/examples.md": _EXAMPLES_MD,
                "assets/template.json": _TEMPLATE_JSON,
                "assets/grammar.lark": _GRAMMAR_LARK,
                "assets/logo.png": _LOGO_PNG,
            },
        )
    )
    registry = SkillsRegistry()
    registry.add_source(source)
    return registry


# --- Tests -------------------------------------------------------------------


class TestSqliteSkillSourceMetadataAndLoad:
    def test_registry_sees_the_skill(self, registry: SkillsRegistry) -> None:
        names = [meta.name for meta in registry.list_metadata()]
        assert names == [_SKILL_NAME]
        assert registry.has_skill(_SKILL_NAME)

    def test_load_skill_returns_parsed_instructions(self, registry: SkillsRegistry) -> None:
        skill = registry.load_skill(_SKILL_NAME)
        assert skill.name == _SKILL_NAME
        assert "Invoice extraction" in skill.instructions
        # The source reports the presence of the standard Anthropic subfolders
        # based on what's persisted in SQLite, so activation UX works even
        # though nothing is on disk.
        assert skill.references_dir is not None
        assert skill.assets_dir is not None
        assert skill.scripts_dir is None

    def test_use_skill_tool_surfaces_instructions(self, registry: SkillsRegistry) -> None:
        use_skill = registry.create_use_skill_tool()
        result = use_skill(_SKILL_NAME)
        assert result["skill_name"] == _SKILL_NAME
        assert "Invoice extraction" in result["instructions"]
        assert result["has_references"] is True
        assert result["has_assets"] is True
        assert result["has_scripts"] is False


class TestSqliteSkillSourceListFiles:
    def test_list_files_returns_every_entry(self, registry: SkillsRegistry) -> None:
        files = registry.list_files(_SKILL_NAME)
        by_path = {file.relative_path: file for file in files}
        assert set(by_path) == {
            "SKILL.md",
            "references/guide.md",
            "references/examples.md",
            "assets/template.json",
            "assets/grammar.lark",
            "assets/logo.png",
        }
        assert by_path["assets/template.json"].mime_type == "application/json"
        assert by_path["assets/logo.png"].mime_type == "image/png"
        assert by_path["references/guide.md"].size_bytes == len(_GUIDE_MD.encode("utf-8"))
        # Listing does not load the payloads.
        for file in files:
            assert file.text_content is None
            assert file.binary_content is None


class TestSqliteSkillSourceReadFile:
    def test_read_file_text(self, registry: SkillsRegistry) -> None:
        file = registry.read_file(_SKILL_NAME, "references/guide.md")
        assert file.text_content == _GUIDE_MD
        assert file.binary_content is None
        assert file.is_text is True

    def test_read_file_binary_returns_bytes(self, registry: SkillsRegistry) -> None:
        file = registry.read_file(_SKILL_NAME, "assets/logo.png")
        assert file.binary_content == _LOGO_PNG
        assert file.text_content is None
        assert file.is_binary is True
        assert file.mime_type == "image/png"

    def test_read_file_rejects_path_escape(self, registry: SkillsRegistry) -> None:
        with pytest.raises(SkillExecutionError, match="escapes skill directory"):
            registry.read_file(_SKILL_NAME, "../secret.txt")

    def test_read_file_missing_raises_execution_error(self, registry: SkillsRegistry) -> None:
        # Programmatic read_file keeps its error minimal; the ``Available:``
        # hint is a registry-level, LLM-facing convenience reserved for
        # read_reference.
        with pytest.raises(SkillExecutionError, match="not found"):
            registry.read_file(_SKILL_NAME, "assets/missing.json")


class TestSqliteSkillSourceReadReference:
    def test_bare_filename_defaults_to_references(self, registry: SkillsRegistry) -> None:
        result = registry.read_reference(_SKILL_NAME, "guide.md")
        assert isinstance(result, ReferenceFile)
        assert result.content == _GUIDE_MD
        assert result.filename == "guide.md"
        # The locator is skill-root-relative; source-specific prefixes
        # (``sqlite://...``) never leak back to the caller.
        assert result.path == "references/guide.md"

    def test_explicit_references_prefix(self, registry: SkillsRegistry) -> None:
        result = registry.read_reference(_SKILL_NAME, "references/examples.md")
        assert result.content == _EXAMPLES_MD
        assert result.path == "references/examples.md"

    def test_asset_path_reads_text_asset(self, registry: SkillsRegistry) -> None:
        # Text assets (JSON, grammar, etc.) are allowed through read_reference
        # in 0.2.0, matching the UX of the filesystem source.
        result = registry.read_reference(_SKILL_NAME, "assets/template.json")
        assert result.content == _TEMPLATE_JSON
        assert result.path == "assets/template.json"
        result = registry.read_reference(_SKILL_NAME, "assets/grammar.lark")
        assert result.content == _GRAMMAR_LARK
        assert result.path == "assets/grammar.lark"

    def test_binary_asset_rejected_with_helpful_message(self, registry: SkillsRegistry) -> None:
        with pytest.raises(SkillExecutionError, match="not a text file"):
            registry.read_reference(_SKILL_NAME, "assets/logo.png")

    def test_skill_md_is_readable(self, registry: SkillsRegistry) -> None:
        # Not idiomatic, but exercises the "known root file" normalisation rule.
        result = registry.read_reference(_SKILL_NAME, "SKILL.md")
        assert "Invoice extraction" in result.content
        assert result.path == "SKILL.md"

    def test_nested_legacy_path_maps_under_references(
        self, sqlite_connection: sqlite3.Connection
    ) -> None:
        source = _SqliteSkillSource(sqlite_connection)
        source.save_package(
            _SqliteSkillPackage(
                name="nested",
                description="Nested reference skill",
                instructions="Body.",
                files={
                    "SKILL.md": "Body.",
                    "references/guides/intro.md": "Nested guide content",
                },
            )
        )
        registry = SkillsRegistry()
        registry.add_source(source)

        result = registry.read_reference("nested", "guides/intro.md")
        assert result.content == "Nested guide content"
        assert result.filename == "intro.md"
        assert result.path == "references/guides/intro.md"

    def test_path_escape_blocked(self, registry: SkillsRegistry) -> None:
        with pytest.raises(SkillExecutionError, match="escapes skill directory"):
            registry.read_reference(_SKILL_NAME, "references/../../etc/passwd")

    def test_missing_reference_hint_lists_neighbours(self, registry: SkillsRegistry) -> None:
        with pytest.raises(SkillExecutionError, match="references/guide.md"):
            registry.read_reference(_SKILL_NAME, "nonexistent.md")


class TestSqliteSkillSourceToolLayer:
    def test_read_reference_tool_returns_dict(self, registry: SkillsRegistry) -> None:
        tool = registry.create_read_reference_tool()
        result = tool(_SKILL_NAME, "guide.md")
        assert result == {
            "content": _GUIDE_MD,
            "path": "references/guide.md",
            "filename": "guide.md",
        }

    def test_read_reference_tool_can_read_assets(self, registry: SkillsRegistry) -> None:
        tool = registry.create_read_reference_tool()
        result = tool(_SKILL_NAME, "assets/template.json")
        assert result["content"] == _TEMPLATE_JSON
        assert result["path"] == "assets/template.json"
        assert result["filename"] == "template.json"

    def test_read_reference_tool_refuses_binary(self, registry: SkillsRegistry) -> None:
        tool = registry.create_read_reference_tool()
        with pytest.raises(SkillExecutionError, match="not a text file"):
            tool(_SKILL_NAME, "assets/logo.png")
