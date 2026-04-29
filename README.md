# ADK Skills

> Bring [Agent Skills](https://agentskills.io) to Google's Agent Development Kit (ADK)

[![PyPI version](https://badge.fury.io/py/adk-skills-agent.svg)](https://badge.fury.io/py/adk-skills-agent)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

**adk-skills** is a Python library that enables [Google ADK](https://github.com/google/adk-python) agents to discover, load, and use skills in the standard [Agent Skills](https://agentskills.io) format. Write skills once, use them across Claude, ADK, and any platform that supports the Agent Skills standard.

## 🚀 Quick Start

### Installation

**From PyPI**:

```bash
uv pip install adk-skills-agent
```

**Development Version**:

```bash
git clone https://github.com/manojlds/adk-skills.git
cd adk-skills
uv sync
```

### Basic Usage

```python
from google.adk.agents import Agent
from adk_skills_agent import SkillsRegistry

async def create_agent() -> Agent:
    registry = SkillsRegistry()
    registry.discover(["./skills"])

    # Pre-render the available skills once during async setup so the model can
    # see what it may activate from the use_skill tool description.
    available_skills_xml = await registry.to_prompt_xml()

    return Agent(
        name="assistant",
        model="gemini-2.5-flash",
        instruction="You are a helpful assistant.",
        tools=[
            registry.create_use_skill_tool(available_skills_xml=available_skills_xml),
            registry.create_read_reference_tool(), # Optional: read reference files
        ],
    )

# Agent can now discover and activate skills as needed!
```

Runtime read methods are async in `0.4.0+`: await registry reads, prompt
formatters, helper functions, `SkillsAgent.build()`, and the generated ADK tool
callables.

## ✨ Features

- 🎯 **Standard Compliance**: 100% compatible with [agentskills.io](https://agentskills.io) specification
- 📦 **On-Demand Loading**: Skills activated only when needed (~50-100 tokens per skill)
- 🔌 **Pluggable Skill Sources**: Plug the built-in filesystem source alongside your own sources (database, remote registry, object storage, …) through a single `SkillSource` interface
- 📁 **Multi-file Skill Packages**: Read `SKILL.md`, references, and binary assets from any backend via the generic `list_files` / `read_file` API
- 🚀 **Simple Integration**: Tool-based pattern following OpenCode's approach
- 🤖 **Custom Agent Class**: `SkillsAgent` for easy agent creation with built-in skills support
- 💉 **Prompt Injection**: Inject skills directly into system prompts (XML or text format)
- ✅ **Validation**: Validate skills against the agentskills.io specification
- 🛠️ **Helper Functions**: Convenient utilities like `with_skills()`, `create_skills_agent()`
- 📚 **Well Documented**: Based on reference implementations

## 📖 What are Agent Skills?

Agent Skills are folders of instructions, scripts, and resources that AI agents can discover and use. They follow an open standard published at [agentskills.io](https://agentskills.io), making capabilities portable across different AI platforms.

### Skill Structure

```
my-skill/
├── SKILL.md           # Instructions and metadata
├── scripts/           # Executable Python/Bash scripts
├── references/        # Documentation and resources
└── assets/            # Templates and binary files
```

### Example SKILL.md

```markdown
---
name: web-scraper
description: Extract content from websites efficiently and ethically
---

# Web Scraping Skill

Use this skill to extract structured data from websites.

## When to Use
- Extracting product information
- Gathering research data
- Content monitoring

## Guidelines
- Respect robots.txt
- Use rate limiting
- Cache responses
```

### File References (references/)

Use `references/` for long-form documentation and link to it from SKILL.md using
relative paths:

```markdown
See `references/api-docs.md` for the full API guide.
```

When a skill is activated, the `use_skill` tool returns a `base_directory`. Use
that path (or call `read_reference`) to load reference files on-demand:

```python
from adk_skills_agent import SkillsRegistry

registry = SkillsRegistry()
registry.discover(["./skills"])

use_skill = registry.create_use_skill_tool()
read_reference = registry.create_read_reference_tool()

skill = await use_skill("web-scraper")
ref = await read_reference("web-scraper", "api-docs.md")
print(ref["content"])
```

## 🎓 Examples

### Discover Skills

```python
from adk_skills_agent import SkillsRegistry

registry = SkillsRegistry()
count = registry.discover(["./skills", "~/.adk/skills"])

print(f"Found {count} skills")
for meta in await registry.list_metadata():
    print(f"  - {meta.name}: {meta.description}")
```

### Tool-Based Activation

```python
from google.adk.agents import Agent
from adk_skills_agent import SkillsRegistry

registry = SkillsRegistry()
registry.discover(["./skills"])
available_skills_xml = await registry.to_prompt_xml()

# Skills are listed in the use_skill tool's description
# Agent activates them on-demand by calling the tool
agent = Agent(
    name="assistant",
    model="gemini-2.5-flash",
    tools=[
        registry.create_use_skill_tool(available_skills_xml=available_skills_xml),
        registry.create_read_reference_tool(),
    ]
)

# When agent calls use_skill(name="calculator"),
# it receives the full skill instructions
```

### Multi-Agent with Different Skills

```python
from google.adk.agents import Agent
from adk_skills_agent import SkillsRegistry

# Each agent gets its own registry with different skills

# Customer service agent
cs_registry = SkillsRegistry()
cs_registry.discover(["./skills/customer-service"])
cs_available_skills_xml = await cs_registry.to_prompt_xml()

cs_agent = Agent(
    name="customer_service",
    model="gemini-2.5-flash",
    tools=[cs_registry.create_use_skill_tool(available_skills_xml=cs_available_skills_xml)]
)

# Research agent
research_registry = SkillsRegistry()
research_registry.discover(["./skills/research"])
research_available_skills_xml = await research_registry.to_prompt_xml()

research_agent = Agent(
    name="researcher",
    model="gemini-2.5-flash",
    tools=[
        research_registry.create_use_skill_tool(
            available_skills_xml=research_available_skills_xml,
        )
    ]
)
```

## 🔥 Advanced Usage

### Prompt Injection Utilities

Inject skills directly into system prompts instead of using tools:

```python
from google.adk.agents import Agent
from adk_skills_agent import SkillsRegistry

registry = SkillsRegistry()
registry.discover(["./skills"])

# Get skills as XML for prompt injection
xml_prompt = await registry.to_prompt_xml()
# Returns: <available_skills>...</available_skills>

# Get skills as plain text
text_prompt = await registry.to_prompt_text()
# Returns: Available Skills: - skill-name: description

# Or inject directly into an instruction (recommended)
base_instruction = "You are helpful."
full_instruction = await registry.inject_skills_prompt(base_instruction, format="xml")
# Returns: "You are helpful.\n\n<available_skills>...</available_skills>"

# Use with agent
agent = Agent(
    name="assistant",
    model="gemini-2.5-flash",
    instruction=full_instruction,
)
```

### Pluggable Skill Sources

Starting in `0.2.0`, `SkillsRegistry` is composed of one or more **skill
sources**. A source is anything that implements the `SkillSource` abstract
base class and knows how to list metadata, load a full skill, and
(optionally) expose the files that back a skill package.

The registry ships with one built-in source:

- `FilesystemSkillSource` — default source backing `registry.discover(...)`.
  Use this for engineering-owned skills that live in your repo as directories
  of `SKILL.md` files.

Everything else — database schemas, remote registries, managed catalogues,
object storage — is a custom source. This keeps `adk-skills-agent` focused on
the generic abstractions; applications own the storage layer that best fits
their data model (versioning, publishing, binary assets, access control, …).
A working, multi-file SQLite-backed source lives in
[`tests/integration/test_sqlite_skill_source.py`](tests/integration/test_sqlite_skill_source.py)
and is the recommended starting point for writing your own.

The minimal shape of a custom source:

```python
from adk_skills_agent import SkillSource, SkillsRegistry
from adk_skills_agent.core.models import Skill, SkillMetadata


class MyDatabaseSource(SkillSource):
    name = "my-db"

    async def list_metadata(self) -> list[SkillMetadata]:
        ...

    async def load_skill(self, name: str) -> Skill:
        ...

    # Implement list_files / read_file if your source stores multi-file
    # skill packages (references, assets, binaries). ``read_reference`` is
    # provided by the registry automatically on top of ``read_file`` — no
    # override needed.


registry = SkillsRegistry()
registry.discover(["./skills"])            # filesystem source
registry.add_source(MyDatabaseSource())    # your source
```

#### Collision policy

Skill names are globally unique across all registered sources. If two sources
advertise a skill with the same name, `await registry.list_metadata()` (and any
lookup that needs to enumerate metadata) raises `SkillSourceCollisionError`. This is
intentional: the registry refuses to guess which version to serve and expects
you to resolve the conflict at the source level (rename, namespace, or remove).

#### What sources implement

Each source owns its own storage and decides which capabilities it can offer:

| Method | Required? | Notes |
| --- | --- | --- |
| `async list_metadata()` | **Required** | Cheap skill discovery. |
| `async load_skill(name)` | **Required** | Full skill body on activation. The registry delegates every call to the owning source; it does not cache loaded `Skill` objects or guarantee object identity between calls. |
| `async has_skill(name)` | Optional | Default falls back to `list_metadata`; override for a cheap existence check. |
| `async refresh()` | Optional | Refresh source-owned catalogs/caches for dynamic stores. Return `True` when visible skills or cached content may have changed. |
| `async clear_cache()` | Optional | Drop source-owned loaded-content caches when callers need explicit invalidation. |
| `async list_files(skill_name)` | Optional | Needed whenever your source stores more than the prompt. |
| `async read_file(skill_name, path)` | Optional | Single file I/O primitive for the registry. |

Dynamic sources backed by databases, remote registries, object storage, or other
mutable stores should override `refresh()` and `clear_cache()` so freshness stays
with the storage implementation. Static or prompt-only sources can keep the
default no-op implementations.

Sources that cannot honour an optional capability should leave the default in
place; the registry converts the resulting `NotImplementedError` into a
`SkillExecutionError` with a clear "source does not support …" message. For
example, a prompt-only database source that does not implement `list_files`
/ `read_file` will cause any call that needs them to fail
cleanly rather than silently.

#### Reference reads are a registry-level concern

`read_reference` is **not** part of the `SkillSource` contract. The registry
implements it once, on top of whatever source owns the skill, by:

1. Normalising the caller's input with
   `adk_skills_agent.core.paths.normalize_skill_reference`
   (`"guide.md"` -> `"references/guide.md"`, `"assets/template.json"` passes
   through, `"SKILL.md"` passes through, etc.).
2. Delegating to `source.read_file(skill_name, normalized_path)`.
3. Refusing binary payloads with a clear "use `read_file()` for binary
   assets" message.
4. Wrapping the text content in a `ReferenceFile` whose `path` is
   skill-root-relative (e.g. `"references/guide.md"`) — source-agnostic.

Custom sources only need a correct `read_file`; the reference UX is free.
Path helpers are also exported for source authors that need them directly:

```python
from adk_skills_agent import (
    normalize_skill_reference,
    validate_skill_root_relative_path,
)
```

#### Generic file access (list_files / read_file)

Every source that stores multi-file skill packages should expose two methods:

- `list_files(skill_name) -> list[SkillFile]` enumerates every file in a skill
  package (`SKILL.md`, anything under `references/`, `assets/`, and anything
  else the skill author included) with path, size, MIME type and a content
  hash.
- `read_file(skill_name, relative_path) -> SkillFile` fetches a single file
  and returns a `SkillFile` with exactly one of `text_content` /
  `binary_content` populated.

`FilesystemSkillSource` implements both methods. Custom sources that back a
richer storage layer (a database schema that stores every skill file
separately, an object-storage adapter, a remote catalogue, …) should
implement these to expose the full skill contents. Sources that cannot
enumerate or read files leave the defaults in place, and the registry
surfaces a clear `SkillExecutionError` when a caller needs them.

```python
from adk_skills_agent import SkillsRegistry

registry = SkillsRegistry()
registry.discover(["./skills"])

for meta in await registry.list_files("pdf-processing"):
    print(meta.relative_path, meta.mime_type, meta.size_bytes)

template = await registry.read_file("pdf-processing", "assets/template.json")
assert template.is_text
print(template.text_content)
```

#### Relaxed read_reference semantics

`registry.read_reference(skill, path)` accepts any path relative to the skill
root:

- `"guide.md"` -> resolves to `references/guide.md` (backwards compat)
- `"guides/intro.md"` -> resolves to `references/guides/intro.md` (nested refs)
- `"references/guide.md"` -> resolves as-is
- `"assets/template.json"` -> resolves as-is (useful for LLM-readable assets)
- `"SKILL.md"` -> resolves as-is

Binary files are rejected with a `SkillExecutionError` — use `read_file` for
those. Paths with `..` segments are refused before source access, and the
filesystem source also refuses symlinks that leave the skill root. When a
reference is missing, the error message includes an `Available: [...]` hint
listing sibling files in the same directory (when the owning source supports
`list_files`).

### Skills Validation

Validate skills against the agentskills.io specification:

```python
from adk_skills_agent import SkillsRegistry

registry = SkillsRegistry()
registry.discover(["./skills"])

# Validate all skills
results = await registry.validate_all(strict=True)
for name, result in results.items():
    if not result.valid:
        print(f"{name}: {result.errors}")
    if result.warnings:
        print(f"{name}: {result.warnings}")

# Validate specific skill
result = await registry.validate_skill_by_name("my-skill")
if result.valid:
    print("Skill is valid!")
```

### SkillsAgent - Custom Agent Class

Use the `SkillsAgent` class for easy agent creation with built-in skills support:

```python
from adk_skills_agent import SkillsAgent

# Create agent with skills integrated
agent = SkillsAgent(
    name="assistant",
    model="gemini-2.5-flash",
    instruction="You are a helpful assistant.",
    skills_directories=["./skills"],
    auto_inject_prompt=True,  # Inject skills into prompt
    prompt_format="xml",       # or "text"
    validate_skills=True,      # Validate during build()
    include_reference_tool=True,
)

# Get the configured ADK agent
adk_agent = await agent.build()
```

### Helper Functions

#### with_skills()

Add skills to an existing agent:

```python
from google.adk.agents import Agent
from adk_skills_agent import with_skills

# Create standard agent
agent = Agent(
    name="assistant",
    model="gemini-2.5-flash",
)

# Add skills support
agent = await with_skills(agent, ["./skills"])
```

#### create_skills_agent()

Create an agent with skills in one call:

```python
from adk_skills_agent import create_skills_agent

agent = await create_skills_agent(
    name="assistant",
    model="gemini-2.5-flash",
    instruction="You are helpful.",
    skills_directories=["./skills"],
)
```

#### inject_skills_prompt()

Inject skills into an instruction string. Supports two patterns:

```python
from adk_skills_agent import inject_skills_prompt, SkillsRegistry

# Pattern 1: Directory-based (discovers skills)
instruction = "You are a helpful assistant."
full_instruction = await inject_skills_prompt(
    instruction,
    directories=["./skills"],
    format="xml"  # or "text"
)

# Pattern 2: Registry-based (more efficient, reuses existing registry)
registry = SkillsRegistry()
registry.discover(["./skills"])
full_instruction = await inject_skills_prompt(
    instruction,
    registry=registry,
    format="xml"
)

# Or use the registry method directly
full_instruction = await registry.inject_skills_prompt(instruction, format="xml")
```

### Integration Patterns

Choose between **two alternative patterns** (not both simultaneously):

**Pattern 1: Tool-Based (Default - OpenCode Pattern)** ✅
```python
# Skills listed in tool description, activated on-demand
registry = SkillsRegistry()
registry.discover(["./skills"])
available_skills_xml = await registry.to_prompt_xml()
agent = Agent(
    name="assistant",
    model="gemini-2.5-flash",
    instruction="You are helpful.",  # NO skills in prompt
    tools=[
        registry.create_use_skill_tool(available_skills_xml=available_skills_xml),
        registry.create_read_reference_tool(),
    ]
)
```

**Pattern 2: Prompt Injection** 🆕
```python
# Skills in system prompt, NOT in tool description (avoids duplication)
registry = SkillsRegistry()
registry.discover(["./skills"])
prompt = await registry.to_prompt_xml()

agent = Agent(
    name="assistant",
    model="gemini-2.5-flash",
    instruction=f"You are helpful.\n\n{prompt}",  # Skills in prompt
    tools=[
        registry.create_use_skill_tool(),  # No XML duplicated in tool description
        registry.create_read_reference_tool(),
    ]
)

skills_agent = SkillsAgent(
    name="assistant",
    model="gemini-2.5-flash",
    skills_directories=["./skills"],
    auto_inject_prompt=True,  # Automatically omits skills from tool description
)
agent = await skills_agent.build()
```

**Why Not Both?** Listing skills in both prompt and tool description wastes tokens with no benefit. Choose one pattern based on your needs.

## 🏗️ Project Status

**Current Phase**: MVP Complete ✅ → Phase 2 in Progress

- [x] Core models and parsers
- [x] Skills discovery and registry
- [x] Validation system
- [x] `use_skill` tool for activation
- [x] `read_reference` tool
- [x] Working examples
- [x] 300+ tests passing
- [ ] Advanced executors and sandboxing
- [ ] Advanced features
- [ ] Public release

## 🎯 Try It Now

Run the examples to see it in action:

**Basic Example:**
```bash
uv run python examples/basic_example.py
```

This demonstrates:
- Discovering 2 example skills
- Creating ADK tools
- Activating a skill on-demand
- Reading reference files

**Advanced Example:**
```bash
uv run python examples/advanced_example.py
```

This demonstrates:
- Prompt injection utilities (XML and text formats)
- Skills validation features
- SkillsAgent custom agent class
- Helper functions (with_skills, create_skills_agent, inject_skills_prompt)
- Common integration patterns

Example skills live in `examples/skills/`.

## 📚 Documentation

- This README contains the primary usage guide.
- Example scripts: `examples/basic_example.py`, `examples/advanced_example.py`
- Example skills: `examples/skills/`

## 🤝 Contributing

We welcome contributions! This project is in active development.

### Development Setup

```bash
git clone https://github.com/manojlds/adk-skills.git
cd adk-skills
uv sync --all-extras  # Creates venv and installs all dependencies
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
uv run pytest  # Run tests
```

## 🔗 Related Projects

- [Google ADK Python](https://github.com/google/adk-python) - Agent Development Kit
- [Agent Skills Spec](https://agentskills.io) - Open standard for agent capabilities
- [Anthropic Skills](https://github.com/anthropics/skills) - Public skills repository

## 📄 License

Apache 2.0 License - see [LICENSE](LICENSE) file for details

## 🙏 Acknowledgments

- Google for creating the Agent Development Kit
- Anthropic for pioneering the Agent Skills standard
- The agentskills.io community for maintaining the specification

---

**Status**: MVP Complete | **Version**: 0.4.0 | **Python**: 3.9+

For questions or support, please open an issue on GitHub.
