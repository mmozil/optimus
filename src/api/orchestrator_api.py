"""
Agent Optimus — Orchestrator API (FASE 0 #24: Orchestrator).
REST endpoints for multi-agent pipeline orchestration.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.core.orchestrator import ExecutionMode, OrchestratorStep, orchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/orchestrator", tags=["orchestrator"])


# ============================================
# Request/Response Models
# ============================================


class StepDefinition(BaseModel):
    """Definition of a single orchestration step."""

    name: str = Field(..., description="Step name")
    agent_name: str = Field(..., description="Agent to execute this step")
    prompt_template: str = Field(
        "{input}", description="Prompt template with {input}, {context}, etc."
    )
    timeout: float = Field(60.0, description="Timeout in seconds", ge=1, le=300)


class RegisterPipelineRequest(BaseModel):
    """Request to register a named pipeline."""

    name: str = Field(..., description="Pipeline name")
    steps: list[StepDefinition] = Field(..., description="Pipeline steps")


class ExecutePipelineRequest(BaseModel):
    """Request to execute a pipeline."""

    input_data: str = Field(..., description="Initial input data")
    context: dict | None = Field(None, description="Optional context")
    mode: str = Field("sequential", description="Execution mode: sequential|parallel|loop")


class RunAdHocRequest(BaseModel):
    """Request to run ad-hoc pipeline."""

    steps: list[StepDefinition] = Field(..., description="Pipeline steps")
    input_data: str = Field(..., description="Initial input data")
    context: dict | None = Field(None, description="Optional context")


class PipelineResultResponse(BaseModel):
    """Response containing pipeline execution result."""

    success: bool
    steps_executed: int
    outputs: dict[str, Any]
    final_output: str
    total_tokens: int
    errors: list[str]


class PipelineInfo(BaseModel):
    """Information about a registered pipeline."""

    name: str
    steps: int


# ============================================
# API Endpoints
# ============================================


@router.post("/pipelines")
async def register_pipeline(request: RegisterPipelineRequest) -> dict[str, Any]:
    """
    Register a named pipeline for reuse.

    Pipelines can be executed later by name without redefining steps.
    """
    try:
        # Convert StepDefinition to OrchestratorStep
        steps = [
            OrchestratorStep(
                name=step.name,
                agent_name=step.agent_name,
                prompt_template=step.prompt_template,
                timeout=step.timeout,
            )
            for step in request.steps
        ]

        orchestrator.register_pipeline(request.name, steps)

        logger.info(f"Pipeline registered: {request.name} with {len(steps)} steps")

        return {
            "success": True,
            "name": request.name,
            "steps": len(steps),
            "message": f"Pipeline '{request.name}' registered successfully",
        }

    except Exception as e:
        logger.error(f"Register pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=f"Register pipeline failed: {e}")


@router.get("/pipelines", response_model=list[PipelineInfo])
async def list_pipelines() -> list[PipelineInfo]:
    """
    List all registered pipelines.

    Returns pipeline names and step counts.
    """
    try:
        pipelines = orchestrator.list_pipelines()

        logger.info(f"Listed {len(pipelines)} registered pipelines")

        return [
            PipelineInfo(name=p["name"], steps=p["steps"])
            for p in pipelines
        ]

    except Exception as e:
        logger.error(f"List pipelines failed: {e}")
        raise HTTPException(status_code=500, detail=f"List pipelines failed: {e}")


@router.delete("/pipelines/{pipeline_name}")
async def delete_pipeline(pipeline_name: str) -> dict[str, Any]:
    """
    Delete a registered pipeline.

    Returns 404 if pipeline not found.
    """
    try:
        if pipeline_name not in orchestrator._pipelines:
            raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_name}' not found")

        del orchestrator._pipelines[pipeline_name]

        logger.info(f"Pipeline deleted: {pipeline_name}")

        return {
            "success": True,
            "name": pipeline_name,
            "message": f"Pipeline '{pipeline_name}' deleted successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=f"Delete pipeline failed: {e}")


@router.post("/execute/{pipeline_name}", response_model=PipelineResultResponse)
async def execute_pipeline(
    pipeline_name: str,
    request: ExecutePipelineRequest,
) -> PipelineResultResponse:
    """
    Execute a registered pipeline.

    Supports sequential, parallel, and loop execution modes.
    """
    try:
        # Parse execution mode
        try:
            mode = ExecutionMode(request.mode.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid mode: {request.mode}. Use: sequential, parallel, or loop"
            )

        # Execute pipeline
        result = await orchestrator.execute(
            pipeline_name=pipeline_name,
            input_data=request.input_data,
            context=request.context,
            mode=mode,
        )

        logger.info(
            f"Pipeline executed: {pipeline_name} ({request.mode}), success={result.success}"
        )

        return PipelineResultResponse(
            success=result.success,
            steps_executed=result.steps_executed,
            outputs=result.outputs,
            final_output=result.final_output,
            total_tokens=result.total_tokens,
            errors=result.errors,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Execute pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=f"Execute pipeline failed: {e}")


@router.post("/run/sequential", response_model=PipelineResultResponse)
async def run_sequential(request: RunAdHocRequest) -> PipelineResultResponse:
    """
    Run an ad-hoc sequential pipeline.

    Steps execute one after another, piping output to next input.
    """
    try:
        # Convert StepDefinition to OrchestratorStep
        steps = [
            OrchestratorStep(
                name=step.name,
                agent_name=step.agent_name,
                prompt_template=step.prompt_template,
                timeout=step.timeout,
            )
            for step in request.steps
        ]

        # Execute
        result = await orchestrator.run_sequential(
            steps=steps,
            input_data=request.input_data,
            context=request.context,
        )

        logger.info(f"Sequential pipeline executed: {len(steps)} steps, success={result.success}")

        return PipelineResultResponse(
            success=result.success,
            steps_executed=result.steps_executed,
            outputs=result.outputs,
            final_output=result.final_output,
            total_tokens=result.total_tokens,
            errors=result.errors,
        )

    except Exception as e:
        logger.error(f"Run sequential failed: {e}")
        raise HTTPException(status_code=500, detail=f"Run sequential failed: {e}")


@router.post("/run/parallel", response_model=PipelineResultResponse)
async def run_parallel(request: RunAdHocRequest) -> PipelineResultResponse:
    """
    Run an ad-hoc parallel pipeline.

    All steps execute simultaneously, outputs are combined.
    """
    try:
        # Convert StepDefinition to OrchestratorStep
        steps = [
            OrchestratorStep(
                name=step.name,
                agent_name=step.agent_name,
                prompt_template=step.prompt_template,
                timeout=step.timeout,
            )
            for step in request.steps
        ]

        # Execute
        result = await orchestrator.run_parallel(
            steps=steps,
            input_data=request.input_data,
            context=request.context,
        )

        logger.info(f"Parallel pipeline executed: {len(steps)} steps, success={result.success}")

        return PipelineResultResponse(
            success=result.success,
            steps_executed=result.steps_executed,
            outputs=result.outputs,
            final_output=result.final_output,
            total_tokens=result.total_tokens,
            errors=result.errors,
        )

    except Exception as e:
        logger.error(f"Run parallel failed: {e}")
        raise HTTPException(status_code=500, detail=f"Run parallel failed: {e}")
