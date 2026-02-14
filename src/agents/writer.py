"""
Agent Optimus — Writer Agent (Loki).
Content writing, copy, documentation, and creative text.
"""

import logging

from src.agents.base import AgentConfig, BaseAgent

logger = logging.getLogger(__name__)


class WriterAgent(BaseAgent):
    """
    Writer Agent — Codinome: Loki.
    Especialista em redação de conteúdo, copywriting,
    documentação técnica e textos criativos.
    """

    def __init__(self, config: AgentConfig | None = None, **kwargs):
        config = config or AgentConfig(
            name="writer",
            role="Content Writer",
            level="specialist",
            model="gemini-2.0-flash",
            temperature=0.8,
            description="Redação de conteúdo, copy, documentação e textos criativos",
        )
        super().__init__(config, **kwargs)

    async def write_content(self, brief: str, tone: str = "profissional", context: dict | None = None) -> dict:
        """Write content based on a brief."""
        prompt = f"""Redija conteúdo com base no seguinte brief:

**Brief:** {brief}
**Tom:** {tone}

Entregue:
1. **Título** — impactante e otimizado para SEO
2. **Conteúdo** — completo e bem estruturado
3. **CTA** — call to action sugerido
4. **Variações** — 2-3 variações do título"""
        return await self.process(prompt, context)

    async def write_documentation(self, subject: str, code: str = "", context: dict | None = None) -> dict:
        """Write technical documentation."""
        prompt = f"""Escreva documentação técnica para: {subject}

Inclua:
- Overview e propósito
- Como usar (com exemplos de código)
- API reference (se aplicável)
- Troubleshooting

{f'Código de referência:\n```\n{code}\n```' if code else ''}"""
        return await self.process(prompt, context)

    async def write_copy(self, product: str, audience: str = "", context: dict | None = None) -> dict:
        """Write marketing copy."""
        prompt = f"""Crie copy de marketing para: {product}
{f'Público-alvo: {audience}' if audience else ''}

Entregue:
1. **Headline** — principal
2. **Subheadline** — complementar
3. **Body copy** — texto principal
4. **Social posts** — 3 variações para redes sociais
5. **Email subject lines** — 3 opções"""
        return await self.process(prompt, context)
