"""
Agent Optimus — ToT Service.
High-level service that wraps ToT Engine with agent integration, caching, and logging.
"""

import logging
from dataclasses import dataclass

from src.engine.tot_engine import ThinkingStrategy, ToTEngine, ToTResult

logger = logging.getLogger(__name__)


@dataclass
class ThinkingLevel:
    """Configures how deep the thinking should be."""
    name: str
    strategies: list[ThinkingStrategy]
    model_chain: str
    parallel: bool = True


# Pre-configured thinking levels
THINKING_LEVELS = {
    "quick": ThinkingLevel(
        name="Quick",
        strategies=[ThinkingStrategy.ANALYTICAL],
        model_chain="default",
        parallel=False,
    ),
    "standard": ThinkingLevel(
        name="Standard",
        strategies=[ThinkingStrategy.CONSERVATIVE, ThinkingStrategy.ANALYTICAL],
        model_chain="default",
        parallel=True,
    ),
    "deep": ThinkingLevel(
        name="Deep",
        strategies=[
            ThinkingStrategy.CONSERVATIVE,
            ThinkingStrategy.CREATIVE,
            ThinkingStrategy.ANALYTICAL,
        ],
        model_chain="complex",
        parallel=True,
    ),
}


class ToTService:
    """
    High-level service for Tree-of-Thought reasoning.
    Provides simplified interface for agents.
    """

    def __init__(self):
        self._engines: dict[str, ToTEngine] = {}

    def _get_engine(self, level: str) -> ToTEngine:
        """Get or create a ToT engine for a specific thinking level."""
        if level not in self._engines:
            config = THINKING_LEVELS.get(level, THINKING_LEVELS["standard"])
            self._engines[level] = ToTEngine(
                strategies=config.strategies,
                model_chain=config.model_chain,
            )
        return self._engines[level]

    async def think(
        self,
        query: str,
        level: str = "standard",
        context: str = "",
        agent_soul: str = "",
    ) -> dict:
        """
        Execute Tree-of-Thought reasoning.

        Args:
            query: The question or task to analyze
            level: Thinking depth ('quick', 'standard', 'deep')
            context: Additional context (working memory, history, etc.)
            agent_soul: Agent's SOUL.md content for personality

        Returns:
            Dict with synthesis, confidence, hypotheses, etc.
        """
        engine = self._get_engine(level)
        config = THINKING_LEVELS.get(level, THINKING_LEVELS["standard"])

        logger.info(f"ToT Service: Starting {level} analysis", extra={
            "props": {"level": level, "strategies": len(config.strategies)}
        })

        result: ToTResult = await engine.think(
            query=query,
            context=context,
            system_prompt=agent_soul,
            parallel=config.parallel,
        )

        return {
            "synthesis": result.synthesis,
            "confidence": result.confidence,
            "thinking_level": level,
            "hypotheses": [
                {
                    "strategy": h.strategy.value,
                    "content": h.content[:500],  # Truncate for response
                    "score": h.score,
                }
                for h in sorted(result.hypotheses, key=lambda x: x.score, reverse=True)
            ],
            "best_strategy": result.best_hypothesis.strategy.value if result.best_hypothesis else "none",
            "model": result.model_used,
            "total_tokens": result.total_tokens,
        }

    async def quick_think(self, query: str, context: str = "") -> str:
        """Quick single-strategy analysis. Returns just the synthesis text."""
        result = await self.think(query, level="quick", context=context)
        return result["synthesis"]

    async def deep_think(self, query: str, context: str = "", agent_soul: str = "") -> dict:
        """Full 3-strategy deep analysis."""
        return await self.think(query, level="deep", context=context, agent_soul=agent_soul)


# Singleton
tot_service = ToTService()
