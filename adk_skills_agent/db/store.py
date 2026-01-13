"""Database-backed skills store using SQLAlchemy sessions."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from adk_skills_agent.core.models import Skill, SkillMetadata
from adk_skills_agent.db.models import Base, SkillRecord


class SkillsStore:
    """Persisted skills store backed by a SQLAlchemy session."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def ensure_schema(self) -> None:
        """Create tables if they do not exist."""
        Base.metadata.create_all(bind=self._session.get_bind())

    def list_metadata(self, app_name: Optional[str] = None) -> list[SkillMetadata]:
        """List metadata for the latest version of each skill."""
        records = self._fetch_records(app_name)
        return [self._record_to_metadata(record) for record in records]

    def get_skill(
        self, name: str, app_name: Optional[str] = None, version: Optional[int] = None
    ) -> Skill:
        """Fetch a skill by name (and optional version)."""
        record = self._fetch_skill_record(name, app_name=app_name, version=version)
        if record is None and app_name is not None:
            record = self._fetch_skill_record(name, app_name=None, version=version)
        if record is None:
            raise KeyError(f"Skill '{name}' not found in database.")
        return self._record_to_skill(record)

    def _fetch_records(self, app_name: Optional[str]) -> list[SkillRecord]:
        stmt = select(SkillRecord)
        if app_name is not None:
            stmt = stmt.where((SkillRecord.app_name == app_name) | (SkillRecord.app_name.is_(None)))
        stmt = stmt.order_by(SkillRecord.name, SkillRecord.app_name.is_(None), SkillRecord.version.desc())
        records = list(self._session.execute(stmt).scalars())
        return list(self._latest_records(records, app_name))

    def _latest_records(
        self, records: Iterable[SkillRecord], app_name: Optional[str]
    ) -> Iterable[SkillRecord]:
        selected: dict[str, SkillRecord] = {}
        for record in records:
            if record.name not in selected:
                selected[record.name] = record
        return selected.values()

    def _fetch_skill_record(
        self, name: str, app_name: Optional[str], version: Optional[int]
    ) -> SkillRecord | None:
        stmt: Select[tuple[SkillRecord]] = select(SkillRecord).where(SkillRecord.name == name)
        if app_name is None:
            stmt = stmt.where(SkillRecord.app_name.is_(None))
        else:
            stmt = stmt.where(SkillRecord.app_name == app_name)
        if version is not None:
            stmt = stmt.where(SkillRecord.version == version)
        else:
            stmt = stmt.order_by(SkillRecord.version.desc())
        return self._session.execute(stmt).scalars().first()

    def _record_to_metadata(self, record: SkillRecord) -> SkillMetadata:
        location = Path(record.location) if record.location else Path(f"/__db__/{record.name}")
        return SkillMetadata(
            name=record.name,
            description=record.description,
            location=location,
            license=record.license,
            compatibility=record.compatibility,
            allowed_tools=record.allowed_tools,
            metadata=record.metadata_json or {},
        )

    def _record_to_skill(self, record: SkillRecord) -> Skill:
        location = Path(record.location) if record.location else Path(f"/__db__/{record.name}/SKILL.md")
        skill_dir = Path(record.skill_dir) if record.skill_dir else Path(f"/__db__/{record.name}")
        return Skill(
            name=record.name,
            description=record.description,
            location=location,
            skill_dir=skill_dir,
            instructions=record.instructions,
            license=record.license,
            compatibility=record.compatibility,
            allowed_tools=record.allowed_tools,
            metadata=record.metadata_json or {},
        )
