"""
Agent Optimus — Friday (Developer Agent).
Specialized in code, debugging, DevOps, and technical tasks.
"""

import logging

from src.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class FridayAgent(BaseAgent):
    """
    Developer agent specialized in code tasks.
    Enhanced with code-specific prompt patterns.
    """

    async def process(self, message: str, context: dict | None = None) -> dict:
        """Process with code-oriented enhancements."""
        enriched_context = dict(context) if context else {}

        # Add code-specific instructions
        enriched_context.setdefault("instructions", "")
        enriched_context["instructions"] += """
Ao responder sobre código:
- Sempre use syntax highlighting com a linguagem correta
- Inclua type hints em Python
- Mostre imports necessários
- Adicione comentários explicativos em trechos complexos
- Se for um bug, mostre: causa raiz → fix → teste → prevenção
"""
        result = await super().process(message, enriched_context)
        return result
