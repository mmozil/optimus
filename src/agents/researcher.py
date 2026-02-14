"""
Agent Optimus — Fury (Researcher Agent).
Specialized in research, analysis, and evidence-based reporting.
"""

import logging

from src.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class FuryAgent(BaseAgent):
    """
    Researcher agent specialized in deep analysis.
    Enhanced with research-specific prompt patterns.
    """

    async def process(self, message: str, context: dict | None = None) -> dict:
        """Process with research-oriented enhancements."""
        enriched_context = dict(context) if context else {}

        enriched_context.setdefault("instructions", "")
        enriched_context["instructions"] += """
Ao responder sobre pesquisas:
- Sempre cite fontes quando possível
- Use tabelas comparativas para alternativas
- Inclua "Nível de Confiança" (Alto/Médio/Baixo) no final
- Estruture como: Resumo Executivo → Análise → Recomendação
- Explore pelo menos 2-3 perspectivas diferentes
"""
        result = await super().process(message, enriched_context)
        return result
