"""
Agent Optimus — MCP Tools.
Native MCP tool definitions for agent capabilities.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


@dataclass
class MCPTool:
    """Definition of an MCP tool."""
    name: str
    description: str
    category: str  # db, fs, research, browser, terminal, custom
    parameters: dict[str, dict] = field(default_factory=dict)  # JSON Schema
    handler: Callable[..., Coroutine] | None = None
    requires_approval: bool = False  # Destructive operations need user approval
    agent_levels: list[str] = field(default_factory=lambda: ["lead", "specialist", "intern"])


@dataclass
class ToolResult:
    """Result from executing an MCP tool."""
    success: bool
    output: Any = None
    error: str | None = None
    tool_name: str = ""


class MCPToolRegistry:
    """
    Registry for native MCP tools.
    Provides tool definitions, execution, and manifest generation.
    """

    def __init__(self):
        self._tools: dict[str, MCPTool] = {}
        self._register_native_tools()

    def register(self, tool: MCPTool):
        """Register an MCP tool."""
        self._tools[tool.name] = tool
        logger.debug(f"MCP Tool registered: {tool.name} ({tool.category})")

    def get(self, name: str) -> MCPTool | None:
        return self._tools.get(name)

    def list_tools(self, category: str | None = None, agent_level: str | None = None) -> list[MCPTool]:
        """List tools, optionally filtered by category or agent level."""
        tools = list(self._tools.values())
        if category:
            tools = [t for t in tools if t.category == category]
        if agent_level:
            tools = [t for t in tools if agent_level in t.agent_levels]
        return tools

    async def execute(self, tool_name: str, params: dict, agent_name: str = "") -> ToolResult:
        """Execute a tool by name."""
        tool = self._tools.get(tool_name)
        if not tool:
            return ToolResult(success=False, error=f"Tool '{tool_name}' not found", tool_name=tool_name)

        if not tool.handler:
            return ToolResult(success=False, error=f"Tool '{tool_name}' has no handler", tool_name=tool_name)

        try:
            logger.info(f"MCP executing: {tool_name}", extra={"props": {
                "tool": tool_name, "agent": agent_name, "category": tool.category,
            }})

            output = await tool.handler(**params)
            return ToolResult(success=True, output=output, tool_name=tool_name)

        except Exception as e:
            logger.error(f"MCP tool '{tool_name}' failed: {e}")
            return ToolResult(success=False, error=str(e), tool_name=tool_name)

    def generate_manifest(self) -> str:
        """Generate TOOLS.md manifest with all registered tools."""
        lines = ["# 🔧 MCP Tools Manifest\n", "_Auto-generated_\n"]

        categories = sorted(set(t.category for t in self._tools.values()))

        for category in categories:
            lines.append(f"\n## {category.upper()}\n")
            tools = [t for t in self._tools.values() if t.category == category]

            for tool in sorted(tools, key=lambda t: t.name):
                approval = " ⚠️ **requires approval**" if tool.requires_approval else ""
                levels = ", ".join(tool.agent_levels)
                lines.append(f"### `{tool.name}`{approval}")
                lines.append(f"{tool.description}")
                lines.append(f"_Levels: {levels}_\n")

                if tool.parameters:
                    lines.append("**Parameters:**")
                    for param_name, param_def in tool.parameters.items():
                        param_type = param_def.get("type", "string")
                        required = " *(required)*" if param_def.get("required") else ""
                        desc = param_def.get("description", "")
                        lines.append(f"- `{param_name}` ({param_type}){required}: {desc}")
                    lines.append("")

        return "\n".join(lines)

    # ============================================
    # Native Tools Registration
    # ============================================

    def _register_native_tools(self):
        """Register built-in MCP tools."""

        # --- Database Tools ---
        self.register(MCPTool(
            name="db_query",
            description="Execute a read-only SQL query against the database",
            category="db",
            parameters={
                "query": {"type": "string", "required": True, "description": "SQL SELECT query"},
                "limit": {"type": "integer", "description": "Max rows to return (default: 100)"},
            },
            handler=self._tool_db_query,
        ))

        self.register(MCPTool(
            name="db_execute",
            description="Execute a write SQL statement (INSERT, UPDATE, DELETE)",
            category="db",
            parameters={
                "statement": {"type": "string", "required": True, "description": "SQL statement"},
            },
            handler=self._tool_db_execute,
            requires_approval=True,
            agent_levels=["lead", "specialist"],
        ))

        # --- File System Tools ---
        self.register(MCPTool(
            name="fs_read",
            description="Read contents of a file",
            category="fs",
            parameters={
                "path": {"type": "string", "required": True, "description": "File path"},
            },
            handler=self._tool_fs_read,
        ))

        self.register(MCPTool(
            name="fs_write",
            description="Write content to a file",
            category="fs",
            parameters={
                "path": {"type": "string", "required": True, "description": "File path"},
                "content": {"type": "string", "required": True, "description": "Content to write"},
            },
            handler=self._tool_fs_write,
            requires_approval=True,
            agent_levels=["lead", "specialist"],
        ))

        self.register(MCPTool(
            name="fs_list",
            description="List files in a directory",
            category="fs",
            parameters={
                "path": {"type": "string", "required": True, "description": "Directory path"},
                "pattern": {"type": "string", "description": "Glob pattern filter"},
            },
            handler=self._tool_fs_list,
        ))

        # --- Research Tools ---
        self.register(MCPTool(
            name="research_search",
            description="Search the web for information",
            category="research",
            parameters={
                "query": {"type": "string", "required": True, "description": "Search query"},
                "max_results": {"type": "integer", "description": "Max results (default: 5)"},
            },
            handler=self._tool_research_search,
        ))

        self.register(MCPTool(
            name="research_fetch_url",
            description="Fetch and extract content from a URL",
            category="research",
            parameters={
                "url": {"type": "string", "required": True, "description": "URL to fetch"},
            },
            handler=self._tool_research_fetch_url,
        ))

        # --- Knowledge Base (RAG) Tools ---
        from src.skills.knowledge_tool import search_knowledge_base
        self.register(MCPTool(
            name="search_knowledge_base",
            description="Search the company knowledge base / long-term memory for documents and information.",
            category="research",
            handler=search_knowledge_base,
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The question or topic to search for."},
                    "limit": {"type": "integer", "description": "Max results (default 5)."}
                },
                "required": ["query"]
            },
            agent_levels=["lead", "specialist"]
        ))
        
        # --- Memory Tools ---
        self.register(MCPTool(
            name="memory_search",
            description="Search agent's long-term memory",
            category="memory",
            parameters={
                "agent_name": {"type": "string", "required": True, "description": "Agent name"},
                "query": {"type": "string", "required": True, "description": "Search query"},
            },
            handler=self._tool_memory_search,
        ))

        self.register(MCPTool(
            name="memory_learn",
            description="Add a learning to agent's long-term memory",
            category="memory",
            parameters={
                "agent_name": {"type": "string", "required": True, "description": "Agent name"},
                "category": {"type": "string", "required": True, "description": "Learning category"},
                "learning": {"type": "string", "required": True, "description": "The learning"},
            },
            handler=self._tool_memory_learn,
        ))

        # --- Code Execution Tools ---
        self.register(MCPTool(
            name="code_execute",
            description="Execute Python or Bash code in a secure sandbox",
            category="technical",
            parameters={
                "language": {"type": "string", "required": True, "description": "Language: 'python' or 'bash'"},
                "code": {"type": "string", "required": True, "description": "The code or command to execute"},
            },
            handler=self._tool_code_execute,
            requires_approval=True,
            agent_levels=["lead", "specialist"],
        ))

    # ============================================
    # Tool Handlers
    # ============================================

    async def _tool_code_execute(self, language: str, code: str) -> str:
        """Execute code in sandbox."""
        from src.infra.sandbox import code_sandbox
        
        if language.lower() == "python":
            result = await code_sandbox.execute_python(code)
        elif language.lower() == "bash":
            result = await code_sandbox.execute_bash(code)
        else:
            return f"Unsupported language: {language}"

        status = "✅ Success" if result.success else "❌ Failed"
        output = [
            f"--- Execution Result ({status}) ---",
            f"Duration: {result.duration_ms:.1f}ms",
            f"Exit Code: {result.exit_code}",
            "",
            "**STDOUT:**",
            result.stdout or "(empty)",
            "",
            "**STDERR:**",
            result.stderr or "(empty)",
        ]
        return "\n".join(output)

    async def _tool_db_query(self, query: str, limit: int = 100) -> str:
        """Execute read-only query."""
        from src.infra.supabase_client import get_async_session
        from sqlalchemy import text

        async with get_async_session() as session:
            result = await session.execute(text(f"{query} LIMIT {limit}"))
            rows = result.fetchall()
            return str([dict(row._mapping) for row in rows])

    async def _tool_db_execute(self, statement: str) -> str:
        """Execute write statement."""
        from src.infra.supabase_client import get_async_session
        from sqlalchemy import text

        async with get_async_session() as session:
            await session.execute(text(statement))
            await session.commit()
            return "Statement executed successfully."

    async def _tool_fs_read(self, path: str) -> str:
        """Read file contents."""
        import asyncio
        from pathlib import Path

        def _read():
            p = Path(path)
            if not p.exists():
                return f"File not found: {path}"
            return p.read_text(encoding="utf-8")[:10_000]

        return await asyncio.to_thread(_read)

    async def _tool_fs_write(self, path: str, content: str) -> str:
        """Write to file."""
        import asyncio
        from pathlib import Path

        def _write():
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return f"Written {len(content)} chars to {path}"

        return await asyncio.to_thread(_write)

    async def _tool_fs_list(self, path: str, pattern: str = "*") -> str:
        """List directory contents."""
        import asyncio
        from pathlib import Path

        def _list():
            p = Path(path)
            if not p.exists():
                return f"Directory not found: {path}"
            files = list(p.glob(pattern))[:50]
            return "\n".join(str(f.relative_to(p)) for f in files)

        return await asyncio.to_thread(_list)

    async def _tool_research_search(self, query: str, max_results: int = 5) -> str:
        """Web search stub — integrate with search API."""
        return f"[Search stub] Query: '{query}' — integrate with Tavily/SerpAPI for real results."

    async def _tool_research_fetch_url(self, url: str) -> str:
        """Fetch URL content."""
        import httpx
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url)
            return response.text[:10_000]

    async def _tool_memory_search(self, agent_name: str, query: str) -> str:
        """Search long-term memory."""
        from src.memory.long_term import long_term_memory
        results = await long_term_memory.search_local(agent_name, query)
        return "\n---\n".join(results) if results else "Nenhum resultado encontrado."

    async def _tool_memory_learn(self, agent_name: str, category: str, learning: str) -> str:
        """Add learning to memory."""
        from src.memory.long_term import long_term_memory
        await long_term_memory.add_learning(agent_name, category, learning)
        return f"Learning adicionado para {agent_name}: {category}"


# Singleton
mcp_tools = MCPToolRegistry()
