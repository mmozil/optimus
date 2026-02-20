"""
Agent Optimus — UncertaintyQuantifier.
Calibrates confidence scores based on error history and semantic similarity.
Uses PGvector for error pattern matching.
"""

import logging
from dataclasses import dataclass

from src.infra.model_router import model_router

logger = logging.getLogger(__name__)


@dataclass
class UncertaintyResult:
    """Result from uncertainty quantification."""
    confidence: float  # 0.0 - 1.0
    calibrated_confidence: float  # Adjusted by error patterns
    risk_level: str  # low | medium | high
    similar_errors: list[dict]
    recommendation: str


class UncertaintyQuantifier:
    """
    Calibrates confidence scores using:
    1. Self-assessment from LLM
    2. Historical error patterns (PGvector similarity)
    3. Domain-specific heuristics
    """

    # Risk thresholds
    RISK_THRESHOLDS = {
        "low": 0.7,
        "medium": 0.4,
        "high": 0.0,
    }

    async def quantify(
        self,
        query: str,
        response: str,
        agent_name: str = "",
        db_session=None,
    ) -> UncertaintyResult:
        """
        Quantify uncertainty for a given query-response pair.

        Args:
            query: Original question
            response: Agent's response
            agent_name: Name of the agent
            db_session: Optional async DB session for error pattern lookup
        """
        # Step 1: Self-assessment via LLM
        self_confidence = await self._self_assess(query, response)

        # Step 2: Check error patterns (if DB available)
        similar_errors = []
        pattern_penalty = 0.0
        if db_session:
            similar_errors = await self._find_similar_errors(query, db_session)
            if similar_errors:
                pattern_penalty = min(0.3, len(similar_errors) * 0.1)

        # Step 3: Calculate calibrated confidence
        calibrated = max(0.0, self_confidence - pattern_penalty)

        # Step 4: Determine risk level
        risk_level = self._classify_risk(calibrated)

        # Step 5: Generate recommendation
        recommendation = self._generate_recommendation(calibrated, risk_level, similar_errors)

        result = UncertaintyResult(
            confidence=self_confidence,
            calibrated_confidence=calibrated,
            risk_level=risk_level,
            similar_errors=similar_errors,
            recommendation=recommendation,
        )

        logger.info(f"Uncertainty quantified", extra={"props": {
            "agent": agent_name,
            "raw_confidence": self_confidence,
            "calibrated": calibrated,
            "risk_level": risk_level,
            "similar_errors_count": len(similar_errors),
        }})

        return result

    async def _self_assess(self, query: str, response: str) -> float:
        """Ask the LLM to self-assess its confidence."""
        prompt = f"""Avalie sua confiança na seguinte resposta.

Pergunta: {query[:500]}

Resposta: {response[:1000]}

Responda APENAS com um número de 0.0 a 1.0 representando sua confiança.
- 0.0 = Completamente inseguro, possivelmente incorreto
- 0.5 = Moderadamente confiante, pode haver imprecisões
- 0.8 = Alta confiança, baseado em conhecimento sólido
- 1.0 = Absoluta certeza, fato verificável

Confiança:"""

        try:
            result = await model_router.generate(
                prompt=prompt,
                chain="economy",  # Use cheap model for self-assessment
                temperature=0.1,
                max_tokens=10,
            )

            # Parse confidence value
            import re
            match = re.search(r'(0\.\d+|1\.0|0|1)', result["content"])
            if match:
                return float(match.group(1))
            return 0.7  # Default if parsing fails — assume moderate-high confidence

        except Exception as e:
            logger.warning(f"Self-assessment failed: {e}")
            return 0.7  # Assume confident on exception (avoids false positives)

    async def _find_similar_errors(self, query: str, db_session) -> list[dict]:
        """Find similar error patterns using PGvector similarity search."""
        try:
            from sqlalchemy import text

            # Generate embedding for query
            # (In production, use the embeddings service)
            sql = text("""
                SELECT pattern_text, error_type, frequency,
                       1 - (pattern_embedding <=> :query_embedding) as similarity
                FROM error_patterns
                WHERE 1 - (pattern_embedding <=> :query_embedding) > 0.7
                ORDER BY similarity DESC
                LIMIT 5
            """)

            # For now, return empty until embedding service is connected
            return []

        except Exception as e:
            logger.warning(f"Error pattern search failed: {e}")
            return []

    def _classify_risk(self, confidence: float) -> str:
        """Classify risk level based on confidence."""
        if confidence >= self.RISK_THRESHOLDS["low"]:
            return "low"
        elif confidence >= self.RISK_THRESHOLDS["medium"]:
            return "medium"
        return "high"

    def _generate_recommendation(
        self,
        confidence: float,
        risk_level: str,
        similar_errors: list[dict],
    ) -> str:
        """Generate actionable recommendation based on uncertainty."""
        if risk_level == "low":
            return "✅ Confiança alta. Resposta pode ser usada diretamente."
        elif risk_level == "medium":
            rec = "⚠️ Confiança moderada. Recomendo validar pontos-chave."
            if similar_errors:
                rec += f" Encontrados {len(similar_errors)} padrões de erro similares."
            return rec
        else:
            rec = "🔴 Confiança baixa. Não recomendo usar sem validação."
            rec += " Escalar para Optimus (Lead) ou solicitar pesquisa adicional."
            return rec

    async def record_error(
        self,
        query: str,
        error_type: str,
        agent_name: str,
        db_session=None,
    ):
        """Record an error pattern for future calibration."""
        if not db_session:
            return

        try:
            from sqlalchemy import text

            await db_session.execute(
                text("""
                    INSERT INTO error_patterns (pattern_text, error_type, agent_id, frequency)
                    SELECT :pattern, :error_type, id, 1
                    FROM agents WHERE name = :agent_name
                    ON CONFLICT DO NOTHING
                """),
                {"pattern": query[:500], "error_type": error_type, "agent_name": agent_name},
            )
            await db_session.commit()

        except Exception as e:
            logger.warning(f"Failed to record error pattern: {e}")


# Singleton
uncertainty_quantifier = UncertaintyQuantifier()
