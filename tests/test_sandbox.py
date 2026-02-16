"""
Tests for Code Execution Sandbox.
"""

import pytest
import asyncio
from src.infra.sandbox import code_sandbox

@pytest.mark.asyncio
async def test_python_success():
    """Test successful Python execution."""
    code = "print('Hello, Optimus!')\nprint(2 + 2)"
    result = await code_sandbox.execute_python(code)
    
    assert result.success is True
    assert "Hello, Optimus!" in result.stdout
    assert "4" in result.stdout
    assert result.exit_code == 0
    assert result.duration_ms > 0

@pytest.mark.asyncio
async def test_python_error():
    """Test Python execution with syntax error."""
    code = "this is not valid python"
    result = await code_sandbox.execute_python(code)
    
    assert result.success is False
    assert result.exit_code != 0
    assert "SyntaxError" in result.stderr or "NameError" in result.stderr or "invalid syntax" in result.stderr.lower()

@pytest.mark.asyncio
async def test_python_timeout():
    """Test Python execution timeout."""
    # Set a short timeout for the test
    from src.infra.sandbox import CodeSandbox
    short_sandbox = CodeSandbox(timeout=1)
    
    code = "import time\ntime.sleep(5)"
    result = await short_sandbox.execute_python(code)
    
    assert result.success is False
    assert "timed out" in result.stderr.lower()

@pytest.mark.asyncio
async def test_bash_simple():
    """Test simple bash command."""
    # We use 'echo' which is common
    result = await code_sandbox.execute_bash("echo 'hello shell'")
    
    # If bash is not found, it won't be success but we shouldn't crash
    if result.exit_code == 0:
        assert "hello shell" in result.stdout.lower()
    else:
        # If bash is missing, verify the error/stderr contains relevant info
        error_msg = result.stderr.lower()
        # On Windows it might be in stderr or just the exception string
        assert any(kw in error_msg for kw in ["not found", "não pode encontrar", "bash", "recognized", "recognised"])

@pytest.mark.asyncio
async def test_mcp_tool_integration():
    """Test the code_execute tool through the registry."""
    from src.skills.mcp_tools import mcp_tools
    
    params = {
        "language": "python",
        "code": "print('integration test')"
    }
    result = await mcp_tools.execute("code_execute", params, agent_name="TestAgent")
    
    assert result.success is True
    assert "integration test" in result.output
    assert "Execution Result (✅ Success)" in result.output
