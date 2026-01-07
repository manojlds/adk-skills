# ADK Skills Examples

This directory contains working examples demonstrating how to use adk-skills.

## Running the Examples

### Basic Example

The basic example demonstrates core functionality:

```bash
python examples/basic_example.py
```

This example shows:
- Discovering skills from a directory
- Listing available skills
- Creating tools for ADK agents
- Activating a skill on-demand
- Reading reference files

## Example Skills

The `skills/` directory contains example skills for testing:

### hello-world
A minimal skill demonstrating the basic SKILL.md structure with just frontmatter and instructions.

**Location**: `skills/hello-world/`

### calculator
A complete skill with scripts and references demonstrating:
- Full SKILL.md with instructions
- Python script in `scripts/` directory
- Reference documentation in `references/` directory

**Location**: `skills/calculator/`

## Using Skills with Google ADK

```python
from google.adk.agents import Agent
from adk_skills_agent import SkillsRegistry

# Discover skills
registry = SkillsRegistry()
registry.discover(["./examples/skills"])

# Create agent with skills support
agent = Agent(
    name="assistant",
    model="gemini-2.5-flash",
    instruction="You are a helpful assistant.",
    tools=[
        registry.create_use_skill_tool(),      # Skill activation
        registry.create_run_script_tool(),     # Script execution
        registry.create_read_reference_tool(), # Reference reading
    ]
)

# Agent can now discover and activate skills as needed!
```

## Next Steps

- See the [main README](../README.md) for installation instructions
- Check the [design document](../DESIGN.md) for architecture details
- Read the [implementation plan](../IMPLEMENTATION_PLAN.md) for roadmap
