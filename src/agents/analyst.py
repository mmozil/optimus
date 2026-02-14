"""
Agent Optimus — Analyst Agent (Shuri).
Product analysis, data insights, and business intelligence.
"""

import logging

from src.agents.base import AgentConfig, BaseAgent

logger = logging.getLogger(__name__)


class AnalystAgent(BaseAgent):
    """
    Analyst Agent — Codinome: Shuri.
    Especialista em análise de dados, métricas de produto,
    business intelligence e tomada de decisão baseada em dados.
    """

    def __init__(self, config: AgentConfig | None = None, **kwargs):
        config = config or AgentConfig(
            name="analyst",
            role="Product Analyst",
            level="specialist",
            model="gemini-2.0-flash",
            temperature=0.3,
            description="Análise de dados, métricas de produto e business intelligence",
        )
        super().__init__(config, **kwargs)

    async def analyze_metrics(self, data: str, context: dict | None = None) -> dict:
        """Analyze metrics and generate insights."""
        prompt = f"""Analise os seguintes dados e forneça:
1. **Resumo Executivo** — situação atual
2. **Métricas Chave** — KPIs identificados
3. **Tendências** — padrões observados
4. **Insights** — análises não óbvias
5. **Recomendações** — ações sugeridas com prioridade

Dados:
{data}"""
        return await self.process(prompt, context)

    async def generate_report(self, topic: str, data: str = "", context: dict | None = None) -> dict:
        """Generate an analytical report."""
        prompt = f"""Gere um relatório analítico sobre: {topic}

Inclua:
- Análise quantitativa e qualitativa
- Visualizações sugeridas (descreva gráficos/tabelas)
- Comparações relevantes
- Conclusões baseadas em dados

{f'Dados disponíveis: {data}' if data else ''}"""
        return await self.process(prompt, context)
