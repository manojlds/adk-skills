# Tools Reference - What the LLM Sees

This document shows exactly what tools are available to the LLM and what descriptions/schemas it sees.

## Overview

The adk-skills library provides **3 main tools** to the LLM:

1. `use_skill` - Activate a skill to get detailed instructions
2. `run_script` - Execute a Python/Bash script from a skill
3. `read_reference` - Read reference documentation from a skill

---

## Tool 1: `use_skill`

**Purpose:** Load a skill to get detailed instructions for a specific task.

**Function Signature:**
```python
use_skill(name: str) -> dict[str, Any]
```

**Parameters:**
- `name` (string, required): The skill identifier to activate

**Returns:**
```python
{
    "skill_name": str,          # Name of the activated skill
    "instructions": str,         # Full markdown instructions from SKILL.md
    "base_directory": str,       # Path to the skill directory
    "has_scripts": bool,         # Whether the skill has a scripts/ directory
    "has_references": bool,      # Whether the skill has a references/ directory
    "has_assets": bool           # Whether the skill has an assets/ directory
}
```

**Description the LLM sees:**
```
Load a skill to get detailed instructions for a specific task.

Skills provide specialized knowledge and step-by-step guidance.
Use this when a task matches an available skill's description.

<available_skills>
  <skill>
    <name>calculator</name>
    <description>Perform basic mathematical calculations (add, subtract, multiply, divide)</description>
  </skill>
  <skill>
    <name>hello-world</name>
    <description>A minimal example skill that demonstrates the basic skill structure</description>
  </skill>
</available_skills>

Args:
    name: The skill identifier to activate

Returns:
    Dict containing:
    - skill_name: Name of the activated skill
    - instructions: Full markdown instructions from SKILL.md
    - base_directory: Path to the skill directory
    - has_scripts: Whether the skill has a scripts/ directory
    - has_references: Whether the skill has a references/ directory
    - has_assets: Whether the skill has an assets/ directory
```

**Key Features:**
- The `<available_skills>` XML block is **dynamically injected** into the tool description
- Lists all discovered skills with name and description
- LLM can see all available skills without needing to load them
- Only loads full instructions when the skill is activated

**Example LLM Usage:**
```
1. LLM sees "calculator" skill in the available_skills list
2. LLM calls: use_skill(name="calculator")
3. Returns full instructions for performing calculations
4. LLM follows the instructions from SKILL.md
```

---

## Tool 2: `run_script`

**Purpose:** Execute a Python or Bash script from an activated skill.

**Function Signature:**
```python
run_script(skill: str, script: str, args: Optional[dict[str, Any]] = None) -> dict[str, Any]
```

**Parameters:**
- `skill` (string, required): Name of the skill containing the script
- `script` (string, required): Name of the script file to execute (e.g., "process.py", "scrape.sh")
- `args` (dict, optional): Dictionary of arguments to pass to the script

**Returns:**
```python
{
    "stdout": str,              # Standard output from the script
    "stderr": str,              # Standard error from the script
    "returncode": int,          # Exit code of the script
    "success": bool             # Whether the script executed successfully (returncode == 0)
}
```

**Description the LLM sees:**
```
Execute a script from an activated skill.

Args:
    skill: Name of the skill containing the script
    script: Name of the script file to execute (e.g., "process.py", "scrape.sh")
    args: Dictionary of arguments to pass to the script (optional)

Returns:
    Dict containing:
    - stdout: Standard output from the script
    - stderr: Standard error from the script
    - returncode: Exit code of the script
    - success: Whether the script executed successfully

Raises:
    SkillNotFoundError: If skill doesn't exist
    SkillExecutionError: If script execution fails
```

**Security Features:**
- Script execution limited by timeout (default: 30 seconds)
- Scripts run in skill's base directory
- Path validation prevents directory traversal
- Sandboxing support (configurable)

**Example LLM Usage:**
```
1. LLM activates a skill with use_skill()
2. Skill instructions mention scripts/calculate.py
3. LLM calls: run_script(skill="calculator", script="calculate.py")
4. Returns output from the calculation
```

---

## Tool 3: `read_reference`

**Purpose:** Read reference documentation from a skill.

**Function Signature:**
```python
read_reference(skill: str, reference: str) -> dict[str, Any]
```

**Parameters:**
- `skill` (string, required): Name of the skill containing the reference
- `reference` (string, required): Name of the reference file to read (e.g., "api_docs.md", "guide.txt")

**Returns:**
```python
{
    "content": str,             # Contents of the reference file
    "path": str,                # Full path to the reference file
    "filename": str             # Name of the reference file
}
```

**Description the LLM sees:**
```
Read a reference document from a skill.

Args:
    skill: Name of the skill containing the reference
    reference: Name of the reference file to read (e.g., "api_docs.md", "guide.txt")

Returns:
    Dict containing:
    - content: Contents of the reference file
    - path: Full path to the reference file
    - filename: Name of the reference file

Raises:
    SkillNotFoundError: If skill doesn't exist
    SkillExecutionError: If reference file cannot be read
```

**Security Features:**
- Path traversal prevention
- UTF-8 text files only
- File validation

**Example LLM Usage:**
```
1. LLM activates a skill with use_skill()
2. Instructions mention references/operations.md
3. LLM calls: read_reference(skill="calculator", reference="operations.md")
4. Returns detailed documentation about operations
```

---

## Complete LLM Workflow

Here's how the LLM typically uses these tools together:

### Step 1: Discovery
The LLM sees the `use_skill` tool description with all available skills:
```xml
<available_skills>
  <skill>
    <name>calculator</name>
    <description>Perform basic mathematical calculations</description>
  </skill>
</available_skills>
```

### Step 2: Activation
When user asks: "Can you help me calculate 25 * 17?"

LLM thinks: "This matches the calculator skill description"

LLM calls:
```python
use_skill(name="calculator")
```

Returns:
```python
{
    "skill_name": "calculator",
    "instructions": "# Calculator Skill\n\nUse this skill to perform calculations...",
    "base_directory": "/path/to/skills/calculator",
    "has_scripts": True,
    "has_references": True,
    "has_assets": False
}
```

### Step 3: Follow Instructions
LLM reads the instructions which say:
```markdown
## How to Use
1. For simple calculations, use scripts/calculate.py
2. For advanced operations, read references/operations.md
```

### Step 4: Execute or Read
LLM can either:

**Option A: Run a script**
```python
run_script(
    skill="calculator",
    script="calculate.py"
)
```

**Option B: Read reference docs**
```python
read_reference(
    skill="calculator",
    reference="operations.md"
)
```

---

## Tool Design Philosophy

### 1. **Lazy Loading** (~50-100 tokens per skill)
- Only skill names and descriptions are in tool description
- Full instructions loaded on-demand when skill is activated
- Keeps context window small

### 2. **Dynamic Discovery**
- The `<available_skills>` block is generated at runtime
- Changes when new skills are added to directories
- No hardcoded skill lists

### 3. **XML Format**
- Uses structured XML for easy parsing
- Special characters properly escaped (&lt;, &gt;, &amp;)
- Follows agentskills.io specification

### 4. **Security First**
- Path validation on all file operations
- Timeout limits on script execution
- Sandboxing support (configurable)
- No arbitrary code execution

---

## Configuration

### Tool Inclusion
You can choose which tools to provide:

```python
agent = SkillsAgent(
    name="assistant",
    model="gemini-2.5-flash",
    skills_directories=["./skills"],
    include_script_tool=True,      # Default: True
    include_reference_tool=True,   # Default: True
)
```

### Script Execution Settings
Configure timeouts and sandboxing:

```python
config = SkillsConfig(
    enable_scripts=True,
    script_timeout=30,        # seconds
    sandbox_mode=True
)

registry = SkillsRegistry(config=config)
```

---

## Alternative: Prompt Injection

Instead of using tools, you can inject skills directly into the system prompt:

### XML Format
```python
registry = SkillsRegistry()
registry.discover(["./skills"])

prompt = registry.to_prompt_xml()
# Returns:
# <available_skills>
#   <skill>
#     <name>calculator</name>
#     <description>Perform calculations</description>
#   </skill>
# </available_skills>
```

### Text Format
```python
prompt = registry.to_prompt_text()
# Returns:
# Available Skills:
# - calculator: Perform basic mathematical calculations
# - hello-world: A minimal example skill
```

### Usage with Agent
```python
agent = Agent(
    name="assistant",
    model="gemini-2.5-flash",
    instruction=f"You are helpful.\n\n{prompt}"
)
```

**Trade-offs:**
- ✅ No tool calls needed
- ✅ All skills visible in system prompt
- ❌ Uses more tokens upfront
- ❌ Can't dynamically load full instructions

---

## Summary

**What the LLM Sees:**
1. **Tool 1 (use_skill)**: List of available skills + activation capability
2. **Tool 2 (run_script)**: Script execution capability
3. **Tool 3 (read_reference)**: Documentation reading capability

**Key Advantages:**
- 🔍 **Discovery**: LLM sees all skills without loading them
- 🎯 **On-Demand**: Only loads full instructions when needed
- 🔧 **Execution**: Can run scripts from skills
- 📚 **Documentation**: Can read reference materials
- 🔒 **Secure**: Path validation and timeouts
- 📦 **Efficient**: Minimal context usage (~50-100 tokens per skill)

**Integration Patterns:**
1. **Tool-based** (default): Skills in tool descriptions
2. **Prompt injection**: Skills in system prompt
3. **Mixed**: Both tools and prompt injection
