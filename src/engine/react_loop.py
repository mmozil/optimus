"""
Agent Optimus — ReAct Loop Engine (Phase 12).
Implements the Reason-Act-Observe loop for autonomous tool calling.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field

from src.core.config import settings
from src.core.security import Permission, security_manager
from src.infra.metrics import MCP_TOOL_CALLS, MCP_TOOL_ERRORS, MCP_TOOL_LATENCY
from src.engine.uncertainty import uncertainty_quantifier  # FASE 0 #2

logger = logging.getLogger(__name__)


# ============================================
# Dataclasses
# ============================================

@dataclass
class ReActStep:
    """Records a single step in the ReAct loop."""
    iteration: int
    type: str  # "reason" | "act" | "observe"
    tool_name: str = ""
    tool_args: dict = field(default_factory=dict)
    result: str = ""
    success: bool = True
    duration_ms: float = 0.0
    error: str = ""


@dataclass
class ReActResult:
    """Final result of a ReAct loop execution."""
    content: str
    model: str = ""
    usage: dict = field(default_factory=dict)
    steps: list[ReActStep] = field(default_factory=list)
    iterations: int = 0
    timed_out: bool = False
    max_iterations_reached: bool = False
    tool_calls_total: int = 0
    uncertainty: dict | None = None  # FASE 0 #2: Uncertainty quantification metadata


# ============================================
# ReAct Loop
# ============================================

async def react_loop(
    user_message: str,
    system_prompt: str,
    context: dict | None = None,
    agent_name: str = "agent",
    agent_level: str = "specialist",
    model_chain: str = "default",
    temperature: float = 0.7,
    max_tokens: int = 4096,
    max_iterations: int | None = None,
    timeout_seconds: int | None = None,
) -> ReActResult:
    """
    Execute a full Reason-Act-Observe loop.

    1. Build messages = [system, user+context]
    2. Get tool_declarations for agent_level from MCPToolRegistry
    3. FOR iteration in 1..max_iterations:
       a. Check timeout
       b. REASON: call model_router.generate_with_history(messages, tools=declarations)
       c. If no tool_calls → return final answer
       d. ACT: for each tool_call: check permission, execute via MCPToolRegistry
       e. OBSERVE: append tool results to messages
    4. Return max-iterations-reached result
    """
    # Lazy imports to avoid circular dependencies
    from src.infra.model_router import model_router
    from src.infra.tool_declarations import get_tool_declarations
    from src.skills.mcp_tools import mcp_tools

    if max_iterations is None:
        max_iterations = settings.REACT_MAX_ITERATIONS
    if timeout_seconds is None:
        timeout_seconds = settings.REACT_TIMEOUT_SECONDS

    # 1. Build initial messages
    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
    ]

    # Inject actual history from context
    if context and context.get("history"):
        messages.extend(_inject_history(context["history"]))

    # Build user content without embedded history (it's now in messages)
    user_content = _build_user_content(user_message, context)
    
    # Support multimodal: if attachments exist, format as list of parts
    if context and context.get("attachments"):
        content_parts = [{"type": "text", "text": user_content}]
        for att in context["attachments"]:
            mime = att.get("mime_type", "")
            if mime and ("image" in mime or "pdf" in mime):
                content_parts.append({
                    "type": "image_url",
                    "image_url": {"url": att.get("public_url", "")}
                })
        messages.append({"role": "user", "content": content_parts})
    else:
        messages.append({"role": "user", "content": user_content})

    # 2. Get tool declarations
    declarations = get_tool_declarations(mcp_tools, agent_level=agent_level)

    steps: list[ReActStep] = []
    total_usage: dict = {"prompt_tokens": 0, "completion_tokens": 0}
    last_model = ""
    tool_calls_total = 0
    start_time = time.monotonic()

    # 3. ReAct loop
    from src.infra.tracing import trace_span, trace_event

    for iteration in range(1, max_iterations + 1):
        # a. Check timeout
        elapsed = time.monotonic() - start_time
        if elapsed > timeout_seconds:
            logger.warning(f"ReAct loop timed out after {elapsed:.1f}s", extra={
                "props": {"agent": agent_name, "iterations": iteration}
            })
            return ReActResult(
                content=_extract_last_content(messages),
                model=last_model,
                usage=total_usage,
                steps=steps,
                iterations=iteration,
                timed_out=True,
                tool_calls_total=tool_calls_total,
            )

        # b. REASON: call LLM
        trace_event(f"react.reason", {
            "agent": agent_name, "iteration": str(iteration),
        })
        try:
            result = await model_router.generate_with_history(
                messages=messages,
                chain=model_chain,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=declarations if declarations else None,
            )
        except Exception as e:
            logger.error(f"ReAct LLM call failed: {e}", extra={
                "props": {"agent": agent_name, "iteration": iteration}
            })
            return ReActResult(
                content=f"Erro no processamento: {e}",
                model=last_model,
                usage=total_usage,
                steps=steps,
                iterations=iteration,
                tool_calls_total=tool_calls_total,
            )

        if not isinstance(result, dict):
            logger.error(f"ReAct unexpected result type: {type(result).__name__} = {str(result)[:300]}")
            return ReActResult(
                content=str(result),
                model=last_model,
                usage=total_usage,
                steps=steps,
                iterations=iteration,
                tool_calls_total=tool_calls_total,
            )

        last_model = result.get("model", "")
        _accumulate_usage(total_usage, result.get("usage", {}))

        # Append assistant message to history
        raw_message = result.get("raw_message")
        if raw_message:
            messages.append(_raw_message_to_dict(raw_message))

        tool_calls = result.get("tool_calls", [])

        # c. If no tool_calls → return final answer
        if not tool_calls:
            steps.append(ReActStep(
                iteration=iteration,
                type="reason",
                result=result.get("content", ""),
            ))

            # FASE 0 #2: Quantify uncertainty before returning
            final_content = result.get("content", "")
            uncertainty_result = None
            try:
                uncertainty_result = await uncertainty_quantifier.quantify(
                    query=user_message,
                    response=final_content,
                    agent_name=agent_name,
                    db_session=None,  # TODO: pass db_session from context if available
                )

                # Add uncertainty metadata to result
                uncertainty_dict = {
                    "confidence": uncertainty_result.confidence,
                    "calibrated_confidence": uncertainty_result.calibrated_confidence,
                    "risk_level": uncertainty_result.risk_level,
                    "recommendation": uncertainty_result.recommendation,
                }

                # Note: recommendation stays in uncertainty metadata only.
                # Never prepend warnings to content — users shouldn't see internal confidence scores.

            except Exception as e:
                logger.warning(f"Uncertainty quantification failed: {e}")
                uncertainty_dict = None

            return ReActResult(
                content=final_content,
                model=last_model,
                usage=total_usage,
                steps=steps,
                iterations=iteration,
                tool_calls_total=tool_calls_total,
                uncertainty=uncertainty_dict,
            )

        # d. ACT: execute each tool call (with self-correction)
        for tc in tool_calls:
            tool_name = tc["name"]
            tool_args = tc["arguments"]
            tool_call_id = tc["id"]
            tool_calls_total += 1

            step = ReActStep(
                iteration=iteration,
                type="act",
                tool_name=tool_name,
                tool_args=tool_args,
            )

            step_start = time.monotonic()

            # Check permission
            has_perm = security_manager.check_permission(
                agent_name=agent_name,
                agent_level=agent_level,
                permission=Permission.MCP_EXECUTE,
                resource=tool_name,
            )

            if not has_perm:
                step.success = False
                step.error = f"Permission denied for {agent_name} ({agent_level}) to execute {tool_name}"
                step.duration_ms = (time.monotonic() - step_start) * 1000
                steps.append(step)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": f"Error: Permission denied. Agent '{agent_name}' ({agent_level}) cannot execute '{tool_name}'.",
                })
                continue

            # FASE 0 #28: Check if tool needs user confirmation (Human-in-the-Loop)
            from src.core.confirmation_service import confirmation_service

            user_id = context.get("user_id", "") if context else ""

            # FASE 11: Jarvis Mode — autonomous_executor bypass for low/medium risk tools
            _needs_confirmation = confirmation_service.should_confirm(tool_name, user_id)
            if _needs_confirmation:
                from src.engine.autonomous_executor import (
                    ExecutionResult,
                    ExecutionStatus,
                    autonomous_executor,
                )

                _task_label = f"{tool_name} {json.dumps(tool_args, ensure_ascii=False)[:80]}"
                if autonomous_executor.should_auto_execute(_task_label, confidence=0.85):
                    # Auto-execute: log to audit trail and fall through to execution
                    autonomous_executor._audit(ExecutionResult(
                        task=_task_label,
                        confidence=0.85,
                        risk=autonomous_executor.classify_risk(_task_label),
                        agent_name=agent_name,
                        status=ExecutionStatus.SUCCESS,
                        output=f"Auto-bypassed confirmation for tool '{tool_name}'",
                    ))
                    autonomous_executor._today_count += 1
                    logger.info(
                        f"FASE 11: Auto-executed '{tool_name}' (bypassed confirmation, "
                        f"risk={autonomous_executor.classify_risk(_task_label).value})",
                        extra={"props": {"agent": agent_name, "tool": tool_name}},
                    )
                    _needs_confirmation = False  # Allow fall-through to execution

            if _needs_confirmation:
                step.success = False
                step.error = f"Tool '{tool_name}' requires user confirmation (HIGH/CRITICAL risk)"
                step.duration_ms = (time.monotonic() - step_start) * 1000
                steps.append(step)

                # Inform agent that confirmation is needed
                confirmation_msg = (
                    f"⚠️ AÇÃO BLOQUEADA: A ferramenta '{tool_name}' requer confirmação do usuário antes de ser executada.\n\n"
                    f"**Motivo:** Esta é uma ação de alto risco ou irreversível "
                    f"(risco: {confirmation_service.get_risk_level(tool_name).value}).\n\n"
                    f"**Próximos passos:**\n"
                    f"1. Informe o usuário sobre a ação que você pretende executar\n"
                    f"2. Explique claramente o que '{tool_name}' fará e quais os impactos\n"
                    f"3. Aguarde aprovação explícita do usuário antes de tentar novamente\n\n"
                    f"**Argumentos que você tentou usar:** {json.dumps(tool_args, ensure_ascii=False)}\n\n"
                    f"Não tente executar esta ação sem confirmação. Explique ao usuário e peça aprovação."
                )

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": confirmation_msg,
                })

                logger.info(
                    f"Tool execution blocked: {tool_name} requires confirmation",
                    extra={"props": {
                        "agent": agent_name,
                        "tool": tool_name,
                        "risk": confirmation_service.get_risk_level(tool_name).value
                    }}
                )
                continue

            # Execute tool
            try:
                MCP_TOOL_CALLS.labels(
                    tool_name=tool_name,
                    category=_get_tool_category(mcp_tools, tool_name),
                ).inc()

                # FASE 4: inject user_id so Google tools can fetch OAuth tokens
                mcp_tools._user_id = user_id

                tool_result = await mcp_tools.execute(tool_name, tool_args, agent_name=agent_name)

                step.duration_ms = (time.monotonic() - step_start) * 1000
                MCP_TOOL_LATENCY.labels(tool_name=tool_name).observe(step.duration_ms / 1000)

                if tool_result.success:
                    step.result = str(tool_result.output)
                    step.success = True
                else:
                    step.success = False
                    step.error = tool_result.error or "Unknown error"
                    MCP_TOOL_ERRORS.labels(tool_name=tool_name).inc()

            except Exception as e:
                step.duration_ms = (time.monotonic() - step_start) * 1000
                step.success = False
                step.error = str(e)
                MCP_TOOL_ERRORS.labels(tool_name=tool_name).inc()

            steps.append(step)

            # e. OBSERVE: append tool result to messages
            if step.success:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": step.result,
                })
            else:
                # Self-Correction: give the agent explicit error context
                # so it can analyze the failure and try a different approach
                correction_msg = (
                    f"⚠️ TOOL FAILED: '{tool_name}' returned an error:\n"
                    f"Error: {step.error}\n"
                    f"Arguments used: {json.dumps(tool_args, ensure_ascii=False)}\n\n"
                    f"Analyze this error carefully. Consider:\n"
                    f"1. Are the parameters correct? (types, values, format)\n"
                    f"2. Should you try a different tool instead?\n"
                    f"3. Do you need more information before retrying?\n"
                    f"Adjust your approach and try again, or explain if the task cannot be completed."
                )
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": correction_msg,
                })
                logger.info(
                    f"Self-correction triggered for {tool_name} (iter {iteration})",
                    extra={"props": {"agent": agent_name, "error": step.error[:200]}}
                )

    # 4. Max iterations reached
    logger.warning(f"ReAct loop reached max iterations ({max_iterations})", extra={
        "props": {"agent": agent_name}
    })
    return ReActResult(
        content=_extract_last_content(messages),
        model=last_model,
        usage=total_usage,
        steps=steps,
        iterations=max_iterations,
        max_iterations_reached=True,
        tool_calls_total=tool_calls_total,
    )


# ============================================
# Helpers
# ============================================

def _build_user_content(message: str, context: dict | None) -> str:
    """Build user message content with optional context."""
    parts = []

    if context:
        # Inject user identity + preferences so agent can personalize responses
        user_name = context.get("user_name")
        user_email = context.get("user_email")
        language = context.get("language")
        comm_style = context.get("communication_style")
        agent_name = context.get("agent_name")

        identity_parts = []
        if user_name or user_email:
            identity_parts.append(f"Nome: {user_name or user_email}")
        if language:
            identity_parts.append(f"Idioma preferido: {language}")
        if comm_style:
            identity_parts.append(f"Estilo: {comm_style}")
        if agent_name:
            identity_parts.append(f"Chama o agente de: {agent_name}")

        if identity_parts:
            parts.append("[Contexto do Usuário: " + " | ".join(identity_parts) + "]")

        if context.get("task"):
            parts.append(f"## Task Atual\n{context['task']}")

        if context.get("working_memory"):
            parts.append(f"## Memória de Trabalho\n{context['working_memory']}")

    parts.append(message)
    return "\n\n".join(parts)


def _inject_history(history: list[dict]) -> list[dict]:
    """Convert persistent messages to LLM roles."""
    injected = []
    for msg in history[-10:]:  # Last 10 messages for context window
        role = msg.get("role", "user")
        content = msg.get("content", "")
        # Normalize role for LLM
        if role == "assistant":
            injected.append({"role": "assistant", "content": content})
        else:
            injected.append({"role": "user", "content": content})
    return injected


def _raw_message_to_dict(raw_message) -> dict:
    """Convert a raw LiteLLM message object to a dict for message history."""
    msg: dict = {"role": "assistant"}

    if raw_message.content:
        msg["content"] = raw_message.content

    if raw_message.tool_calls:
        msg["tool_calls"] = []
        for tc in raw_message.tool_calls:
            msg["tool_calls"].append({
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments if isinstance(tc.function.arguments, str) else json.dumps(tc.function.arguments),
                },
            })

    return msg


def _accumulate_usage(total: dict, new: dict) -> None:
    """Accumulate token usage across iterations."""
    total["prompt_tokens"] = total.get("prompt_tokens", 0) + new.get("prompt_tokens", 0)
    total["completion_tokens"] = total.get("completion_tokens", 0) + new.get("completion_tokens", 0)


def _extract_last_content(messages: list[dict]) -> str:
    """Extract the last assistant content from messages (for timeout/max-iter fallback)."""
    for msg in reversed(messages):
        if msg.get("role") == "assistant" and msg.get("content"):
            return msg["content"]
    return "Não foi possível gerar uma resposta completa."


def _get_tool_category(registry, tool_name: str) -> str:
    """Get the category of a tool for metrics labeling."""
    tool = registry.get(tool_name)
    return tool.category if tool else "unknown"
