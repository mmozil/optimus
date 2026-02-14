"""
Tests for Phase 5 — Orchestration: Orchestrator, MCP, A2A, Tools Manifest.
"""

import pytest
from uuid import uuid4

from src.core.orchestrator import (
    ExecutionMode, Orchestrator, OrchestratorStep, PipelineResult,
)
from src.skills.mcp_tools import MCPTool, MCPToolRegistry, ToolResult
from src.skills.mcp_plugin import MCPPluginLoader, MCPPluginConfig
from src.core.a2a_protocol import (
    A2AProtocol, AgentCard, A2AMessage, DelegationRequest,
)


# ============================================
# Orchestrator Tests
# ============================================
class TestOrchestrator:
    def setup_method(self):
        self.orch = Orchestrator()

    def test_register_pipeline(self):
        steps = [
            OrchestratorStep(name="step1", agent_name="optimus"),
            OrchestratorStep(name="step2", agent_name="friday"),
        ]
        self.orch.register_pipeline("test_pipe", steps)
        pipes = self.orch.list_pipelines()
        assert len(pipes) == 1
        assert pipes[0]["steps"] == 2

    @pytest.mark.asyncio
    async def test_execute_unknown_pipeline(self):
        result = await self.orch.execute("nonexistent", "input")
        assert not result.success
        assert "not found" in result.errors[0]

    def test_pipeline_result_defaults(self):
        result = PipelineResult()
        assert result.success is True
        assert result.steps_executed == 0

    def test_orchestrator_step_defaults(self):
        step = OrchestratorStep(name="test", agent_name="optimus")
        assert step.timeout == 60.0
        assert step.prompt_template == "{input}"
        assert step.condition is None

    def test_execution_modes(self):
        assert ExecutionMode.SEQUENTIAL == "sequential"
        assert ExecutionMode.PARALLEL == "parallel"
        assert ExecutionMode.LOOP == "loop"


# ============================================
# MCP Tools Tests
# ============================================
class TestMCPTools:
    def setup_method(self):
        self.registry = MCPToolRegistry()

    def test_native_tools_registered(self):
        tools = self.registry.list_tools()
        assert len(tools) >= 8  # At least 8 native tools

    def test_list_by_category(self):
        db_tools = self.registry.list_tools(category="db")
        assert len(db_tools) >= 2  # db_query, db_execute

    def test_list_by_agent_level(self):
        # Interns shouldn't see destructive tools
        intern_tools = self.registry.list_tools(agent_level="intern")
        destructive = [t for t in intern_tools if t.requires_approval]
        # db_execute and fs_write require lead/specialist level
        assert all(t.name not in ("db_execute", "fs_write") for t in intern_tools
                    if "intern" not in t.agent_levels)

    def test_get_tool(self):
        tool = self.registry.get("fs_read")
        assert tool is not None
        assert tool.category == "fs"

    def test_register_custom_tool(self):
        async def custom_handler(text: str) -> str:
            return f"processed: {text}"

        tool = MCPTool(
            name="custom_test",
            description="A test tool",
            category="custom",
            handler=custom_handler,
        )
        self.registry.register(tool)
        assert self.registry.get("custom_test") is not None

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self):
        result = await self.registry.execute("nonexistent", {})
        assert not result.success
        assert "not found" in result.error

    def test_generate_manifest(self):
        manifest = self.registry.generate_manifest()
        assert "MCP Tools Manifest" in manifest
        assert "db_query" in manifest
        assert "fs_read" in manifest

    @pytest.mark.asyncio
    async def test_fs_read_not_found(self):
        result = await self.registry.execute("fs_read", {"path": "/nonexistent/file.txt"})
        assert result.success
        assert "not found" in result.output.lower()

    @pytest.mark.asyncio
    async def test_fs_list_not_found(self):
        result = await self.registry.execute("fs_list", {"path": "/nonexistent/dir"})
        assert result.success
        assert "not found" in result.output.lower()


# ============================================
# MCP Plugin Loader Tests
# ============================================
class TestMCPPluginLoader:
    def setup_method(self):
        self.registry = MCPToolRegistry()
        self.loader = MCPPluginLoader(registry=self.registry)

    @pytest.mark.asyncio
    async def test_load_disabled_plugin(self):
        config = MCPPluginConfig(name="disabled", module_path="test", enabled=False)
        result = await self.loader.load_plugin(config)
        assert result is False

    @pytest.mark.asyncio
    async def test_load_nonexistent_plugin(self):
        config = MCPPluginConfig(name="nope", module_path="nonexistent.module")
        result = await self.loader.load_plugin(config)
        assert result is False

    @pytest.mark.asyncio
    async def test_load_from_nonexistent_directory(self):
        count = await self.loader.load_from_directory("/nonexistent/plugins")
        assert count == 0

    def test_list_plugins_empty(self):
        plugins = self.loader.list_plugins()
        assert plugins == []


# ============================================
# A2A Protocol Tests
# ============================================
class TestA2AProtocol:
    def setup_method(self):
        self.a2a = A2AProtocol()

    def test_register_agent(self):
        card = AgentCard(name="optimus", role="Orchestrator", level="lead",
                         capabilities=["planning", "delegation"])
        self.a2a.register_agent(card)
        found = self.a2a.get_card("optimus")
        assert found is not None
        assert found.role == "Orchestrator"

    def test_discover_by_capability(self):
        self.a2a.register_agent(AgentCard(
            name="friday", role="Developer", level="specialist",
            capabilities=["code", "debug"]
        ))
        self.a2a.register_agent(AgentCard(
            name="fury", role="Researcher", level="specialist",
            capabilities=["research", "analysis"]
        ))

        coders = self.a2a.discover(capability="code")
        assert len(coders) == 1
        assert coders[0].name == "friday"

    def test_discover_available_only(self):
        self.a2a.register_agent(AgentCard(name="bot1", role="R", level="intern", status="available"))
        self.a2a.register_agent(AgentCard(name="bot2", role="R", level="intern", status="busy"))
        available = self.a2a.discover(available_only=True)
        assert len(available) == 1

    def test_find_best_agent_lowest_load(self):
        self.a2a.register_agent(AgentCard(
            name="a1", role="Dev", level="specialist",
            capabilities=["code"], current_load=3
        ))
        self.a2a.register_agent(AgentCard(
            name="a2", role="Dev", level="specialist",
            capabilities=["code"], current_load=1
        ))
        best = self.a2a.find_best_agent("code")
        assert best.name == "a2"

    @pytest.mark.asyncio
    async def test_send_message(self):
        self.a2a.register_agent(AgentCard(name="optimus", role="Lead", level="lead"))
        self.a2a.register_agent(AgentCard(name="friday", role="Dev", level="specialist"))

        msg = A2AMessage(from_agent="optimus", to_agent="friday", content="Do this task")
        result = await self.a2a.send(msg)
        assert result is True

    @pytest.mark.asyncio
    async def test_send_to_unknown_agent(self):
        msg = A2AMessage(from_agent="optimus", to_agent="unknown", content="Hello")
        result = await self.a2a.send(msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_broadcast(self):
        self.a2a.register_agent(AgentCard(name="opt", role="L", level="lead"))
        self.a2a.register_agent(AgentCard(name="fri", role="D", level="specialist"))
        self.a2a.register_agent(AgentCard(name="fur", role="R", level="specialist"))

        await self.a2a.broadcast("opt", "Team meeting!")
        msgs_fri = await self.a2a.get_messages("fri")
        msgs_fur = await self.a2a.get_messages("fur")
        msgs_opt = await self.a2a.get_messages("opt")

        assert len(msgs_fri) == 1
        assert len(msgs_fur) == 1
        assert len(msgs_opt) == 0  # Sender excluded

    @pytest.mark.asyncio
    async def test_delegation(self):
        self.a2a.register_agent(AgentCard(name="optimus", role="Lead", level="lead"))
        self.a2a.register_agent(AgentCard(name="friday", role="Dev", level="specialist"))

        request = DelegationRequest(
            from_agent="optimus",
            to_agent="friday",
            task_description="Implement feature X",
        )
        msg = await self.a2a.delegate(request)
        assert msg.message_type == "delegation"

        # friday should have increased load
        card = self.a2a.get_card("friday")
        assert card.current_load == 1

        # Complete delegation
        await self.a2a.complete_delegation(msg.id, "Feature X done!")
        card = self.a2a.get_card("friday")
        assert card.current_load == 0

    def test_stats(self):
        self.a2a.register_agent(AgentCard(name="test", role="T", level="intern"))
        stats = self.a2a.get_stats()
        assert stats["registered_agents"] == 1
        assert "test" in stats["agents"]

    def test_update_status(self):
        self.a2a.register_agent(AgentCard(name="bot", role="R", level="intern"))
        self.a2a.update_status("bot", "busy")
        card = self.a2a.get_card("bot")
        assert card.status == "busy"
