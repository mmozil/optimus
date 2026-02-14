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

    async def process(self, message: str, context: dict | None = None) -> dict:
        """
        Process a message and return response.
        Checks rate limiting, builds prompt, calls LLM.
        """
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

        # 2. Build full prompt
        full_prompt = self._build_prompt(message, context)

        # 3. Call LLM via model router (with failover)
        try:
            result = await model_router.generate(
                prompt=full_prompt,
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

    def _build_prompt(self, message: str, context: dict | None = None) -> str:
        """Build the complete prompt with system + context + message."""
        parts = [self._system_prompt]

        if context:
            if context.get("history"):
                history_str = "\n".join(
                    f"- [{msg['role']}]: {msg['content'][:200]}"
                    for msg in context["history"][-10:]  # Last 10 messages
                )
                parts.append(f"\n## Histórico Recente\n{history_str}")

            if context.get("task"):
                parts.append(f"\n## Task Atual\n{context['task']}")

            if context.get("working_memory"):
                parts.append(f"\n## Memória de Trabalho\n{context['working_memory']}")

        parts.append(f"\n## Mensagem do Usuário\n{message}")

        return "\n".join(parts)

    async def think(self, query: str, context: dict | None = None) -> dict:
        """Process with enhanced thinking (ToT-ready). Override in subclasses."""
        return await self.process(query, context)

    def __repr__(self) -> str:
        return f"<Agent name='{self.name}' role='{self.role}' level='{self.level}'>"
