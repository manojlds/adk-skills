#!/usr/bin/env python3
"""Advanced example demonstrating new adk-skills features.

This example showcases:
1. Prompt injection utilities
2. Skills validation
3. SkillsAgent custom agent class
4. Helper functions (with_skills, create_skills_agent, inject_skills_prompt)
"""

from pathlib import Path

from adk_skills_agent import (
    SkillsAgent,
    SkillsRegistry,
    create_skills_agent,
    inject_skills_prompt,
    with_skills,
)


def demo_prompt_injection() -> None:
    """Demonstrate prompt injection utilities."""
    print("=" * 60)
    print("1. Prompt Injection Utilities")
    print("=" * 60)
    print()

    registry = SkillsRegistry()
    skills_dir = Path(__file__).parent / "skills"
    registry.discover([skills_dir])

    # XML format (default)
    print("XML Format:")
    print("-" * 60)
    xml_prompt = registry.to_prompt_xml()
    print(xml_prompt)
    print()

    # Text format
    print("Text Format:")
    print("-" * 60)
    text_prompt = registry.to_prompt_text()
    print(text_prompt)
    print()

    # Using get_skills_prompt with format parameter
    print("Using get_skills_prompt():")
    print("-" * 60)
    prompt = registry.get_skills_prompt(format="xml")
    print(f"Length: {len(prompt)} characters")
    print()


def demo_validation() -> None:
    """Demonstrate skills validation features."""
    print("=" * 60)
    print("2. Skills Validation")
    print("=" * 60)
    print()

    registry = SkillsRegistry()
    skills_dir = Path(__file__).parent / "skills"
    registry.discover([skills_dir])

    # Validate all skills
    print("Validating all skills...")
    results = registry.validate_all(strict=True)

    for name, result in results.items():
        status = "✓ Valid" if result.valid else "✗ Invalid"
        print(f"  {name}: {status}")

        if result.errors:
            for error in result.errors:
                print(f"    Error: {error}")

        if result.warnings:
            for warning in result.warnings:
                print(f"    Warning: {warning}")

    print()

    # Validate specific skill
    if "calculator" in registry:
        print("Validating 'calculator' skill...")
        result = registry.validate_skill_by_name("calculator", strict=True)
        print(f"  Valid: {result.valid}")
        print(f"  Errors: {len(result.errors)}")
        print(f"  Warnings: {len(result.warnings)}")
        print()


def demo_skills_agent() -> None:
    """Demonstrate SkillsAgent class."""
    print("=" * 60)
    print("3. SkillsAgent Custom Agent Class")
    print("=" * 60)
    print()

    skills_dir = Path(__file__).parent / "skills"

    # Create SkillsAgent with auto prompt injection
    print("Creating SkillsAgent with auto prompt injection...")
    agent = SkillsAgent(
        name="assistant",
        model="gemini-2.5-flash",
        instruction="You are a helpful assistant with specialized skills.",
        skills_directories=[skills_dir],
        auto_inject_prompt=True,
        prompt_format="xml",
        validate_skills=True,
    )

    print(f"  ✓ Agent created: {agent}")
    print(f"  ✓ Skills discovered: {len(agent.registry)}")
    print(f"  ✓ Tools available: {len(agent.get_tools())}")
    print()

    # Get instruction with injected skills
    print("Generated instruction (first 300 chars):")
    print("-" * 60)
    instruction = agent.get_instruction()
    print(instruction[:300] + "...")
    print()

    # Note: To build the actual ADK agent, google.adk must be installed:
    # agent_instance = agent.build()


def demo_helper_functions() -> None:
    """Demonstrate helper functions."""
    print("=" * 60)
    print("4. Helper Functions")
    print("=" * 60)
    print()

    skills_dir = Path(__file__).parent / "skills"

    # inject_skills_prompt helper
    print("Using inject_skills_prompt():")
    print("-" * 60)
    base_instruction = "You are a helpful assistant."
    full_instruction = inject_skills_prompt(
        base_instruction, [skills_dir], format="text"
    )
    print(full_instruction)
    print()

    # with_skills helper (requires a mock agent for demo)
    print("Using with_skills():")
    print("-" * 60)
    print("Note: with_skills() adds skills to an existing ADK agent.")
    print()
    print("Example usage:")
    print("  from google.adk.agents import Agent")
    print("  agent = Agent(name='assistant', model='gemini-2.5-flash')")
    print("  agent = with_skills(agent, ['./skills'])")
    print()

    # create_skills_agent helper
    print("Using create_skills_agent():")
    print("-" * 60)
    print("Note: create_skills_agent() creates an ADK agent with skills in one call.")
    print()
    print("Example usage:")
    print("  agent = create_skills_agent(")
    print("      name='assistant',")
    print("      model='gemini-2.5-flash',")
    print("      skills_directories=['./skills'],")
    print("  )")
    print()


def demo_integration_patterns() -> None:
    """Demonstrate common integration patterns."""
    print("=" * 60)
    print("5. Integration Patterns")
    print("=" * 60)
    print()

    skills_dir = Path(__file__).parent / "skills"

    print("Pattern 1: Tool-based (Default)")
    print("-" * 60)
    print("Skills are listed in tool descriptions, activated on-demand:")
    print()
    print("  registry = SkillsRegistry()")
    print("  registry.discover(['./skills'])")
    print("  agent = Agent(")
    print("      name='assistant',")
    print("      model='gemini-2.5-flash',")
    print("      tools=[")
    print("          registry.create_use_skill_tool(),")
    print("          registry.create_run_script_tool(),")
    print("      ]")
    print("  )")
    print()

    print("Pattern 2: System Prompt Injection")
    print("-" * 60)
    print("Skills are injected directly into system prompt:")
    print()
    print("  agent = SkillsAgent(")
    print("      name='assistant',")
    print("      model='gemini-2.5-flash',")
    print("      skills_directories=['./skills'],")
    print("      auto_inject_prompt=True,")
    print("  ).build()")
    print()

    print("Important: Choose ONE pattern, not both!")
    print("-" * 60)
    print("Listing skills in both prompt AND tool description wastes tokens.")
    print("SkillsAgent automatically uses include_skills_listing=False when")
    print("auto_inject_prompt=True to avoid duplication.")
    print()


def main() -> None:
    """Run all demonstrations."""
    print()
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  ADK Skills - Advanced Features Demo".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "═" * 58 + "╝")
    print()

    try:
        demo_prompt_injection()
        demo_validation()
        demo_skills_agent()
        demo_helper_functions()
        demo_integration_patterns()

        print("=" * 60)
        print("Demo Complete!")
        print("=" * 60)
        print()
        print("New features available:")
        print("  • Prompt injection utilities (to_prompt_xml, to_prompt_text)")
        print("  • Validation methods (validate_all, validate_skill_by_name)")
        print("  • SkillsAgent class for easy agent creation")
        print("  • Helper functions (with_skills, create_skills_agent)")
        print()

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
