"""
Tests for Phase 12 — Agent Real: Tool Calling + ReAct Loop.
All tests mock litellm.acompletion (never call real LLM APIs).
"""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.base import AgentConfig, BaseAgent
from src.core.security import Permission, SecurityManager
from src.infra.model_router import FALLBACK_CHAINS, MODEL_NAME_MAP, ModelRouter
from src.infra.tool_declarations import (
    get_tool_declarations,
    mcp_tool_to_function_declaration,
)
from src.skills.mcp_tools import MCPTool, MCPToolRegistry


# ============================================
# Helpers — Build mock LiteLLM responses
# ============================================

def _make_response(content="Hello", tool_calls=None, finish_reason="stop", prompt_tokens=10, completion_tokens=5):
    """Build a mock litellm acompletion response."""
    message = SimpleNamespace(
        content=content,
        tool_calls=tool_calls,
    )
    choice = SimpleNamespace(
        message=message,
        finish_reason=finish_reason,
    )
    usage = SimpleNamespace(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )
    return SimpleNamespace(choices=[choice], usage=usage)


def _make_tool_call(tc_id="tc_1", name="fs_read", arguments=None):
    """Build a mock tool_call object."""
    if arguments is None:
        arguments = {"path": "/tmp/test.txt"}
    return SimpleNamespace(
        id=tc_id,
        function=SimpleNamespace(
            name=name,
            arguments=json.dumps(arguments),
        ),
    )


# ============================================
# 1. Tool Declarations Tests
# ============================================

class TestToolDeclarations:
    def test_basic_conversion(self):
        tool = MCPTool(
            name="test_tool",
            description="A test tool",
            category="test",
            parameters={
                "query": {"type": "string", "required": True, "description": "Search query"},
            },
        )
        decl = mcp_tool_to_function_declaration(tool)

        assert decl["type"] == "function"
        assert decl["function"]["name"] == "test_tool"
        assert decl["function"]["description"] == "A test tool"
        assert "query" in decl["function"]["parameters"]["properties"]
        assert "query" in decl["function"]["parameters"]["required"]

    def test_required_params_extraction(self):
        tool = MCPTool(
            name="multi_param",
            description="Tool with mixed params",
            category="test",
            parameters={
                "required_field": {"type": "string", "required": True, "description": "Required"},
                "optional_field": {"type": "integer", "description": "Optional"},
            },
        )
        decl = mcp_tool_to_function_declaration(tool)

        assert "required_field" in decl["function"]["parameters"]["required"]
        assert "optional_field" not in decl["function"]["parameters"]["required"]

    def test_level_filtering(self):
        registry = MCPToolRegistry.__new__(MCPToolRegistry)
        registry._tools = {}

        # Tool for all levels
        registry._tools["all_tool"] = MCPTool(
            name="all_tool", description="For all", category="test",
            agent_levels=["lead", "specialist", "intern"],
        )
        # Tool for lead only
        registry._tools["lead_tool"] = MCPTool(
            name="lead_tool", description="Lead only", category="test",
            agent_levels=["lead"],
        )

        intern_decls = get_tool_declarations(registry, agent_level="intern")
        assert len(intern_decls) == 1
        assert intern_decls[0]["function"]["name"] == "all_tool"

        lead_decls = get_tool_declarations(registry, agent_level="lead")
        assert len(lead_decls) == 2

    def test_lead_gets_all_tools(self):
        """Lead agents should see all tools from the real registry."""
        from src.skills.mcp_tools import mcp_tools
        lead_tools = get_tool_declarations(mcp_tools, agent_level="lead")
        intern_tools = get_tool_declarations(mcp_tools, agent_level="intern")

        assert len(lead_tools) >= len(intern_tools)


# ============================================
# 2. Model Router Tests (LiteLLM)
# ============================================

class TestModelRouter:
    @pytest.mark.asyncio
    @patch("src.infra.model_router.litellm.acompletion")
    async def test_basic_response(self, mock_acomp):
        mock_acomp.return_value = _make_response(content="Test reply")

        router = ModelRouter()
        result = await router.generate("Hello", chain="default")

        assert result["content"] == "Test reply"
        assert result["model"] in FALLBACK_CHAINS["default"]
        assert result["tool_calls"] == []
        assert result["finish_reason"] == "stop"

    @pytest.mark.asyncio
    @patch("src.infra.model_router.litellm.acompletion")
    async def test_tool_calls_extraction(self, mock_acomp):
        tc = _make_tool_call(tc_id="tc_42", name="fs_read", arguments={"path": "/x"})
        mock_acomp.return_value = _make_response(
            content=None, tool_calls=[tc], finish_reason="tool_calls",
        )

        router = ModelRouter()
        result = await router.generate("Read file", chain="default", tools=[{"type": "function"}])

        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["id"] == "tc_42"
        assert result["tool_calls"][0]["name"] == "fs_read"
        assert result["tool_calls"][0]["arguments"] == {"path": "/x"}
        assert result["finish_reason"] == "tool_calls"

    @pytest.mark.asyncio
    @patch("src.infra.model_router.litellm.acompletion")
    async def test_failover(self, mock_acomp):
        """First model fails, second succeeds."""
        mock_acomp.side_effect = [
            Exception("Model 1 down"),
            _make_response(content="From model 2"),
        ]

        router = ModelRouter()
        result = await router.generate("Hello", chain="default")

        assert result["content"] == "From model 2"
        assert mock_acomp.call_count == 2

    @pytest.mark.asyncio
    @patch("src.infra.model_router.litellm.acompletion")
    async def test_all_models_fail(self, mock_acomp):
        mock_acomp.side_effect = Exception("All down")

        router = ModelRouter()
        with pytest.raises(RuntimeError, match="All models in chain"):
            await router.generate("Hello", chain="default")

    @pytest.mark.asyncio
    @patch("src.infra.model_router.litellm.acompletion")
    async def test_generate_with_history(self, mock_acomp):
        mock_acomp.return_value = _make_response(content="History reply")

        router = ModelRouter()
        messages = [
            {"role": "system", "content": "You are a bot"},
            {"role": "user", "content": "Hi"},
        ]
        result = await router.generate_with_history(messages, chain="default")

        assert result["content"] == "History reply"
        assert "raw_message" in result


# ============================================
# 3. ReAct Loop Tests
# ============================================

class TestReActLoop:
    @pytest.mark.asyncio
    @patch("src.infra.model_router.litellm.acompletion")
    async def test_direct_answer_no_tools(self, mock_acomp):
        """LLM returns text directly without calling any tools."""
        mock_acomp.return_value = _make_response(content="Direct answer")

        from src.engine.react_loop import react_loop
        result = await react_loop(
            user_message="What is 2+2?",
            system_prompt="You are a helpful assistant.",
            agent_name="test",
            agent_level="lead",
            max_iterations=5,
        )

        assert result.content == "Direct answer"
        assert result.iterations == 1
        assert result.tool_calls_total == 0
        assert not result.timed_out
        assert not result.max_iterations_reached

    @pytest.mark.asyncio
    @patch("src.infra.model_router.litellm.acompletion")
    async def test_single_tool_call(self, mock_acomp):
        """LLM calls one tool, then responds."""
        tc = _make_tool_call(tc_id="tc_1", name="fs_list", arguments={"path": "/tmp"})

        mock_acomp.side_effect = [
            # Iteration 1: LLM wants to call fs_list
            _make_response(content=None, tool_calls=[tc], finish_reason="tool_calls"),
            # Iteration 2: LLM gives final answer after observing tool result
            _make_response(content="Directory has 3 files."),
        ]

        from src.engine.react_loop import react_loop
        result = await react_loop(
            user_message="List /tmp",
            system_prompt="You are a file helper.",
            agent_name="test",
            agent_level="lead",
            max_iterations=5,
        )

        assert result.content == "Directory has 3 files."
        assert result.iterations == 2
        assert result.tool_calls_total == 1
        assert any(s.tool_name == "fs_list" for s in result.steps)

    @pytest.mark.asyncio
    @patch("src.infra.model_router.litellm.acompletion")
    async def test_multi_step_tools(self, mock_acomp):
        """LLM calls tools across 3 iterations."""
        tc1 = _make_tool_call(tc_id="tc_1", name="research_search", arguments={"query": "test"})
        tc2 = _make_tool_call(tc_id="tc_2", name="fs_read", arguments={"path": "/tmp/x"})
        tc3 = _make_tool_call(tc_id="tc_3", name="memory_search", arguments={"agent_name": "test", "query": "test"})

        mock_acomp.side_effect = [
            _make_response(content=None, tool_calls=[tc1], finish_reason="tool_calls"),
            _make_response(content=None, tool_calls=[tc2], finish_reason="tool_calls"),
            _make_response(content=None, tool_calls=[tc3], finish_reason="tool_calls"),
            _make_response(content="Synthesis of all results"),
        ]

        from src.engine.react_loop import react_loop
        result = await react_loop(
            user_message="Research and report",
            system_prompt="You are a researcher.",
            agent_name="test",
            agent_level="lead",
            max_iterations=10,
        )

        assert result.content == "Synthesis of all results"
        assert result.iterations == 4
        assert result.tool_calls_total == 3

    @pytest.mark.asyncio
    @patch("src.infra.model_router.litellm.acompletion")
    async def test_max_iterations_reached(self, mock_acomp):
        """LLM keeps calling tools until max_iterations is hit."""
        tc = _make_tool_call(tc_id="tc_loop", name="fs_list", arguments={"path": "/"})

        # Every call returns a tool call (never stops)
        mock_acomp.return_value = _make_response(
            content=None, tool_calls=[tc], finish_reason="tool_calls",
        )

        from src.engine.react_loop import react_loop
        result = await react_loop(
            user_message="Loop forever",
            system_prompt="System",
            agent_name="test",
            agent_level="lead",
            max_iterations=3,
        )

        assert result.max_iterations_reached
        assert result.iterations == 3

    @pytest.mark.asyncio
    @patch("src.infra.model_router.litellm.acompletion")
    async def test_timeout(self, mock_acomp):
        """Loop times out when execution takes too long."""
        async def slow_completion(**kwargs):
            await asyncio.sleep(0.2)
            tc = _make_tool_call(tc_id="tc_slow", name="fs_list", arguments={"path": "/"})
            return _make_response(content=None, tool_calls=[tc], finish_reason="tool_calls")

        mock_acomp.side_effect = slow_completion

        from src.engine.react_loop import react_loop
        result = await react_loop(
            user_message="Slow task",
            system_prompt="System",
            agent_name="test",
            agent_level="lead",
            max_iterations=100,
            timeout_seconds=1,
        )

        assert result.timed_out

    @pytest.mark.asyncio
    @patch("src.infra.model_router.litellm.acompletion")
    async def test_permission_denied(self, mock_acomp):
        """Intern agent tries to call a tool that requires higher permissions."""
        tc = _make_tool_call(tc_id="tc_denied", name="db_execute", arguments={"statement": "DROP TABLE users"})

        mock_acomp.side_effect = [
            _make_response(content=None, tool_calls=[tc], finish_reason="tool_calls"),
            _make_response(content="I couldn't execute that."),
        ]

        # Revoke MCP_EXECUTE permission from intern-level by using a custom SecurityManager
        from src.core.security import security_manager
        original_check = security_manager.check_permission

        def deny_mcp(agent_name, agent_level, permission, resource=""):
            if agent_level == "no_perm_level":
                return False
            return original_check(agent_name, agent_level, permission, resource)

        from src.engine.react_loop import react_loop
        with patch.object(security_manager, "check_permission", side_effect=deny_mcp):
            result = await react_loop(
                user_message="Drop users table",
                system_prompt="System",
                agent_name="bad_agent",
                agent_level="no_perm_level",
                max_iterations=5,
            )

        # The denied step should be recorded
        denied_steps = [s for s in result.steps if not s.success and "Permission denied" in s.error]
        assert len(denied_steps) >= 1

    @pytest.mark.asyncio
    @patch("src.infra.model_router.litellm.acompletion")
    async def test_tool_not_found(self, mock_acomp):
        """LLM calls a tool that doesn't exist in the registry."""
        tc = _make_tool_call(tc_id="tc_ghost", name="nonexistent_tool", arguments={})

        mock_acomp.side_effect = [
            _make_response(content=None, tool_calls=[tc], finish_reason="tool_calls"),
            _make_response(content="Tool wasn't found, here's my best answer."),
        ]

        from src.engine.react_loop import react_loop
        result = await react_loop(
            user_message="Use the magic tool",
            system_prompt="System",
            agent_name="test",
            agent_level="lead",
            max_iterations=5,
        )

        # Should still produce a final answer
        assert result.content
        # The failed step should be recorded
        failed_steps = [s for s in result.steps if not s.success]
        assert len(failed_steps) >= 1


# ============================================
# 4. BaseAgent Integration Tests
# ============================================

class TestBaseAgentReAct:
    def test_config_backward_compat(self):
        """AgentConfig still works with original fields."""
        config = AgentConfig(name="compat", role="Test Agent")
        assert config.level == "specialist"
        assert config.model == "gemini-2.5-flash"
        assert config.model_chain == "default"
        assert config.temperature == 0.7

    @pytest.mark.asyncio
    @patch("src.infra.model_router.litellm.acompletion")
    async def test_process_shape(self, mock_acomp):
        """Process result has expected keys."""
        mock_acomp.return_value = _make_response(content="Agent reply")

        config = AgentConfig(name="shape_test", role="Test")
        agent = BaseAgent(config=config)
        result = await agent.process("Hello")

        assert "content" in result
        assert "agent" in result
        assert "model" in result
        assert "rate_limited" in result
        assert "usage" in result
        assert result["agent"] == "shape_test"
        assert result["rate_limited"] is False

    @pytest.mark.asyncio
    @patch("src.skills.mcp_tools.MCPToolRegistry.list_tools", return_value=[])
    @patch("src.infra.model_router.litellm.acompletion")
    async def test_no_tools_fallback(self, mock_acomp, mock_list):
        """When no tools are available, uses simple path."""
        mock_acomp.return_value = _make_response(content="Simple reply")

        config = AgentConfig(name="simple_agent", role="Test")
        agent = BaseAgent(config=config)
        result = await agent.process("Hi")

        assert result["content"] == "Simple reply"
        # Simple path doesn't include react_steps
        assert "react_steps" not in result

    @pytest.mark.asyncio
    @patch("src.infra.model_router.litellm.acompletion")
    async def test_react_path_includes_steps(self, mock_acomp):
        """When tools are available, uses ReAct path and returns steps."""
        tc = _make_tool_call(tc_id="tc_base", name="fs_list", arguments={"path": "/tmp"})
        mock_acomp.side_effect = [
            _make_response(content=None, tool_calls=[tc], finish_reason="tool_calls"),
            _make_response(content="Listed files"),
        ]

        config = AgentConfig(name="react_agent", role="Test", level="lead")
        agent = BaseAgent(config=config)
        result = await agent.process("List files")

        assert result["content"] == "Listed files"
        assert "react_steps" in result
        assert "iterations" in result
        assert result["iterations"] == 2


# ============================================
# 5. Model Name Mapping Tests
# ============================================

    @pytest.mark.asyncio
    async def test_dynamic_config_loading(self):
        """Test that ModelRouter loads mappings from settings."""
        from src.core.config import settings
        from src.infra.model_router import ModelRouter

        settings.MODEL_MAPPINGS = json.dumps({"my-custom-model": "litellm/custom"})
        settings.MODEL_FALLBACKS = json.dumps({"custom-chain": ["my-custom-model"]})

        router = ModelRouter()
        assert router.model_map["my-custom-model"] == "litellm/custom"
        assert router.fallback_chains["custom-chain"] == ["my-custom-model"]

        # Cleanup
        settings.MODEL_MAPPINGS = "{}"
        settings.MODEL_FALLBACKS = "{}"

    @pytest.mark.asyncio
    @patch("src.infra.model_router.litellm.acompletion")
    async def test_dynamic_failover(self, mock_acomp):
        """Test that dynamic chains work for failover."""
        from src.core.config import settings
        from src.infra.model_router import ModelRouter

        settings.MODEL_FALLBACKS = json.dumps({"test-chain": ["m1", "m2"]})
        mock_acomp.side_effect = [
            Exception("m1 failed"),
            _make_response(content="m2 success")
        ]

        router = ModelRouter()
        result = await router.generate("test", chain="test-chain")

        assert result["content"] == "m2 success"
        assert mock_acomp.call_count == 2

        # Cleanup
        settings.MODEL_FALLBACKS = "{}"
