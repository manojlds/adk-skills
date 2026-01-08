# ADK Skills - Project Structure

## Directory Layout

```
adk-skills/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                    # CI/CD pipeline
│   │   ├── publish.yml               # PyPI publishing
│   │   └── docs.yml                  # Documentation deployment
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   └── feature_request.md
│   └── PULL_REQUEST_TEMPLATE.md
│
├── adk_skills/                       # Main package
│   ├── __init__.py                   # Package exports
│   │
│   ├── core/                         # Core functionality
│   │   ├── __init__.py
│   │   ├── skill.py                  # Skill dataclass
│   │   ├── parser.py                 # SKILL.md parser
│   │   ├── loader.py                 # Skills loader
│   │   ├── validator.py              # Spec validator
│   │   └── manager.py                # SkillsManager class
│   │
│   ├── integration/                  # ADK integration
│   │   ├── __init__.py
│   │   ├── agent_adapter.py          # Agent instruction injection
│   │   ├── tool_adapter.py           # Script → Tool conversion
│   │   └── context_manager.py        # References & assets
│   │
│   ├── executors/                    # Script execution
│   │   ├── __init__.py
│   │   ├── base.py                   # Base executor interface
│   │   ├── python_executor.py        # Python script executor
│   │   ├── bash_executor.py          # Bash script executor
│   │   └── sandbox.py                # Security & sandboxing
│   │
│   ├── utils/                        # Utilities
│   │   ├── __init__.py
│   │   ├── yaml_parser.py            # YAML frontmatter parser
│   │   └── markdown.py               # Markdown processing
│   │
│   ├── registry.py                   # SkillsRegistry class
│   ├── helpers.py                    # Helper functions
│   ├── config.py                     # Configuration system
│   ├── exceptions.py                 # Custom exceptions
│   ├── logging.py                    # Logging setup
│   └── cli.py                        # CLI interface
│
├── tests/                            # Test suite
│   ├── __init__.py
│   ├── conftest.py                   # Pytest fixtures
│   │
│   ├── core/
│   │   ├── test_skill.py
│   │   ├── test_parser.py
│   │   ├── test_loader.py
│   │   ├── test_validator.py
│   │   └── test_manager.py
│   │
│   ├── integration/
│   │   ├── test_agent_adapter.py
│   │   ├── test_tool_adapter.py
│   │   └── test_context_manager.py
│   │
│   ├── executors/
│   │   ├── test_python_executor.py
│   │   ├── test_bash_executor.py
│   │   └── test_sandbox.py
│   │
│   ├── utils/
│   │   ├── test_yaml_parser.py
│   │   └── test_markdown.py
│   │
│   ├── test_registry.py
│   ├── test_helpers.py
│   ├── test_config.py
│   ├── test_cli.py
│   │
│   ├── fixtures/                     # Test fixtures
│   │   ├── skills/                   # Sample skills for testing
│   │   │   ├── valid-skill/
│   │   │   │   ├── SKILL.md
│   │   │   │   ├── scripts/
│   │   │   │   │   └── example.py
│   │   │   │   └── references/
│   │   │   │       └── docs.md
│   │   │   ├── minimal-skill/
│   │   │   │   └── SKILL.md
│   │   │   └── invalid-skill/
│   │   │       └── SKILL.md
│   │   └── skill_md_samples/        # SKILL.md test cases
│   │
│   └── integration/                  # Integration tests
│       ├── test_full_pipeline.py
│       └── test_with_adk.py
│
├── examples/                         # Usage examples
│   ├── README.md
│   │
│   ├── basic_example.py              # Phase 1: Basic usage
│   ├── script_example.py             # Phase 2: With scripts
│   ├── advanced_example.py           # Phase 3: Advanced features
│   ├── multi_agent_example.py        # Multiple agents with different skills
│   │
│   └── skills/                       # Example skills
│       ├── hello-skill/
│       │   └── SKILL.md
│       ├── calculator/
│       │   ├── SKILL.md
│       │   └── scripts/
│       │       └── calculate.py
│       ├── web-scraper/
│       │   ├── SKILL.md
│       │   ├── scripts/
│       │   │   └── scrape.py
│       │   └── references/
│       │       └── best_practices.md
│       └── data-analyzer/
│           ├── SKILL.md
│           ├── scripts/
│           │   ├── analyze.py
│           │   └── visualize.py
│           └── assets/
│               └── report_template.html
│
├── docs/                             # Documentation
│   ├── index.md
│   ├── quickstart.md
│   ├── user-guide/
│   │   ├── installation.md
│   │   ├── basic-usage.md
│   │   ├── loading-skills.md
│   │   ├── script-execution.md
│   │   ├── configuration.md
│   │   └── troubleshooting.md
│   ├── skill-developer-guide/
│   │   ├── creating-skills.md
│   │   ├── skill-structure.md
│   │   ├── writing-scripts.md
│   │   ├── best-practices.md
│   │   └── examples.md
│   ├── api-reference/
│   │   ├── skills-manager.md
│   │   ├── skill-class.md
│   │   ├── helpers.md
│   │   └── cli.md
│   ├── architecture/
│   │   ├── overview.md
│   │   ├── data-models.md
│   │   ├── pipeline.md
│   │   └── security.md
│   └── contributing.md
│
├── scripts/                          # Development scripts
│   ├── setup_dev.sh                  # Setup dev environment
│   ├── run_tests.sh                  # Run test suite
│   ├── build_docs.sh                 # Build documentation
│   └── release.sh                    # Release workflow
│
├── .gitignore
├── .python-version                   # Python version for pyenv
├── pyproject.toml                    # Project metadata & dependencies
├── README.md                         # Main README
├── LICENSE                           # MIT License
├── DESIGN.md                         # Design document (created)
├── IMPLEMENTATION_PLAN.md            # Implementation plan (created)
├── PROJECT_STRUCTURE.md              # This file
├── CONTRIBUTING.md                   # Contribution guidelines
├── CHANGELOG.md                      # Version changelog
└── mkdocs.yml                        # MkDocs configuration
```

## Key Files Description

### Root Files

- **pyproject.toml**: Python project configuration (PEP 621)
  - Package metadata
  - Dependencies
  - Build system
  - Tool configurations (pytest, black, ruff, mypy)

- **README.md**: Project introduction and quick start
  - What is adk-skills
  - Installation instructions
  - Quick example
  - Links to documentation

- **LICENSE**: MIT License for open source distribution

- **DESIGN.md**: Architecture and design decisions

- **IMPLEMENTATION_PLAN.md**: Phased development plan

### Package Structure (`adk_skills/`)

#### Core Module (`core/`)
The heart of the library:
- **skill.py**: `Skill`, `SkillsConfig` dataclasses
- **parser.py**: Parse SKILL.md files
- **loader.py**: Discover and load skills
- **validator.py**: Validate against spec
- **manager.py**: Main `SkillsManager` API

#### Integration Module (`integration/`)
ADK-specific adapters:
- **agent_adapter.py**: Inject instructions into agents
- **tool_adapter.py**: Convert scripts to ADK tools
- **context_manager.py**: Manage references and assets

#### Executors Module (`executors/`)
Script execution engines:
- **base.py**: Abstract executor interface
- **python_executor.py**: Run Python scripts
- **bash_executor.py**: Run Bash scripts
- **sandbox.py**: Security and resource limits

#### Utils Module (`utils/`)
Helper utilities:
- **yaml_parser.py**: YAML frontmatter extraction
- **markdown.py**: Markdown processing

#### Top-Level Modules
- **registry.py**: Multi-source skill registry
- **helpers.py**: Convenience functions (`with_skills`, etc.)
- **config.py**: Configuration loading and management
- **exceptions.py**: Custom exception hierarchy
- **logging.py**: Structured logging setup
- **cli.py**: Command-line interface

### Tests (`tests/`)

Mirror the package structure for unit tests:
- Each module has a corresponding `test_*.py` file
- `fixtures/` contains test data (sample skills)
- `integration/` has end-to-end tests
- `conftest.py` defines pytest fixtures

### Examples (`examples/`)

Practical usage examples:
- Progressive complexity (basic → advanced)
- Real-world use cases
- Runnable example scripts
- Sample skills for testing

### Documentation (`docs/`)

Comprehensive documentation:
- User guides for getting started
- Skill developer guides for creating skills
- API reference (auto-generated from docstrings)
- Architecture documentation
- Built with MkDocs Material

### Development Scripts (`scripts/`)

Helper scripts for development:
- Environment setup
- Running tests with coverage
- Building and previewing docs
- Release automation

## Import Structure

### Public API (exported from `__init__.py`)

```python
from adk_skills_agent import (
    # Core classes
    SkillsManager,
    Skill,
    SkillsConfig,
    SkillsRegistry,

    # Helper functions
    with_skills,
    validate_skill,
    create_skill_template,

    # Exceptions
    SkillError,
    SkillLoadError,
    SkillValidationError,
    SkillExecutionError,
)
```

### Internal Imports

```python
# Within package
from adk_skills_agent.core.skill import Skill
from adk_skills_agent.core.parser import SkillParser
from adk_skills_agent.executors.python_executor import PythonExecutor
```

## Configuration Files

### pyproject.toml
```toml
[project]
name = "adk-skills"
version = "1.0.0"
description = "Agent Skills support for Google ADK"
authors = [{name = "Your Name", email = "you@example.com"}]
dependencies = [
    "google-adk>=1.0.0",
    "pyyaml>=6.0",
    "pydantic>=2.0",
    "click>=8.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "pytest-asyncio>=0.21",
    "black>=23.0",
    "ruff>=0.1",
    "mypy>=1.0",
]

[project.scripts]
adk-skills = "adk_skills.cli:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

[tool.coverage.run]
source = ["adk_skills"]
omit = ["*/tests/*"]

[tool.black]
line-length = 100
target-version = ['py39']

[tool.ruff]
line-length = 100
target-version = "py39"

[tool.mypy]
python_version = "3.9"
strict = true
```

### mkdocs.yml
```yaml
site_name: ADK Skills
theme:
  name: material
  features:
    - navigation.tabs
    - search.highlight

nav:
  - Home: index.md
  - Quick Start: quickstart.md
  - User Guide:
    - Installation: user-guide/installation.md
    - Basic Usage: user-guide/basic-usage.md
  - API Reference:
    - SkillsManager: api-reference/skills-manager.md
  - Contributing: contributing.md
```

## Development Workflow

### Setup
```bash
# Clone repository
git clone https://github.com/yourusername/adk-skills.git
cd adk-skills

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install in development mode
pip install -e ".[dev]"
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=adk_skills --cov-report=html

# Run specific test
pytest tests/core/test_parser.py
```

### Linting & Formatting
```bash
# Format code
black adk_skills tests examples

# Lint code
ruff check adk_skills tests

# Type check
mypy adk_skills
```

### Documentation
```bash
# Serve docs locally
mkdocs serve

# Build docs
mkdocs build
```

## Next Steps

1. ✅ Project structure defined
2. ⏭️ Create initial package scaffold
3. ⏭️ Setup development environment
4. ⏭️ Begin Phase 1 implementation

---

**Version**: 1.0
**Last Updated**: 2026-01-06
