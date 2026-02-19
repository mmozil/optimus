"""
Agent Optimus — Contradiction Detection Service (FASE 15).

Detecta quando novo conhecimento contradiz entradas existentes no PGvector.

Fórmula:
    1. semantic_search(new_text, threshold=0.8, limit=5) → top-5 similares
    2. LLM classifica a relação: complementary | update | contradiction
    3. Se contradiction → raise ContradictionDetected (caller decide o que fazer)

Call Path:
    POST /api/v1/knowledge/share
        ↓
    collective_intelligence.async_share(force=False)
        ↓
    contradiction_service.check(new_text) → ContradictionResult | None
        → se type == contradiction → raise ContradictionDetected
        → se force=True → skip check
"""

import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# Minimum similarity to trigger contradiction check (below this = clearly different topic)
SIMILARITY_THRESHOLD = 0.80
# Max similar entries to evaluate
TOP_K = 5
# Classification prompt
_CLASSIFY_PROMPT = """Você é um verificador de consistência de conhecimento.

Afirmação existente: "{existing}"
Nova afirmação: "{new}"

Classifique a relação entre elas com UMA das opções abaixo:
- complementary: as afirmações se complementam ou abordam aspectos diferentes
- update: a nova afirmação atualiza, refina ou corrige a existente com informação mais precisa
- contradiction: as afirmações se contradizem diretamente (afirmam coisas opostas ou incompatíveis)

Responda EXATAMENTE neste formato (sem aspas):
CLASSIFICAÇÃO | explicação em 1 linha

Exemplos:
complementary | A primeira fala de custo, a segunda fala de performance.
update | A nova versão do framework mudou a sintaxe descrita.
contradiction | A primeira diz que X é verdadeiro, a segunda diz que X é falso.
"""


class ContradictionType(str, Enum):
    COMPLEMENTARY = "complementary"
    UPDATE = "update"
    CONTRADICTION = "contradiction"


@dataclass
class ContradictionResult:
    """Resultado da classificação de contradição."""

    contradiction_type: ContradictionType
    existing_content: str
    new_content: str
    similarity: float
    confidence: float  # 0.0-1.0, estimado pela similaridade
    explanation: str


class ContradictionDetected(Exception):
    """Raised quando nova entrada contradiz conhecimento existente."""

    def __init__(self, result: ContradictionResult):
        self.result = result
        super().__init__(
            f"Contradiction detected (similarity={result.similarity:.2f}): {result.explanation}"
        )


class ContradictionService:
    """
    Detecta contradições ao salvar novo conhecimento.

    Métodos:
        check(new_text)  — busca entradas similares e classifica relação via LLM
    """

    async def check(self, new_text: str) -> ContradictionResult | None:
        """
        Verifica se new_text contradiz alguma entrada existente no PGvector.

        Returns:
            ContradictionResult com type=CONTRADICTION se contradição detectada.
            ContradictionResult com outro type se relação diferente.
            None se nenhuma entrada similar encontrada ou LLM indisponível.

        Nunca lança exceção — sempre retorna gracefully.
        """
        try:
            similar = await self._find_similar(new_text)
            if not similar:
                return None

            top = similar[0]
            return await self._classify(
                existing_content=top["content"],
                new_content=new_text,
                similarity=top.get("final_score") or top.get("similarity", 0.0),
            )

        except Exception as e:
            logger.warning(f"FASE 15: contradiction check failed (non-critical): {e}")
            return None

    async def _find_similar(self, new_text: str) -> list[dict]:
        """Busca entradas similares no PGvector (threshold=0.8, source=collective)."""
        try:
            from src.infra.supabase_client import get_async_session
            from src.memory.embeddings import embedding_service

            async with get_async_session() as session:
                results = await embedding_service.semantic_search(
                    db_session=session,
                    query=new_text,
                    source_type="collective",
                    limit=TOP_K,
                    threshold=SIMILARITY_THRESHOLD,
                )
            return results
        except Exception as e:
            logger.debug(f"FASE 15: _find_similar failed: {e}")
            return []

    async def _classify(
        self,
        existing_content: str,
        new_content: str,
        similarity: float,
    ) -> ContradictionResult:
        """
        Usa LLM para classificar a relação entre existing e new.

        Fallback: se LLM falhar → retorna COMPLEMENTARY (permissivo).
        """
        contradiction_type = ContradictionType.COMPLEMENTARY
        explanation = "LLM classification unavailable — assumed complementary"

        try:
            prompt = _CLASSIFY_PROMPT.format(
                existing=existing_content[:500],
                new=new_content[:500],
            )

            from src.infra.model_router import model_router
            from src.core.config import settings

            response = await model_router.generate(
                prompt=prompt,
                model=settings.LLM_FALLBACK_MODEL,  # Flash para custo mínimo
                temperature=0.0,
                max_tokens=100,
            )

            raw = ""
            if hasattr(response, "choices") and response.choices:
                raw = response.choices[0].message.content or ""
            elif isinstance(response, str):
                raw = response

            raw = raw.strip()
            if "|" in raw:
                parts = raw.split("|", 1)
                label = parts[0].strip().lower()
                explanation = parts[1].strip() if len(parts) > 1 else ""
                if label in (t.value for t in ContradictionType):
                    contradiction_type = ContradictionType(label)
            else:
                # Fallback: procura keyword na resposta
                raw_lower = raw.lower()
                if "contradiction" in raw_lower:
                    contradiction_type = ContradictionType.CONTRADICTION
                elif "update" in raw_lower:
                    contradiction_type = ContradictionType.UPDATE
                explanation = raw[:200]

            logger.info(
                f"FASE 15: classified as {contradiction_type.value} "
                f"(similarity={similarity:.2f}) — {explanation[:80]}"
            )

        except Exception as e:
            logger.warning(f"FASE 15: LLM classification failed, assuming complementary: {e}")

        return ContradictionResult(
            contradiction_type=contradiction_type,
            existing_content=existing_content,
            new_content=new_content,
            similarity=similarity,
            confidence=similarity,  # similarity como proxy de confiança
            explanation=explanation,
        )


# Singleton
contradiction_service = ContradictionService()
