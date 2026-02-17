"""
Agent Optimus — Guardian Agent (Vision).
QA, security auditing, code review, and compliance.
"""

import logging

from src.agents.base import AgentConfig, BaseAgent

logger = logging.getLogger(__name__)


class GuardianAgent(BaseAgent):
    """
    Guardian Agent — Codinome: Vision.
    Especialista em QA, auditoria de segurança,
    code review e compliance.
    """

    def __init__(self, config: AgentConfig | None = None, **kwargs):
        config = config or AgentConfig(
            name="guardian",
            role="QA/Security Guardian",
            level="specialist",
            model="gemini-2.5-flash",
            model_chain="default",
            temperature=0.2,
        )
        super().__init__(config, **kwargs)

    async def security_audit(self, code: str, language: str = "python", context: dict | None = None) -> dict:
        """Perform a security audit on code."""
        prompt = f"""Realize uma auditoria de segurança completa no seguinte código ({language}):

```{language}
{code}
```

Analise:
1. **Vulnerabilidades Críticas** — SQL injection, XSS, SSRF, etc.
2. **Vulnerabilidades Médias** — exposição de dados, auth fraca
3. **Boas Práticas** — o que está correto
4. **Recomendações** — correções com código corrigido
5. **Score de Segurança** — 0-100 com justificativa

Classifique cada achado: 🔴 Crítico | 🟡 Médio | 🟢 Baixo"""
        return await self.process(prompt, context)

    async def code_review(self, code: str, context_description: str = "", context: dict | None = None) -> dict:
        """Perform a comprehensive code review."""
        prompt = f"""Faça um code review detalhado:
{f'Contexto: {context_description}' if context_description else ''}

```
{code}
```

Avalie:
1. **Qualidade** — Clean code, SOLID, DRY
2. **Performance** — Complexidade, otimizações
3. **Manutenibilidade** — Legibilidade, documentação
4. **Testes** — Cobertura e edge cases
5. **Sugestões** — Melhorias concretas com exemplos"""
        return await self.process(prompt, context)

    async def compliance_check(self, system_description: str, standard: str = "OWASP", context: dict | None = None) -> dict:
        """Check compliance against a security standard."""
        prompt = f"""Verifique compliance contra o padrão {standard}:

Sistema: {system_description}

Para cada item do {standard} aplicável:
- ✅ Conformidade atendida
- ⚠️ Parcialmente atendida (com recomendações)
- ❌ Não atendida (com prioridade de correção)

Gere um relatório de gap analysis."""
        return await self.process(prompt, context)
