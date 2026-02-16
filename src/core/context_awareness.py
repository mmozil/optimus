"""
Agent Optimus — Context Awareness (Fase 11: Jarvis Mode).
Ambient context: timezone, day-of-week, business hours, project state.
Generates contextual greetings and time-sensitive suggestions.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from src.memory.daily_notes import daily_notes

logger = logging.getLogger(__name__)

# Portuguese day-of-week names
DAY_NAMES = {
    0: "segunda-feira", 1: "terça-feira", 2: "quarta-feira",
    3: "quinta-feira", 4: "sexta-feira", 5: "sábado", 6: "domingo",
}

# Greetings by time of day
GREETINGS = {
    "morning": "Bom dia",
    "afternoon": "Boa tarde",
    "evening": "Boa noite",
    "night": "Boa noite",
}

# Day-specific contextual suggestions
DAY_CONTEXT = {
    0: "É segunda-feira. Vamos revisar o que ficou pendente da semana passada?",
    1: "Terça-feira — bom dia para focar em implementação.",
    2: "Metade da semana! Quarta-feira — hora de checar o progresso.",
    3: "Quinta-feira — reta final da semana. Algo urgente para fechar?",
    4: "Sexta-feira! 🎉 Vamos fechar a semana. Algo para deploy?",
    5: "Sábado — descanse! Mas se quiser fazer algo leve, estou aqui.",
    6: "Domingo — recarregando energias. Posso ajudar com planejamento para amanhã?",
}


@dataclass
class AmbientContext:
    """Snapshot of the current ambient context."""

    # Time
    timezone_offset: int = -3  # UTC offset in hours
    local_time: str = ""
    utc_time: str = ""
    day_of_week: str = ""
    day_number: int = 0  # 0=Monday
    time_slot: str = ""  # "morning", "afternoon", "evening", "night"

    # Business context
    is_business_hours: bool = False
    is_weekend: bool = False

    # Contextual
    greeting: str = ""
    day_suggestion: str = ""
    time_sensitivity: str = "normal"  # "urgent", "normal", "relaxed"

    # Activity (from daily notes)
    yesterday_summary: str = ""
    today_activity_count: int = 0


class ContextAwareness:
    """
    Builds ambient context for the agent.

    Knows: timezone, day-of-week, business hours, yesterday's work.
    Generates: greetings, suggestions, time sensitivity levels.
    """

    def _get_time_slot(self, hour: int) -> str:
        """Classify hour into time slot."""
        if 6 <= hour < 12:
            return "morning"
        elif 12 <= hour < 18:
            return "afternoon"
        elif 18 <= hour < 23:
            return "evening"
        return "night"

    def build_context(self, timezone_offset: int = -3) -> AmbientContext:
        """
        Build a full ambient context snapshot.

        Args:
            timezone_offset: UTC offset in hours (default: -3 for BRT)
        """
        tz = timezone(timedelta(hours=timezone_offset))
        now = datetime.now(tz)
        utc_now = datetime.now(timezone.utc)

        day_number = now.weekday()
        time_slot = self._get_time_slot(now.hour)

        ctx = AmbientContext(
            timezone_offset=timezone_offset,
            local_time=now.strftime("%H:%M"),
            utc_time=utc_now.strftime("%H:%M UTC"),
            day_of_week=DAY_NAMES.get(day_number, ""),
            day_number=day_number,
            time_slot=time_slot,
            is_business_hours=9 <= now.hour <= 18 and day_number < 5,
            is_weekend=day_number >= 5,
            greeting=GREETINGS.get(time_slot, "Olá"),
            day_suggestion=DAY_CONTEXT.get(day_number, ""),
            time_sensitivity=self.get_time_sensitivity_from_slot(time_slot, day_number),
        )

        return ctx

    def get_time_sensitivity_from_slot(self, time_slot: str, day_number: int) -> str:
        """Determine time sensitivity based on time and day."""
        if day_number >= 5:
            return "relaxed"
        if time_slot == "morning":
            return "normal"
        elif time_slot == "afternoon":
            return "normal"
        elif time_slot in ("evening", "night"):
            return "relaxed"
        return "normal"

    def generate_greeting(self, user_name: str, ctx: AmbientContext | None = None) -> str:
        """Generate a contextual greeting."""
        if ctx is None:
            ctx = self.build_context()

        parts = [f"{ctx.greeting}, {user_name}!"]

        if ctx.yesterday_summary:
            parts.append(f"Ontem: {ctx.yesterday_summary[:150]}")

        if ctx.day_suggestion:
            parts.append(ctx.day_suggestion)

        return " ".join(parts)

    async def enrich_with_activity(
        self,
        ctx: AmbientContext,
        agent_name: str,
    ) -> AmbientContext:
        """Enrich context with activity data from daily notes."""
        # Yesterday's summary
        tz = timezone(timedelta(hours=ctx.timezone_offset))
        yesterday = (datetime.now(tz) - timedelta(days=1)).strftime("%Y-%m-%d")
        yesterday_notes = await daily_notes.get_date(agent_name, yesterday)

        if yesterday_notes and "Sem atividades" not in yesterday_notes:
            entry_count = yesterday_notes.count("### [")
            ctx.yesterday_summary = f"{entry_count} atividades registradas"

        # Today's activity count
        today_notes = await daily_notes.get_today(agent_name)
        if today_notes:
            ctx.today_activity_count = today_notes.count("### [")

        return ctx

    def build_context_prompt(self, ctx: AmbientContext) -> str:
        """Build a context block for injection into system prompt."""
        lines = [
            "## Ambient Context",
            f"- **Hora local:** {ctx.local_time} ({ctx.day_of_week})",
            f"- **Horário comercial:** {'Sim' if ctx.is_business_hours else 'Não'}",
            f"- **Sensibilidade:** {ctx.time_sensitivity}",
        ]

        if ctx.yesterday_summary:
            lines.append(f"- **Ontem:** {ctx.yesterday_summary}")

        if ctx.today_activity_count > 0:
            lines.append(f"- **Atividades hoje:** {ctx.today_activity_count}")

        return "\n".join(lines)


# Singleton
context_awareness = ContextAwareness()
