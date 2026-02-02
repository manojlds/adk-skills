"""Database-backed skills store using SQLAlchemy sessions."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

from sqlalchemy import CursorResult, Select, delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from adk_skills_agent.core.models import Skill, SkillMetadata
from adk_skills_agent.db.models import Base, SkillRecord

# Maximum retries for version conflicts due to race conditions
_MAX_VERSION_RETRIES = 3


class SkillsStore:
    """Persisted skills store backed by a SQLAlchemy session."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def ensure_schema(self) -> None:
        """Create tables if they do not exist."""
        Base.metadata.create_all(bind=self._session.get_bind())

    def list_metadata(self, app_name: str | None = None) -> list[SkillMetadata]:
        """List metadata for the latest version of each skill."""
        records = self._fetch_records(app_name)
        return [self._record_to_metadata(record) for record in records]

    def get_skill(
        self, name: str, app_name: str | None = None, version: int | None = None
    ) -> Skill:
        """Fetch a skill by name (and optional version)."""
        record = self._fetch_skill_record(name, app_name=app_name, version=version)
        if record is None and app_name is not None:
            record = self._fetch_skill_record(name, app_name=None, version=version)
        if record is None:
            raise KeyError(f"Skill '{name}' not found in database.")
        return self._record_to_skill(record)

    def _fetch_records(self, app_name: str | None) -> list[SkillRecord]:
        stmt = select(SkillRecord)
        if app_name is not None:
            stmt = stmt.where((SkillRecord.app_name == app_name) | (SkillRecord.app_name.is_(None)))
        stmt = stmt.order_by(
            SkillRecord.name, SkillRecord.app_name.is_(None), SkillRecord.version.desc()
        )
        records = list(self._session.execute(stmt).scalars())
        return list(self._latest_records(records, app_name))

    def _latest_records(
        self, records: Iterable[SkillRecord], app_name: str | None
    ) -> Iterable[SkillRecord]:
        selected: dict[str, SkillRecord] = {}
        for record in records:
            if record.name not in selected:
                selected[record.name] = record
        return selected.values()

    def _fetch_skill_record(
        self, name: str, app_name: str | None, version: int | None
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
        location = (
            Path(record.location) if record.location else Path(f"/__db__/{record.name}/SKILL.md")
        )
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

    # CRUD operations

    def save_skill(
        self,
        skill: Skill,
        app_name: str | None = None,
        version: int | None = None,
        *,
        _commit: bool = True,
    ) -> SkillRecord:
        """Save a skill to the database.

        If version is None, auto-increments from the latest version.
        If version is specified and exists, updates that version.

        Args:
            skill: The skill to save
            app_name: Optional app scope for the skill
            version: Optional specific version (auto-increments if None)
            _commit: Internal flag to control commit behavior (for bulk operations)

        Returns:
            The saved SkillRecord

        Note:
            When auto-incrementing versions, this method handles race conditions
            by retrying with a new version number if a concurrent insert occurs.
        """
        # If version is specified, use direct save (no race condition)
        if version is not None:
            return self._save_skill_with_version(skill, app_name, version, _commit)

        # Auto-increment with retry logic to handle race conditions
        for attempt in range(_MAX_VERSION_RETRIES):
            latest = self._get_latest_version(skill.name, app_name)
            next_version = (latest or 0) + 1

            try:
                return self._save_skill_with_version(skill, app_name, next_version, _commit)
            except IntegrityError:
                # Version conflict - another process inserted the same version
                self._session.rollback()
                if attempt == _MAX_VERSION_RETRIES - 1:
                    raise  # Re-raise on final attempt
                # Retry with a new version number
                continue

        # Should not reach here, but satisfy type checker
        raise RuntimeError("Failed to save skill after maximum retries")

    def _save_skill_with_version(
        self,
        skill: Skill,
        app_name: str | None,
        version: int,
        commit: bool,
    ) -> SkillRecord:
        """Save a skill with a specific version number."""
        # Check if this exact version exists
        existing = self._fetch_skill_record(skill.name, app_name, version)
        if existing is not None:
            # Update existing record
            existing.description = skill.description
            existing.instructions = skill.instructions
            existing.location = str(skill.location) if skill.location else None
            existing.skill_dir = str(skill.skill_dir) if skill.skill_dir else None
            existing.license = skill.license
            existing.compatibility = skill.compatibility
            existing.allowed_tools = skill.allowed_tools
            existing.metadata_json = skill.metadata or {}
            if commit:
                self._session.commit()
            return existing

        # Create new record
        record = SkillRecord(
            name=skill.name,
            app_name=app_name,
            version=version,
            description=skill.description,
            instructions=skill.instructions,
            location=str(skill.location) if skill.location else None,
            skill_dir=str(skill.skill_dir) if skill.skill_dir else None,
            license=skill.license,
            compatibility=skill.compatibility,
            allowed_tools=skill.allowed_tools,
            metadata_json=skill.metadata or {},
        )
        self._session.add(record)
        if commit:
            self._session.commit()
        return record

    def delete_skill(
        self,
        name: str,
        app_name: str | None = None,
        version: int | None = None,
    ) -> int:
        """Delete skill(s) from the database.

        Args:
            name: Skill name to delete
            app_name: Optional app scope (None for global skills)
            version: If specified, deletes only that version.
                    If None, deletes all versions.

        Returns:
            Number of records deleted
        """
        stmt = delete(SkillRecord).where(SkillRecord.name == name)

        if app_name is None:
            stmt = stmt.where(SkillRecord.app_name.is_(None))
        else:
            stmt = stmt.where(SkillRecord.app_name == app_name)

        if version is not None:
            stmt = stmt.where(SkillRecord.version == version)

        result = cast(CursorResult[Any], self._session.execute(stmt))
        self._session.commit()
        return result.rowcount or 0

    def skill_exists(
        self,
        name: str,
        app_name: str | None = None,
        version: int | None = None,
    ) -> bool:
        """Check if a skill exists in the database.

        Args:
            name: Skill name to check
            app_name: Optional app scope
            version: Optional specific version to check

        Returns:
            True if skill exists
        """
        stmt = select(func.count()).select_from(SkillRecord).where(SkillRecord.name == name)

        if app_name is None:
            stmt = stmt.where(SkillRecord.app_name.is_(None))
        else:
            stmt = stmt.where(SkillRecord.app_name == app_name)

        if version is not None:
            stmt = stmt.where(SkillRecord.version == version)

        count = self._session.execute(stmt).scalar()
        return count is not None and count > 0

    def list_versions(
        self,
        name: str,
        app_name: str | None = None,
    ) -> list[int]:
        """List all versions of a skill.

        Args:
            name: Skill name
            app_name: Optional app scope

        Returns:
            List of version numbers in ascending order
        """
        stmt = (
            select(SkillRecord.version)
            .where(SkillRecord.name == name)
            .order_by(SkillRecord.version.asc())
        )

        if app_name is None:
            stmt = stmt.where(SkillRecord.app_name.is_(None))
        else:
            stmt = stmt.where(SkillRecord.app_name == app_name)

        return list(self._session.execute(stmt).scalars())

    def import_skill(
        self,
        skill: Skill,
        app_name: str | None = None,
        *,
        _commit: bool = True,
    ) -> SkillRecord:
        """Import a file-based skill into the database.

        Creates a new version of the skill in the database, preserving
        the original file location.

        Args:
            skill: The skill to import (typically loaded from file)
            app_name: Optional app scope for the imported skill
            _commit: Internal flag to control commit behavior (for bulk operations)

        Returns:
            The created SkillRecord
        """
        return self.save_skill(skill, app_name=app_name, _commit=_commit)

    def import_skills_bulk(
        self,
        skills: list[Skill],
        app_name: str | None = None,
        skip_existing: bool = True,
    ) -> int:
        """Import multiple skills in a single transaction.

        This method ensures atomicity - either all skills are imported
        or none are (on error, the transaction is rolled back).

        Args:
            skills: List of skills to import
            app_name: Optional app scope for imported skills
            skip_existing: If True, skips skills that already exist

        Returns:
            Number of skills imported

        Raises:
            Exception: Re-raises any exception after rolling back
        """
        imported = 0
        try:
            for skill in skills:
                if skip_existing and self.skill_exists(skill.name, app_name=app_name):
                    continue
                self.import_skill(skill, app_name=app_name, _commit=False)
                imported += 1

            self._session.commit()
            return imported
        except Exception:
            self._session.rollback()
            raise

    def _get_latest_version(self, name: str, app_name: str | None) -> int | None:
        """Get the latest version number for a skill."""
        stmt = select(func.max(SkillRecord.version)).where(SkillRecord.name == name)

        if app_name is None:
            stmt = stmt.where(SkillRecord.app_name.is_(None))
        else:
            stmt = stmt.where(SkillRecord.app_name == app_name)

        return self._session.execute(stmt).scalar()
