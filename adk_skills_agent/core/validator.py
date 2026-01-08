"""Skill validator - validate against agentskills.io specification."""

import re
from pathlib import Path
from typing import Union

from adk_skills_agent.core.models import Skill, SkillMetadata, ValidationResult
from adk_skills_agent.core.parser import find_skill_md, parse_metadata


def validate_skill_name(name: str) -> list[str]:
    """Validate skill name against spec.

    Spec requirements:
    - Lowercase letters, numbers, and hyphens only
    - Must not start or end with hyphen
    - Max 64 characters

    Args:
        name: Skill name to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    if not name:
        errors.append("Skill name cannot be empty")
        return errors

    if len(name) > 64:
        errors.append(f"Skill name too long (max 64 chars): {len(name)}")

    if name.startswith("-") or name.endswith("-"):
        errors.append("Skill name cannot start or end with hyphen")

    # Check for valid characters (lowercase, numbers, hyphens)
    if not re.match(r"^[a-z0-9-]+$", name):
        errors.append("Skill name must contain only lowercase letters, numbers, and hyphens")

    return errors


def validate_skill_description(description: str) -> list[str]:
    """Validate skill description against spec.

    Spec requirements:
    - Non-empty
    - Max 1024 characters

    Args:
        description: Skill description to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    if not description or not description.strip():
        errors.append("Skill description cannot be empty")
        return errors

    if len(description) > 1024:
        errors.append(f"Skill description too long (max 1024 chars): {len(description)}")

    return errors


def validate_skill_compatibility(compatibility: str) -> list[str]:
    """Validate skill compatibility field against spec.

    Spec requirements:
    - Max 500 characters if present

    Args:
        compatibility: Compatibility string to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    if compatibility and len(compatibility) > 500:
        errors.append(f"Compatibility field too long (max 500 chars): {len(compatibility)}")

    return errors


def validate_skill_metadata(metadata: SkillMetadata, strict: bool = True) -> ValidationResult:
    """Validate skill metadata against spec.

    Args:
        metadata: Skill metadata to validate
        strict: If True, enforce strict validation

    Returns:
        ValidationResult with errors and warnings
    """
    result = ValidationResult(valid=True, skill_path=metadata.location)

    # Validate required fields
    name_errors = validate_skill_name(metadata.name)
    for error in name_errors:
        result.add_error(error)

    desc_errors = validate_skill_description(metadata.description)
    for error in desc_errors:
        result.add_error(error)

    # Validate optional fields
    if metadata.compatibility:
        compat_errors = validate_skill_compatibility(metadata.compatibility)
        for error in compat_errors:
            result.add_error(error)

    # Warnings for missing optional fields (if strict)
    if strict:
        if not metadata.license:
            result.add_warning("License field not specified")

        if not metadata.compatibility:
            result.add_warning("Compatibility field not specified")

    return result


def validate_skill_directory(skill_path: Path, strict: bool = True) -> ValidationResult:
    """Validate a skill directory against spec.

    Args:
        skill_path: Path to skill directory or SKILL.md file
        strict: If True, enforce strict validation

    Returns:
        ValidationResult with validation details
    """
    # Handle both file and directory paths
    if skill_path.is_dir():
        skill_dir = skill_path
        skill_md = find_skill_md(skill_path)
        if skill_md is None:
            result = ValidationResult(valid=False, skill_path=skill_path)
            result.add_error("SKILL.md not found in directory")
            return result
        skill_path = skill_md
    else:
        skill_dir = skill_path.parent

    result = ValidationResult(valid=True, skill_path=skill_path)

    # Parse and validate metadata
    try:
        metadata = parse_metadata(skill_path)
        metadata_result = validate_skill_metadata(metadata, strict=strict)

        # Merge results
        result.errors.extend(metadata_result.errors)
        result.warnings.extend(metadata_result.warnings)
        if not metadata_result.valid:
            result.valid = False

    except Exception as e:
        result.add_error(f"Failed to parse SKILL.md: {e}")
        return result

    # Check directory structure (warnings only)
    if not (skill_dir / "scripts").exists():
        result.add_warning("No scripts/ directory found")

    if not (skill_dir / "references").exists():
        result.add_warning("No references/ directory found")

    return result


def validate_skill(
    skill: Union[Skill, SkillMetadata, Path], strict: bool = True
) -> ValidationResult:
    """Validate a skill against the agentskills.io specification.

    Convenience function that handles multiple input types.

    Args:
        skill: Skill, SkillMetadata, or Path to validate
        strict: If True, enforce strict validation

    Returns:
        ValidationResult with validation details
    """
    if isinstance(skill, Path):
        return validate_skill_directory(skill, strict=strict)
    elif isinstance(skill, SkillMetadata):
        return validate_skill_metadata(skill, strict=strict)
    elif isinstance(skill, Skill):
        return validate_skill_metadata(skill.to_metadata(), strict=strict)
    else:
        raise TypeError(f"Invalid skill type: {type(skill)}")
