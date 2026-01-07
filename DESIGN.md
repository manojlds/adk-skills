# ADK Skills - Design Document (Revised)

## Overview

`adk-skills` is a Python library that brings [Agent Skills](https://agentskills.io) support to Google's [Agent Development Kit (ADK)](https://github.com/google/adk-python). It enables ADK agents to discover and activate skills on-demand using the standard Agent Skills format, making capabilities portable across AI platforms.

## Problem Statement

- **ADK agents** need reusable, packaged capabilities for specialized tasks
- **Agent Skills** provide a standardized format (agentskills.io) for packaging agent capabilities
- Currently, no bridge exists between the Agent Skills standard and ADK
- Developers want to use the same skills across Claude, ADK, and other platforms

## How Agent Skills Actually Work

After studying the [reference implementation](https://github.com/agentskills/agentskills/tree/main/skills-ref) and [OpenCode's integration](https://github.com/anomalyco/opencode), the correct pattern is:

### ❌ NOT This (Initial Misconception)
```python
# WRONG: Pre-injecting all skill content bloats context
agent = Agent(
    instruction=skills.get_combined_instructions(),  # ❌ Bloats context
    tools=skills.get_tools()  # ❌ Creates tools upfront
)
```

### ✅ Correct Pattern: On-Demand Activation

1. **Discovery**: Scan directories for SKILL.md files, extract metadata (name + description)
2. **Tool Integration**: Provide a `use_skill` tool with `<available_skills>` in its description
3. **Activation**: When agent calls `use_skill("skill-name")`, return full SKILL.md content
4. **Optional**: Provide separate tools for script execution

```python
# CORRECT: Lightweight metadata + on-demand activation
agent = Agent(
    name="assistant",
    model="gemini-2.5-flash",
    tools=[
        skills.create_use_skill_tool(),      # Lists available skills, loads on demand
        skills.create_run_script_tool(),     # Optional: Execute skill scripts
    ]
)
```

## Goals

1. **Skills Discovery**: Scan directories for SKILL.md files (~50-100 tokens per skill)
2. **Metadata Extraction**: Parse frontmatter (name, description) for skill listing
3. **On-Demand Loading**: Load full instructions only when agent activates a skill
4. **Tool-Based Integration**: Provide ADK tools for skill activation and script execution
5. **Resource Access**: Enable access to scripts/, references/, assets/ directories
6. **Standard Compliance**: 100% compatible with agentskills.io specification
7. **Developer Experience**: Simple, Pythonic API matching OpenCode's pattern

## Architecture

### Core Components

```
adk-skills/
├── adk_skills/
│   ├── __init__.py
│   ├── core/
│   │   ├── skill.py           # Skill data model (metadata + content)
│   │   ├── parser.py          # SKILL.md parser (frontmatter + body)
│   │   ├── loader.py          # Skills discovery & loading
│   │   └── validator.py       # Spec validation
│   ├── tools/
│   │   ├── use_skill.py       # Tool: activate a skill
│   │   ├── run_script.py      # Tool: execute skill scripts
│   │   └── read_reference.py  # Tool: read skill references
│   ├── executors/
│   │   ├── python_executor.py # Execute Python scripts
│   │   └── bash_executor.py   # Execute Bash scripts
│   └── utils/
│       ├── yaml_parser.py     # YAML frontmatter parsing
│       └── markdown.py        # Markdown processing
```

### Data Model

```python
@dataclass
class SkillMetadata:
    """Lightweight metadata for skill discovery (50-100 tokens)"""
    name: str                          # Required: skill identifier
    description: str                   # Required: when to use this skill
    location: Path                     # Path to SKILL.md file

    # Optional frontmatter fields
    license: Optional[str] = None
    compatibility: Optional[str] = None
    allowed_tools: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Skill:
    """Full skill with content (loaded on-demand)"""
    # Metadata
    name: str
    description: str
    location: Path
    skill_dir: Path                    # Base directory

    # Full content (loaded on activation)
    instructions: str                  # Full markdown body

    # Optional fields
    license: Optional[str] = None
    compatibility: Optional[str] = None
    allowed_tools: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Directory structure (discovered lazily)
    scripts_dir: Optional[Path] = None      # scripts/ if exists
    references_dir: Optional[Path] = None   # references/ if exists
    assets_dir: Optional[Path] = None       # assets/ if exists
```

## Integration Pattern (Based on OpenCode)

### Step 1: Skills Discovery & Registry

```python
from adk_skills_agent import SkillsRegistry

# Initialize registry
registry = SkillsRegistry()

# Discover skills from directories
registry.discover([
    "./skills",           # Project skills
    "~/.adk/skills",     # User skills
])

# Registry now has lightweight metadata for all skills
print(f"Found {len(registry)} skills")
for meta in registry.list_metadata():
    print(f"  - {meta.name}: {meta.description}")
```

### Step 2: Create ADK Agent with Skills Support

```python
from google.adk.agents import Agent

# Create use_skill tool
use_skill_tool = registry.create_use_skill_tool()

# The tool's description contains <available_skills> block
# Agent sees available skills without loading full content

agent = Agent(
    name="assistant",
    model="gemini-2.5-flash",
    instruction="You are a helpful assistant.",
    tools=[
        use_skill_tool,                      # Main skill activation tool
        registry.create_run_script_tool(),   # Optional: run scripts
    ]
)
```

### Step 3: Agent Activates Skill On-Demand

When agent needs a skill:

```python
# Agent calls: use_skill(name="pdf-processing")
#
# Tool execution:
# 1. Loads full SKILL.md content
# 2. Returns instructions + base directory
# 3. Agent now has detailed guidance for the task
```

## Tool Design

### Tool 1: `use_skill`

**Purpose**: Activate a skill by loading its full instructions

**Tool Description** (what agent sees):
```
Load a skill to get detailed instructions for a specific task.
Skills provide specialized knowledge and step-by-step guidance.
Use this when a task matches an available skill's description.

<available_skills>
  <skill>
    <name>pdf-processing</name>
    <description>Extract text and tables from PDF files, fill forms, merge documents</description>
  </skill>
  <skill>
    <name>web-scraper</name>
    <description>Extract content from websites efficiently and ethically</description>
  </skill>
</available_skills>
```

**Parameters**:
```python
{
    "name": "skill-name"  # Required: skill identifier
}
```

**Returns**:
```python
{
    "skill_name": "pdf-processing",
    "base_directory": "/path/to/skills/pdf-processing",
    "instructions": "# PDF Processing Skill\n\n[Full SKILL.md content...]",
    "has_scripts": True,
    "has_references": True,
}
```

### Tool 2: `run_script` (Optional)

**Purpose**: Execute a script from an activated skill

**Parameters**:
```python
{
    "skill": "pdf-processing",
    "script": "extract_text.py",
    "args": {
        "file": "/path/to/document.pdf"
    }
}
```

**Returns**: Script output (stdout/stderr)

### Tool 3: `read_reference` (Optional)

**Purpose**: Read a reference document from a skill

**Parameters**:
```python
{
    "skill": "pdf-processing",
    "reference": "api_docs.md"
}
```

**Returns**: Reference file content

## Skills Processing Pipeline

```
1. Discovery (Startup)
   ├─ Scan configured directories
   ├─ Find SKILL.md files
   ├─ Parse frontmatter only (name, description)
   └─ Store in registry (~50-100 tokens per skill)

2. Tool Creation
   ├─ Generate use_skill tool
   ├─ Embed <available_skills> in tool description
   └─ Register with ADK agent

3. Skill Activation (On-Demand)
   ├─ Agent calls use_skill(name="...")
   ├─ Load full SKILL.md content
   ├─ Parse markdown body
   ├─ Discover subdirectories (scripts/, references/, assets/)
   └─ Return full instructions to agent

4. Script Execution (Optional)
   ├─ Agent calls run_script(skill="...", script="...")
   ├─ Locate script in skill's scripts/ directory
   ├─ Execute with provided arguments
   └─ Return output to agent
```

## API Design

### SkillsRegistry API

```python
class SkillsRegistry:
    """Main interface for managing skills in ADK"""

    def __init__(self, config: Optional[SkillsConfig] = None):
        """Initialize with optional configuration"""

    def discover(self, directories: List[str | Path]) -> int:
        """
        Discover skills from directories.
        Returns number of skills found.
        Parses only frontmatter for efficiency.
        """

    def list_metadata(self) -> List[SkillMetadata]:
        """List all discovered skills (lightweight metadata)"""

    def get_metadata(self, name: str) -> Optional[SkillMetadata]:
        """Get metadata for a specific skill"""

    def load_skill(self, name: str) -> Skill:
        """
        Load full skill content (on-demand).
        Parses complete SKILL.md including body.
        """

    def create_use_skill_tool(self) -> Callable:
        """
        Create ADK tool for skill activation.
        Tool description includes <available_skills> block.
        """

    def create_run_script_tool(self) -> Callable:
        """Create ADK tool for script execution"""

    def create_read_reference_tool(self) -> Callable:
        """Create ADK tool for reading references"""
```

### Helper Functions

```python
def with_skills(agent: Agent, directories: List[str | Path]) -> Agent:
    """
    Convenience function to add skills support to an existing agent.

    Example:
        agent = Agent(name="assistant", model="gemini-2.5-flash")
        agent = with_skills(agent, ["./skills", "~/.adk/skills"])
    """

def validate_skill(skill_path: Path) -> ValidationResult:
    """Validate a skill directory against the spec"""

def create_skill_template(output_dir: Path, name: str) -> None:
    """Create a new skill from template"""
```

## Example Use Cases

### Use Case 1: Research Assistant with Skills

```python
from google.adk.agents import Agent
from adk_skills_agent import SkillsRegistry

# Discover skills
registry = SkillsRegistry()
registry.discover(["./skills"])

# Create agent
agent = Agent(
    name="research_assistant",
    model="gemini-2.5-flash",
    instruction="You are a research assistant. Use available skills for specialized tasks.",
    tools=[
        registry.create_use_skill_tool(),
        registry.create_run_script_tool(),
        # ... other tools (web search, etc.)
    ]
)

# Agent workflow:
# 1. User: "Extract data from this research paper PDF"
# 2. Agent sees pdf-processing in available_skills
# 3. Agent calls use_skill(name="pdf-processing")
# 4. Gets detailed instructions for PDF processing
# 5. Agent calls run_script(skill="pdf-processing", script="extract.py", args={...})
# 6. Returns results to user
```

### Use Case 2: Multi-Agent System with Specialized Skills

```python
# Coordinator agent - no skills
coordinator = Agent(
    name="coordinator",
    model="gemini-2.5-flash",
    sub_agents=[research_agent, code_agent]
)

# Research agent - web scraping skills
research_registry = SkillsRegistry()
research_registry.discover(["./skills/research"])

research_agent = Agent(
    name="researcher",
    model="gemini-2.5-flash",
    tools=[research_registry.create_use_skill_tool()]
)

# Code agent - development skills
code_registry = SkillsRegistry()
code_registry.discover(["./skills/development"])

code_agent = Agent(
    name="developer",
    model="gemini-2.5-flash",
    tools=[code_registry.create_use_skill_tool()]
)
```

### Use Case 3: Filesystem-Based Pattern (Alternative)

For agents with filesystem access (like Claude Code), an alternative pattern:

```python
# Simpler pattern: Agent reads SKILL.md files directly
registry = SkillsRegistry()
registry.discover(["./skills"])

# Just inject metadata into system prompt
agent = Agent(
    name="assistant",
    model="gemini-2.5-flash",
    instruction=f"""
    You are a helpful assistant with access to the filesystem.

    {registry.to_available_skills_xml()}

    To activate a skill, read its SKILL.md file using the Read tool.
    """,
    tools=[read_tool, write_tool, bash_tool, ...]
)
```

## Technical Decisions

### 1. Skills Activation Strategy

**Decision**: Tool-based on-demand activation (not pre-injection)

**Rationale**:
- Keeps context small (~50-100 tokens per skill)
- Scales to hundreds of skills
- Agent only loads what it needs
- Matches reference implementation pattern

### 2. Metadata vs Full Content

**Decision**: Separate `SkillMetadata` (discovery) and `Skill` (activation)

**Rationale**:
- Efficient discovery without parsing full content
- Lazy loading of instructions
- Clearer separation of concerns

### 3. Tool Description for Skill Listing

**Decision**: Embed `<available_skills>` in tool description (not system prompt)

**Rationale**:
- Follows OpenCode's proven pattern
- Tool description is contextually relevant
- Easier to manage skill visibility per agent

### 4. Script Execution

**Decision**: Separate `run_script` tool (not automatic conversion)

**Rationale**:
- Scripts are optional skill components
- Explicit execution is more secure
- Agent decides when to run scripts
- Simpler implementation

### 5. Directory Structure Discovery

**Decision**: Discover scripts/references/assets lazily on activation

**Rationale**:
- Not needed during initial discovery
- Reduces filesystem I/O
- Only matters when skill is activated

## Dependencies

```toml
[project]
dependencies = [
    "google-adk>=1.0.0",      # ADK framework
    "pyyaml>=6.0",            # YAML parsing (or strictyaml)
    "pydantic>=2.0",          # Data validation
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

## Security Considerations

### Script Execution
- **Sandboxing**: Run in isolated subprocess with resource limits
- **Timeouts**: Default 30s execution timeout
- **Validation**: Verify script exists in skill directory
- **User Confirmation**: Optional permission system (like OpenCode)

### Path Traversal
- **Validation**: Ensure all paths stay within skill directory
- **Sanitization**: Reject `..` and absolute paths in script/reference names

### Malicious Skills
- **Allowlisting**: Only load from trusted directories
- **Validation**: Strict YAML and markdown parsing
- **Logging**: Track all skill activations and script executions

## Standards Compliance

Implements Agent Skills specification v1.0:

- ✅ SKILL.md with YAML frontmatter
- ✅ Required fields: name, description
- ✅ Optional fields: license, compatibility, metadata, allowed-tools
- ✅ scripts/ directory for executables
- ✅ references/ directory for documentation
- ✅ assets/ directory for templates/binaries
- ✅ Name validation (lowercase, hyphens, 64 chars max)
- ✅ Description validation (1024 chars max)

## Comparison with Reference Implementations

### skills-ref (Python)
```python
# Their approach
from skills_ref import to_prompt, read_properties, validate

# Generate XML for system prompt
prompt = to_prompt([Path("skill-a"), Path("skill-b")])

# Our approach (similar but ADK-focused)
registry = SkillsRegistry()
registry.discover([Path("skill-a"), Path("skill-b")])
tool = registry.create_use_skill_tool()  # XML in tool description
```

### OpenCode (TypeScript)
```typescript
// Their approach
const SkillTool = Tool.define("skill", async (ctx) => {
  const skills = await Skill.all()
  const description = `<available_skills>...</available_skills>`

  return {
    description,
    async execute(params) {
      const skill = await Skill.get(params.name)
      const content = await loadSkillContent(skill.location)
      return { output: content }
    }
  }
})

// Our approach (Python equivalent)
def create_use_skill_tool(registry):
    def use_skill(name: str) -> dict:
        """
        <available_skills>
        ... (from registry metadata)
        </available_skills>
        """
        skill = registry.load_skill(name)
        return {
            "instructions": skill.instructions,
            "base_directory": str(skill.skill_dir)
        }
    return use_skill
```

## Future Enhancements

### Phase 2
- Remote skills (GitHub, package registries)
- Skills versioning and updates
- Skill dependencies

### Phase 3
- Skills marketplace integration
- Usage analytics
- Auto-discovery from MCP servers

---

**Document Version**: 2.0 (Revised)
**Last Updated**: 2026-01-06
**Status**: Design Phase
**References**:
- https://agentskills.io/specification
- https://github.com/agentskills/agentskills/tree/main/skills-ref
- https://github.com/anomalyco/opencode (skill integration)
