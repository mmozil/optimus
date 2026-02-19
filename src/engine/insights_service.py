"""
Agent Optimus — Proactive Insights Service (FASE 16).

Agrega insights de múltiplas fontes internas e os apresenta como
suggestion chips no frontend.

Fontes:
  1. intent_predictor     — padrões comportamentais (dia/hora)
  2. research findings    — arquivos de briefing de hoje/ontem
  3. long_term_memory     — últimas entradas de alta relevância

Call Path:
  GET /api/v1/autonomous/suggestions
    → insights_service.get_insights(agent_name)
    → [intent_predictor] predict_next(patterns)
    → [research] _parse_briefing_file(hoje, ontem)
    → [learnings] long_term_memory últimas 3 entradas HIGH
    → retorna lista de ProactiveInsight ordenada por prioridade
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

FINDINGS_DIR = Path(__file__).parent.parent.parent / "workspace" / "research" / "findings"
LONG_TERM_DIR = Path(__file__).parent.parent.parent / "workspace" / "memory" / "long_term"

# Minimum relevance score to include a research finding as suggestion
RESEARCH_MIN_RELEVANCE = 0.7
# Max insights returned total
MAX_INSIGHTS = 5


@dataclass
class ProactiveInsight:
    """
    A single actionable suggestion for the user.

    Rendered as a clickable chip in the frontend that pre-fills the chat input.
    """

    type: str                     # "pattern" | "research" | "learning"
    action: str                   # Short label (3-6 words)
    reason: str                   # Why this is suggested
    message: str                  # Pre-filled message for the chat input
    confidence: float = 0.5       # 0.0-1.0
    priority: float = 0.5         # 0.0-1.0, used for sorting
    metadata: dict = field(default_factory=dict)


class InsightsService:
    """
    Agregates proactive insights from multiple internal sources.

    Designed to be lightweight and fast — all sources are file-based or
    in-memory, so no DB round-trips (DB is only for persistence/recovery).
    """

    async def get_insights(
        self,
        agent_name: str = "optimus",
        max_results: int = MAX_INSIGHTS,
    ) -> list[ProactiveInsight]:
        """
        Return top-N proactive insights sorted by priority.

        Graceful: each source failure is caught independently —
        partial results are always returned.
        """
        insights: list[ProactiveInsight] = []

        # 1. Behavioral patterns (intent_predictor)
        try:
            pattern_insights = await self._get_pattern_insights(agent_name)
            insights.extend(pattern_insights)
        except Exception as e:
            logger.debug(f"FASE 16: pattern insights unavailable: {e}")

        # 2. Recent research findings
        try:
            research_insights = self._get_research_insights(agent_name)
            insights.extend(research_insights)
        except Exception as e:
            logger.debug(f"FASE 16: research insights unavailable: {e}")

        # 3. Recent high-relevance learnings
        try:
            learning_insights = self._get_learning_insights(agent_name)
            insights.extend(learning_insights)
        except Exception as e:
            logger.debug(f"FASE 16: learning insights unavailable: {e}")

        # Sort by priority descending, cap at max_results
        insights.sort(key=lambda x: x.priority, reverse=True)
        return insights[:max_results]

    # ------------------------------------------------------------------
    # Source 1: Behavioral patterns (intent_predictor)
    # ------------------------------------------------------------------

    async def _get_pattern_insights(self, agent_name: str) -> list[ProactiveInsight]:
        """Load behavioral patterns and convert to ProactiveInsight."""
        from src.engine.intent_predictor import UserPattern, intent_predictor

        patterns: list[UserPattern] = []

        patterns_file = (
            Path(__file__).parent.parent.parent / "workspace" / "patterns" / f"{agent_name}.json"
        )
        if patterns_file.exists():
            import json
            try:
                raw = json.loads(patterns_file.read_text(encoding="utf-8"))
                patterns = [UserPattern(**p) for p in raw]
            except Exception:
                pass

        if not patterns:
            patterns = await intent_predictor.learn_patterns(agent_name, days=30)
            if patterns:
                await intent_predictor.save_patterns(agent_name, patterns)

        predictions = intent_predictor.predict_next(patterns)

        return [
            ProactiveInsight(
                type="pattern",
                action=p.action,
                reason=p.reason,
                message=p.suggested_message,
                confidence=p.confidence,
                priority=p.confidence * 0.8,  # Patterns slightly below research
            )
            for p in predictions
        ]

    # ------------------------------------------------------------------
    # Source 2: Research findings from saved briefing files
    # ------------------------------------------------------------------

    def _get_research_insights(self, agent_name: str) -> list[ProactiveInsight]:
        """
        Parse today's and yesterday's research briefing files for high-relevance findings.

        Briefing format:
            ### N. 🔴 Title
            _source_ — YYYY-MM-DD
            Summary text
            🔗 [Link](url)
        """
        insights: list[ProactiveInsight] = []
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

        for date in [today, yesterday]:
            file_path = FINDINGS_DIR / f"{agent_name}-{date}.md"
            if not file_path.exists():
                continue
            try:
                content = file_path.read_text(encoding="utf-8")
                parsed = self._parse_briefing(content)
                insights.extend(parsed)
                if insights:
                    break  # Today's file was found — don't also add yesterday's
            except Exception as e:
                logger.debug(f"FASE 16: failed to parse briefing {file_path}: {e}")

        return insights

    def _parse_briefing(self, content: str) -> list[ProactiveInsight]:
        """Extract high-relevance (🔴) findings from a markdown briefing."""
        insights: list[ProactiveInsight] = []

        # Match sections: ### N. 🔴 Title (only high-relevance = red circle)
        # Each section starts with "### " and has 🔴 (or 🟡 for medium)
        sections = re.split(r"\n### \d+\.", content)
        for section in sections[1:]:  # Skip header section
            lines = [l.strip() for l in section.strip().splitlines() if l.strip()]
            if not lines:
                continue

            title_line = lines[0]
            relevance_high = "🔴" in title_line
            relevance_medium = "🟡" in title_line
            if not (relevance_high or relevance_medium):
                continue

            # Clean emoji and whitespace from title
            clean_title = re.sub(r"[🔴🟡⚪📦🔨]", "", title_line).strip()[:80]
            summary = lines[2] if len(lines) > 2 else ""

            priority = 0.9 if relevance_high else 0.6

            insights.append(ProactiveInsight(
                type="research",
                action=f"Ver: {clean_title[:40]}",
                reason=f"Nova descoberta de pesquisa: {summary[:80]}",
                message=f"Me diga mais sobre: {clean_title}",
                confidence=priority,
                priority=priority,
                metadata={"source": "research_briefing"},
            ))

        return insights[:2]  # Max 2 research findings

    # ------------------------------------------------------------------
    # Source 3: Recent learnings from long-term memory
    # ------------------------------------------------------------------

    def _get_learning_insights(self, agent_name: str) -> list[ProactiveInsight]:
        """
        Read the last 3 entries from MEMORY.md and suggest follow-up actions.

        Only returns insights for entries from the last 7 days.
        """
        insights: list[ProactiveInsight] = []
        memory_file = LONG_TERM_DIR / f"{agent_name}.md"
        if not memory_file.exists():
            return insights

        try:
            content = memory_file.read_text(encoding="utf-8")
        except Exception:
            return insights

        # Parse "### [YYYY-MM-DD] category\nlearning text"
        sections = re.split(r"\n### \[", content)
        recent = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)

        for section in reversed(sections[1:]):  # most recent first
            try:
                date_str, rest = section.split("]", 1)
                entry_date = datetime.strptime(date_str.strip(), "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
                if entry_date < cutoff:
                    break
                category_and_text = rest.strip()
                # First line is category, rest is learning
                parts = category_and_text.split("\n", 1)
                category = parts[0].strip().lstrip()
                learning = parts[1].strip()[:120] if len(parts) > 1 else ""
                if learning:
                    recent.append((category, learning))
                    if len(recent) >= 3:
                        break
            except (ValueError, IndexError):
                continue

        for category, learning in recent:
            label = learning[:50].rstrip(".,")
            insights.append(ProactiveInsight(
                type="learning",
                action=f"Revisar: {label}",
                reason=f"Aprendizado recente em '{category}': {learning[:80]}",
                message=f"Quero revisar: {learning[:80]}",
                confidence=0.4,
                priority=0.4,
                metadata={"category": category},
            ))

        return insights


# Singleton
insights_service = InsightsService()
