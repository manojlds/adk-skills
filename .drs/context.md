# DRS Project Context

## Architecture
ADK Skills is a Python library that lets Google ADK agents discover, load, and use skills that follow the Agent Skills standard. The library focuses on safe discovery, metadata validation, and tool-based skill activation.

### Key Components
- **SkillsRegistry**: Discovers skills on disk, validates metadata, and exposes helpers to load skills on demand.
- **SkillsAgent**: Convenience agent wrapper that wires skills into an ADK agent.
- **Tools**: `use_skill` and `read_reference` tools for skill activation and reference access.
- **Validation & Helpers**: Pydantic-based validation and utilities for prompt injection or registry setup.

## Technology Stack
- **Language**: Python 3.9+
- **Config/Serialization**: PyYAML
- **Validation**: Pydantic v2
- **Testing/Quality**: Pytest, Ruff, MyPy (dev extras)

## Trust Boundaries

### Trusted Inputs
- **Local filesystem**: Skill folders and metadata are loaded from local paths configured by the developer.
- **ADK agent code**: The library is embedded in trusted Python applications.
- **Environment variables**: Used for runtime configuration and optional execution limits.

### User Inputs (Limited)
- **Skill metadata**: `SKILL.md` contents and scripts are authored by the skill developer.
- **Paths supplied to discovery**: Caller-provided paths are validated and normalized.

### NOT Web-Facing
- This is a Python library used inside trusted applications.
- No public web endpoints or direct untrusted network inputs.
- Avoid assuming adversarial inputs unless the host app explicitly accepts them.

## Security Context

### Standard Practices (NOT Security Issues)
- ✅ Reading skills from local directories
- ✅ YAML/Markdown parsing with validation
- ✅ Tool descriptions listing available skills

### What Actually Matters
- Path traversal or unexpected file access when discovering skills
- Leaking secrets in logs or exceptions
- Validation gaps that allow malformed skill metadata or scripts

## Review Guidelines

### Focus Areas
- Correctness of skill discovery/validation
- Clear error handling and user-facing messages
- Type safety and consistent Pydantic models
- Performance for large skill registries

### Avoid Over-Flagging
- Don't flag standard Python patterns as security issues
- Keep recommendations actionable for a library context
- Prioritize issues that impact skill loading safety or runtime behavior
