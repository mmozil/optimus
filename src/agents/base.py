"""
Agent Optimus — Base Agent (Agno wrapper).
Connects Agno agent with SOUL.md + memory + rate limiting.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from src.infra.model_router import model_router
from src.infra.redis_client import AgentRateLimiter

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for an agent instance."""
    name: str
    role: str
    level: str = "specialist"  # intern | specialist | lead
    model: str = "gemini-2.5-flash"
    model_chain: str = "default"  # default | complex | economy | heartbeat
    max_tokens: int = 4096
    temperature: float = 0.7
    soul_md: str = ""
    tools: list = field(default_factory=list)


class BaseAgent:
    """
    Base class for all Optimus agents.
    Wraps model_router with SOUL.md persona, rate limiting, and structured logging.
    """

    def __init__(self, config: AgentConfig, rate_limiter: AgentRateLimiter | None = None):
        self.config = config
        self.name = config.name
        self.role = config.role
        self.level = config.level
        self.rate_limiter = rate_limiter

        # Build system prompt from SOUL.md
        self._system_prompt = self._build_system_prompt()

        logger.info(f"Agent '{self.name}' initialized", extra={"props": {
            "agent": self.name, "role": self.role, "level": self.level,
            "model": config.model, "chain": config.model_chain,
        }})

    def _build_system_prompt(self) -> str:
        """Build system prompt combining SOUL.md + base instructions."""
        base = f"""Você é {self.name}, {self.role} do Agent Optimus.

## Personalidade
{self.config.soul_md or 'Sem personalidade definida.'}

## Regras Gerais
- Responda sempre em português brasileiro.
- Seja objetivo e preciso.
- Nunca invente dados. Se não sabe, diga que não sabe.
- Cite fontes quando possível.
- Seu nível é '{self.level}' — respeite os limites do seu papel.
"""
        return base

    async def process(self, message: str, context: dict | None = None, stream: bool = False) -> Any:
        """
        Process a message and return response.
        Chooses ReAct path (tools available) or simple path (no tools).
        """
        if stream:
            return self.stream_process(message, context)
        # 1. Rate limiting check
        if self.rate_limiter:
            allowed = await self.rate_limiter.can_call_llm(self.name, self.level)
            if not allowed:
                usage = await self.rate_limiter.get_usage(self.name, self.level)
                logger.warning(f"Agent '{self.name}' rate limited", extra={"props": usage})
                return {
                    "content": f"⏳ Rate limit atingido para {self.name}. Tente novamente em breve.",
                    "agent": self.name,
                    "model": "none",
                    "rate_limited": True,
                    "usage": {},
                }

        # 2. Choose path based on available tools
        from src.skills.mcp_tools import mcp_tools
        if mcp_tools.list_tools(agent_level=self.level):
            result = await self._process_react(message, context)
        else:
            result = await self._process_simple(message, context)

        # 3. Track Cost (Phase 16)
        if context and context.get("user_id") and result.get("usage"):
            from src.core.cost_tracker import cost_tracker
            # Fire and forget tracking
            import asyncio
            asyncio.create_task(cost_tracker.track_usage(
                user_id=context["user_id"],
                agent_name=self.name,
                model=result.get("model", self.config.model),
                prompt_tokens=result["usage"].get("prompt_tokens", 0),
                completion_tokens=result["usage"].get("completion_tokens", 0),
            ))

        return result

    async def _process_react(self, message: str, context: dict | None = None) -> dict:
        """Process using the ReAct loop with tool calling."""
        from src.engine.react_loop import react_loop

        try:
            result = await react_loop(
                user_message=message,
                system_prompt=self._system_prompt,
                context=context,
                agent_name=self.name,
                agent_level=self.level,
                model_chain=self.config.model_chain,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

            logger.info(f"Agent '{self.name}' responded (ReAct)", extra={"props": {
                "agent": self.name,
                "model": result.model,
                "iterations": result.iterations,
                "tool_calls": result.tool_calls_total,
            }})

            return {
                "content": result.content,
                "agent": self.name,
                "model": result.model,
                "rate_limited": False,
                "usage": result.usage,
                "react_steps": [
                    {
                        "type": s.type,
                        "tool_name": s.tool_name,
                        "success": s.success,
                        "duration_ms": s.duration_ms,
                    }
                    for s in result.steps
                ],
                "iterations": result.iterations,
            }

        except Exception as e:
            logger.error(f"Agent '{self.name}' ReAct failed: {e}", extra={"props": {
                "agent": self.name, "error": str(e),
            }})
            # Fall back to simple processing so the user still gets a response
            return await self._process_simple(message, context)

    async def _process_simple(self, message: str, context: dict | None = None) -> dict:
        """Original single-shot processing (no tools available)."""
        system_prompt = self._system_prompt
        messages = [{"role": "system", "content": system_prompt}]
        
        if context and context.get("history"):
            messages.extend(self._inject_history(context["history"]))
            
        user_content = self._build_prompt(message, context)
        
        # Check for attachments for multimodal support
        if context and context.get("attachments"):
            user_message_dict = {
                "role": "user",
                "content": self._build_multimodal_content(user_content, context["attachments"])
            }
        else:
            user_message_dict = {"role": "user", "content": user_content}
            
        messages.append(user_message_dict)

        try:
            result = await model_router.generate_with_history(
                messages=messages,
                chain=self.config.model_chain,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

            logger.info(f"Agent '{self.name}' responded", extra={"props": {
                "agent": self.name,
                "model": result["model"],
                "prompt_tokens": result["usage"].get("prompt_tokens", 0),
                "completion_tokens": result["usage"].get("completion_tokens", 0),
            }})

            return {
                "content": result["content"],
                "agent": self.name,
                "model": result["model"],
                "rate_limited": False,
                "usage": result["usage"],
            }

        except Exception as e:
            logger.error(f"Agent '{self.name}' failed", extra={"props": {
                "agent": self.name, "error": str(e),
            }})
            return {
                "content": f"❌ Erro ao processar: {e}",
                "agent": self.name,
                "model": "error",
                "rate_limited": False,
                "usage": {},
            }

    async def stream_process(self, message: str, context: dict | None = None):
        """Yield response chunks in real-time."""
        # 1. Rate limiting (Simplified for stream)
        if self.rate_limiter:
            allowed = await self.rate_limiter.can_call_llm(self.name, self.level)
            if not allowed:
                yield {"type": "error", "content": "Rate limit atingido."}
                return

        # 2. Choose path
        from src.skills.mcp_tools import mcp_tools
        if mcp_tools.list_tools(agent_level=self.level):
            async for chunk in self._stream_process_simple(message, context):
                yield chunk
        else:
            async for chunk in self._stream_process_simple(message, context):
                yield chunk

    async def _stream_process_simple(self, message: str, context: dict | None = None):
        """Streaming single-shot processing."""
        system_prompt = self._system_prompt
        messages = [{"role": "system", "content": system_prompt}]
        
        if context and context.get("history"):
            messages.extend(self._inject_history(context["history"]))
            
        user_content = self._build_prompt(message, context)
        
        # Check for attachments for multimodal support
        if context and context.get("attachments"):
            user_message_dict = {
                "role": "user",
                "content": self._build_multimodal_content(user_content, context["attachments"])
            }
        else:
            user_message_dict = {"role": "user", "content": user_content}
            
        messages.append(user_message_dict)

        try:
            async for chunk in model_router.stream_generate(
                messages=messages,
                chain=self.config.model_chain,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            ):
                yield chunk
        except Exception as e:
            yield {"type": "error", "content": str(e)}

    def _build_multimodal_content(self, text: str, attachments: list[dict]) -> list[dict]:
        """Format content as list of parts (text + images)."""
        parts = [{"type": "text", "text": text}]
        for att in attachments:
            mime = att.get("mime_type", "")
            if mime and ("image" in mime or "pdf" in mime):
                parts.append({
                    "type": "image_url",
                    "image_url": {"url": att.get("public_url", "")}
                })
        return parts

    def _inject_history(self, history: list[dict]) -> list[dict]:
        """Convert persistent messages to LLM roles."""
        injected = []
        for msg in history[-10:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "assistant":
                injected.append({"role": "assistant", "content": content})
            else:
                injected.append({"role": "user", "content": content})
        return injected

    def _build_prompt(self, message: str, context: dict | None = None) -> str:
        """Build ONLY the user part of the prompt (context + message)."""
        parts = []

        if context:
            if context.get("task"):
                parts.append(f"\n## Task Atual\n{context['task']}")

            if context.get("working_memory"):
                parts.append(f"\n## Memória de Trabalho\n{context['working_memory']}")

        parts.append(f"\n## Mensagem\n{message}")

        return "\n".join(parts)

    async def think(self, query: str, context: dict | None = None) -> dict:
        """Process with enhanced thinking (ToT-ready). Override in subclasses."""
        return await self.process(query, context)

    def __repr__(self) -> str:
        return f"<Agent name='{self.name}' role='{self.role}' level='{self.level}'>"
