"""Alembic helpers for integrating ADK skills models into app migrations."""

from __future__ import annotations

from sqlalchemy import MetaData

from adk_skills_agent.db.models import Base


def get_metadata() -> MetaData:
    """Return SQLAlchemy metadata for Alembic configuration."""
    return Base.metadata
