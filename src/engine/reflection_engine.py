"""
Agent Optimus — Self-Reflection Engine (Fase 10: Proactive Intelligence).
Periodic analysis of recent interactions to identify knowledge gaps,
frequent topics, and improvement suggestions. Zero LLM tokens.
"""

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.memory.daily_notes import daily_notes

logger = logging.getLogger(__name__)

REFLECTIONS_DIR = Path(__file__).parent.parent.parent / "workspace" / "memory" / "reflections"


@dataclass
class TopicFrequency:
    """A topic and how often it appeared."""

    topic: str
    count: int
    example_query: str = ""


@dataclass
class KnowledgeGap:
    """A detected gap in the agent's knowledge."""

    topic: str
    failure_count: int
    suggestion: str


@dataclass
class ReflectionReport:
    """Weekly reflection analysis report."""

    agent_name: str
    period_start: str
    period_end: str
    total_interactions: int = 0
    topics: list[TopicFrequency] = field(default_factory=list)
    gaps: list[KnowledgeGap] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_markdown(self) -> str:
        """Format report as markdown."""
        lines = [
            f"# Reflection Report — {self.agent_name}",
            f"**Period:** {self.period_start} → {self.period_end}",
            f"**Total interactions:** {self.total_interactions}",
            f"**Generated:** {self.generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
            "",
        ]

        if self.topics:
            lines.append("## 📊 Top Topics")
            for t in self.topics[:10]:
                lines.append(f"- **{t.topic}** ({t.count}x)")

        if self.gaps:
            lines.append("\n## 🔴 Knowledge Gaps")
            for g in self.gaps:
                lines.append(f"- **{g.topic}** — {g.failure_count} falhas → {g.suggestion}")

        if self.suggestions:
            lines.append("\n## 💡 Suggestions")
            for s in self.suggestions:
                lines.append(f"- {s}")

        return "\n".join(lines)


# Common topic keywords for classification
TOPIC_KEYWORDS: dict[str, list[str]] = {
    "python": ["python", "pip", "venv", "pytest", "fastapi", "pydantic"],
    "docker": ["docker", "container", "dockerfile", "compose", "image"],
    "database": ["sql", "postgres", "supabase", "migration", "query", "database"],
    "deploy": ["deploy", "coolify", "hetzner", "server", "production", "staging"],
    "git": ["git", "commit", "push", "branch", "merge", "pull request"],
    "ai/llm": ["llm", "gemini", "openai", "embedding", "token", "prompt", "agent"],
    "frontend": ["react", "next.js", "html", "css", "javascript", "typescript"],
    "api": ["api", "endpoint", "rest", "webhook", "request", "response"],
    "security": ["auth", "jwt", "password", "secret", "ssl", "cors"],
    "debug": ["erro", "bug", "error", "traceback", "exception", "fix", "debug"],
}

# Failure indicators
FAILURE_INDICATORS: list[str] = [
    "não sei", "não consigo", "i don't know", "i can't", "unable to",
    "error", "failed", "falha", "sorry", "desculpe", "I'm not sure",
    "incerto", "uncertain", "sem informação", "no information",
]


class ReflectionEngine:
    """
    Analyzes recent daily notes to identify patterns, gaps, and suggestions.
    Runs periodically (weekly or on-demand). Zero LLM cost.
    """

    def __init__(self):
        REFLECTIONS_DIR.mkdir(parents=True, exist_ok=True)

    async def analyze_recent(self, agent_name: str, days: int = 7) -> ReflectionReport:
        """
        Analyze daily notes from the last N days.

        Returns a ReflectionReport with topics, gaps, and suggestions.
        """
        now = datetime.now(timezone.utc)
        period_end = now.strftime("%Y-%m-%d")
        period_start = (now - timedelta(days=days)).strftime("%Y-%m-%d")

        report = ReflectionReport(
            agent_name=agent_name,
            period_start=period_start,
            period_end=period_end,
        )

        # Collect all daily notes for the period
        all_content: list[str] = []
        for i in range(days):
            date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            content = await daily_notes.get_date(agent_name, date)
            if content and "Sem atividades" not in content:
                all_content.append(content)
                report.total_interactions += content.count("### [")

        if not all_content:
            report.suggestions.append("No activity data found. Start interacting to build patterns.")
            return report

        combined = "\n".join(all_content).lower()

        # 1. Topic frequency analysis
        report.topics = self._analyze_topics(combined)

        # 2. Knowledge gap detection
        report.gaps = self._detect_gaps(combined)

        # 3. Generate suggestions
        report.suggestions = self._generate_suggestions(report)

        return report

    def _analyze_topics(self, text: str) -> list[TopicFrequency]:
        """Count topic mentions in combined daily notes."""
        topic_counts: Counter = Counter()

        for topic, keywords in TOPIC_KEYWORDS.items():
            count = sum(text.count(kw) for kw in keywords)
            if count > 0:
                topic_counts[topic] = count

        return [
            TopicFrequency(topic=topic, count=count)
            for topic, count in topic_counts.most_common(10)
        ]

    def _detect_gaps(self, text: str) -> list[KnowledgeGap]:
        """Detect knowledge gaps based on failure indicators in context."""
        gaps: list[KnowledgeGap] = []

        # Find paragraphs containing failure indicators
        paragraphs = text.split("\n### ")
        failure_topics: Counter = Counter()

        for para in paragraphs:
            has_failure = any(indicator in para for indicator in FAILURE_INDICATORS)
            if has_failure:
                # Determine which topic the failure belongs to
                for topic, keywords in TOPIC_KEYWORDS.items():
                    if any(kw in para for kw in keywords):
                        failure_topics[topic] += 1

        for topic, count in failure_topics.most_common(5):
            if count >= 2:
                gaps.append(KnowledgeGap(
                    topic=topic,
                    failure_count=count,
                    suggestion=f"Estudar mais sobre {topic} — {count} falhas detectadas",
                ))

        return gaps

    def _generate_suggestions(self, report: ReflectionReport) -> list[str]:
        """Generate actionable suggestions based on the analysis."""
        suggestions: list[str] = []

        if report.total_interactions == 0:
            suggestions.append("Aumentar frequência de uso para gerar dados de reflexão.")
            return suggestions

        # Suggest based on gaps
        for gap in report.gaps:
            suggestions.append(f"📚 Estudar {gap.topic} — {gap.failure_count} falhas esta semana")

        # Suggest based on dominant topics
        if report.topics and report.topics[0].count > 20:
            top = report.topics[0]
            suggestions.append(
                f"🎯 {top.topic} é o tópico dominante ({top.count}x). "
                "Considerar criar uma skill especializada."
            )

        if not suggestions:
            suggestions.append("✅ Boa semana! Nenhum gap significativo detectado.")

        return suggestions

    async def save_report(self, report: ReflectionReport) -> Path:
        """Save reflection report to workspace."""
        agent_dir = REFLECTIONS_DIR / report.agent_name
        agent_dir.mkdir(parents=True, exist_ok=True)

        # Use ISO week number for filename
        week = report.generated_at.strftime("%Y-W%W")
        path = agent_dir / f"{week}.md"
        path.write_text(report.to_markdown(), encoding="utf-8")

        logger.info(f"Reflection report saved: {path}")
        return path


# Singleton
reflection_engine = ReflectionEngine()
