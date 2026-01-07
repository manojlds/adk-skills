"""Tests for markdown parser."""

from adk_skills_agent.utils.markdown import extract_body, parse_markdown


class TestExtractBody:
    """Tests for extract_body function."""

    def test_extract_with_frontmatter(self) -> None:
        """Test extracting body from content with frontmatter."""
        content = """---
name: test
---

# Body

Content here"""
        body = extract_body(content)
        assert body == "# Body\n\nContent here"

    def test_extract_without_frontmatter(self) -> None:
        """Test extracting body from content without frontmatter."""
        content = "# Just markdown\n\nNo frontmatter"
        body = extract_body(content)
        assert body == "# Just markdown\n\nNo frontmatter"

    def test_extract_unclosed_frontmatter(self) -> None:
        """Test extracting from unclosed frontmatter."""
        content = """---
name: test

No closing ---"""
        body = extract_body(content)
        assert body == ""

    def test_extract_empty_body(self) -> None:
        """Test extracting empty body."""
        content = """---
name: test
---

"""
        body = extract_body(content)
        assert body == ""


class TestParseMarkdown:
    """Tests for parse_markdown function."""

    def test_parse_with_frontmatter(self) -> None:
        """Test parsing content with frontmatter."""
        content = """---
name: test
description: Test skill
---

# Body"""
        frontmatter, body = parse_markdown(content)

        assert "name: test" in frontmatter
        assert "description: Test skill" in frontmatter
        assert body == "# Body"

    def test_parse_without_frontmatter(self) -> None:
        """Test parsing content without frontmatter."""
        content = "# Just markdown"
        frontmatter, body = parse_markdown(content)

        assert frontmatter == ""
        assert body == "# Just markdown"

    def test_parse_empty_content(self) -> None:
        """Test parsing empty content."""
        frontmatter, body = parse_markdown("")

        assert frontmatter == ""
        assert body == ""
