"""SQLAlchemy models for skills persistence."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


class SkillRecord(Base):
    """Skill record with versioning and optional app scoping."""

    __tablename__ = "adk_skills"
    __table_args__ = (
        UniqueConstraint("name", "app_name", "version", name="uq_adk_skills_name_app_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), index=True)
    app_name: Mapped[Optional[str]] = mapped_column(  # noqa: UP045
        String(128), nullable=True, index=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1)

    description: Mapped[str] = mapped_column(Text)
    instructions: Mapped[str] = mapped_column(Text)

    location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # noqa: UP045
    skill_dir: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # noqa: UP045

    license: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # noqa: UP045
    compatibility: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # noqa: UP045
    allowed_tools: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # noqa: UP045
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
