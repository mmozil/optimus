"""
Agent Optimus — Intent Predictor (Fase 11: Jarvis Mode).
Detects behavioral patterns from daily notes to predict user needs.
Suggests proactive actions based on time-of-day and day-of-week patterns.
"""

import json
import logging
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.memory.daily_notes import daily_notes

logger = logging.getLogger(__name__)

PATTERNS_DIR = Path(__file__).parent.parent.parent / "workspace" / "patterns"

# Day name mapping (Portuguese)
WEEKDAY_NAMES = {
    0: "segunda", 1: "terça", 2: "quarta", 3: "quinta",
    4: "sexta", 5: "sábado", 6: "domingo",
}

# Time slot classification
TIME_SLOTS = {
    "morning": (6, 12),
    "afternoon": (12, 18),
    "evening": (18, 23),
    "night": (23, 6),
}


@dataclass
class UserPattern:
    """A detected behavioral pattern."""

    action: str  # e.g., "deploy", "standup", "code_review"
    frequency: int  # How many times observed
    weekdays: list[int] = field(default_factory=list)  # 0=Monday, 6=Sunday
    time_slots: list[str] = field(default_factory=list)  # "morning", "afternoon", etc.
    confidence: float = 0.0  # 0.0 to 1.0
    last_seen: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Prediction:
    """A predicted action the user might need."""

    action: str
    reason: str
    confidence: float
    suggested_message: str


# Action keywords to detect in daily notes
ACTION_KEYWORDS: dict[str, list[str]] = {
    "deploy": ["deploy", "production", "staging", "release", "push"],
    "code_review": ["review", "pull request", "PR", "merge", "code review"],
    "bug_fix": ["bug", "fix", "debug", "traceback", "error", "hotfix"],
    "meeting": ["standup", "meeting", "call", "sync", "reunião"],
    "documentation": ["docs", "readme", "documentation", "documentação", "wiki"],
    "database": ["migration", "database", "sql", "backup", "schema"],
    "testing": ["test", "pytest", "coverage", "QA", "teste"],
    "research": ["research", "study", "learn", "pesquisa", "estudar"],
    "planning": ["plan", "sprint", "roadmap", "backlog", "planejamento"],
}


class IntentPredictor:
    """
    Predicts user needs based on behavioral patterns in daily notes.

    Analyzes:
    - Day-of-week patterns (e.g., deploys on Fridays)
    - Time-of-day patterns (e.g., standups in the morning)
    - Action frequency (e.g., most common tasks)
    """

    def __init__(self):
        PATTERNS_DIR.mkdir(parents=True, exist_ok=True)

    def _get_time_slot(self, hour: int) -> str:
        """Classify an hour into a time slot."""
        if 6 <= hour < 12:
            return "morning"
        elif 12 <= hour < 18:
            return "afternoon"
        elif 18 <= hour < 23:
            return "evening"
        return "night"

    def _extract_actions(self, text: str) -> list[str]:
        """Extract action types from daily note text."""
        text_lower = text.lower()
        found: list[str] = []
        for action, keywords in ACTION_KEYWORDS.items():
            if any(kw.lower() in text_lower for kw in keywords):
                found.append(action)
        return found

    async def learn_patterns(self, agent_name: str, days: int = 30) -> list[UserPattern]:
        """
        Analyze daily notes to extract behavioral patterns.

        Args:
            agent_name: Agent to analyze
            days: Number of days to look back
        """
        now = datetime.now(timezone.utc)
        action_data: dict[str, dict] = {}  # action -> {weekdays: Counter, time_slots: Counter, ...}

        for i in range(days):
            date = now - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            content = await daily_notes.get_date(agent_name, date_str)

            if not content or "Sem atividades" in content:
                continue

            weekday = date.weekday()
            actions = self._extract_actions(content)

            # Extract time slots from entries like "### [10:00:00]"
            time_slots_found: list[str] = []
            for line in content.split("\n"):
                if line.startswith("### [") and ":" in line:
                    try:
                        time_str = line.split("[")[1].split("]")[0]
                        hour = int(time_str.split(":")[0])
                        time_slots_found.append(self._get_time_slot(hour))
                    except (IndexError, ValueError):
                        pass

            primary_slot = max(set(time_slots_found), key=time_slots_found.count) if time_slots_found else "morning"

            for action in actions:
                if action not in action_data:
                    action_data[action] = {
                        "weekdays": Counter(),
                        "time_slots": Counter(),
                        "count": 0,
                        "last_seen": date_str,
                    }
                action_data[action]["weekdays"][weekday] += 1
                action_data[action]["time_slots"][primary_slot] += 1
                action_data[action]["count"] += 1

        # Build patterns
        patterns: list[UserPattern] = []
        for action, data in action_data.items():
            top_weekdays = [wd for wd, _ in data["weekdays"].most_common(3)]
            top_slots = [ts for ts, _ in data["time_slots"].most_common(2)]
            confidence = min(data["count"] / (days * 0.3), 1.0)  # Normalize

            patterns.append(UserPattern(
                action=action,
                frequency=data["count"],
                weekdays=top_weekdays,
                time_slots=top_slots,
                confidence=round(confidence, 2),
                last_seen=data["last_seen"],
            ))

        patterns.sort(key=lambda p: p.confidence, reverse=True)
        return patterns

    def predict_next(
        self,
        patterns: list[UserPattern],
        current_time: datetime | None = None,
    ) -> list[Prediction]:
        """
        Predict what the user might need right now.

        Based on matching current day/time against learned patterns.
        """
        now = current_time or datetime.now(timezone.utc)
        current_weekday = now.weekday()
        current_slot = self._get_time_slot(now.hour)
        day_name = WEEKDAY_NAMES.get(current_weekday, "")

        predictions: list[Prediction] = []

        for pattern in patterns:
            if pattern.confidence < 0.3:
                continue

            # Score: does this pattern match current day + time?
            day_match = current_weekday in pattern.weekdays
            time_match = current_slot in pattern.time_slots
            score = pattern.confidence

            if day_match:
                score *= 1.5
            if time_match:
                score *= 1.3

            score = min(score, 1.0)

            if score >= 0.4 and (day_match or time_match):
                reason_parts = []
                if day_match:
                    reason_parts.append(f"você costuma fazer isso às {day_name}s")
                if time_match:
                    reason_parts.append(f"geralmente no período da {current_slot}")

                reason = " e ".join(reason_parts)

                predictions.append(Prediction(
                    action=pattern.action,
                    reason=reason,
                    confidence=round(score, 2),
                    suggested_message=self._build_suggestion(pattern.action, reason),
                ))

        predictions.sort(key=lambda p: p.confidence, reverse=True)
        return predictions[:5]

    def _build_suggestion(self, action: str, reason: str) -> str:
        """Build a natural suggestion message."""
        templates = {
            "deploy": "🚀 Preparar deploy? {reason}.",
            "code_review": "👀 Hora de revisar PRs? {reason}.",
            "bug_fix": "🐛 Quer que eu verifique bugs pendentes? {reason}.",
            "meeting": "📅 Preparar agenda da reunião? {reason}.",
            "documentation": "📝 Atualizar documentação? {reason}.",
            "database": "🗃️ Verificar estado do banco de dados? {reason}.",
            "testing": "🧪 Rodar testes? {reason}.",
            "research": "🔍 Pesquisar novidades? {reason}.",
            "planning": "📋 Revisar o planejamento? {reason}.",
        }
        template = templates.get(action, "💡 Posso ajudar com {action}? {reason}.")
        return template.format(action=action, reason=reason)

    async def save_patterns(self, agent_name: str, patterns: list[UserPattern]) -> Path:
        """Save learned patterns to disk."""
        path = PATTERNS_DIR / f"{agent_name}.json"
        data = [p.to_dict() for p in patterns]
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info(f"Patterns saved for {agent_name}: {len(patterns)} patterns")
        return path


# Singleton
intent_predictor = IntentPredictor()
