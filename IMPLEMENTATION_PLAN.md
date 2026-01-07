# ADK Skills - Implementation Plan (Revised)

## Project Overview

Build a Python library that enables Google ADK agents to discover and activate skills on-demand using the Agent Skills standard format (agentskills.io).

**Target Timeline**: 4-6 weeks for MVP + Production
**Language**: Python 3.9+
**Primary Dependencies**: google-adk, pyyaml (or strictyaml), pydantic
**Pattern**: Tool-based on-demand activation (following OpenCode's approach)

## Key Architectural Changes

Based on analysis of reference implementations:

### ❌ Old Approach (Incorrect)
- Pre-inject all skill instructions → bloats context
- Convert scripts to tools upfront → complex, unnecessary
- SkillsManager with `get_combined_instructions()` → wrong pattern

### ✅ New Approach (Correct)
- Lightweight metadata discovery (~50-100 tokens/skill)
- On-demand activation via `use_skill` tool
- `<available_skills>` in tool description, not system prompt
- Separate `run_script` tool for optional script execution

## Implementation Phases

---

## Phase 1: Foundation & Discovery (Week 1-2) - MVP

### Milestone: Skills discovery and on-demand activation via tool

#### 1.1 Project Setup
**Files**: `pyproject.toml`, `.github/workflows/`, `tests/conftest.py`

- [ ] Initialize Python package structure
- [ ] Setup pyproject.toml with dependencies
- [ ] Configure development tools (black, ruff, mypy, pytest)
- [ ] Setup GitHub Actions for CI/CD
- [ ] Create initial test fixtures

**Deliverable**: Working Python package scaffold

#### 1.2 Core Data Models
**Files**: `adk_skills/core/models.py`

- [ ] Define `SkillMetadata` dataclass (name, description, location)
- [ ] Define `Skill` dataclass (full content, lazy-loaded)
- [ ] Define `SkillsConfig` dataclass
- [ ] Define `ValidationResult` for validation output
- [ ] Add type hints throughout
- [ ] Write unit tests

**Deliverable**: Two-tier data model (metadata vs full content)

**Example**:
```python
@dataclass
class SkillMetadata:
    name: str
    description: str
    location: Path
    # lightweight, ~50-100 tokens

@dataclass
class Skill:
    # Full skill (loaded on-demand)
    name: str
    instructions: str  # complete markdown body
    skill_dir: Path
    # ...
```

#### 1.3 YAML Frontmatter Parser
**Files**: `adk_skills/utils/yaml_parser.py`

- [ ] Implement frontmatter extraction from SKILL.md
- [ ] Parse YAML into Python dict
- [ ] Handle malformed YAML gracefully
- [ ] Support optional fields with defaults
- [ ] Write parser tests

**Deliverable**: Robust YAML frontmatter parser

**Note**: Consider using `strictyaml` like the reference implementation

#### 1.4 Markdown Parser
**Files**: `adk_skills/utils/markdown.py`

- [ ] Extract markdown body after frontmatter
- [ ] Split on `---` delimiters
- [ ] Preserve formatting and structure
- [ ] Handle edge cases
- [ ] Write parser tests

**Deliverable**: Markdown body extractor

#### 1.5 SKILL.md Parser
**Files**: `adk_skills/core/parser.py`

- [ ] Implement `parse_metadata(path)` - frontmatter only (fast)
- [ ] Implement `parse_full(path)` - frontmatter + body (on-demand)
- [ ] Validate required fields (name, description)
- [ ] Handle optional fields
- [ ] Write comprehensive tests

**Deliverable**: Two-mode parser (metadata vs full)

**Key Functions**:
```python
def parse_metadata(skill_md_path: Path) -> SkillMetadata:
    """Parse only frontmatter - fast discovery"""

def parse_full(skill_md_path: Path) -> Skill:
    """Parse complete SKILL.md - on activation"""
```

#### 1.6 Skills Discovery
**Files**: `adk_skills/core/discovery.py`

- [ ] Implement `discover_skills(directories)` - scan for SKILL.md
- [ ] Use glob patterns (like OpenCode): `{skill,skills}/**/SKILL.md`
- [ ] Handle both `SKILL.md` and `skill.md`
- [ ] Parse metadata only (not full content)
- [ ] Return list of SkillMetadata
- [ ] Write discovery tests

**Deliverable**: Efficient skills discovery system

#### 1.7 Skill Validator
**Files**: `adk_skills/core/validator.py`

- [ ] Validate name format (lowercase, hyphens, max 64 chars)
- [ ] Validate description length (max 1024 chars)
- [ ] Check required fields present
- [ ] Validate file structure (SKILL.md exists)
- [ ] Return detailed validation results
- [ ] Write validation tests

**Deliverable**: Spec-compliant validator

#### 1.8 Skills Registry (Core Component)
**Files**: `adk_skills/registry.py`

- [ ] Implement `SkillsRegistry` class
- [ ] Method: `discover(directories)` - scan and load metadata
- [ ] Method: `list_metadata()` - list all discovered skills
- [ ] Method: `get_metadata(name)` - get specific skill metadata
- [ ] Method: `load_skill(name)` - lazy-load full skill content
- [ ] Internal registry: Dict[str, SkillMetadata]
- [ ] Write registry tests

**Deliverable**: Main registry interface

**API**:
```python
class SkillsRegistry:
    def discover(self, directories: List[Path]) -> int:
        """Scan directories, parse metadata only"""

    def list_metadata(self) -> List[SkillMetadata]:
        """List discovered skills (lightweight)"""

    def load_skill(self, name: str) -> Skill:
        """Load full skill on-demand"""
```

#### 1.9 Use Skill Tool (Critical Component)
**Files**: `adk_skills/tools/use_skill.py`

- [ ] Implement `create_use_skill_tool(registry)` function
- [ ] Generate tool description with `<available_skills>` XML
- [ ] Tool parameter: `name: str`
- [ ] Tool execution: load full skill, return instructions
- [ ] Return: dict with instructions, base_dir, has_scripts, etc.
- [ ] Write tool tests

**Deliverable**: Main skill activation tool

**Example**:
```python
def create_use_skill_tool(registry: SkillsRegistry) -> Callable:
    """
    Create ADK tool for skill activation.

    Tool description includes:
    <available_skills>
      <skill>
        <name>pdf-processing</name>
        <description>Extract text from PDFs...</description>
      </skill>
      ...
    </available_skills>
    """
    def use_skill(name: str) -> dict:
        skill = registry.load_skill(name)
        return {
            "instructions": skill.instructions,
            "base_directory": str(skill.skill_dir),
            "has_scripts": skill.scripts_dir is not None,
        }

    # Set docstring with <available_skills>
    use_skill.__doc__ = generate_description(registry)

    return use_skill
```

#### 1.10 MVP Integration Example
**Files**: `examples/basic_example.py`, `examples/skills/hello-skill/`

- [ ] Create simple "hello-skill" with SKILL.md
- [ ] Demonstrate discovery with SkillsRegistry
- [ ] Show ADK agent with use_skill tool
- [ ] Simulate skill activation
- [ ] Document example thoroughly

**Deliverable**: Working end-to-end example

**Example**:
```python
from google.adk.agents import Agent
from adk_skills_agent import SkillsRegistry

registry = SkillsRegistry()
registry.discover(["./examples/skills"])

agent = Agent(
    name="assistant",
    model="gemini-2.5-flash",
    tools=[registry.create_use_skill_tool()]
)
```

#### 1.11 Initial Documentation
**Files**: `README.md`, `docs/quickstart.md`

- [ ] Update README with correct pattern
- [ ] Add quick start guide
- [ ] Document tool-based activation
- [ ] API reference for SkillsRegistry
- [ ] Note differences from initial design

**Deliverable**: Accurate user documentation

---

## Phase 2: Script Execution & References (Week 3-4)

### Milestone: Execute skill scripts and access references

#### 2.1 Directory Structure Discovery
**Files**: `adk_skills/core/parser.py` (extend)

- [ ] Detect scripts/ directory in skill
- [ ] Detect references/ directory
- [ ] Detect assets/ directory
- [ ] Populate Skill dataclass fields
- [ ] Lazy discovery (only when skill activated)
- [ ] Write tests

**Deliverable**: Skill directory structure detection

#### 2.2 Script Discovery
**Files**: `adk_skills/executors/discovery.py`

- [ ] List scripts in skill's scripts/ directory
- [ ] Identify Python (.py) and Bash (.sh) scripts
- [ ] Extract basic metadata (filename, path)
- [ ] Handle missing scripts/ directory
- [ ] Write tests

**Deliverable**: Script enumeration

#### 2.3 Python Script Executor
**Files**: `adk_skills/executors/python_executor.py`

- [ ] Execute Python scripts via subprocess
- [ ] Pass arguments as JSON or CLI args
- [ ] Capture stdout/stderr
- [ ] Parse JSON output
- [ ] Handle execution errors
- [ ] Timeout support (default 30s)
- [ ] Write executor tests

**Deliverable**: Python script execution

#### 2.4 Bash Script Executor
**Files**: `adk_skills/executors/bash_executor.py`

- [ ] Execute Bash scripts via subprocess
- [ ] Pass arguments as environment vars or args
- [ ] Capture stdout/stderr
- [ ] Parse output (text or JSON)
- [ ] Handle execution errors
- [ ] Timeout support
- [ ] Write executor tests

**Deliverable**: Bash script execution

#### 2.5 Run Script Tool
**Files**: `adk_skills/tools/run_script.py`

- [ ] Implement `create_run_script_tool(registry)` function
- [ ] Parameters: `skill: str`, `script: str`, `args: dict`
- [ ] Validate skill exists and is activated
- [ ] Validate script exists in skill's scripts/
- [ ] Execute script with appropriate executor
- [ ] Return output
- [ ] Write tool tests

**Deliverable**: Script execution tool

**Example**:
```python
def create_run_script_tool(registry: SkillsRegistry) -> Callable:
    def run_script(skill: str, script: str, args: dict) -> dict:
        """Execute a script from a skill"""
        skill_obj = registry.load_skill(skill)
        script_path = skill_obj.scripts_dir / script

        # Execute with appropriate executor
        result = execute_script(script_path, args)
        return {"output": result.stdout, "error": result.stderr}

    return run_script
```

#### 2.6 Read Reference Tool
**Files**: `adk_skills/tools/read_reference.py`

- [ ] Implement `create_read_reference_tool(registry)` function
- [ ] Parameters: `skill: str`, `reference: str`
- [ ] Validate reference exists in skill's references/
- [ ] Read and return file content
- [ ] Handle different file types
- [ ] Write tool tests

**Deliverable**: Reference reading tool

#### 2.7 Security & Sandboxing
**Files**: `adk_skills/executors/sandbox.py`

- [ ] Implement execution timeouts
- [ ] Add resource limits (memory, CPU)
- [ ] Path validation (prevent traversal)
- [ ] Input sanitization
- [ ] Output validation
- [ ] Write security tests

**Deliverable**: Secure execution environment

#### 2.8 Complete Example with Scripts
**Files**: `examples/script_example.py`, `examples/skills/calculator/`

- [ ] Create "calculator" skill with Python scripts
- [ ] Demonstrate skill activation
- [ ] Show script execution via run_script tool
- [ ] Document workflow
- [ ] Include error handling

**Deliverable**: End-to-end script execution example

---

## Phase 3: Advanced Features & Polish (Week 5-6)

### Milestone: Production-ready library

#### 3.1 Helper Functions
**Files**: `adk_skills/helpers.py`

- [ ] Implement `with_skills(agent, directories)` convenience function
- [ ] Implement `validate_skill(path)` helper
- [ ] Implement `create_skill_template(dir, name)` helper
- [ ] Write helper tests

**Deliverable**: Developer convenience functions

#### 3.2 CLI Tool
**Files**: `adk_skills/cli.py`

- [ ] Create Click-based CLI
- [ ] Command: `adk-skills discover <dirs>` - list skills
- [ ] Command: `adk-skills validate <path>` - validate skill
- [ ] Command: `adk-skills init <name>` - create template
- [ ] Command: `adk-skills info <name>` - show skill details
- [ ] Write CLI tests

**Deliverable**: Command-line interface

#### 3.3 Configuration System
**Files**: `adk_skills/config.py`

- [ ] Load config from file (.adk-skills.yaml)
- [ ] Environment variable overrides
- [ ] Default skill directories
- [ ] Security settings (sandboxing, timeouts)
- [ ] Write config tests

**Deliverable**: Flexible configuration

#### 3.4 Advanced Validation
**Files**: `adk_skills/core/validator.py` (extend)

- [ ] Validate compatibility field
- [ ] Check script executability
- [ ] Verify references exist
- [ ] Validate metadata structure
- [ ] Comprehensive validation report
- [ ] Write advanced tests

**Deliverable**: Enhanced validation

#### 3.5 Error Handling
**Files**: `adk_skills/exceptions.py`

- [ ] Define exception hierarchy
- [ ] `SkillNotFoundError`, `SkillValidationError`, etc.
- [ ] Meaningful error messages
- [ ] Error recovery strategies
- [ ] Write error tests

**Deliverable**: Robust error handling

#### 3.6 Logging System
**Files**: `adk_skills/logging.py`

- [ ] Setup structured logging
- [ ] Debug mode for verbose output
- [ ] Log discovery, activation, execution
- [ ] Performance metrics (optional)
- [ ] Write logging tests

**Deliverable**: Comprehensive logging

#### 3.7 Performance Optimization
**Files**: Various

- [ ] Cache parsed metadata
- [ ] Lazy loading of full content
- [ ] Optimize discovery (parallel scanning)
- [ ] Profile and optimize hot paths
- [ ] Write performance tests

**Deliverable**: Optimized performance

#### 3.8 Comprehensive Examples
**Files**: `examples/`

- [ ] Multi-agent with different skills
- [ ] Filesystem-based pattern (alternative)
- [ ] Custom executors
- [ ] Error handling patterns
- [ ] Document all examples

**Deliverable**: Rich examples library

#### 3.9 Full Documentation
**Files**: `docs/`

- [ ] API Reference (auto-generated)
- [ ] User Guide (comprehensive)
- [ ] Skill Developer Guide
- [ ] Architecture docs
- [ ] Troubleshooting guide
- [ ] Setup MkDocs site

**Deliverable**: Complete documentation

---

## Phase 4: Testing & Release (Week 7)

### Milestone: Public release v1.0.0

#### 4.1 Testing
- [ ] Achieve 90%+ code coverage
- [ ] Integration tests with real ADK agents
- [ ] Test against Anthropic skills repository
- [ ] Security audit
- [ ] Performance benchmarks

#### 4.2 Compliance Testing
- [ ] Test with reference implementation skills
- [ ] Validate against agentskills.io spec
- [ ] Cross-platform testing (Linux, macOS, Windows)
- [ ] Python version testing (3.9, 3.10, 3.11, 3.12)

#### 4.3 Documentation Review
- [ ] Technical review
- [ ] User testing of docs
- [ ] Fix gaps and errors
- [ ] Add FAQs
- [ ] Create video walkthrough (optional)

#### 4.4 Packaging
- [ ] Finalize pyproject.toml
- [ ] Create distribution packages
- [ ] Test installation from PyPI test
- [ ] Prepare release notes
- [ ] Create changelog

#### 4.5 Community
- [ ] Contributing guide
- [ ] Code of conduct
- [ ] Issue templates
- [ ] PR templates
- [ ] GitHub discussions setup

#### 4.6 Release
- [ ] Tag v1.0.0
- [ ] Publish to PyPI
- [ ] Publish documentation
- [ ] Announce on relevant channels
- [ ] Monitor for issues

---

## Success Criteria

### Phase 1 (MVP)
✅ Discover skills from directories (metadata only)
✅ Parse SKILL.md files correctly
✅ Create use_skill tool with <available_skills> in description
✅ Load full skill content on-demand
✅ Working example with ADK agent

### Phase 2 (Scripts)
✅ Execute Python scripts via run_script tool
✅ Execute Bash scripts via run_script tool
✅ Secure sandboxed execution
✅ Read reference files from skills

### Phase 3 (Production)
✅ Full spec compliance
✅ 90%+ test coverage
✅ Complete documentation
✅ CLI interface
✅ Performance optimized

### Phase 4 (Release)
✅ Published on PyPI
✅ Community ready
✅ Security audited
✅ Active users

---

## Key Differences from Initial Plan

### Architecture Changes
1. **SkillsRegistry** instead of SkillsManager
2. **Two-tier data model**: SkillMetadata (lightweight) vs Skill (full)
3. **Tool-based activation**: use_skill tool, not pre-injection
4. **Lazy loading**: Parse metadata at discovery, full content on activation

### API Changes
1. **No `get_combined_instructions()`** - wrong pattern
2. **No `get_tools()` for script conversion** - separate run_script tool
3. **`<available_skills>` in tool description** - not system prompt
4. **`discover()` instead of `load_from_directory()`** - clearer intent

### Implementation Changes
1. **Phase 1 focus**: Discovery + use_skill tool (not instruction injection)
2. **Script execution**: Separate tool in Phase 2 (not automatic conversion)
3. **Simpler overall**: Less complex, follows proven patterns

---

## Technical Stack

### Core Dependencies
- `google-adk>=1.0.0` - ADK framework
- `pyyaml>=6.0` or `strictyaml` - YAML parsing
- `pydantic>=2.0` - Data validation

### Development Dependencies
- `pytest>=7.0` - Testing
- `pytest-cov>=4.0` - Coverage
- `black>=23.0` - Formatting
- `ruff>=0.1` - Linting
- `mypy>=1.0` - Type checking
- `click>=8.0` - CLI

### Optional Dependencies
- `mkdocs-material` - Documentation
- `pytest-asyncio` - Async testing

---

## Risk Mitigation

### Risk: ADK API Changes
- **Mitigation**: Pin version, monitor releases, maintain compatibility layer

### Risk: Security in Script Execution
- **Mitigation**: Sandboxing, timeouts, validation, security audit

### Risk: Performance with Many Skills
- **Mitigation**: Metadata-only discovery, lazy loading, caching

### Risk: Spec Divergence
- **Mitigation**: Automated compliance tests, track agentskills.io

### Risk: Adoption Challenges
- **Mitigation**: Great docs, examples, follow OpenCode's patterns

---

## Next Steps

1. ✅ Review revised plan
2. ⏭️ Set up project structure
3. ⏭️ Begin Phase 1.1: Project Setup
4. ⏭️ Implement metadata-based discovery
5. ⏭️ Create use_skill tool

---

**Plan Version**: 2.0 (Revised)
**Created**: 2026-01-06
**Status**: Ready for Implementation
**References**:
- https://github.com/agentskills/agentskills/tree/main/skills-ref
- https://github.com/anomalyco/opencode (skills integration)
- https://agentskills.io/specification
