# Pi-Mono and Pi-Skills Analysis

## Executive Summary

This document analyzes the pi-mono/pi-skills ecosystem and compares it with our adk-skills implementation to identify opportunities for improvement and potential features to adopt.

**Key Findings:**
- Pi-mono is a TypeScript-based AI agent toolkit focusing on coding agents
- Pi-skills provides 8 practical skills but uses a **non-standard format**
- Our adk-skills correctly follows the official agentskills.io specification
- Pi-skills offers valuable **skill ideas** we can implement in standard format
- No MCP support exists in pi-mono despite initial documentation mentions

**Date:** 2026-01-07
**Repository:** https://github.com/badlogic/pi-mono (pi-mono) and https://github.com/badlogic/pi-skills (pi-skills)

---

## Pi-Mono Repository Overview

### What is Pi-Mono?

Pi-mono is an AI agent toolkit developed by Mario Zechner (@badlogic) that provides:

1. **Core Packages:**
   - `@mariozechner/pi-ai` - Unified LLM API supporting multiple providers (OpenAI, Anthropic, Google, etc.)
   - `@mariozechner/pi-agent-core` - Agent runtime with tool calling and state management
   - `@mariozechner/pi-coding-agent` - Interactive CLI-based coding agent
   - `@mariozechner/pi-tui` - Terminal UI library with differential rendering
   - `@mariozechner/pi-web-ui` - Web components for AI chat interfaces
   - `@mariozechner/pi-mom` - Slack bot that delegates to the coding agent
   - `@mariozechner/pi-pods` - CLI for managing vLLM deployments on GPU pods

2. **Technology Stack:**
   - Language: TypeScript (95.6%)
   - License: MIT
   - Active development: 1,804 commits, 55 contributors

3. **Architecture:**
   - Tool-based agent architecture with TypeBox schemas
   - Event streaming for real-time UI updates
   - Stateful conversation management
   - Multi-model support with runtime switching

### Skills vs MCP in Pi-Mono

**Important Discovery:** Despite the README mentioning "MCP Registry," pi-mono does **NOT implement MCP (Model Context Protocol)**.

From the developer's blog post:
> "Popular MCP servers like Playwright MCP and Chrome DevTools MCP dump their entire tool descriptions into your context on every session, consuming 7-9% of the context window before work begins."

**Alternative Approach:** Pi-mono recommends building CLI tools with README files (called "Skills") that agents read on-demand, paying token costs only when necessary.

This aligns with the **progressive disclosure** pattern that both agentskills.io and our adk-skills implementation use!

---

## Pi-Skills Repository Overview

### Repository Details

- **URL:** https://github.com/badlogic/pi-skills
- **Purpose:** Skills for pi-coding-agent (compatible with Claude Code, Codex CLI, Amp, and Droid)
- **Skills Count:** 8 skills
- **Format:** Custom markdown format (NOT agentskills.io compliant)

### Available Skills

#### 1. Web & Information Retrieval
- **brave-search** - Web search and content extraction via Brave Search API
- **youtube-transcript** - Fetch YouTube video transcripts
- **browser-tools** - Interactive browser automation via Chrome DevTools Protocol

#### 2. Google Workspace Integration
- **gccli** - Google Calendar CLI for events and availability
- **gdcli** - Google Drive CLI for file management and sharing
- **gmcli** - Gmail CLI for email, drafts, and labels

#### 3. Development & Utilities
- **vscode** - VS Code integration for diffs and file comparison
- **transcribe** - Speech-to-text transcription via Groq Whisper API

---

## Pi-Skills Format Analysis

### Format Differences from agentskills.io

| Aspect | Pi-Skills Format | Agentskills.io Standard | Our Implementation |
|--------|------------------|------------------------|-------------------|
| **Metadata** | Markdown table | YAML frontmatter | ✅ YAML frontmatter |
| **Directory** | Flat structure | scripts/ subdirectory | ✅ scripts/ subdirectory |
| **Script Path** | `{baseDir}/script.js` | `scripts/script.py` | ✅ Standard paths |
| **Required Fields** | name, description | name, description | ✅ Matches spec |
| **Optional Fields** | None | license, compatibility, metadata | ✅ Full support |
| **Compliance** | ❌ Non-standard | ✅ Official spec | ✅ Compliant |

### Example: Pi-Skills Metadata

```markdown
| name | browser-tools |
| description | Interactive browser automation via Chrome DevTools Protocol |
```

### Example: Agentskills.io Metadata (Our Format)

```yaml
---
name: browser-tools
description: Interactive browser automation via Chrome DevTools Protocol
license: MIT
compatibility: Node.js 18+, Chrome/Chromium installed
---
```

### Key Observations

1. **Non-Standard Format:** Pi-skills doesn't follow agentskills.io specification
2. **Flat Structure:** Scripts in root directory instead of `scripts/` subdirectory
3. **Runtime Path Substitution:** Uses `{baseDir}` placeholder for script paths
4. **Minimal Metadata:** Only name and description (no license, compatibility, etc.)
5. **Node.js Focus:** All skills are JavaScript/Node.js based

**Verdict:** While pi-skills provides valuable skill ideas, the format is not compatible with the agentskills.io ecosystem.

---

## Comparison: adk-skills vs Pi-Skills

### Architecture Comparison

| Feature | adk-skills | Pi-Skills |
|---------|-----------|-----------|
| **Language** | Python | JavaScript/Node.js |
| **Format** | agentskills.io standard | Custom markdown |
| **Target Platform** | Google ADK | pi-coding-agent |
| **Discovery** | Metadata-only (fast) | Full read per skill |
| **Activation** | On-demand via tool | Direct file read |
| **Script Execution** | Subprocess with sandboxing | CLI invocation |
| **Validation** | Spec-compliant validator | None (informal) |
| **Cross-Platform** | ✅ Portable to Claude, etc. | ⚠️ Platform-specific |

### Feature Parity

| Capability | adk-skills | Pi-Skills |
|------------|-----------|-----------|
| Skill discovery | ✅ Implemented | ✅ Via filesystem |
| Metadata parsing | ✅ YAML frontmatter | ⚠️ Markdown table |
| On-demand loading | ✅ Tool-based | ✅ File-based |
| Script execution | ✅ Python/Bash | ✅ Node.js CLI |
| Reference files | ✅ references/ dir | ❌ Not used |
| Asset management | ✅ assets/ dir | ❌ Not used |
| Validation | ✅ Spec validator | ❌ None |
| Security | ✅ Sandboxing planned | ⚠️ Trust-based |

### Strengths of Each Approach

**adk-skills Strengths:**
- ✅ Standards-compliant (portable across platforms)
- ✅ Well-structured (clean separation of concerns)
- ✅ Type-safe (Pydantic models)
- ✅ Validated (spec-compliant validator)
- ✅ Tested (90%+ coverage, 129 tests)
- ✅ Documented (comprehensive design docs)
- ✅ Extensible (clear architecture)

**pi-skills Strengths:**
- ✅ Practical skills (8 working, useful skills)
- ✅ Real-world tested (used in production)
- ✅ Simple setup (no complex configuration)
- ✅ Fast execution (direct CLI calls)
- ✅ Platform-proven (works with multiple agents)

---

## Key Insights and Learnings

### 1. Progressive Disclosure Pattern

Both ecosystems use the same core pattern:
- **Lightweight discovery:** Parse minimal metadata
- **On-demand activation:** Load full content when needed
- **Token efficiency:** Only pay for what you use

This validates our architectural approach! ✅

### 2. CLI-Based Skills Philosophy

Pi-mono's approach emphasizes:
- Build simple CLI tools with good READMEs
- Agents read READMEs when needed
- Direct CLI invocation (no protocol overhead)

**Implication for adk-skills:** We should encourage skill developers to create CLI-based scripts with clear documentation. This is already compatible with our `scripts/` directory approach!

### 3. Real-World Skill Categories

Pi-skills demonstrates valuable skill categories:
- **External API Integration** (Brave Search, Groq Whisper)
- **Productivity Tools** (Google Workspace)
- **Browser Automation** (Chrome DevTools)
- **Media Processing** (Transcription)
- **Developer Tools** (VS Code integration)

These represent high-value, practical capabilities agents need.

### 4. Interactive vs Headless

Some pi-skills (browser-tools) support **interactive workflows** requiring user input. This is an interesting use case we haven't explicitly designed for.

**Question for future:** Should adk-skills support interactive scripts? Or focus on fully automated capabilities?

### 5. Runtime Path Substitution

Pi-skills uses `{baseDir}` placeholders that get replaced at runtime. Our approach is more explicit:
- We return `base_directory` in tool results
- Agent knows skill location
- Scripts referenced by relative paths

Both approaches work, ours is more explicit and standard-compliant.

---

## Opportunities for adk-skills

### 1. Skill Library Expansion 🎯 HIGH PRIORITY

**Opportunity:** Create agentskills.io-compliant versions of pi-skills capabilities.

**Actionable Skills to Implement:**
1. **brave-search** → Create standard Python/CLI version
2. **browser-tools** → Create Playwright/Selenium-based version
3. **youtube-transcript** → Python version with youtube-transcript-api
4. **transcribe** → Python version with Whisper API
5. **google-workspace** → Python versions of gccli/gdcli/gmcli
6. **vscode** → Python version for file diffs

**Benefits:**
- Demonstrate real-world value
- Provide reference implementations
- Grow the agentskills.io ecosystem
- Attract users with practical examples

**Implementation Plan:**
- Create new repo: `adk-skills-library` or `agentskills-standard`
- Each skill follows agentskills.io spec perfectly
- Well-documented with tests
- Can be used with ADK, Claude, or any compliant platform

### 2. Format Converter Tool 🛠️ MEDIUM PRIORITY

**Opportunity:** Create tool to convert pi-skills format to agentskills.io format.

**Tool Features:**
```bash
adk-skills convert --input pi-skills/brave-search --output skills/brave-search
```

**Conversion Logic:**
- Parse markdown table → Generate YAML frontmatter
- Move scripts to `scripts/` subdirectory
- Replace `{baseDir}/script.js` with `scripts/script.js`
- Add recommended fields (license, compatibility)
- Validate output

**Benefits:**
- Help pi-skills users migrate to standard format
- Demonstrate format flexibility
- Grow agentskills.io adoption
- Educational tool for format differences

### 3. Node.js Script Support 🔧 LOW PRIORITY

**Current State:** We support Python (.py) and Bash (.sh) scripts.

**Opportunity:** Add JavaScript (.js, .mjs) executor.

**Implementation:**
```python
# adk_skills/executors/javascript_executor.py
class JavaScriptExecutor:
    def execute(self, script_path, args):
        # Execute with node
        result = subprocess.run(
            ['node', script_path, *args],
            capture_output=True,
            timeout=self.timeout
        )
        return result
```

**Benefits:**
- Support Node.js-based skills
- Broader skill compatibility
- Leverage existing npm ecosystem

**Trade-offs:**
- Adds Node.js dependency
- More complex environment requirements
- Security considerations

**Recommendation:** Low priority. Most ADK users are Python-focused. Better to focus on Python implementations of popular skills.

### 4. Interactive Script Support 🎮 FUTURE

**Opportunity:** Support skills that require user interaction.

**Use Cases:**
- Browser automation with user selection (pi-skills browser-pick)
- Form filling with user confirmation
- Manual approval workflows

**Design Questions:**
- How to handle stdin/stdout interaction?
- Should scripts open GUI windows?
- How to communicate back to agent?

**Recommendation:** Defer to Phase 3+. Focus on fully automated skills first.

### 5. Enhanced Documentation 📚 MEDIUM PRIORITY

**Opportunity:** Learn from pi-skills' practical documentation style.

**What Pi-Skills Does Well:**
- Clear use cases upfront
- Concrete examples with exact commands
- Setup instructions (API keys, dependencies)
- Output format examples

**Action Items:**
- Update our example skills with better docs
- Add "When to Use" sections
- Include setup instructions
- Show example outputs
- Reference real-world scenarios

### 6. CLI-First Design Philosophy 📖 DOCUMENTATION

**Opportunity:** Articulate the CLI-first pattern in our docs.

**Key Message:**
> "The best skills are simple CLI tools with excellent READMEs. Agents read the README, understand the capability, and invoke the CLI when needed. Keep it simple."

**Documentation Additions:**
- Skill developer guide: CLI-first patterns
- Examples of good CLI design
- README writing guidelines
- Emphasize simplicity over complexity

---

## What We Should NOT Do

### ❌ 1. Abandon agentskills.io Standard

**Why Not:** The standard provides:
- Cross-platform compatibility (Claude, ADK, etc.)
- Clear validation criteria
- Community alignment
- Long-term portability

Pi-skills' custom format is expedient but limits ecosystem growth.

### ❌ 2. Add MCP Support

**Why Not:**
- Pi-mono explicitly avoids MCP due to context overhead
- Our on-demand activation pattern is superior
- MCP adds complexity without clear benefits
- Focus on skills standard instead

### ❌ 3. Copy Non-Standard Patterns

**Why Not:**
- Markdown table metadata → Less structured
- Flat script structure → Less organized
- `{baseDir}` placeholders → Less explicit

Our patterns are better designed and spec-compliant.

### ❌ 4. Support Every Script Language

**Why Not:**
- Python + Bash covers 90% of use cases
- Each executor adds maintenance burden
- Better to port valuable skills to Python
- Keep dependencies minimal

---

## Recommendations Summary

### Immediate Actions (Phase 2)

1. ✅ **Continue with current implementation** - Our architecture is sound
2. 📝 **Document CLI-first philosophy** - Emphasize simplicity
3. 📚 **Improve example skills** - Add better documentation, use cases

### Near-Term (Phase 3)

4. 🎯 **Create skill library** - Implement standard versions of popular pi-skills
   - Start with: brave-search, youtube-transcript, browser-tools (Playwright)
   - Each skill: Python-based, well-documented, fully tested
5. 🛠️ **Build format converter** - Tool to convert pi-skills → agentskills.io
6. 📖 **Enhanced documentation** - Skill developer guide with best practices

### Future Considerations

7. 🔧 **Node.js executor** - Only if strong demand from community
8. 🎮 **Interactive skills** - Research and design, but don't rush
9. 🌐 **Remote skills** - Skills from GitHub/registries (Phase 4+)

---

## Competitive Analysis

### Positioning

| Project | Focus | Format | Language | Target |
|---------|-------|--------|----------|--------|
| **pi-skills** | Practical coding skills | Custom | JavaScript | pi-coding-agent |
| **adk-skills** | Standard-compliant skills | agentskills.io | Python | Google ADK |
| **anthropic/skills** | Reference implementations | agentskills.io | Various | Claude |

**Our Niche:**
- Python-focused ADK integration
- Standards-compliant
- Well-architected and tested
- Foundation for ecosystem growth

**Market Opportunity:**
- Pi-skills users wanting standards
- ADK users wanting skills support
- Python developers building agents
- Cross-platform skill sharing

---

## Conclusion

### What We Learned

1. ✅ **Our architecture is sound** - Progressive disclosure pattern is proven
2. ✅ **Standards matter** - Agentskills.io provides long-term value
3. 💡 **Practical skills are key** - Users need working, useful capabilities
4. 🎯 **Focus on value** - Build real skills that solve real problems
5. 📚 **Documentation matters** - Clear, practical examples drive adoption

### Strategic Direction

**Short-term:** Complete Phase 1-2 implementation (MVP + Script Execution)

**Mid-term:** Build practical skill library demonstrating value

**Long-term:** Grow the Python/ADK skills ecosystem

### Next Steps

1. Continue with current implementation plan
2. After MVP completion, start building skill library
3. Focus on Python implementations of high-value capabilities
4. Document patterns and best practices
5. Engage with agentskills.io community

---

## References

- Pi-Mono Repository: https://github.com/badlogic/pi-mono
- Pi-Skills Repository: https://github.com/badlogic/pi-skills
- Blog Post: https://mariozechner.at/posts/2025-11-30-pi-coding-agent/
- Agentskills.io Specification: https://agentskills.io/specification
- Our Design Document: [DESIGN.md](DESIGN.md)
- Our Implementation Plan: [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)

---

**Analysis Version:** 1.0
**Date:** 2026-01-07
**Author:** ADK Skills Project
**Status:** Complete
