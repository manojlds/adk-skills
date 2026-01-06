# ADK Skills - Design Document

## Overview

`adk-skills` is a Python library that brings [Agent Skills](https://agentskills.io) support to Google's [Agent Development Kit (ADK)](https://github.com/google/adk-python). It enables ADK agents to discover, load, and use skills in the standard Agent Skills format, making capabilities portable across AI platforms.

## Problem Statement

- **ADK agents** need reusable, packaged capabilities beyond individual tools
- **Agent Skills** provide a standardized format for packaging agent capabilities
- Currently, no bridge exists between the Agent Skills standard and ADK
- Developers want to use the same skills across Claude, ADK, and other platforms

## Goals

1. **Skills Discovery**: Automatically discover skills from directories, packages, or registries
2. **Skills Loading**: Parse SKILL.md files and integrate them into ADK agents
3. **Instruction Integration**: Inject skill instructions into agent system prompts
4. **Script Execution**: Convert skill scripts into ADK tools
5. **Resource Management**: Handle references and assets appropriately
6. **Standard Compliance**: Full compatibility with agentskills.io specification
7. **Developer Experience**: Simple, Pythonic API for ADK developers

## Architecture

### Core Components

```
adk-skills/
├── adk_skills/
│   ├── __init__.py
│   ├── core/
│   │   ├── skill.py           # Skill data model
│   │   ├── parser.py          # SKILL.md parser
│   │   ├── loader.py          # Skills discovery & loading
│   │   └── validator.py       # Spec validation
│   ├── integration/
│   │   ├── agent_adapter.py   # ADK Agent integration
│   │   ├── tool_adapter.py    # Script → Tool conversion
│   │   └── context_manager.py # References & assets handling
│   ├── executors/
│   │   ├── python_executor.py # Execute Python scripts
│   │   └── bash_executor.py   # Execute Bash scripts
│   └── utils/
│       ├── yaml_parser.py     # YAML frontmatter parsing
│       └── markdown.py        # Markdown processing
├── tests/
├── examples/
├── docs/
└── pyproject.toml
```

### Data Model

```python
@dataclass
class Skill:
    """Represents a loaded Agent Skill"""
    name: str                          # Required: skill identifier
    description: str                   # Required: what skill does
    instructions: str                  # Markdown body content
    license: Optional[str]             # License info
    compatibility: Optional[str]       # Environment requirements
    metadata: Dict[str, Any]           # Custom metadata
    allowed_tools: List[str]           # Pre-approved tools

    # Directory structure
    skill_dir: Path                    # Root skill directory
    scripts: List[Path]                # Executable scripts
    references: List[Path]             # Reference documents
    assets: List[Path]                 # Template/binary files
```

## Integration Patterns

### Pattern 1: Agent-Level Skills

Skills modify the agent's instruction and add tools:

```python
from google.adk.agents import Agent
from adk_skills import SkillsManager

# Initialize skills manager
skills = SkillsManager()

# Load skills from directory
skills.load_from_directory("./skills")

# Create agent with skills
root_agent = Agent(
    name="assistant",
    model="gemini-2.5-flash",
    instruction=skills.get_combined_instructions(),
    tools=skills.get_tools()
)
```

### Pattern 2: Dynamic Skills Loading

Skills can be loaded/unloaded at runtime:

```python
from adk_skills import SkillsManager, with_skills

skills = SkillsManager()

# Load specific skills
skills.load_skill("my-skill")
skills.load_skill("another-skill")

# Create enhanced agent
agent = with_skills(
    Agent(name="assistant", model="gemini-2.5-flash"),
    skills=["my-skill", "another-skill"]
)
```

### Pattern 3: Skill Discovery

Auto-discover skills from multiple sources:

```python
from adk_skills import SkillsRegistry

registry = SkillsRegistry()

# Auto-discover from common locations
registry.discover([
    "./skills",                    # Local directory
    "~/.adk-skills",              # User skills
    "github:anthropics/skills",   # GitHub repo (future)
])

# List available skills
for skill in registry.list_skills():
    print(f"{skill.name}: {skill.description}")
```

## Skills Processing Pipeline

```
1. Discovery
   ├─ Scan directories for SKILL.md files
   ├─ Identify skill directory structure
   └─ Build skill inventory

2. Parsing
   ├─ Extract YAML frontmatter
   ├─ Validate required fields (name, description)
   ├─ Parse markdown instructions
   └─ Identify scripts, references, assets

3. Validation
   ├─ Check spec compliance
   ├─ Verify script executability
   ├─ Validate file references
   └─ Check compatibility requirements

4. Integration
   ├─ Combine skill instructions into agent prompt
   ├─ Convert scripts to ADK tools
   ├─ Load references into context (if needed)
   └─ Register assets for access

5. Execution
   ├─ Agent receives skill-enhanced instructions
   ├─ Agent can invoke skill-provided tools
   └─ Tools execute scripts in secure sandbox
```

## Script Execution

Skills can contain Python and Bash scripts that become ADK tools:

```python
# scripts/fetch_data.py becomes a tool
def fetch_data(source: str) -> dict:
    """Fetch data from source (auto-generated from script)"""
    result = execute_python_script(
        script_path="scripts/fetch_data.py",
        args={"source": source}
    )
    return result
```

### Security Considerations

- **Sandboxing**: Scripts run in isolated environments
- **Validation**: Input/output validation for all scripts
- **Permissions**: Explicit approval for file system/network access
- **Timeout**: Execution time limits
- **Resource Limits**: Memory and CPU constraints

## API Design

### SkillsManager API

```python
class SkillsManager:
    """Main interface for managing skills in ADK"""

    def __init__(self, config: Optional[SkillsConfig] = None):
        """Initialize with optional configuration"""

    def load_from_directory(self, path: str | Path) -> List[Skill]:
        """Load all skills from a directory"""

    def load_skill(self, path: str | Path) -> Skill:
        """Load a single skill"""

    def get_skill(self, name: str) -> Optional[Skill]:
        """Get loaded skill by name"""

    def list_skills(self) -> List[Skill]:
        """List all loaded skills"""

    def get_combined_instructions(self, skills: Optional[List[str]] = None) -> str:
        """Get combined instructions for agent"""

    def get_tools(self, skills: Optional[List[str]] = None) -> List[Callable]:
        """Get all tools from skills"""

    def unload_skill(self, name: str) -> bool:
        """Unload a skill"""
```

### Helper Functions

```python
def with_skills(agent: Agent, skills: List[str] | SkillsManager) -> Agent:
    """Enhance an ADK agent with skills"""

def validate_skill(skill_path: Path) -> ValidationResult:
    """Validate a skill against the spec"""

def create_skill_template(output_dir: Path, name: str) -> None:
    """Create a new skill from template"""
```

## Configuration

```python
@dataclass
class SkillsConfig:
    """Configuration for skills system"""

    # Discovery
    skills_directories: List[Path] = field(default_factory=list)
    auto_discover: bool = True

    # Execution
    enable_scripts: bool = True
    script_timeout: int = 30  # seconds
    sandbox_mode: bool = True

    # Integration
    inject_instructions: bool = True
    prefix_skill_name: bool = True
    combine_strategy: str = "concatenate"  # or "hierarchical"

    # Validation
    strict_validation: bool = True
    allow_experimental: bool = False
```

## Example Use Cases

### Use Case 1: Web Scraping Skill

```
web-scraper/
├── SKILL.md
├── scripts/
│   └── scrape.py
└── references/
    └── best_practices.md
```

**SKILL.md:**
```markdown
---
name: web-scraper
description: Extract content from websites efficiently and ethically
compatibility: Requires Python requests and beautifulsoup4
---

# Web Scraping Skill

Use this skill to extract structured data from websites.

## When to Use
- Extracting product information
- Gathering research data
- Monitoring content changes

## Guidelines
- Always respect robots.txt
- Use rate limiting
- Cache responses when appropriate
```

**Integration:**
```python
skills.load_skill("./skills/web-scraper")
agent = Agent(
    name="research_assistant",
    model="gemini-2.5-flash",
    instruction=skills.get_combined_instructions(),
    tools=skills.get_tools()
)
# Agent now has scraping instructions and scrape.py as a tool
```

### Use Case 2: Enterprise Skills Repository

```python
from adk_skills import SkillsRegistry

# Corporate skills repository
registry = SkillsRegistry()
registry.add_source("git+https://github.com/company/skills.git")

# Create specialized agents
customer_service_agent = Agent(
    name="customer_service",
    model="gemini-2.5-flash",
    instruction=registry.get_instructions([
        "handle-complaints",
        "check-order-status",
        "process-refunds"
    ]),
    tools=registry.get_tools([
        "handle-complaints",
        "check-order-status",
        "process-refunds"
    ])
)
```

## Technical Decisions

### 1. Instruction Injection Strategy

**Decision**: Concatenate skill instructions with agent instructions

**Options Considered:**
- **Concatenation** (chosen): Append skill instructions to agent's base instruction
- **Hierarchical**: Nest skills under sections
- **Dynamic**: Load into context only when needed

**Rationale**: Simple, predictable, works with ADK's instruction parameter

### 2. Script-to-Tool Conversion

**Decision**: Wrap scripts as Python callables with type hints

**Approach:**
- Parse script docstrings for function signatures
- Generate wrapper functions with proper types
- Use subprocess for bash, direct import for Python
- Return structured data (JSON-serializable)

### 3. References Handling

**Decision**: Make references available but don't auto-inject

**Rationale:**
- Large reference docs can bloat context
- Let agent request via tools if needed
- Provide helper: `get_reference(skill_name, filename)`

### 4. Compatibility Checking

**Decision**: Parse and warn, don't block

**Approach:**
- Parse compatibility field
- Check system capabilities
- Emit warnings for mismatches
- Let developers decide to proceed

## Dependencies

```toml
[project]
dependencies = [
    "google-adk>=1.0.0",      # ADK framework
    "pyyaml>=6.0",            # YAML parsing
    "markdown>=3.4",          # Markdown processing
    "pydantic>=2.0",          # Data validation
    "click>=8.0",             # CLI interface
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "black>=23.0",
    "ruff>=0.1",
    "mypy>=1.0",
]
```

## Standards Compliance

This library implements the Agent Skills specification version 1.0:

- ✅ SKILL.md with YAML frontmatter
- ✅ Required fields: name, description
- ✅ Optional fields: license, compatibility, metadata, allowed-tools
- ✅ scripts/ directory for executables
- ✅ references/ directory for documentation
- ✅ assets/ directory for templates/binaries
- ✅ Name validation (lowercase, hyphens, 64 chars max)
- ✅ Description validation (1024 chars max)

## Future Enhancements

### Phase 2
- **Remote Skills**: Load from GitHub, package registries
- **Skills Marketplace**: Discover and install from skillsmp.com
- **Skill Composition**: Combine multiple skills intelligently
- **Version Management**: Support skill versioning

### Phase 3
- **Multi-Agent Skills**: Skills that spawn sub-agents
- **Skill Analytics**: Track skill usage and effectiveness
- **Auto-Generation**: Create skills from examples
- **IDE Integration**: VS Code extension for skill development

## Testing Strategy

1. **Unit Tests**: Each component tested in isolation
2. **Integration Tests**: Full pipeline with sample skills
3. **Compliance Tests**: Validation against agentskills.io spec
4. **Security Tests**: Script execution sandboxing
5. **Performance Tests**: Large skill collections

## Documentation Plan

- **README.md**: Quick start and examples
- **API Reference**: Auto-generated from docstrings
- **User Guide**: Detailed usage patterns
- **Skill Developer Guide**: Creating skills for ADK
- **Migration Guide**: Adapting Claude skills to ADK

## Success Metrics

1. **Functionality**: Load and execute skills per spec
2. **Compatibility**: Works with existing Agent Skills
3. **Performance**: <100ms overhead per skill load
4. **Usability**: 5-line integration for basic use case
5. **Adoption**: Community creates ADK-specific skills

## References

- Agent Skills Specification: https://agentskills.io/specification
- Google ADK Documentation: https://google.github.io/adk-docs/
- ADK Python GitHub: https://github.com/google/adk-python
- Anthropic Skills Repository: https://github.com/anthropics/skills

---

**Document Version**: 1.0
**Last Updated**: 2026-01-06
**Status**: Design Phase
