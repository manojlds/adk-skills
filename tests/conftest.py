"""Pytest configuration and shared fixtures."""

from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to the test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def skills_dir(fixtures_dir: Path) -> Path:
    """Return the path to the test skills directory."""
    return fixtures_dir / "skills"


@pytest.fixture
def temp_skill_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary directory for skill testing."""
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()
    yield skill_dir
