"""
Agent Optimus — Collective Intelligence (Fase 11: Jarvis Mode).
Cross-agent knowledge sharing. When one agent learns, all benefit.
Knowledge graph: who knows what. Deduplication via hash.
"""

import hashlib
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

COLLECTIVE_DIR = Path(__file__).parent.parent.parent / "workspace" / "memory" / "collective"
KNOWLEDGE_FILE = COLLECTIVE_DIR / "knowledge.json"


@dataclass
class SharedKnowledge:
    """A piece of knowledge shared across agents."""

    source_agent: str
    topic: str
    learning: str
    shared_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    used_by: list[str] = field(default_factory=list)
    hash: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SharedKnowledge":
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in data.items() if k in known})


class CollectiveIntelligence:
    """
    Cross-agent knowledge sharing system.

    When Friday resolves a bug → all agents learn.
    When Fury discovers a new API → Friday already knows.
    """

    def __init__(self):
        COLLECTIVE_DIR.mkdir(parents=True, exist_ok=True)
        self._knowledge: list[SharedKnowledge] = []
        self._hashes: set[str] = set()
        self._load()

    def _load(self) -> None:
        """Load shared knowledge from persistent storage."""
        if KNOWLEDGE_FILE.exists():
            try:
                data = json.loads(KNOWLEDGE_FILE.read_text(encoding="utf-8"))
                for item in data:
                    sk = SharedKnowledge.from_dict(item)
                    self._knowledge.append(sk)
                    if sk.hash:
                        self._hashes.add(sk.hash)
                logger.info(f"Collective: loaded {len(self._knowledge)} shared learnings")
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Collective: failed to load: {e}")

    def _save(self) -> None:
        """Persist shared knowledge to JSON."""
        data = [sk.to_dict() for sk in self._knowledge]
        KNOWLEDGE_FILE.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _compute_hash(self, text: str) -> str:
        """Compute deduplication hash."""
        normalized = re.sub(r"\s+", " ", text.strip().lower())
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def share(self, source_agent: str, topic: str, learning: str) -> SharedKnowledge | None:
        """
        Share a learning from one agent with all others.

        Deduplicates by content hash — won't share the same thing twice.
        """
        content_hash = self._compute_hash(f"{topic}:{learning}")

        if content_hash in self._hashes:
            logger.debug(f"Collective: duplicate skipped from {source_agent}")
            return None

        sk = SharedKnowledge(
            source_agent=source_agent,
            topic=topic,
            learning=learning,
            hash=content_hash,
        )

        self._knowledge.append(sk)
        self._hashes.add(content_hash)
        self._save()

        logger.info(f"Collective: {source_agent} shared '{topic}' ({content_hash})")
        return sk

    def query(self, topic: str, requesting_agent: str = "") -> list[SharedKnowledge]:
        """
        Query shared knowledge by topic.

        Returns all knowledge matching the topic (keyword search).
        Marks the requesting agent in used_by for tracking.
        """
        topic_lower = topic.lower()
        results: list[SharedKnowledge] = []

        for sk in self._knowledge:
            if topic_lower in sk.topic.lower() or topic_lower in sk.learning.lower():
                # Track who used this knowledge
                if requesting_agent and requesting_agent not in sk.used_by:
                    sk.used_by.append(requesting_agent)
                results.append(sk)

        if results and requesting_agent:
            self._save()  # Persist used_by updates

        return results

    def get_knowledge_graph(self) -> dict:
        """
        Build a knowledge graph: who knows what.

        Returns:
            {agent_name: [topic1, topic2, ...], ...}
        """
        graph: dict[str, set[str]] = {}

        for sk in self._knowledge:
            # Source agent knows this topic
            if sk.source_agent not in graph:
                graph[sk.source_agent] = set()
            graph[sk.source_agent].add(sk.topic)

            # Agents that used this knowledge also "know" it
            for agent in sk.used_by:
                if agent not in graph:
                    graph[agent] = set()
                graph[agent].add(sk.topic)

        return {agent: sorted(topics) for agent, topics in graph.items()}

    def get_agent_expertise(self, agent_name: str) -> list[str]:
        """Get topics an agent has shared knowledge about."""
        topics = set()
        for sk in self._knowledge:
            if sk.source_agent == agent_name:
                topics.add(sk.topic)
        return sorted(topics)

    def find_expert(self, topic: str) -> str | None:
        """Find which agent knows most about a topic."""
        topic_lower = topic.lower()
        agent_counts: dict[str, int] = {}

        for sk in self._knowledge:
            if topic_lower in sk.topic.lower() or topic_lower in sk.learning.lower():
                agent_counts[sk.source_agent] = agent_counts.get(sk.source_agent, 0) + 1

        if not agent_counts:
            return None

        return max(agent_counts, key=agent_counts.get)

    def get_stats(self) -> dict:
        """Get collective intelligence statistics."""
        agents = set()
        topics = set()
        for sk in self._knowledge:
            agents.add(sk.source_agent)
            topics.add(sk.topic)

        return {
            "total_shared": len(self._knowledge),
            "unique_agents": len(agents),
            "unique_topics": len(topics),
            "agents": sorted(agents),
        }


# Singleton
collective_intelligence = CollectiveIntelligence()
