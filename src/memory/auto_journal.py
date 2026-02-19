"""
Agent Optimus — Auto Journal (Fase 10: Proactive Intelligence).
Post-response hook that automatically extracts learnings from interactions
and persists them to MEMORY.md and daily notes. Zero LLM tokens.
"""

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from src.memory.daily_notes import daily_notes
from src.memory.long_term import long_term_memory

logger = logging.getLogger(__name__)

# Keywords for category detection (Portuguese + English)
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "decisões": [
        "decidi", "decidimos", "optei", "escolhi", "definimos",
        "decided", "chose", "picked", "selected", "went with",
    ],
    "preferências": [
        "prefiro", "gosto", "quero", "sempre uso", "favorite",
        "prefer", "like", "want", "always use", "my default",
        # Informações pessoais explícitas (fruta preferida, cor favorita, etc.)
        "preferida", "preferido", "favorita", "favorito",
        "minha cor", "meu time", "minha comida", "minha fruta",
        "meu nome", "me chamo", "meu apelido",
        "gosto de", "não gosto", "odeio", "adoro",
        "moro em", "trabalho em", "sou de",
    ],
    "erros": [
        "erro", "bug", "falha", "fix", "corrigir", "traceback",
        "error", "crash", "exception", "failed", "broken", "issue",
    ],
    "conhecimento": [
        "aprendi", "descobri", "funciona assim", "importante saber",
        "learned", "discovered", "works like", "good to know", "TIL",
    ],
    "técnico": [
        "implementar", "configurar", "instalar", "deploy", "migration",
        "implement", "configure", "install", "setup", "architecture",
    ],
}

# Keywords that indicate high-relevance interactions
RELEVANCE_KEYWORDS: list[str] = [
    "importante", "critical", "lembrar", "nunca", "sempre", "atenção",
    "important", "remember", "never", "always", "attention", "note",
    "decisão", "decision", "config", "password", "secret", "deploy",
    "erro", "error", "bug", "fix", "solução", "solution",
]

# Minimum lengths to avoid journaling trivial interactions
MIN_QUERY_LENGTH = 30
MIN_RESPONSE_LENGTH = 100


@dataclass
class JournalEntry:
    """A single auto-extracted journal entry."""

    category: str
    learning: str
    relevance: str  # "high", "medium", "low"
    source: str
    hash: str


class AutoJournal:
    """
    Automatic journaling — extracts learnings from (query, response) pairs.

    Rules:
    - Only saves "high" relevance entries to MEMORY.md
    - All entries are logged in daily notes
    - Deduplication via content hash
    - Zero LLM tokens — classification is keyword-based
    """

    def __init__(self):
        self._seen_hashes: set[str] = set()

    def _compute_hash(self, text: str) -> str:
        """Compute hash for deduplication."""
        normalized = re.sub(r"\s+", " ", text.strip().lower())
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def _classify_relevance(self, query: str, response: str) -> str:
        """Classify relevance as high/medium/low based on keywords."""
        combined = f"{query} {response}".lower()

        score = sum(1 for kw in RELEVANCE_KEYWORDS if kw in combined)

        if score >= 3:
            return "high"
        elif score >= 1:
            return "medium"
        return "low"

    def _detect_category(self, query: str, response: str) -> str:
        """Detect the category of the interaction based on keywords."""
        combined = f"{query} {response}".lower()

        category_scores: dict[str, int] = {}
        for category, keywords in CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in combined)
            if score > 0:
                category_scores[category] = score

        if not category_scores:
            return "geral"

        return max(category_scores, key=category_scores.get)

    def _extract_learning(self, query: str, response: str, category: str) -> str:
        """Extract a concise learning from the interaction."""
        # Take the first meaningful sentence of the response as the learning
        sentences = re.split(r"[.!?\n]", response)
        meaningful = [s.strip() for s in sentences if len(s.strip()) > 20]

        if meaningful:
            learning = meaningful[0][:300]
        else:
            learning = response[:200]

        return f"[{category}] Q: {query[:100]}... → {learning}"

    async def extract_and_save(
        self,
        agent_name: str,
        query: str,
        response: str,
        metadata: dict | None = None,
    ) -> JournalEntry | None:
        """
        Analyze a (query, response) pair and save learnings if relevant.

        Args:
            agent_name: Agent that processed the interaction
            query: User's original query
            response: Agent's response
            metadata: Optional extra data (model, tokens, etc.)

        Returns:
            JournalEntry if saved, None if skipped
        """
        # Skip trivial interactions
        if len(query) < MIN_QUERY_LENGTH and len(response) < MIN_RESPONSE_LENGTH:
            return None

        # Classify
        relevance = self._classify_relevance(query, response)
        category = self._detect_category(query, response)
        learning = self._extract_learning(query, response, category)

        # Preferências e decisões pessoais são SEMPRE high relevance
        # (ex: "minha fruta preferida é a goiaba" seria "low" sem essa regra)
        if category in ("preferências", "decisões") and relevance != "high":
            relevance = "high"
            logger.debug(f"Auto-journal: upgrading to high (category={category})")

        # Deduplication
        content_hash = self._compute_hash(learning)
        if content_hash in self._seen_hashes:
            logger.debug(f"Duplicate learning skipped: {content_hash}")
            return None
        self._seen_hashes.add(content_hash)

        entry = JournalEntry(
            category=category,
            learning=learning,
            relevance=relevance,
            source=f"auto-journal/{agent_name}",
            hash=content_hash,
        )

        # Always log to daily notes
        await daily_notes.log(
            agent_name=agent_name,
            event_type="auto_journal",
            message=f"[{relevance}] {learning[:200]}",
            metadata=metadata,
        )

        # Only persist to MEMORY.md if high relevance
        if relevance == "high":
            await long_term_memory.add_learning(
                agent_name=agent_name,
                category=category,
                learning=learning,
                source=entry.source,
            )
            logger.info(f"Auto-journal: HIGH relevance learning saved for {agent_name}: {category}")
        else:
            logger.debug(f"Auto-journal: {relevance} relevance, daily-only for {agent_name}")

        return entry

    async def summarize_day(self, agent_name: str) -> str:
        """
        Generate end-of-day summary from daily notes.
        Extracts key insights from today's auto-journal entries.
        """
        today_notes = await daily_notes.get_today(agent_name)

        if not today_notes or "auto_journal" not in today_notes:
            return f"No auto-journal entries for {agent_name} today."

        # Count entries by relevance
        high_count = today_notes.count("[high]")
        medium_count = today_notes.count("[medium]")
        total = today_notes.count("auto_journal")

        # Extract high-relevance learnings
        high_learnings: list[str] = []
        for line in today_notes.split("\n"):
            if "[high]" in line.lower():
                clean = line.replace("[high]", "").strip()
                if clean:
                    high_learnings.append(f"- {clean[:150]}")

        summary_parts = [
            f"# Daily Summary — {agent_name}",
            f"**Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
            f"**Interactions journaled:** {total} (🔴 {high_count} high, 🟡 {medium_count} medium)",
        ]

        if high_learnings:
            summary_parts.append("\n## Key Learnings")
            summary_parts.extend(high_learnings[:10])

        return "\n".join(summary_parts)


# Singleton
auto_journal = AutoJournal()
