"""
Agent Optimus — Code Execution Sandbox.
Provides a secure(ish) environment to execute Python and Bash code.
Includes timeouts, resource limits, and output sanitization.
"""

import asyncio
import logging
import shlex
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

@dataclass
class SandboxResult:
    """Result of code execution in the sandbox."""
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: float

class CodeSandbox:
    """
    Manages isolated execution of code blocks.
    In this version, it uses local subprocesses with strict timeouts.
    Prepared for future Docker/E2B integration.
    """

    def __init__(self, timeout: int = 30, max_output_size: int = 10_000):
        self.timeout = timeout
        self.max_output_size = max_output_size

    async def execute_python(self, code: str) -> SandboxResult:
        """Execute Python code and return the result."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as tmp:
            tmp.write(code)
            tmp_path = Path(tmp.name)

        try:
            # Use current python executable
            cmd = [sys.executable, str(tmp_path)]
            return await self._run_process(cmd)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    async def execute_bash(self, command: str) -> SandboxResult:
        """Execute Bash/Shell command and return the result."""
        # On Windows, we use 'cmd /c' if bash isn't available, but roadmap says 'bash'
        # Let's try to be smart about OS
        if sys.platform == "win32":
            # Check if bash is in path (git bash, wsl, etc)
            cmd = ["bash", "-c", command]
        else:
            cmd = ["bash", "-c", command]
            
        return await self._run_process(cmd)

    async def _run_process(self, cmd: list[str]) -> SandboxResult:
        """Internal helper to run subprocesses with timeout."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self.timeout)
                exit_code = process.returncode or 0
            except asyncio.TimeoutError:
                # Terminate timed out process
                try:
                    process.terminate()
                    await process.wait()
                except:
                    pass
                return SandboxResult(
                    success=False,
                    stdout="",
                    stderr=f"Execution timed out after {self.timeout}s",
                    exit_code=-1,
                    duration_ms=(asyncio.get_event_loop().time() - start_time) * 1000
                )

            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            # Decode and sanitize output
            out_str = stdout.decode(errors="replace")
            err_str = stderr.decode(errors="replace")

            if len(out_str) > self.max_output_size:
                out_str = out_str[:self.max_output_size] + "\n... [Output truncated]"

            return SandboxResult(
                success=exit_code == 0,
                stdout=out_str,
                stderr=err_str,
                exit_code=exit_code,
                duration_ms=duration_ms
            )

        except Exception as e:
            logger.error(f"Sandbox execution error: {e}")
            return SandboxResult(
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                duration_ms=(asyncio.get_event_loop().time() - start_time) * 1000
            )

# Singleton instances
code_sandbox = CodeSandbox()
