# ADK Skills

> Bring [Agent Skills](https://agentskills.io) to Google's Agent Development Kit (ADK)

[![PyPI version](https://badge.fury.io/py/adk-skills.svg)](https://badge.fury.io/py/adk-skills)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**adk-skills** is a Python library that enables [Google ADK](https://github.com/google/adk-python) agents to discover, load, and use skills in the standard [Agent Skills](https://agentskills.io) format. Write skills once, use them across Claude, ADK, and any platform that supports the Agent Skills standard.

## 🚀 Quick Start

### Installation

```bash
pip install adk-skills
```

### Basic Usage

```python
from google.adk.agents import Agent
from adk_skills import SkillsManager

# Load skills
skills = SkillsManager()
skills.load_from_directory("./skills")

# Create ADK agent with skills
agent = Agent(
    name="assistant",
    model="gemini-2.5-flash",
    instruction=skills.get_combined_instructions(),
    tools=skills.get_tools()
)

# Your agent now has skill-powered capabilities!
```

## ✨ Features

- 🎯 **Standard Compliance**: Fully compatible with [agentskills.io](https://agentskills.io) specification
- 📦 **Easy Loading**: Discover and load skills from directories
- 🔧 **Script Execution**: Convert Python and Bash scripts into ADK tools
- 🚀 **Simple Integration**: 5-line integration with existing ADK agents
- 🔒 **Secure**: Sandboxed script execution with timeouts and resource limits
- 📚 **Well Documented**: Comprehensive guides and examples

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

### Load a Single Skill

```python
from adk_skills import SkillsManager

skills = SkillsManager()
skill = skills.load_skill("./skills/web-scraper")

print(f"Loaded: {skill.name}")
print(f"Description: {skill.description}")
```

### Use Skills with Scripts

```python
from google.adk.agents import Agent
from adk_skills import with_skills

# Create agent with calculator skill (includes scripts)
agent = with_skills(
    Agent(name="math_assistant", model="gemini-2.5-flash"),
    skills=["calculator"]
)

# Agent can now use calculator scripts as tools
```

### Multi-Agent with Different Skills

```python
# Customer service agent with specialized skills
cs_agent = Agent(
    name="customer_service",
    model="gemini-2.5-flash",
    instruction=skills.get_instructions(["handle-complaints", "check-orders"]),
    tools=skills.get_tools(["handle-complaints", "check-orders"])
)

# Research agent with different skills
research_agent = Agent(
    name="researcher",
    model="gemini-2.5-flash",
    instruction=skills.get_instructions(["web-scraper", "data-analyzer"]),
    tools=skills.get_tools(["web-scraper", "data-analyzer"])
)
```

## 🏗️ Project Status

**Current Phase**: Design & Planning ✅

- [x] Architecture design complete
- [x] Implementation plan finalized
- [ ] Phase 1: Foundation (MVP) - In Progress
- [ ] Phase 2: Script Execution
- [ ] Phase 3: Advanced Features
- [ ] Phase 4: Public Release

See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for detailed roadmap.

## 📚 Documentation

- **[Design Document](DESIGN.md)**: Architecture and technical decisions
- **[Implementation Plan](IMPLEMENTATION_PLAN.md)**: Phased development roadmap
- **[Project Structure](PROJECT_STRUCTURE.md)**: Codebase organization
- **Quick Start Guide**: Coming soon
- **API Reference**: Coming soon
- **Skill Developer Guide**: Coming soon

## 🤝 Contributing

We welcome contributions! This project is in active development. See our [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) to find areas where you can help.

### Development Setup

```bash
git clone https://github.com/yourusername/adk-skills.git
cd adk-skills
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
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

**Status**: Design Phase | **Target Release**: v1.0.0 | **Python**: 3.9+

For questions or support, please open an issue on GitHub.