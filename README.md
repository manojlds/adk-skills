# ADK Skills

> Bring [Agent Skills](https://agentskills.io) to Google's Agent Development Kit (ADK)

[![PyPI version](https://badge.fury.io/py/adk-skills-agent.svg)](https://badge.fury.io/py/adk-skills-agent)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**adk-skills** is a Python library that enables [Google ADK](https://github.com/google/adk-python) agents to discover, load, and use skills in the standard [Agent Skills](https://agentskills.io) format. Write skills once, use them across Claude, ADK, and any platform that supports the Agent Skills standard.

## 🚀 Quick Start

### Installation

**From PyPI**:

```bash
pip install adk-skills-agent
```

**Development Version**:

```bash
git clone https://github.com/manojlds/adk-skills.git
cd adk-skills
pip install -e .
```

### Basic Usage

```python
from google.adk.agents import Agent
from adk_skills_agent import SkillsRegistry

# Discover skills
registry = SkillsRegistry()
registry.discover(["./skills"])

# Create ADK agent with skills support
agent = Agent(
    name="assistant",
    model="gemini-2.5-flash",
    instruction="You are a helpful assistant.",
    tools=[
        registry.create_use_skill_tool(),      # Loads skills on-demand
        registry.create_run_script_tool(),     # Optional: run skill scripts
    ]
)

# Agent can now discover and activate skills as needed!
```

## ✨ Features

- 🎯 **Standard Compliance**: 100% compatible with [agentskills.io](https://agentskills.io) specification
- 📦 **On-Demand Loading**: Skills activated only when needed (~50-100 tokens per skill)
- 🔧 **Script Execution**: Execute Python and Bash scripts from skills
- 🚀 **Simple Integration**: Tool-based pattern following OpenCode's approach
- 🔒 **Secure**: Sandboxed script execution with timeouts and resource limits
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

## 🎓 Examples

### Discover Skills

```python
from adk_skills_agent import SkillsRegistry

registry = SkillsRegistry()
count = registry.discover(["./skills", "~/.adk/skills"])

print(f"Found {count} skills")
for meta in registry.list_metadata():
    print(f"  - {meta.name}: {meta.description}")
```

### Tool-Based Activation

```python
from google.adk.agents import Agent
from adk_skills_agent import SkillsRegistry

registry = SkillsRegistry()
registry.discover(["./skills"])

# Skills are listed in the use_skill tool's description
# Agent activates them on-demand by calling the tool
agent = Agent(
    name="assistant",
    model="gemini-2.5-flash",
    tools=[
        registry.create_use_skill_tool(),    # <available_skills> in description
        registry.create_run_script_tool(),
    ]
)

# When agent calls use_skill(name="calculator"),
# it receives the full skill instructions
```

### Multi-Agent with Different Skills

```python
# Each agent gets its own registry with different skills

# Customer service agent
cs_registry = SkillsRegistry()
cs_registry.discover(["./skills/customer-service"])

cs_agent = Agent(
    name="customer_service",
    model="gemini-2.5-flash",
    tools=[cs_registry.create_use_skill_tool()]
)

# Research agent
research_registry = SkillsRegistry()
research_registry.discover(["./skills/research"])

research_agent = Agent(
    name="researcher",
    model="gemini-2.5-flash",
    tools=[research_registry.create_use_skill_tool()]
)
```

## 🔥 Advanced Usage

### Prompt Injection Utilities

Inject skills directly into system prompts instead of using tools:

```python
from adk_skills_agent import SkillsRegistry

registry = SkillsRegistry()
registry.discover(["./skills"])

# Get skills as XML for prompt injection
xml_prompt = registry.to_prompt_xml()
# Returns: <available_skills>...</available_skills>

# Get skills as plain text
text_prompt = registry.to_prompt_text()
# Returns: Available Skills: - skill-name: description

# Use with agent
agent = Agent(
    name="assistant",
    model="gemini-2.5-flash",
    instruction=f"You are helpful.\n\n{xml_prompt}",
)
```

### Skills Validation

Validate skills against the agentskills.io specification:

```python
from adk_skills_agent import SkillsRegistry

registry = SkillsRegistry()
registry.discover(["./skills"])

# Validate all skills
results = registry.validate_all(strict=True)
for name, result in results.items():
    if not result.valid:
        print(f"{name}: {result.errors}")
    if result.warnings:
        print(f"{name}: {result.warnings}")

# Validate specific skill
result = registry.validate_skill_by_name("my-skill")
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
    validate_skills=True,      # Validate on discovery
    include_script_tool=True,
    include_reference_tool=True,
)

# Get the configured ADK agent
adk_agent = agent.build()
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
agent = with_skills(agent, ["./skills"])
```

#### create_skills_agent()

Create an agent with skills in one call:

```python
from adk_skills_agent import create_skills_agent

agent = create_skills_agent(
    name="assistant",
    model="gemini-2.5-flash",
    instruction="You are helpful.",
    skills_directories=["./skills"],
)
```

#### inject_skills_prompt()

Inject skills into an instruction string:

```python
from adk_skills_agent import inject_skills_prompt

instruction = "You are a helpful assistant."
full_instruction = inject_skills_prompt(
    instruction,
    ["./skills"],
    format="xml"  # or "text"
)
```

### Integration Patterns

Choose between **two alternative patterns** (not both simultaneously):

**Pattern 1: Tool-Based (Default - OpenCode Pattern)** ✅
```python
# Skills listed in tool description, activated on-demand
registry = SkillsRegistry()
registry.discover(["./skills"])
agent = Agent(
    name="assistant",
    model="gemini-2.5-flash",
    instruction="You are helpful.",  # NO skills in prompt
    tools=[
        registry.create_use_skill_tool(),  # <available_skills> in tool description
        registry.create_run_script_tool(),
    ]
)
```

**Pattern 2: Prompt Injection** 🆕
```python
# Skills in system prompt, NOT in tool description (avoids duplication)
registry = SkillsRegistry()
registry.discover(["./skills"])
prompt = registry.to_prompt_xml()

agent = Agent(
    name="assistant",
    model="gemini-2.5-flash",
    instruction=f"You are helpful.\n\n{prompt}",  # Skills in prompt
    tools=[
        registry.create_use_skill_tool(include_skills_listing=False),  # No XML
        registry.create_run_script_tool(),
    ]
)

# Or use SkillsAgent (handles this automatically):
agent = SkillsAgent(
    name="assistant",
    model="gemini-2.5-flash",
    skills_directories=["./skills"],
    auto_inject_prompt=True,  # Automatically omits skills from tool description
).build()
```

**Why Not Both?** Listing skills in both prompt and tool description wastes tokens with no benefit. Choose one pattern based on your needs.

## 🏗️ Project Status

**Current Phase**: MVP Complete ✅ → Phase 2 in Progress

- [x] Architecture design complete
- [x] Implementation plan finalized
- [x] **Phase 1: Foundation (MVP)** - ✅ Complete!
  - [x] Core models and parsers
  - [x] Skills discovery and registry
  - [x] Validation system
  - [x] `use_skill` tool for activation
  - [x] `run_script` and `read_reference` tools
  - [x] Working examples
  - [x] 90%+ test coverage (129 tests passing)
- [ ] Phase 2: Script Execution - In Progress
  - [x] Basic script execution
  - [ ] Advanced executors with sandboxing
- [ ] Phase 3: Advanced Features
- [ ] Phase 4: Public Release

See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for detailed roadmap.

## 🎯 Try It Now

Run the examples to see it in action:

**Basic Example:**
```bash
python examples/basic_example.py
```

This demonstrates:
- Discovering 2 example skills
- Creating ADK tools
- Activating a skill on-demand
- Reading reference files

**Advanced Example:**
```bash
python examples/advanced_example.py
```

This demonstrates:
- Prompt injection utilities (XML and text formats)
- Skills validation features
- SkillsAgent custom agent class
- Helper functions (with_skills, create_skills_agent, inject_skills_prompt)
- Common integration patterns

See [examples/README.md](examples/README.md) for more details.

## 📚 Documentation

- **[Design Document](DESIGN.md)**: Architecture and technical decisions
- **[Implementation Plan](IMPLEMENTATION_PLAN.md)**: Phased development roadmap
- **[Project Structure](PROJECT_STRUCTURE.md)**: Codebase organization
- **[Examples](examples/README.md)**: Working code examples
- Quick Start Guide: Coming soon
- API Reference: Coming soon
- Skill Developer Guide: Coming soon

## 🤝 Contributing

We welcome contributions! This project is in active development. See our [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) to find areas where you can help.

### Development Setup

```bash
git clone https://github.com/manojlds/adk-skills.git
cd adk-skills
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -e ".[dev]"
pytest  # Run tests (129 tests, 90%+ coverage)
```

## 🔗 Related Projects

- [Google ADK Python](https://github.com/google/adk-python) - Agent Development Kit
- [Agent Skills Spec](https://agentskills.io) - Open standard for agent capabilities
- [Anthropic Skills](https://github.com/anthropics/skills) - Public skills repository

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details

## 🙏 Acknowledgments

- Google for creating the Agent Development Kit
- Anthropic for pioneering the Agent Skills standard
- The agentskills.io community for maintaining the specification

---

**Status**: MVP Complete | **Version**: 0.1.0 (dev) | **Python**: 3.9+

For questions or support, please open an issue on GitHub.