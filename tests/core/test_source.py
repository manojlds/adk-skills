"""Tests for source-layer data contracts."""

import pytest

from adk_skills_agent.core.source import SkillFile


def test_skill_file_allows_metadata_only_listing_entry() -> None:
    file = SkillFile(
        relative_path="references/guide.md",
        mime_type="text/markdown",
        size_bytes=12,
        content_hash="hash",
    )

    assert file.text_content is None
    assert file.binary_content is None


def test_skill_file_allows_text_payload_only() -> None:
    file = SkillFile(
        relative_path="references/guide.md",
        mime_type="text/markdown",
        size_bytes=12,
        content_hash="hash",
        text_content="hello",
    )

    assert file.is_text is True
    assert file.is_binary is False


def test_skill_file_allows_binary_payload_only() -> None:
    file = SkillFile(
        relative_path="assets/logo.png",
        mime_type="image/png",
        size_bytes=8,
        content_hash="hash",
        binary_content=b"\x89PNG\r\n\x1a\n",
    )

    assert file.is_text is False
    assert file.is_binary is True


def test_skill_file_rejects_both_text_and_binary_payloads() -> None:
    with pytest.raises(ValueError, match="must not have both"):
        SkillFile(
            relative_path="assets/template.json",
            mime_type="application/json",
            size_bytes=2,
            content_hash="hash",
            text_content="{}",
            binary_content=b"{}",
        )
