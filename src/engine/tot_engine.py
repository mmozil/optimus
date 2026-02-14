"""
Agent Optimus — Tree-of-Thought Engine.
Generates N hypotheses via different thinking strategies, evaluates, and synthesizes.
Generalized for any domain (not finance-specific like Maestro).
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum

from src.infra.model_router import model_router

logger = logging.getLogger(__name__)


class ThinkingStrategy(str, Enum):
    """Different thinking approaches for hypothesis generation."""
    CONSERVATIVE = "conservative"
    CREATIVE = "creative"
    ANALYTICAL = "analytical"


@dataclass
class Hypothesis:
    """Single hypothesis from one thinking strategy."""
    strategy: ThinkingStrategy
    content: str
    score: float = 0.0
    evaluation: dict = field(default_factory=dict)


@dataclass
class ToTResult:
    """Complete Tree-of-Thought result."""
    query: str
    hypotheses: list[Hypothesis] = field(default_factory=list)
    synthesis: str = ""
    best_hypothesis: Hypothesis | None = None
    confidence: float = 0.0
    model_used: str = ""
    total_tokens: int = 0


# Strategy-specific prompt templates
STRATEGY_PROMPTS = {
    ThinkingStrategy.CONSERVATIVE: """Analise de forma CONSERVADORA e PRAGMÁTICA.
- Foque em soluções comprovadas e de baixo risco.
- Considere precedentes e práticas estabelecidas.
- Priorize estabilidade e previsibilidade.
- Seja cauteloso com suposições.""",

    ThinkingStrategy.CREATIVE: """Analise de forma CRIATIVA e INOVADORA.
- Pense fora da caixa, considere abordagens não convencionais.
- Explore conexões inesperadas entre conceitos.
- Proponha soluções que outros poderiam não considerar.
- Valor em originalidade e potencial disruptivo.""",

    ThinkingStrategy.ANALYTICAL: """Analise de forma ANALÍTICA e baseada em DADOS.
- Decomponha o problema em componentes menores.
- Use raciocínio lógico e estruturado.
- Considere trade-offs explicitamente.
- Quantifique quando possível (probabilidades, custos, impactos).""",
}

EVALUATION_PROMPT = """Avalie cada hipótese numa escala de 0 a 10 nos seguintes critérios:

1. **Precisão** (0-10): Quão correta e factual é a resposta?
2. **Completude** (0-10): Cobre todos os aspectos da pergunta?
3. **Praticidade** (0-10): Quão aplicável e acionável é?
4. **Originalidade** (0-10): Traz insights ou perspectivas únicas?

Responda EXATAMENTE neste formato JSON para CADA hipótese:
```json
{{
  "hypotheses": [
    {{
      "strategy": "nome_estrategia",
      "scores": {{
        "precisao": 0,
        "completude": 0,
        "praticidade": 0,
        "originalidade": 0
      }},
      "total": 0,
      "justificativa": "breve justificativa"
    }}
  ]
}}
```"""

SYNTHESIS_PROMPT = """Com base nas hipóteses e suas avaliações, crie uma SÍNTESE FINAL que:

1. Combine os melhores insights de cada hipótese
2. Elimine contradições priorizando os argumentos mais fortes
3. Apresente uma resposta coerente e completa
4. Mencione o nível de confiança geral (Alta/Média/Baixa)

Hipóteses e avaliações:
{hypotheses_text}

Síntese:"""


class ToTEngine:
    """
    Tree-of-Thought reasoning engine.
    Gera N hipóteses com estratégias diferentes, avalia e sintetiza.
    """

    def __init__(
        self,
        strategies: list[ThinkingStrategy] | None = None,
        model_chain: str = "complex",
    ):
        self.strategies = strategies or [
            ThinkingStrategy.CONSERVATIVE,
            ThinkingStrategy.CREATIVE,
            ThinkingStrategy.ANALYTICAL,
        ]
        self.model_chain = model_chain

    async def think(
        self,
        query: str,
        context: str = "",
        system_prompt: str = "",
        parallel: bool = True,
    ) -> ToTResult:
        """
        Execute full Tree-of-Thought pipeline:
        1. Generate N hypotheses (parallel or sequential)
        2. Meta-evaluate all hypotheses
        3. Synthesize best response
        """
        result = ToTResult(query=query)

        # Step 1: Generate hypotheses
        logger.info(f"ToT: Generating {len(self.strategies)} hypotheses", extra={
            "props": {"query_length": len(query), "strategies": [s.value for s in self.strategies]}
        })

        if parallel:
            tasks = [
                self._generate_hypothesis(query, strategy, context, system_prompt)
                for strategy in self.strategies
            ]
            hypotheses = await asyncio.gather(*tasks, return_exceptions=True)
            result.hypotheses = [h for h in hypotheses if isinstance(h, Hypothesis)]
        else:
            for strategy in self.strategies:
                try:
                    h = await self._generate_hypothesis(query, strategy, context, system_prompt)
                    result.hypotheses.append(h)
                except Exception as e:
                    logger.warning(f"ToT: Strategy {strategy} failed: {e}")

        if not result.hypotheses:
            result.synthesis = "❌ Nenhuma hipótese gerada com sucesso."
            return result

        # Step 2: Evaluate hypotheses
        await self._evaluate_hypotheses(result)

        # Step 3: Synthesize
        await self._synthesize(result)

        # Set best hypothesis
        if result.hypotheses:
            result.best_hypothesis = max(result.hypotheses, key=lambda h: h.score)
            result.confidence = result.best_hypothesis.score / 10.0

        logger.info(f"ToT: Complete", extra={"props": {
            "num_hypotheses": len(result.hypotheses),
            "best_strategy": result.best_hypothesis.strategy.value if result.best_hypothesis else "none",
            "confidence": result.confidence,
            "total_tokens": result.total_tokens,
        }})

        return result

    async def _generate_hypothesis(
        self,
        query: str,
        strategy: ThinkingStrategy,
        context: str = "",
        system_prompt: str = "",
    ) -> Hypothesis:
        """Generate a single hypothesis using a specific thinking strategy."""
        strategy_instruction = STRATEGY_PROMPTS[strategy]

        prompt = f"""{system_prompt}

## Estratégia de Pensamento
{strategy_instruction}

{f"## Contexto\n{context}" if context else ""}

## Pergunta/Tarefa
{query}

Responda usando a estratégia {strategy.value}:"""

        response = await model_router.generate(
            prompt=prompt,
            chain=self.model_chain,
            temperature=self._strategy_temperature(strategy),
            max_tokens=2048,
        )

        return Hypothesis(
            strategy=strategy,
            content=response["content"],
        )

    async def _evaluate_hypotheses(self, result: ToTResult):
        """Meta-evaluate all hypotheses with scoring."""
        hypotheses_text = "\n\n".join(
            f"### Hipótese {i+1} ({h.strategy.value})\n{h.content}"
            for i, h in enumerate(result.hypotheses)
        )

        eval_prompt = f"""Dado a pergunta: "{result.query}"

{hypotheses_text}

{EVALUATION_PROMPT}"""

        try:
            response = await model_router.generate(
                prompt=eval_prompt,
                chain=self.model_chain,
                temperature=0.1,  # Low temperature for consistent evaluation
                max_tokens=1024,
            )

            # Parse scores (simplified — production would use structured output)
            self._parse_evaluation(response["content"], result)

        except Exception as e:
            logger.warning(f"ToT: Evaluation failed: {e}")
            # Assign default scores
            for h in result.hypotheses:
                h.score = 5.0

    async def _synthesize(self, result: ToTResult):
        """Synthesize the final response from evaluated hypotheses."""
        hypotheses_text = "\n\n".join(
            f"### {h.strategy.value} (Score: {h.score:.1f}/10)\n{h.content}"
            for h in sorted(result.hypotheses, key=lambda x: x.score, reverse=True)
        )

        prompt = SYNTHESIS_PROMPT.format(hypotheses_text=hypotheses_text)

        response = await model_router.generate(
            prompt=prompt,
            chain=self.model_chain,
            temperature=0.5,
            max_tokens=4096,
        )

        result.synthesis = response["content"]
        result.model_used = response["model"]

    def _strategy_temperature(self, strategy: ThinkingStrategy) -> float:
        """Get appropriate temperature for each strategy."""
        temps = {
            ThinkingStrategy.CONSERVATIVE: 0.3,
            ThinkingStrategy.CREATIVE: 0.9,
            ThinkingStrategy.ANALYTICAL: 0.2,
        }
        return temps.get(strategy, 0.5)

    def _parse_evaluation(self, eval_text: str, result: ToTResult):
        """Parse evaluation response and assign scores to hypotheses."""
        import json
        import re

        # Try to extract JSON from the response
        json_match = re.search(r'\{[\s\S]*\}', eval_text)
        if json_match:
            try:
                data = json.loads(json_match.group())
                evals = data.get("hypotheses", [])

                for i, h in enumerate(result.hypotheses):
                    if i < len(evals):
                        scores = evals[i].get("scores", {})
                        h.score = evals[i].get("total", sum(scores.values()) / max(len(scores), 1))
                        h.evaluation = evals[i]
                    else:
                        h.score = 5.0
                return
            except (json.JSONDecodeError, KeyError):
                pass

        # Fallback: assign default scores
        for h in result.hypotheses:
            h.score = 5.0
