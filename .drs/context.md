# DRS Project Context

## Architecture
ADK Skills is a Python library that lets Google ADK agents discover, load, and use skills that follow the Agent Skills standard. The library focuses on safe discovery, metadata validation, pluggable skill sources, and async tool-based skill activation.

### Key Components
- **SkillsRegistry**: Composes skill sources, discovers filesystem skills, validates metadata, and exposes async helpers to load skills on demand.
- **SkillsAgent**: Convenience agent wrapper that wires skills into an ADK agent.
- **Tools**: Async `use_skill` and `read_reference` tools for skill activation and reference access.
- **Sources**: Built-in filesystem source plus custom `SkillSource` implementations for databases, remote registries, or object storage.
- **Validation & Helpers**: Spec validation and async utilities for prompt injection or registry setup.

## Technology Stack
- **Language**: Python 3.9+
- **Config/Serialization**: PyYAML
- **Validation/Data Models**: Dataclasses plus custom spec validation
- **Testing/Quality**: Pytest, pytest-asyncio, Ruff, MyPy (dev extras)

## Trust Boundaries

### Trusted Inputs
- **Local filesystem**: Skill folders and metadata are loaded from local paths configured by the developer.
- **ADK agent code**: The library is embedded in trusted Python applications.
- **Environment variables**: No required runtime environment variables.

### User Inputs (Limited)
- **Skill packages**: `SKILL.md`, references, assets, and optional scripts are authored by the skill developer. This library reads package files but does not execute scripts.
- **Paths supplied to discovery**: Caller-provided paths are validated and normalized.

### NOT Web-Facing
- This is a Python library used inside trusted applications.
- No public web endpoints or direct untrusted network inputs.
- Avoid assuming adversarial inputs unless the host app explicitly accepts them.

## Security Context

### Standard Practices (NOT Security Issues)
- ✅ Reading skills from local directories
- ✅ YAML/Markdown parsing with validation
- ✅ Tool descriptions listing available skills when setup code passes pre-rendered `available_skills_xml`

### What Actually Matters
- Path traversal or unexpected file access when discovering skills
- Leaking secrets in logs or exceptions
- Validation gaps that allow malformed skill metadata or unsafe package paths

## Review Guidelines

### Focus Areas
- Correctness of skill discovery/validation
- Clear error handling and user-facing messages
- Type safety and consistent dataclass models
- Performance for large skill registries

### Avoid Over-Flagging
- Don't flag standard Python patterns as security issues
- Keep recommendations actionable for a library context
- Prioritize issues that impact skill loading safety or runtime behavior
