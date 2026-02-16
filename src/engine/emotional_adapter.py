"""
Agent Optimus — Emotional Adapter (Fase 11: Jarvis Mode).
Keyword-based sentiment analysis of user messages. Zero LLM tokens.
Adapts response tone based on detected mood. Persists mood in daily notes.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from src.memory.daily_notes import daily_notes

logger = logging.getLogger(__name__)


class Mood(str, Enum):
    """Detected user mood."""

    FRUSTRATED = "frustrated"
    CURIOUS = "curious"
    RUSHED = "rushed"
    CELEBRATING = "celebrating"
    NEUTRAL = "neutral"


@dataclass
class SentimentResult:
    """Result of sentiment analysis."""

    mood: Mood
    confidence: float  # 0.0 to 1.0
    indicators: list[str]  # Keywords that triggered the detection
    tone_instruction: str  # Instruction for adapting response tone


# Keyword dictionaries per mood (Portuguese + English)
MOOD_KEYWORDS: dict[Mood, list[str]] = {
    Mood.FRUSTRATED: [
        # Portuguese
        "droga", "pqp", "que saco", "não funciona", "de novo", "tá quebrado",
        "não consigo", "impossível", "merda", "inferno", "aff", "cansado disso",
        "tô perdido", "socorro", "help", "nada funciona",
        # English
        "damn", "wtf", "broken again", "doesn't work", "frustrated", "sick of",
        "can't figure", "impossible", "annoying", "ugh", "ffs",
    ],
    Mood.CURIOUS: [
        # Portuguese
        "como funciona", "por que", "será que", "o que é", "explica",
        "me conta", "quero entender", "como assim", "interessante",
        "tipo o quê", "qual a diferença", "possível", "dá pra",
        # English
        "how does", "why does", "what is", "explain", "curious",
        "want to understand", "interesting", "what if", "could we",
    ],
    Mood.RUSHED: [
        # Portuguese
        "rápido", "urgente", "agora", "deadline", "correndo", "sem tempo",
        "preciso já", "pra ontem", "depressa", "asap", "pressa",
        "tá pegando fogo", "emergência", "crítico",
        # English
        "quick", "urgent", "asap", "hurry", "emergency", "right now",
        "deadline", "running out of time", "critical", "immediately",
    ],
    Mood.CELEBRATING: [
        # Portuguese
        "consegui", "funcionou", "deu certo", "show", "top", "perfeito",
        "maravilha", "excelente", "incrível", "massa", "valeu", "obrigado",
        "finalmente", "sucesso", "mandou bem",
        # English
        "it works", "awesome", "perfect", "amazing", "great", "fantastic",
        "nailed it", "success", "thank you", "brilliant", "finally",
        "well done", "celebration", "yay", "🎉", "🚀", "✅",
    ],
}

# Tone instructions per mood
TONE_INSTRUCTIONS: dict[Mood, str] = {
    Mood.FRUSTRATED: (
        "O usuário está frustrado. Seja DIRETO e SOLUCIONADOR. "
        "Evite explicações longas. Foque no que resolver o problema imediatamente. "
        "Mostre empatia breve ('Entendo a frustração') e vá direto ao ponto."
    ),
    Mood.CURIOUS: (
        "O usuário está curioso e quer aprender. Seja DETALHADO e EDUCATIVO. "
        "Explique o 'porquê' além do 'como'. Use exemplos e analogias. "
        "Encoraje a exploração com perguntas relacionadas."
    ),
    Mood.RUSHED: (
        "O usuário tem PRESSA. Seja ULTRA-CONCISO. Só o essencial. "
        "Use bullet points. Sem introduções ou conclusões. "
        "Formato: problema → solução → pronto."
    ),
    Mood.CELEBRATING: (
        "O usuário está celebrando! Compartilhe o entusiasmo genuinamente. "
        "Reconheça a conquista ('Parabéns! 🎉'). Sugira próximos passos com energia positiva. "
        "Mantenha o tom leve e motivador."
    ),
    Mood.NEUTRAL: (
        "Tom padrão: profissional, amigável, e eficiente. "
        "Balance clareza com completude."
    ),
}


class EmotionalAdapter:
    """
    Analyzes user sentiment via keywords and adapts response tone.

    Zero LLM cost — all classification is keyword-based.
    Persists mood history in daily notes for continuity.
    """

    def analyze(self, message: str) -> SentimentResult:
        """
        Analyze a user message and detect mood.

        Returns a SentimentResult with mood, confidence, and tone instruction.
        """
        message_lower = message.lower()

        # Score each mood
        mood_scores: dict[Mood, list[str]] = {}
        for mood, keywords in MOOD_KEYWORDS.items():
            matches = [kw for kw in keywords if kw in message_lower]
            if matches:
                mood_scores[mood] = matches

        if not mood_scores:
            return SentimentResult(
                mood=Mood.NEUTRAL,
                confidence=0.5,
                indicators=[],
                tone_instruction=TONE_INSTRUCTIONS[Mood.NEUTRAL],
            )

        # Pick the mood with most keyword matches
        best_mood = max(mood_scores, key=lambda m: len(mood_scores[m]))
        indicators = mood_scores[best_mood]
        confidence = min(len(indicators) / 3.0, 1.0)  # 3+ keywords = full confidence

        return SentimentResult(
            mood=best_mood,
            confidence=round(confidence, 2),
            indicators=indicators[:5],
            tone_instruction=TONE_INSTRUCTIONS[best_mood],
        )

    def get_tone_instruction(self, mood: Mood) -> str:
        """Get tone adaptation instruction for a specific mood."""
        return TONE_INSTRUCTIONS.get(mood, TONE_INSTRUCTIONS[Mood.NEUTRAL])

    async def log_mood(self, agent_name: str, result: SentimentResult) -> None:
        """Persist mood detection to daily notes for continuity."""
        await daily_notes.log(
            agent_name=agent_name,
            event_type="mood_detected",
            message=f"Mood: {result.mood.value} (confidence: {result.confidence})",
            metadata={
                "mood": result.mood.value,
                "confidence": result.confidence,
                "indicators": ", ".join(result.indicators[:3]),
            },
        )
        logger.debug(f"Mood logged for {agent_name}: {result.mood.value}")

    def get_mood_emoji(self, mood: Mood) -> str:
        """Get an emoji representation of the mood."""
        return {
            Mood.FRUSTRATED: "😤",
            Mood.CURIOUS: "🤔",
            Mood.RUSHED: "⚡",
            Mood.CELEBRATING: "🎉",
            Mood.NEUTRAL: "😊",
        }.get(mood, "😊")


# Singleton
emotional_adapter = EmotionalAdapter()
