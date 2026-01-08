"""Tests for core data models."""

from pathlib import Path

from adk_skills_agent.core.models import Skill, SkillMetadata, SkillsConfig, ValidationResult


class TestSkillMetadata:
    """Tests for SkillMetadata dataclass."""

    def test_minimal_metadata(self) -> None:
        """Test creating metadata with only required fields."""
        metadata = SkillMetadata(
            name="test-skill",
            description="A test skill",
            location=Path("/path/to/SKILL.md"),
        )

        assert metadata.name == "test-skill"
        assert metadata.description == "A test skill"
        assert metadata.location == Path("/path/to/SKILL.md")
        assert metadata.license is None
        assert metadata.compatibility is None
        assert metadata.allowed_tools is None
        assert metadata.metadata == {}

    def test_full_metadata(self) -> None:
        """Test creating metadata with all fields."""
        metadata = SkillMetadata(
            name="test-skill",
            description="A test skill",
            location=Path("/path/to/SKILL.md"),
            license="MIT",
            compatibility="Requires Python 3.9+",
            allowed_tools="bash python",
            metadata={"author": "Test", "version": "1.0"},
        )

        assert metadata.name == "test-skill"
        assert metadata.description == "A test skill"
        assert metadata.license == "MIT"
        assert metadata.compatibility == "Requires Python 3.9+"
        assert metadata.allowed_tools == "bash python"
        assert metadata.metadata == {"author": "Test", "version": "1.0"}

    def test_to_dict(self) -> None:
        """Test converting metadata to dictionary."""
        metadata = SkillMetadata(
            name="test-skill",
            description="A test skill",
            location=Path("/path/to/SKILL.md"),
            license="MIT",
        )

        result = metadata.to_dict()

        assert result["name"] == "test-skill"
        assert result["description"] == "A test skill"
        assert result["location"] == "/path/to/SKILL.md"
        assert result["license"] == "MIT"
        assert "compatibility" not in result  # None values excluded
        assert "allowed_tools" not in result


class TestSkill:
    """Tests for Skill dataclass."""

    def test_minimal_skill(self) -> None:
        """Test creating skill with only required fields."""
        skill = Skill(
            name="test-skill",
            description="A test skill",
            location=Path("/path/to/SKILL.md"),
            skill_dir=Path("/path/to"),
            instructions="# Test Skill\n\nInstructions here",
        )

        assert skill.name == "test-skill"
        assert skill.description == "A test skill"
        assert skill.location == Path("/path/to/SKILL.md")
        assert skill.skill_dir == Path("/path/to")
        assert skill.instructions == "# Test Skill\n\nInstructions here"
        assert skill.scripts_dir is None
        assert skill.references_dir is None
        assert skill.assets_dir is None

    def test_full_skill(self) -> None:
        """Test creating skill with all fields."""
        skill = Skill(
            name="test-skill",
            description="A test skill",
            location=Path("/path/to/SKILL.md"),
            skill_dir=Path("/path/to"),
            instructions="# Test Skill\n\nInstructions here",
            license="MIT",
            compatibility="Requires Python 3.9+",
            scripts_dir=Path("/path/to/scripts"),
            references_dir=Path("/path/to/references"),
            assets_dir=Path("/path/to/assets"),
        )

        assert skill.license == "MIT"
        assert skill.compatibility == "Requires Python 3.9+"
        assert skill.scripts_dir == Path("/path/to/scripts")
        assert skill.references_dir == Path("/path/to/references")
        assert skill.assets_dir == Path("/path/to/assets")

    def test_to_metadata(self) -> None:
        """Test converting skill to metadata."""
        skill = Skill(
            name="test-skill",
            description="A test skill",
            location=Path("/path/to/SKILL.md"),
            skill_dir=Path("/path/to"),
            instructions="# Test Skill",
            license="MIT",
        )

        metadata = skill.to_metadata()

        assert isinstance(metadata, SkillMetadata)
        assert metadata.name == "test-skill"
        assert metadata.description == "A test skill"
        assert metadata.location == Path("/path/to/SKILL.md")
        assert metadata.license == "MIT"

    def test_to_dict(self) -> None:
        """Test converting skill to dictionary."""
        skill = Skill(
            name="test-skill",
            description="A test skill",
            location=Path("/path/to/SKILL.md"),
            skill_dir=Path("/path/to"),
            instructions="# Test Skill",
            scripts_dir=Path("/path/to/scripts"),
        )

        result = skill.to_dict()

        assert result["name"] == "test-skill"
        assert result["description"] == "A test skill"
        assert result["location"] == "/path/to/SKILL.md"
        assert result["skill_dir"] == "/path/to"
        assert result["instructions"] == "# Test Skill"
        assert result["scripts_dir"] == "/path/to/scripts"
        assert "references_dir" not in result  # None values excluded


class TestSkillsConfig:
    """Tests for SkillsConfig dataclass."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = SkillsConfig()

        assert config.skills_directories == []
        assert config.auto_discover is True
        assert config.enable_scripts is True
        assert config.script_timeout == 30
        assert config.sandbox_mode is True
        assert config.strict_validation is True
        assert config.allow_experimental is False

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = SkillsConfig(
            skills_directories=[Path("./skills")],
            auto_discover=False,
            script_timeout=60,
            allow_experimental=True,
        )

        assert config.skills_directories == [Path("./skills")]
        assert config.auto_discover is False
        assert config.script_timeout == 60
        assert config.allow_experimental is True


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_valid_result(self) -> None:
        """Test creating a valid validation result."""
        result = ValidationResult(valid=True, skill_path=Path("/path/to/skill"))

        assert result.valid is True
        assert result.skill_path == Path("/path/to/skill")
        assert result.errors == []
        assert result.warnings == []
        assert bool(result) is True

    def test_invalid_result(self) -> None:
        """Test creating an invalid validation result."""
        result = ValidationResult(
            valid=False,
            skill_path=Path("/path/to/skill"),
            errors=["Missing required field: name"],
        )

        assert result.valid is False
        assert result.errors == ["Missing required field: name"]
        assert bool(result) is False

    def test_add_error(self) -> None:
        """Test adding an error to validation result."""
        result = ValidationResult(valid=True, skill_path=Path("/path/to/skill"))

        result.add_error("Invalid name format")

        assert result.valid is False
        assert "Invalid name format" in result.errors
        assert bool(result) is False

    def test_add_warning(self) -> None:
        """Test adding a warning to validation result."""
        result = ValidationResult(valid=True, skill_path=Path("/path/to/skill"))

        result.add_warning("Compatibility field not specified")

        assert result.valid is True  # Warnings don't invalidate
        assert "Compatibility field not specified" in result.warnings
        assert bool(result) is True
