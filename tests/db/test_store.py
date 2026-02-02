"""SQLite-backed tests for the database skills store."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from adk_skills_agent.core.models import SkillsConfig
from adk_skills_agent.db.models import SkillRecord
from adk_skills_agent.db.store import SkillsStore
from adk_skills_agent.registry import SkillsRegistry


@pytest.fixture
def sqlite_session() -> Generator[Session, None, None]:
    """Provide an in-memory SQLite session for DB tests."""
    engine = create_engine("sqlite:///:memory:")
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()


def test_store_list_metadata_prefers_app_specific(sqlite_session: Session) -> None:
    """Ensure app-scoped records take precedence over global records."""
    store = SkillsStore(sqlite_session)
    store.ensure_schema()

    sqlite_session.add_all(
        [
            SkillRecord(
                name="alpha",
                app_name=None,
                version=1,
                description="global alpha",
                instructions="global alpha instructions",
            ),
            SkillRecord(
                name="alpha",
                app_name="my-app",
                version=2,
                description="app alpha",
                instructions="app alpha instructions",
            ),
            SkillRecord(
                name="beta",
                app_name=None,
                version=1,
                description="global beta",
                instructions="global beta instructions",
            ),
        ]
    )
    sqlite_session.commit()

    app_metadata = {metadata.name: metadata for metadata in store.list_metadata(app_name="my-app")}
    assert app_metadata["alpha"].description == "app alpha"
    assert app_metadata["beta"].description == "global beta"

    global_metadata = {metadata.name: metadata for metadata in store.list_metadata()}
    assert global_metadata["alpha"].description == "app alpha"
    assert global_metadata["beta"].description == "global beta"


def test_store_get_skill_returns_latest_version(sqlite_session: Session) -> None:
    """Ensure latest version is returned when no version is requested."""
    store = SkillsStore(sqlite_session)
    store.ensure_schema()

    sqlite_session.add_all(
        [
            SkillRecord(
                name="gamma",
                app_name=None,
                version=1,
                description="gamma v1",
                instructions="gamma instructions v1",
            ),
            SkillRecord(
                name="gamma",
                app_name=None,
                version=2,
                description="gamma v2",
                instructions="gamma instructions v2",
            ),
        ]
    )
    sqlite_session.commit()

    skill = store.get_skill("gamma")
    assert skill.description == "gamma v2"
    assert skill.instructions == "gamma instructions v2"


def test_store_get_skill_falls_back_to_global(sqlite_session: Session) -> None:
    """Ensure app-specific lookups fall back to global records."""
    store = SkillsStore(sqlite_session)
    store.ensure_schema()

    sqlite_session.add(
        SkillRecord(
            name="delta",
            app_name=None,
            version=1,
            description="global delta",
            instructions="global delta instructions",
        )
    )
    sqlite_session.commit()

    skill = store.get_skill("delta", app_name="my-app")
    assert skill.description == "global delta"


def test_registry_loads_skills_from_db(sqlite_session: Session) -> None:
    """Ensure registry pulls metadata and skills from the DB store."""
    store = SkillsStore(sqlite_session)
    store.ensure_schema()

    sqlite_session.add(
        SkillRecord(
            name="epsilon",
            app_name="my-app",
            version=1,
            description="epsilon from db",
            instructions="epsilon instructions",
            license="MIT",
            compatibility="python",
            allowed_tools="bash",
            metadata_json={"source": "db"},
        )
    )
    sqlite_session.commit()

    config = SkillsConfig(db_enabled=True, db_session=sqlite_session, app_name="my-app")
    registry = SkillsRegistry(config=config)

    metadata = {item.name: item for item in registry.list_metadata()}
    assert metadata["epsilon"].description == "epsilon from db"
    assert metadata["epsilon"].metadata == {"source": "db"}

    skill = registry.load_skill("epsilon")
    assert skill.instructions == "epsilon instructions"


# CRUD operation tests


def test_store_save_skill_creates_new(sqlite_session: Session) -> None:
    """Ensure save_skill creates a new skill record."""
    from pathlib import Path

    from adk_skills_agent.core.models import Skill

    store = SkillsStore(sqlite_session)
    store.ensure_schema()

    skill = Skill(
        name="test-skill",
        description="A test skill",
        location=Path("/test/SKILL.md"),
        skill_dir=Path("/test"),
        instructions="Test instructions",
        license="MIT",
    )

    record = store.save_skill(skill)
    assert record.name == "test-skill"
    assert record.version == 1
    assert record.description == "A test skill"
    assert record.instructions == "Test instructions"


def test_store_save_skill_auto_increments_version(sqlite_session: Session) -> None:
    """Ensure save_skill auto-increments version when not specified."""
    from pathlib import Path

    from adk_skills_agent.core.models import Skill

    store = SkillsStore(sqlite_session)
    store.ensure_schema()

    skill = Skill(
        name="versioned-skill",
        description="Version 1",
        location=Path("/test/SKILL.md"),
        skill_dir=Path("/test"),
        instructions="v1 instructions",
    )

    record1 = store.save_skill(skill)
    assert record1.version == 1

    skill.description = "Version 2"
    skill.instructions = "v2 instructions"
    record2 = store.save_skill(skill)
    assert record2.version == 2

    # Verify both versions exist
    versions = store.list_versions("versioned-skill")
    assert versions == [1, 2]


def test_store_save_skill_updates_existing_version(sqlite_session: Session) -> None:
    """Ensure save_skill updates an existing version when specified."""
    from pathlib import Path

    from adk_skills_agent.core.models import Skill

    store = SkillsStore(sqlite_session)
    store.ensure_schema()

    skill = Skill(
        name="update-skill",
        description="Original",
        location=Path("/test/SKILL.md"),
        skill_dir=Path("/test"),
        instructions="original instructions",
    )

    store.save_skill(skill, version=1)

    # Update the same version
    skill.description = "Updated"
    skill.instructions = "updated instructions"
    store.save_skill(skill, version=1)

    # Should still be version 1, but updated
    retrieved = store.get_skill("update-skill")
    assert retrieved.description == "Updated"
    assert retrieved.instructions == "updated instructions"

    # Only one version should exist
    versions = store.list_versions("update-skill")
    assert versions == [1]


def test_store_delete_skill_single_version(sqlite_session: Session) -> None:
    """Ensure delete_skill can delete a single version."""
    store = SkillsStore(sqlite_session)
    store.ensure_schema()

    sqlite_session.add_all(
        [
            SkillRecord(
                name="delete-me",
                app_name=None,
                version=1,
                description="v1",
                instructions="v1 instructions",
            ),
            SkillRecord(
                name="delete-me",
                app_name=None,
                version=2,
                description="v2",
                instructions="v2 instructions",
            ),
        ]
    )
    sqlite_session.commit()

    count = store.delete_skill("delete-me", version=1)
    assert count == 1

    versions = store.list_versions("delete-me")
    assert versions == [2]


def test_store_delete_skill_all_versions(sqlite_session: Session) -> None:
    """Ensure delete_skill deletes all versions when version not specified."""
    store = SkillsStore(sqlite_session)
    store.ensure_schema()

    sqlite_session.add_all(
        [
            SkillRecord(
                name="delete-all",
                app_name=None,
                version=1,
                description="v1",
                instructions="v1",
            ),
            SkillRecord(
                name="delete-all",
                app_name=None,
                version=2,
                description="v2",
                instructions="v2",
            ),
        ]
    )
    sqlite_session.commit()

    count = store.delete_skill("delete-all")
    assert count == 2
    assert not store.skill_exists("delete-all")


def test_store_skill_exists(sqlite_session: Session) -> None:
    """Ensure skill_exists correctly detects skills."""
    store = SkillsStore(sqlite_session)
    store.ensure_schema()

    assert not store.skill_exists("nonexistent")

    sqlite_session.add(
        SkillRecord(
            name="exists-test",
            app_name=None,
            version=1,
            description="test",
            instructions="test",
        )
    )
    sqlite_session.commit()

    assert store.skill_exists("exists-test")
    assert store.skill_exists("exists-test", version=1)
    assert not store.skill_exists("exists-test", version=2)


def test_store_list_versions(sqlite_session: Session) -> None:
    """Ensure list_versions returns all versions in order."""
    store = SkillsStore(sqlite_session)
    store.ensure_schema()

    sqlite_session.add_all(
        [
            SkillRecord(
                name="multi-version",
                app_name=None,
                version=3,
                description="v3",
                instructions="v3",
            ),
            SkillRecord(
                name="multi-version",
                app_name=None,
                version=1,
                description="v1",
                instructions="v1",
            ),
            SkillRecord(
                name="multi-version",
                app_name=None,
                version=2,
                description="v2",
                instructions="v2",
            ),
        ]
    )
    sqlite_session.commit()

    versions = store.list_versions("multi-version")
    assert versions == [1, 2, 3]


def test_store_app_scoped_operations(sqlite_session: Session) -> None:
    """Ensure CRUD operations respect app scoping."""
    from pathlib import Path

    from adk_skills_agent.core.models import Skill

    store = SkillsStore(sqlite_session)
    store.ensure_schema()

    skill = Skill(
        name="scoped-skill",
        description="app scoped",
        location=Path("/test/SKILL.md"),
        skill_dir=Path("/test"),
        instructions="app instructions",
    )

    # Save for app "my-app"
    store.save_skill(skill, app_name="my-app")

    # Should exist for "my-app"
    assert store.skill_exists("scoped-skill", app_name="my-app")
    # Should not exist globally
    assert not store.skill_exists("scoped-skill", app_name=None)

    # Delete for "my-app"
    count = store.delete_skill("scoped-skill", app_name="my-app")
    assert count == 1
    assert not store.skill_exists("scoped-skill", app_name="my-app")


# Registry integration tests


def test_registry_save_and_load_skill(sqlite_session: Session) -> None:
    """Ensure registry can save and load skills from DB."""
    from pathlib import Path

    from adk_skills_agent.core.models import Skill

    store = SkillsStore(sqlite_session)
    store.ensure_schema()

    config = SkillsConfig(db_enabled=True, db_session=sqlite_session)
    registry = SkillsRegistry(config=config)

    skill = Skill(
        name="registry-test",
        description="saved via registry",
        location=Path("/test/SKILL.md"),
        skill_dir=Path("/test"),
        instructions="registry instructions",
    )

    registry.save_skill_to_db(skill)

    # Should be discoverable
    assert "registry-test" in registry
    assert registry.skill_exists_in_db("registry-test")

    # Should be loadable
    loaded = registry.load_skill("registry-test")
    assert loaded.description == "saved via registry"


def test_registry_delete_skill(sqlite_session: Session) -> None:
    """Ensure registry can delete skills from DB."""
    store = SkillsStore(sqlite_session)
    store.ensure_schema()

    sqlite_session.add(
        SkillRecord(
            name="to-delete",
            app_name=None,
            version=1,
            description="will be deleted",
            instructions="delete me",
        )
    )
    sqlite_session.commit()

    config = SkillsConfig(db_enabled=True, db_session=sqlite_session)
    registry = SkillsRegistry(config=config)

    assert "to-delete" in registry

    count = registry.delete_skill_from_db("to-delete")
    assert count == 1
    assert "to-delete" not in registry


def test_registry_list_versions(sqlite_session: Session) -> None:
    """Ensure registry can list skill versions."""
    store = SkillsStore(sqlite_session)
    store.ensure_schema()

    sqlite_session.add_all(
        [
            SkillRecord(
                name="versioned",
                app_name=None,
                version=1,
                description="v1",
                instructions="v1",
            ),
            SkillRecord(
                name="versioned",
                app_name=None,
                version=2,
                description="v2",
                instructions="v2",
            ),
        ]
    )
    sqlite_session.commit()

    config = SkillsConfig(db_enabled=True, db_session=sqlite_session)
    registry = SkillsRegistry(config=config)

    versions = registry.list_skill_versions("versioned")
    assert versions == [1, 2]


def test_registry_len_no_double_count(sqlite_session: Session) -> None:
    """Ensure __len__ doesn't double-count skills in both registries."""
    from pathlib import Path

    store = SkillsStore(sqlite_session)
    store.ensure_schema()

    # Add a skill to DB
    sqlite_session.add(
        SkillRecord(
            name="shared-skill",
            app_name=None,
            version=1,
            description="in db",
            instructions="db instructions",
        )
    )
    sqlite_session.commit()

    config = SkillsConfig(db_enabled=True, db_session=sqlite_session)
    registry = SkillsRegistry(config=config)

    # Manually add the same skill to file registry (simulating discovery)
    from adk_skills_agent.core.models import SkillMetadata

    registry._metadata_registry["shared-skill"] = SkillMetadata(
        name="shared-skill",
        description="in files",
        location=Path("/test/SKILL.md"),
    )

    # Should count as 1, not 2
    assert len(registry) == 1


def test_registry_import_skill_to_db(sqlite_session: Session, tmp_path: Path) -> None:
    """Ensure import_skill_to_db imports a single file-based skill."""
    store = SkillsStore(sqlite_session)
    store.ensure_schema()

    # Create test skill file
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: my-skill
description: A test skill
license: MIT
---
Instructions for my skill.
"""
    )

    config = SkillsConfig(db_enabled=True, db_session=sqlite_session)
    registry = SkillsRegistry(config=config)
    registry.discover([tmp_path])

    # Import single skill
    registry.import_skill_to_db("my-skill")

    # Verify it's in DB
    assert registry.skill_exists_in_db("my-skill")

    # Verify content
    skill = registry.load_skill("my-skill")
    assert skill.description == "A test skill"
    assert skill.license == "MIT"
    assert "Instructions for my skill" in skill.instructions


def test_registry_import_skill_to_db_not_found(sqlite_session: Session) -> None:
    """Ensure import_skill_to_db raises error for non-existent skill."""
    from adk_skills_agent.exceptions import SkillNotFoundError

    store = SkillsStore(sqlite_session)
    store.ensure_schema()

    config = SkillsConfig(db_enabled=True, db_session=sqlite_session)
    registry = SkillsRegistry(config=config)

    with pytest.raises(SkillNotFoundError):
        registry.import_skill_to_db("nonexistent-skill")


def test_registry_import_all_to_db(sqlite_session: Session, tmp_path: Path) -> None:
    """Ensure import_all_to_db imports all file-based skills."""
    store = SkillsStore(sqlite_session)
    store.ensure_schema()

    # Create test skill files
    skill1_dir = tmp_path / "skill-one"
    skill1_dir.mkdir()
    (skill1_dir / "SKILL.md").write_text(
        """---
name: skill-one
description: First skill
---
Instructions for skill one.
"""
    )

    skill2_dir = tmp_path / "skill-two"
    skill2_dir.mkdir()
    (skill2_dir / "SKILL.md").write_text(
        """---
name: skill-two
description: Second skill
---
Instructions for skill two.
"""
    )

    config = SkillsConfig(db_enabled=True, db_session=sqlite_session)
    registry = SkillsRegistry(config=config)
    registry.discover([tmp_path])

    # Import all to DB
    count = registry.import_all_to_db()
    assert count == 2

    # Verify both are in DB
    assert registry.skill_exists_in_db("skill-one")
    assert registry.skill_exists_in_db("skill-two")


def test_registry_import_all_to_db_skip_existing(sqlite_session: Session, tmp_path: Path) -> None:
    """Ensure import_all_to_db skips existing skills by default."""
    store = SkillsStore(sqlite_session)
    store.ensure_schema()

    # Pre-add one skill to DB
    sqlite_session.add(
        SkillRecord(
            name="skill-one",
            app_name=None,
            version=1,
            description="already in db",
            instructions="db instructions",
        )
    )
    sqlite_session.commit()

    # Create test skill files
    skill1_dir = tmp_path / "skill-one"
    skill1_dir.mkdir()
    (skill1_dir / "SKILL.md").write_text(
        """---
name: skill-one
description: First skill from file
---
File instructions for skill one.
"""
    )

    skill2_dir = tmp_path / "skill-two"
    skill2_dir.mkdir()
    (skill2_dir / "SKILL.md").write_text(
        """---
name: skill-two
description: Second skill
---
Instructions for skill two.
"""
    )

    config = SkillsConfig(db_enabled=True, db_session=sqlite_session)
    registry = SkillsRegistry(config=config)
    registry.discover([tmp_path])

    # Import all - should skip skill-one
    count = registry.import_all_to_db(skip_existing=True)
    assert count == 1

    # skill-one should still have original DB content
    skill_one = registry.load_skill("skill-one")
    assert skill_one.description == "already in db"


def test_registry_import_all_to_db_no_skip(sqlite_session: Session, tmp_path: Path) -> None:
    """Ensure import_all_to_db creates new versions when skip_existing=False."""
    store = SkillsStore(sqlite_session)
    store.ensure_schema()

    # Pre-add one skill to DB
    sqlite_session.add(
        SkillRecord(
            name="skill-one",
            app_name=None,
            version=1,
            description="v1 in db",
            instructions="v1 instructions",
        )
    )
    sqlite_session.commit()

    # Create test skill file
    skill1_dir = tmp_path / "skill-one"
    skill1_dir.mkdir()
    (skill1_dir / "SKILL.md").write_text(
        """---
name: skill-one
description: Updated from file
---
Updated instructions.
"""
    )

    config = SkillsConfig(db_enabled=True, db_session=sqlite_session)
    registry = SkillsRegistry(config=config)
    registry.discover([tmp_path])

    # Import all with skip_existing=False
    count = registry.import_all_to_db(skip_existing=False)
    assert count == 1

    # Should now have 2 versions
    versions = registry.list_skill_versions("skill-one")
    assert versions == [1, 2]

    # Latest version should have updated content
    skill_one = registry.load_skill("skill-one")
    assert skill_one.description == "Updated from file"


# Error handling tests


def test_registry_db_operations_require_db_enabled() -> None:
    """Ensure DB operations raise RuntimeError when DB is not enabled."""
    from adk_skills_agent.core.models import Skill

    registry = SkillsRegistry()  # DB not enabled

    skill = Skill(
        name="test",
        description="test",
        location=Path("/test"),
        skill_dir=Path("/test"),
        instructions="test",
    )

    with pytest.raises(RuntimeError, match="Database not enabled"):
        registry.save_skill_to_db(skill)

    with pytest.raises(RuntimeError, match="Database not enabled"):
        registry.delete_skill_from_db("test")

    with pytest.raises(RuntimeError, match="Database not enabled"):
        registry.import_skill_to_db("test")

    with pytest.raises(RuntimeError, match="Database not enabled"):
        registry.import_all_to_db()

    with pytest.raises(RuntimeError, match="Database not enabled"):
        registry.list_skill_versions("test")

    with pytest.raises(RuntimeError, match="Database not enabled"):
        registry.skill_exists_in_db("test")
