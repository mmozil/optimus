"""
Agent Optimus — Collective Intelligence (Fase 11: Jarvis Mode).
Cross-agent knowledge sharing with deduplication and knowledge graph.

Phase 11 completion: added async query_semantic() with PGvector and
graceful fallback to keyword search, plus index_knowledge() method.
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class SharedKnowledge:
    """A piece of knowledge shared between agents."""

    source_agent: str
    topic: str
    learning: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    used_by: list[str] = field(default_factory=list)
    upvotes: int = 0

    @property
    def content_hash(self) -> str:
        return hashlib.md5(self.learning.encode()).hexdigest()


class CollectiveIntelligence:
    """
    Cross-agent knowledge sharing and discovery.

    Features:
    - Share learnings between agents (with deduplication)
    - Query by topic (keyword + semantic)
    - Build knowledge graph (agent → topics)
    - Find expert agent for a topic
    - PGvector semantic search with keyword fallback
    """

    def __init__(self):
        self._knowledge: list[SharedKnowledge] = []
        self._hashes: set[str] = set()

    def share(self, agent_name: str, topic: str, learning: str) -> SharedKnowledge | None:
        """
        Share a learning from one agent to the collective (in-memory, sync).

        Returns the SharedKnowledge if new, None if duplicate.
        """
        sk = SharedKnowledge(source_agent=agent_name, topic=topic, learning=learning)

        # Deduplication check
        if sk.content_hash in self._hashes:
            logger.debug(f"Collective: duplicate learning skipped from '{agent_name}'")
            return None

        self._hashes.add(sk.content_hash)
        self._knowledge.append(sk)
        logger.info(f"Collective: '{agent_name}' shared learning on '{topic}'")
        return sk

    async def async_share(self, agent_name: str, topic: str, learning: str) -> SharedKnowledge | None:
        """
        Share a learning + persist to PGvector embeddings table (FASE 11 fix).

        In-memory deduplication → DB embedding → semantic search ready.
        Falls back gracefully if embeddings service is unavailable.
        """
        sk = self.share(agent_name, topic, learning)
        if sk is None:
            return None  # duplicate

        # Persist to DB for semantic search
        try:
            from src.infra.supabase_client import get_async_session
            from src.memory.embeddings import embedding_service

            text = f"[{topic}] {learning}"
            embedding = await embedding_service.embed_text(text)
            if embedding:
                async with get_async_session() as session:
                    await embedding_service.store_embedding(
                        db_session=session,
                        content=text,
                        embedding=embedding,
                        source_type="collective",
                        source_id=agent_name,
                        metadata={"topic": topic, "content_hash": sk.content_hash},
                    )
                logger.info(f"Collective: '{agent_name}' knowledge persisted to PGvector (topic='{topic}')")
        except Exception as e:
            logger.warning(f"Collective: PGvector persist failed (in-memory still works): {e}")

        return sk

    def query(self, topic: str, requesting_agent: str = "") -> list[SharedKnowledge]:
        """
        Query shared knowledge by topic (keyword match).

        Tracks which agent requested the knowledge for usage metrics.
        """
        topic_lower = topic.lower()
        results = [
            sk for sk in self._knowledge
            if topic_lower in sk.topic.lower() or topic_lower in sk.learning.lower()
        ]

        # Track usage
        if requesting_agent:
            for sk in results:
                if requesting_agent not in sk.used_by:
                    sk.used_by.append(requesting_agent)

        return results

    async def query_semantic(self, topic: str, requesting_agent: str = "") -> list[SharedKnowledge]:
        """
        Query shared knowledge using PGvector semantic similarity.

        Falls back to keyword query if PGvector/embeddings are unavailable.
        """
        try:
            from src.infra.supabase_client import get_async_session as get_session
            from src.memory.embeddings import embedding_service

            async with get_session() as session:
                results = await embedding_service.semantic_search(
                    db_session=session,
                    query=topic,
                    source_type="collective",
                    limit=10,
                    threshold=0.5,
                )

                if results:
                    # Map DB results back to SharedKnowledge objects where possible
                    matched = []
                    for r in results:
                        # Try to find the matching knowledge in memory
                        for sk in self._knowledge:
                            if sk.learning in r["content"] or r["content"] in sk.learning:
                                if requesting_agent and requesting_agent not in sk.used_by:
                                    sk.used_by.append(requesting_agent)
                                matched.append(sk)
                                break
                        else:
                            # Create a synthetic SharedKnowledge from DB result
                            matched.append(SharedKnowledge(
                                source_agent=r.get("source_id", "unknown"),
                                topic=topic,
                                learning=r["content"],
                            ))

                    logger.debug(f"Collective semantic search: {len(matched)} results for '{topic[:50]}'")
                    return matched

        except Exception as e:
            logger.debug(f"Collective semantic search unavailable ({e}), falling back to keyword")

        # Fallback to keyword search
        return self.query(topic, requesting_agent)

    async def index_knowledge(self) -> int:
        """
        Index all shared knowledge to PGvector for semantic search.

        Returns the number of items indexed.
        """
        count = 0
        try:
            from src.infra.supabase_client import get_async_session as get_session
            from src.memory.embeddings import embedding_service

            if not self._knowledge:
                return 0

            async with get_session() as session:
                for sk in self._knowledge:
                    text = f"[{sk.topic}] {sk.learning}"
                    embedding = await embedding_service.embed_text(text)
                    await embedding_service.store_embedding(
                        db_session=session,
                        content=text,
                        embedding=embedding,
                        source_type="collective",
                        source_id=sk.source_agent,
                        metadata={"topic": sk.topic},
                    )
                    count += 1

            logger.info(f"Collective: indexed {count} knowledge items to PGvector")

        except Exception as e:
            logger.error(f"Collective PGvector indexing failed: {e}")

        return count

    def get_knowledge_graph(self) -> dict[str, list[str]]:
        """
        Build a knowledge graph: agent → list of topics.

        Returns a dict mapping agent names to their expertise topics.
        """
        graph: dict[str, list[str]] = {}
        for sk in self._knowledge:
            if sk.source_agent not in graph:
                graph[sk.source_agent] = []
            if sk.topic not in graph[sk.source_agent]:
                graph[sk.source_agent].append(sk.topic)
        return graph

    def find_expert(self, topic: str) -> str | None:
        """
        Find the agent with the most knowledge on a topic.

        Returns the agent name, or None if no knowledge exists.
        """
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
        agents = {sk.source_agent for sk in self._knowledge}
        topics = {sk.topic for sk in self._knowledge}

        return {
            "total_shared": len(self._knowledge),
            "unique_agents": len(agents),
            "unique_topics": len(topics),
            "most_used": sorted(
                self._knowledge,
                key=lambda sk: len(sk.used_by),
                reverse=True,
            )[:3] if self._knowledge else [],
        }


# Singleton
collective_intelligence = CollectiveIntelligence()
