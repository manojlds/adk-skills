#!/usr/bin/env python3
"""Basic example demonstrating adk-skills usage.

This example shows:
1. Discovering skills from a directory
2. Listing available skills
3. Creating tools for skill activation
4. Activating a skill on-demand
5. Reading references
"""

from pathlib import Path

from adk_skills_agent import SkillsRegistry


def main() -> None:
    """Run basic example."""
    print("=" * 60)
    print("ADK Skills - Basic Example")
    print("=" * 60)
    print()

    # 1. Create registry and discover skills
    print("1. Discovering skills...")
    registry = SkillsRegistry()
    skills_dir = Path(__file__).parent / "skills"
    count = registry.discover([skills_dir])
    print(f"   ✓ Found {count} skill(s)")
    print()

    # 2. List discovered skills
    print("2. Available skills:")
    for metadata in registry.list_metadata():
        print(f"   - {metadata.name}: {metadata.description}")
    print()

    # 3. Create tools
    print("3. Creating ADK tools...")
    use_skill = registry.create_use_skill_tool()
    run_script = registry.create_run_script_tool()
    read_reference = registry.create_read_reference_tool()
    print("   ✓ Created use_skill tool")
    print("   ✓ Created run_script tool")
    print("   ✓ Created read_reference tool")
    print()

    # 4. Demonstrate tool docstrings (what ADK agents see)
    print("4. Tool description (what agents see):")
    print("-" * 60)
    print(use_skill.__doc__[:500] + "...")
    print("-" * 60)
    print()

    # 5. Activate a skill
    print("5. Activating 'calculator' skill...")
    result = use_skill("calculator")
    print(f"   ✓ Skill activated: {result['skill_name']}")
    print(f"   ✓ Base directory: {result['base_directory']}")
    print(f"   ✓ Has scripts: {result['has_scripts']}")
    print(f"   ✓ Has references: {result['has_references']}")
    print()
    print("   Instructions preview:")
    print("   " + "-" * 56)
    instructions = result["instructions"]
    preview = instructions[:300].replace("\n", "\n   ")
    print(f"   {preview}...")
    print("   " + "-" * 56)
    print()

    # 6. Read a reference file
    print("6. Reading reference file...")
    try:
        ref_result = read_reference("calculator", "operations.md")
        print(f"   ✓ Read reference: {ref_result['filename']}")
        print(f"   ✓ Content length: {len(ref_result['content'])} characters")
        print()
        print("   Content preview:")
        print("   " + "-" * 56)
        preview = ref_result["content"][:250].replace("\n", "\n   ")
        print(f"   {preview}...")
        print("   " + "-" * 56)
    except Exception as e:
        print(f"   ✗ Error reading reference: {e}")
    print()

    # 7. Show how to integrate with ADK (pseudo-code)
    print("7. Integration with Google ADK:")
    print()
    print("   ```python")
    print("   from google.adk.agents import Agent")
    print("   from adk_skills_agent import SkillsRegistry")
    print()
    print("   registry = SkillsRegistry()")
    print('   registry.discover(["./skills"])')
    print()
    print("   agent = Agent(")
    print('       name="assistant",')
    print('       model="gemini-2.5-flash",')
    print('       instruction="You are a helpful assistant.",')
    print("       tools=[")
    print("           registry.create_use_skill_tool(),")
    print("           registry.create_run_script_tool(),")
    print("       ]")
    print("   )")
    print("   ```")
    print()

    print("=" * 60)
    print("Example complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
