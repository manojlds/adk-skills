"""Tests for YAML frontmatter parser."""

from pathlib import Path

import pytest

from adk_skills_agent.exceptions import SkillParseError
from adk_skills_agent.utils.yaml_parser import extract_frontmatter, parse_frontmatter


class TestParseFrontmatter:
    """Tests for parse_frontmatter function."""

    def test_valid_frontmatter(self) -> None:
        """Test parsing valid YAML frontmatter."""
        content = """---
name: test-skill
description: A test skill
license: MIT
---

# Body content
"""
        metadata, body = parse_frontmatter(content)

        assert metadata["name"] == "test-skill"
        assert metadata["description"] == "A test skill"
        assert metadata["license"] == "MIT"
        assert body == "# Body content"

    def test_minimal_frontmatter(self) -> None:
        """Test parsing minimal frontmatter."""
        content = """---
name: test-skill
description: A test skill
---

Body"""
        metadata, body = parse_frontmatter(content)

        assert metadata["name"] == "test-skill"
        assert metadata["description"] == "A test skill"
        assert body == "Body"

    def test_frontmatter_with_metadata(self) -> None:
        """Test parsing frontmatter with nested metadata."""
        content = """---
name: test-skill
description: A test skill
metadata:
  author: Test
  version: 1.0
---

Body"""
        metadata, body = parse_frontmatter(content)

        assert metadata["name"] == "test-skill"
        assert metadata["metadata"] == {"author": "Test", "version": "1.0"}

    def test_empty_content(self) -> None:
        """Test parsing empty content raises error."""
        with pytest.raises(SkillParseError, match="empty"):
            parse_frontmatter("")

    def test_no_frontmatter(self) -> None:
        """Test content without frontmatter raises error."""
        with pytest.raises(SkillParseError, match="must start with YAML frontmatter"):
            parse_frontmatter("Just some text")

    def test_unclosed_frontmatter(self) -> None:
        """Test unclosed frontmatter raises error."""
        content = """---
name: test-skill
description: A test skill

Body without closing ---"""
        with pytest.raises(SkillParseError):  # Caught by YAML parser
            parse_frontmatter(content)

    def test_invalid_yaml(self) -> None:
        """Test invalid YAML raises error."""
        content = """---
name: test-skill
description: [unclosed list
---

Body"""
        with pytest.raises(SkillParseError, match="Invalid YAML"):
            parse_frontmatter(content)

    def test_empty_frontmatter(self) -> None:
        """Test empty frontmatter raises error."""
        content = """---
---

Body"""
        with pytest.raises(SkillParseError, match="empty"):
            parse_frontmatter(content)

    def test_non_dict_frontmatter(self) -> None:
        """Test non-dictionary frontmatter raises error."""
        content = """---
- item1
- item2
---

Body"""
        with pytest.raises(SkillParseError, match="must be a YAML mapping"):
            parse_frontmatter(content)


class TestExtractFrontmatter:
    """Tests for extract_frontmatter function."""

    def test_extract_from_valid_file(self, skills_dir: Path) -> None:
        """Test extracting frontmatter from valid SKILL.md file."""
        skill_path = skills_dir / "valid-skill" / "SKILL.md"
        metadata = extract_frontmatter(skill_path)

        assert metadata["name"] == "valid-skill"
        assert metadata["description"] == "A valid test skill with all optional fields"
        assert metadata["license"] == "MIT"
        assert metadata["compatibility"] == "Requires Python 3.9+"

    def test_extract_from_minimal_file(self, skills_dir: Path) -> None:
        """Test extracting frontmatter from minimal SKILL.md file."""
        skill_path = skills_dir / "minimal-skill" / "SKILL.md"
        metadata = extract_frontmatter(skill_path)

        assert metadata["name"] == "minimal-skill"
        assert metadata["description"] == "A minimal test skill with only required fields"
        assert "license" not in metadata

    def test_extract_from_missing_file(self, tmp_path: Path) -> None:
        """Test extracting from missing file raises error."""
        missing_path = tmp_path / "nonexistent.md"
        with pytest.raises(SkillParseError, match="not found"):
            extract_frontmatter(missing_path)
