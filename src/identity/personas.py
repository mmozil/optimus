"""
Agent Optimus — Identity: Dynamic Personas.
Selects persona style based on user intent for more contextual responses.
"""

import logging

logger = logging.getLogger(__name__)


# Persona modifiers by intent type
PERSONAS = {
    "analysis": {
        "name": "Analista",
        "style": "Detalhado e baseado em dados. Use números, métricas e comparações.",
        "temperature": 0.3,
    },
    "creative": {
        "name": "Criativo",
        "style": "Exploratório e inovador. Pense fora da caixa, sugira alternativas incomuns.",
        "temperature": 0.9,
    },
    "education": {
        "name": "Educador",
        "style": "Didático e paciente. Use exemplos, analogias e explique passo a passo.",
        "temperature": 0.5,
    },
    "alert": {
        "name": "Alerta",
        "style": "Direto e urgente. Foque no problema, impacto e ação imediata.",
        "temperature": 0.2,
    },
    "planning": {
        "name": "Planejador",
        "style": "Estruturado e organizado. Use listas, prazos e dependências.",
        "temperature": 0.4,
    },
    "debug": {
        "name": "Debugger",
        "style": "Sistemático e investigativo. Isole variáveis, teste hipóteses, trace o fluxo.",
        "temperature": 0.2,
    },
    "default": {
        "name": "Padrão",
        "style": "Equilibrado e profissional. Adapte-se ao contexto.",
        "temperature": 0.7,
    },
}


class PersonaSelector:
    """Selects the appropriate persona based on message intent."""

    # Simple keyword-based intent classification
    # (will be replaced by LLM classification in Phase 2)
    INTENT_KEYWORDS = {
        "analysis": ["análise", "analise", "comparar", "comparação", "métrica", "dados", "relatório", "report"],
        "creative": ["ideia", "sugestão", "criativo", "inovador", "brainstorm", "alternativa"],
        "education": ["como", "explique", "ensine", "o que é", "tutorial", "aprenda"],
        "alert": ["urgente", "erro", "bug", "caiu", "falhou", "alerta", "429", "timeout", "down"],
        "planning": ["planejar", "roadmap", "fase", "sprint", "cronograma", "agenda", "task"],
        "debug": ["debug", "traceback", "error", "exception", "stack", "log", "investigate"],
    }

    @classmethod
    def classify_intent(cls, message: str) -> str:
        """Classify message intent using keyword matching (v1)."""
        message_lower = message.lower()

        best_intent = "default"
        best_score = 0

        for intent, keywords in cls.INTENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in message_lower)
            if score > best_score:
                best_score = score
                best_intent = intent

        return best_intent

    @classmethod
    def get_persona(cls, intent: str) -> dict:
        """Get persona configuration for a given intent."""
        return PERSONAS.get(intent, PERSONAS["default"])

    @classmethod
    def get_persona_for_message(cls, message: str) -> dict:
        """Classify intent and return the matching persona."""
        intent = cls.classify_intent(message)
        persona = cls.get_persona(intent)

        logger.debug(f"Persona selected: {persona['name']} (intent={intent})")
        return {**persona, "intent": intent}

    @classmethod
    def get_persona_prompt(cls, message: str) -> str:
        """Get a persona instruction to prepend to the system prompt."""
        persona = cls.get_persona_for_message(message)
        return f"\n## Modo Atual: {persona['name']}\n{persona['style']}\n"
