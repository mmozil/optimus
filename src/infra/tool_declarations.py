"""
Agent Optimus — Tool Declarations Bridge (Phase 12).
Converts MCPTool definitions to OpenAI-compatible function declarations for LiteLLM.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.skills.mcp_tools import MCPTool, MCPToolRegistry


def mcp_tool_to_function_declaration(tool: MCPTool) -> dict:
    """Convert a single MCPTool to an OpenAI-compatible function declaration."""
    properties: dict = {}
    required: list[str] = []

    for param_name, param_def in tool.parameters.items():
        prop: dict = {"type": param_def.get("type", "string")}
        if param_def.get("description"):
            prop["description"] = param_def["description"]
        properties[param_name] = prop

        if param_def.get("required"):
            required.append(param_name)

    function_def: dict = {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": {
                "type": "object",
                "properties": properties,
            },
        },
    }

    if required:
        function_def["function"]["parameters"]["required"] = required

    return function_def


def get_tool_declarations(
    registry: MCPToolRegistry,
    agent_level: str | None = None,
) -> list[dict]:
    """Get all tool declarations filtered by agent level."""
    tools = registry.list_tools(agent_level=agent_level)
    return [mcp_tool_to_function_declaration(t) for t in tools]
