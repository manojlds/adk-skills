"""Markdown body parser for SKILL.md files."""


def extract_body(content: str) -> str:
    """Extract the markdown body from SKILL.md content.

    Args:
        content: Raw content of SKILL.md file (with frontmatter)

    Returns:
        Markdown body content (without frontmatter)
    """
    # Handle case where there's no frontmatter
    if not content.startswith("---"):
        return content.strip()

    # Split on --- delimiters
    parts = content.split("---", 2)

    # If frontmatter exists, return the body
    if len(parts) >= 3:
        return parts[2].strip()

    # If frontmatter is not properly closed, return empty
    return ""


def parse_markdown(content: str) -> tuple[str, str]:
    """Parse SKILL.md separating frontmatter and body.

    Args:
        content: Raw content of SKILL.md file

    Returns:
        Tuple of (frontmatter string, markdown body)
    """
    if not content.startswith("---"):
        return "", content.strip()

    parts = content.split("---", 2)

    if len(parts) >= 3:
        frontmatter = parts[1].strip()
        body = parts[2].strip()
        return frontmatter, body

    return "", content.strip()
