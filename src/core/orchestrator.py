"""
Agent Optimus — ADK Orchestrator.
Google Agent Development Kit integration for agent orchestration.
Provides SequentialAgent, ParallelAgent, and LoopAgent patterns.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class ExecutionMode(str, Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    LOOP = "loop"


@dataclass
class OrchestratorStep:
    """A single step in an orchestration pipeline."""
    name: str
    agent_name: str  # Agent from AgentFactory to execute
    prompt_template: str = "{input}"  # Template with {input}, {context}, etc.
    transform: Callable | None = None  # Optional output transformer
    condition: Callable | None = None  # Skip step if returns False
    timeout: float = 60.0  # Seconds


@dataclass
class PipelineResult:
    """Result from executing an orchestration pipeline."""
    success: bool = True
    steps_executed: int = 0
    outputs: dict[str, Any] = field(default_factory=dict)  # step_name → output
    final_output: str = ""
    total_tokens: int = 0
    errors: list[str] = field(default_factory=list)


class Orchestrator:
    """
    ADK-inspired orchestration layer.
    Manages multi-agent pipelines with Sequential, Parallel, and Loop patterns.
    """

    def __init__(self):
        self._pipelines: dict[str, list[OrchestratorStep]] = {}

    def register_pipeline(self, name: str, steps: list[OrchestratorStep]):
        """Register a named pipeline."""
        self._pipelines[name] = steps
        logger.info(f"Pipeline registered: '{name}' with {len(steps)} steps")

    async def execute(
        self,
        pipeline_name: str,
        input_data: str,
        context: dict | None = None,
        mode: ExecutionMode = ExecutionMode.SEQUENTIAL,
    ) -> PipelineResult:
        """Execute a registered pipeline."""
        steps = self._pipelines.get(pipeline_name)
        if not steps:
            return PipelineResult(success=False, errors=[f"Pipeline '{pipeline_name}' not found"])

        logger.info(f"Executing pipeline '{pipeline_name}' ({mode.value})", extra={
            "props": {"steps": len(steps), "mode": mode.value}
        })

        if mode == ExecutionMode.SEQUENTIAL:
            return await self._execute_sequential(steps, input_data, context)
        elif mode == ExecutionMode.PARALLEL:
            return await self._execute_parallel(steps, input_data, context)
        elif mode == ExecutionMode.LOOP:
            return await self._execute_loop(steps, input_data, context)

        return PipelineResult(success=False, errors=[f"Unknown mode: {mode}"])

    async def run_sequential(
        self,
        steps: list[OrchestratorStep],
        input_data: str,
        context: dict | None = None,
    ) -> PipelineResult:
        """Run an ad-hoc sequential pipeline (no registration needed)."""
        return await self._execute_sequential(steps, input_data, context)

    async def run_parallel(
        self,
        steps: list[OrchestratorStep],
        input_data: str,
        context: dict | None = None,
    ) -> PipelineResult:
        """Run an ad-hoc parallel pipeline."""
        return await self._execute_parallel(steps, input_data, context)

    # ============================================
    # Execution Engines
    # ============================================

    async def _execute_sequential(
        self, steps: list[OrchestratorStep], input_data: str, context: dict | None
    ) -> PipelineResult:
        """Execute steps one after another, piping output to next input."""
        from src.core.agent_factory import AgentFactory

        result = PipelineResult()
        current_input = input_data

        for step in steps:
            # Check condition
            if step.condition and not step.condition(current_input, context):
                logger.debug(f"Step '{step.name}' skipped (condition=False)")
                continue

            agent = AgentFactory.get(step.agent_name)
            if not agent:
                result.errors.append(f"Agent '{step.agent_name}' not found for step '{step.name}'")
                continue

            try:
                prompt = step.prompt_template.format(
                    input=current_input,
                    context=str(context or {}),
                )

                response = await asyncio.wait_for(
                    agent.process(prompt, context),
                    timeout=step.timeout,
                )

                output = response.get("content", "")

                # Apply transform if provided
                if step.transform:
                    output = step.transform(output)

                result.outputs[step.name] = output
                result.steps_executed += 1
                result.total_tokens += response.get("tokens", 0)

                # Pipe output as next input
                current_input = output

                logger.debug(f"Step '{step.name}' completed ({len(output)} chars)")

            except asyncio.TimeoutError:
                result.errors.append(f"Step '{step.name}' timed out ({step.timeout}s)")
                result.success = False
                break
            except Exception as e:
                result.errors.append(f"Step '{step.name}' failed: {e}")
                result.success = False
                break

        result.final_output = current_input
        return result

    async def _execute_parallel(
        self, steps: list[OrchestratorStep], input_data: str, context: dict | None
    ) -> PipelineResult:
        """Execute all steps in parallel, collect all outputs."""
        from src.core.agent_factory import AgentFactory

        result = PipelineResult()

        async def run_step(step: OrchestratorStep) -> tuple[str, Any]:
            if step.condition and not step.condition(input_data, context):
                return step.name, None

            agent = AgentFactory.get(step.agent_name)
            if not agent:
                return step.name, f"ERROR: Agent '{step.agent_name}' not found"

            prompt = step.prompt_template.format(input=input_data, context=str(context or {}))
            response = await asyncio.wait_for(
                agent.process(prompt, context),
                timeout=step.timeout,
            )
            output = response.get("content", "")
            if step.transform:
                output = step.transform(output)
            return step.name, output

        # Execute all in parallel
        tasks = [run_step(step) for step in steps]
        outcomes = await asyncio.gather(*tasks, return_exceptions=True)

        for outcome in outcomes:
            if isinstance(outcome, Exception):
                result.errors.append(str(outcome))
            elif isinstance(outcome, tuple):
                name, output = outcome
                if output is not None:
                    result.outputs[name] = output
                    result.steps_executed += 1

        # Combine all outputs
        result.final_output = "\n\n---\n\n".join(
            f"## {name}\n{output}" for name, output in result.outputs.items()
        )

        return result

    async def _execute_loop(
        self, steps: list[OrchestratorStep], input_data: str, context: dict | None,
        max_iterations: int = 5,
    ) -> PipelineResult:
        """Execute steps in a loop until a condition or max iterations."""
        result = PipelineResult()
        current_input = input_data

        for i in range(max_iterations):
            loop_result = await self._execute_sequential(steps, current_input, context)
            result.steps_executed += loop_result.steps_executed
            result.total_tokens += loop_result.total_tokens

            if not loop_result.success or loop_result.errors:
                result.errors.extend(loop_result.errors)
                break

            # Check if output changed (convergence)
            if loop_result.final_output == current_input:
                logger.info(f"Loop converged after {i + 1} iterations")
                break

            current_input = loop_result.final_output
            result.outputs[f"iteration_{i + 1}"] = current_input

        result.final_output = current_input
        return result

    def list_pipelines(self) -> list[dict]:
        """List registered pipelines."""
        return [
            {"name": name, "steps": len(steps)}
            for name, steps in self._pipelines.items()
        ]


# Singleton
orchestrator = Orchestrator()
