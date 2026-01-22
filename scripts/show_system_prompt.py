#!/usr/bin/env python3
"""Output the complete system prompt including injected tools"""

import sys
from pathlib import Path

import tiktoken

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from zikos.mcp.server import MCPServer  # noqa: E402
from zikos.services.prompt import SystemPromptBuilder  # noqa: E402
from zikos.services.prompt.sections import CorePromptSection, ToolInstructionsSection  # noqa: E402
from zikos.services.tool_providers import get_tool_provider  # noqa: E402


def main():
    prompt_file = Path(__file__).parent.parent / "SYSTEM_PROMPT.md"

    builder = SystemPromptBuilder()
    builder.add_section(CorePromptSection(prompt_file))
    base_prompt = builder.build()

    mcp_server = MCPServer()
    tool_registry = mcp_server.get_tool_registry()
    tools = tool_registry.get_all_tools()

    tool_provider = get_tool_provider()

    tool_instructions = tool_provider.format_tool_instructions()
    tool_summary = tool_provider.generate_tool_summary(tools)
    tool_schemas_text = tool_provider.format_tool_schemas(tools)
    tool_examples = tool_provider.get_tool_call_examples()

    tools_text = f"{tool_instructions}\n{tool_summary}\n{tool_schemas_text}\n{tool_examples}"

    full_prompt = base_prompt
    if tools_text.strip():
        full_prompt = f"{full_prompt}\n\n{tools_text}"

    enc = tiktoken.get_encoding("cl100k_base")
    base_tokens = len(enc.encode(base_prompt))
    tools_tokens = len(enc.encode(tools_text)) if tools_text.strip() else 0
    total_tokens = len(enc.encode(full_prompt))

    print(full_prompt)
    print("\n" + "=" * 80)
    print("Token count (cl100k_base encoding):")
    print(f"  Base system prompt: {base_tokens:,} tokens")
    if tools_tokens > 0:
        print(f"  Tools section:      {tools_tokens:,} tokens")
    print(f"  Total:               {total_tokens:,} tokens")


if __name__ == "__main__":
    main()
