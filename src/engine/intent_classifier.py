"""
Agent Optimus — Intent Classifier.
Classifies user messages into intents for routing and persona selection.
V1: Keyword-based. V2 will use LLM classification.
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class IntentResult:
    """Classification result."""
    intent: str
    confidence: float
    suggested_agent: str
    thinking_level: str  # quick | standard | deep
    keywords_matched: list[str]


# Intent definitions with routing rules
INTENT_DEFINITIONS = {
    "code": {
        "keywords": ["código", "code", "bug", "debug", "traceback", "error", "exception",
                      "implementar", "refatorar", "deploy", "dockerfile", "api", "endpoint",
                      "migration", "teste", "test", "python", "javascript", "sql"],
        "agent": "friday",
        "thinking": "standard",
    },
    "research": {
        "keywords": ["pesquisar", "pesquisa", "comparar", "comparação", "alternativa",
                      "investigar", "documentação", "artigo", "paper", "benchmark",
                      "best practice", "estudo", "análise competitiva"],
        "agent": "fury",
        "thinking": "deep",
    },
    "analysis": {
        "keywords": ["analisar", "análise", "métrica", "dados", "relatório", "report",
                      "dashboard", "kpi", "tendência", "previsão", "statistics"],
        "agent": "optimus",
        "thinking": "deep",
    },
    "planning": {
        "keywords": ["planejar", "plan", "roadmap", "fase", "sprint", "cronograma",
                      "priorizar", "strategy", "objetivo", "meta", "milestone"],
        "agent": "optimus",
        "thinking": "standard",
    },
    "creative": {
        "keywords": ["ideia", "brainstorm", "sugestão", "criativo", "inovador",
                      "nome", "design", "conceito", "proposta", "visão"],
        "agent": "optimus",
        "thinking": "deep",
    },
    "urgent": {
        "keywords": ["urgente", "caiu", "down", "offline", "429", "500", "erro crítico",
                      "produção", "production", "outage", "incident"],
        "agent": "friday",
        "thinking": "quick",
    },
    "content": {
        "keywords": ["escrever", "redigir", "texto", "artigo", "blog", "documentação",
                      "email", "comunicado", "post", "conteúdo", "marketing"],
        "agent": "optimus",  # Will be "loki" when available
        "thinking": "standard",
    },
    "general": {
        "keywords": [],
        "agent": "optimus",
        "thinking": "standard",
    },
}


class IntentClassifier:
    """
    Classifies user messages into intents.
    V1: Keyword matching with scoring.
    """

    def classify(self, message: str) -> IntentResult:
        """Classify a message intent."""
        message_lower = message.lower()

        best_intent = "general"
        best_score = 0
        matched_keywords = []

        for intent, config in INTENT_DEFINITIONS.items():
            if intent == "general":
                continue

            keywords = config["keywords"]
            matches = [kw for kw in keywords if kw in message_lower]
            score = len(matches)

            if score > best_score:
                best_score = score
                best_intent = intent
                matched_keywords = matches

        config = INTENT_DEFINITIONS[best_intent]
        confidence = min(1.0, best_score * 0.25) if best_score > 0 else 0.3

        result = IntentResult(
            intent=best_intent,
            confidence=confidence,
            suggested_agent=config["agent"],
            thinking_level=config["thinking"],
            keywords_matched=matched_keywords,
        )

        logger.debug(f"Intent classified", extra={"props": {
            "intent": result.intent,
            "confidence": result.confidence,
            "agent": result.suggested_agent,
            "keywords": matched_keywords,
        }})

        return result

    def get_thinking_level(self, message: str) -> str:
        """Quick method to get just the recommended thinking level."""
        return self.classify(message).thinking_level

    def get_suggested_agent(self, message: str) -> str:
        """Quick method to get just the suggested agent."""
        return self.classify(message).suggested_agent


# Singleton
intent_classifier = IntentClassifier()
