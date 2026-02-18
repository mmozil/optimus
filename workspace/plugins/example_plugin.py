"""
Example MCP Plugin - demonstração de plugin customizado.
Este plugin adiciona uma ferramenta simples de exemplo.
"""

from src.skills.mcp_tools import MCPTool, MCPToolRegistry


async def hello_world(name: str = "World") -> str:
    """Simple hello world function."""
    return f"Hello, {name}! This is a custom MCP plugin."


async def calculate_sum(a: float, b: float) -> float:
    """Calculate sum of two numbers."""
    return a + b


def register_tools(registry: MCPToolRegistry):
    """Register custom tools with the MCP registry."""

    registry.register(MCPTool(
        name="hello_world",
        description="Say hello to someone (example plugin tool)",
        category="example",
        handler=hello_world,
        parameters={
            "name": {"type": "string", "description": "Name to greet", "default": "World"},
        },
    ))

    registry.register(MCPTool(
        name="calculate_sum",
        description="Calculate sum of two numbers (example plugin tool)",
        category="example",
        handler=calculate_sum,
        parameters={
            "a": {"type": "number", "description": "First number"},
            "b": {"type": "number", "description": "Second number"},
        },
    ))
