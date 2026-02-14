"""
Tests for Phase 2 — Intelligence Engine, Memory, RAG.
"""

import pytest

from src.engine.intent_classifier import IntentClassifier
from src.engine.tot_engine import Hypothesis, ThinkingStrategy, ToTResult
from src.engine.tot_service import THINKING_LEVELS, ToTService
from src.engine.uncertainty import UncertaintyQuantifier
from src.memory.rag import RAGPipeline


# ============================================
# Intent Classifier Tests
# ============================================
class TestIntentClassifier:
    def setup_method(self):
        self.classifier = IntentClassifier()

    def test_classify_code_intent(self):
        result = self.classifier.classify("Tem um bug no traceback do código Python")
        assert result.intent == "code"
        assert result.suggested_agent == "friday"

    def test_classify_research_intent(self):
        result = self.classifier.classify("Pesquise as melhores práticas de documentação")
        assert result.intent == "research"
        assert result.suggested_agent == "fury"
        assert result.thinking_level == "deep"

    def test_classify_urgent_intent(self):
        result = self.classifier.classify("Urgente! Servidor caiu, erro 500 em produção")
        assert result.intent == "urgent"
        assert result.suggested_agent == "friday"
        assert result.thinking_level == "quick"

    def test_classify_planning_intent(self):
        result = self.classifier.classify("Vamos planejar o roadmap da próxima sprint")
        assert result.intent == "planning"
        assert result.suggested_agent == "optimus"

    def test_classify_general_intent(self):
        result = self.classifier.classify("Bom dia!")
        assert result.intent == "general"

    def test_get_thinking_level(self):
        level = self.classifier.get_thinking_level("Analise os dados de vendas")
        assert level in ("quick", "standard", "deep")

    def test_get_suggested_agent(self):
        agent = self.classifier.get_suggested_agent("Implemente um endpoint de API")
        assert agent == "friday"


# ============================================
# ToT Engine Tests (Unit — no LLM)
# ============================================
class TestToTResult:
    def test_empty_result(self):
        result = ToTResult(query="test")
        assert result.synthesis == ""
        assert result.hypotheses == []
        assert result.confidence == 0.0

    def test_hypothesis_creation(self):
        h = Hypothesis(
            strategy=ThinkingStrategy.CONSERVATIVE,
            content="Test hypothesis",
            score=7.5,
        )
        assert h.strategy == ThinkingStrategy.CONSERVATIVE
        assert h.score == 7.5


class TestToTService:
    def test_thinking_levels_defined(self):
        assert "quick" in THINKING_LEVELS
        assert "standard" in THINKING_LEVELS
        assert "deep" in THINKING_LEVELS

    def test_quick_has_one_strategy(self):
        assert len(THINKING_LEVELS["quick"].strategies) == 1

    def test_deep_has_three_strategies(self):
        assert len(THINKING_LEVELS["deep"].strategies) == 3

    def test_service_creation(self):
        service = ToTService()
        assert service is not None


# ============================================
# UncertaintyQuantifier Tests (Unit)
# ============================================
class TestUncertaintyQuantifier:
    def setup_method(self):
        self.quantifier = UncertaintyQuantifier()

    def test_risk_thresholds_defined(self):
        assert "low" in self.quantifier.RISK_THRESHOLDS
        assert "medium" in self.quantifier.RISK_THRESHOLDS
        assert "high" in self.quantifier.RISK_THRESHOLDS

    def test_classify_low_risk(self):
        assert self.quantifier._classify_risk(0.9) == "low"
        assert self.quantifier._classify_risk(0.7) == "low"

    def test_classify_medium_risk(self):
        assert self.quantifier._classify_risk(0.5) == "medium"
        assert self.quantifier._classify_risk(0.4) == "medium"

    def test_classify_high_risk(self):
        assert self.quantifier._classify_risk(0.3) == "high"
        assert self.quantifier._classify_risk(0.0) == "high"

    def test_recommendation_low_risk(self):
        rec = self.quantifier._generate_recommendation(0.9, "low", [])
        assert "✅" in rec

    def test_recommendation_high_risk(self):
        rec = self.quantifier._generate_recommendation(0.2, "high", [])
        assert "🔴" in rec


# ============================================
# RAG Pipeline Tests (Chunking — no DB)
# ============================================
class TestRAGPipeline:
    def setup_method(self):
        self.rag = RAGPipeline(chunk_size=200, chunk_overlap=50)

    def test_chunk_empty_text(self):
        chunks = self.rag.chunk_text("")
        assert chunks == []

    def test_chunk_short_text(self):
        chunks = self.rag.chunk_text("Hello world")
        assert len(chunks) == 1
        assert chunks[0] == "Hello world"

    def test_chunk_by_paragraphs(self):
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        chunks = self.rag.chunk_text(text)
        assert len(chunks) >= 1

    def test_chunk_by_headings(self):
        text = "# Section 1\nContent 1\n\n# Section 2\nContent 2\n\n# Section 3\nContent 3"
        chunks = self.rag.chunk_text(text)
        assert len(chunks) >= 1

    def test_long_text_splits(self):
        # Create text longer than chunk_size
        long_text = "This is a sentence. " * 100
        chunks = self.rag.chunk_text(long_text)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= self.rag.chunk_size + 100  # Allow small overflow
