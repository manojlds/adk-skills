"""SQLite-backed tests for the database skills store."""

from __future__ import annotations

from collections.abc import Generator

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
