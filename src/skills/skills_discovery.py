"""
Agent Optimus — Skills Discovery (Fase 10: Proactive Intelligence).
Semantic search & auto-discovery for skills with PGvector and keyword fallback.

Phase 10 completion: added async search_semantic() with PGvector and
graceful fallback to TF-IDF keyword search.
"""

import logging
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SkillMatch:
    """A matched skill from search."""

    skill_name: str
    description: str
    relevance_score: float
    category: str = ""


class SkillsDiscovery:
    """
    Skills search engine with semantic + keyword search.

    - search(): keyword-based TF-IDF search (always available)
    - search_semantic(): PGvector cosine similarity (falls back to keyword)
    - suggest_for_query(): intent-based suggestions
    - detect_capability_gap(): detect missing skills
    - scan_skill_files(): auto-discover SKILL.md files
    """

    # Stopwords for tokenization
    STOPWORDS = frozenset({
        "a", "an", "the", "in", "on", "at", "for", "to", "of", "and", "or",
        "is", "it", "by", "as", "with", "from", "this", "that", "be", "are",
        "was", "will", "can", "do", "no", "not", "but", "if", "so", "up",
        "de", "o", "e", "um", "uma", "para", "com", "em", "que", "do", "da",
        "os", "as", "se", "na", "no", "por", "mais", "como",
    })

    def __init__(self):
        self._index: dict[str, Counter] = {}

    def _tokenize(self, text: str) -> list[str]:
        """Split text into lowercase tokens, removing stopwords."""
        words = text.lower().split()
        return [w for w in words if len(w) > 1 and w not in self.STOPWORDS]

    def _rebuild_index(self) -> None:
        """Rebuild the search index from current registry."""
        from src.skills.skills_registry import skills_registry

        self._index.clear()
        for skill in skills_registry.list_skills(enabled_only=False):
            tokens = self._tokenize(f"{skill.name} {skill.description} {skill.category}")
            self._index[skill.name] = Counter(tokens)
        logger.debug(f"Skills index rebuilt: {len(self._index)} skills indexed")

    def search(self, query: str, top_k: int = 5) -> list[SkillMatch]:
        """
        Search skills by keyword relevance.

        Uses TF-IDF-like scoring: query terms matched against skill term index.
        """
        if not self._index:
            self._rebuild_index()

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        from src.skills.skills_registry import skills_registry

        results: list[SkillMatch] = []

        for skill_name, term_freq in self._index.items():
            # Calculate relevance score
            total_terms = sum(term_freq.values()) or 1
            matched_terms = sum(term_freq.get(qt, 0) for qt in query_tokens)
            score = matched_terms / (total_terms * len(query_tokens)) if query_tokens else 0.0

            # Boost exact name matches
            if any(qt in skill_name.lower() for qt in query_tokens):
                score += 0.3

            if score > 0.0:
                skill = skills_registry.get(skill_name)
                results.append(SkillMatch(
                    skill_name=skill_name,
                    description=skill.description if skill else "",
                    relevance_score=min(score, 1.0),
                    category=skill.category if skill else "",
                ))

        # Sort by relevance (descending)
        results.sort(key=lambda m: m.relevance_score, reverse=True)
        return results[:top_k]

    async def search_semantic(self, query: str, top_k: int = 5) -> list[SkillMatch]:
        """
        Search skills using PGvector semantic similarity.

        Falls back to keyword search if PGvector/embeddings are unavailable.
        """
        try:
            from src.infra.supabase_client import get_async_session as get_session
            from src.memory.embeddings import embedding_service

            async with get_session() as session:
                results = await embedding_service.semantic_search(
                    db_session=session,
                    query=query,
                    source_type="skill",
                    limit=top_k,
                    threshold=0.5,
                )

                if results:
                    from src.skills.skills_registry import skills_registry

                    matches = []
                    for r in results:
                        skill = skills_registry.get(r["source_id"])
                        matches.append(SkillMatch(
                            skill_name=r["source_id"],
                            description=r["content"][:200],
                            relevance_score=r["similarity"],
                            category=skill.category if skill else "",
                        ))
                    logger.debug(f"Skills semantic search: {len(matches)} results for '{query[:50]}'")
                    return matches

        except Exception as e:
            logger.debug(f"Skills semantic search unavailable ({e}), falling back to keyword")

        # Fallback to keyword search
        return self.search(query, top_k)

    async def index_skills_to_pgvector(self) -> int:
        """
        Index all skills to PGvector for semantic search.

        Returns the number of skills indexed.
        """
        count = 0
        try:
            from src.infra.supabase_client import get_async_session as get_session
            from src.memory.embeddings import embedding_service
            from src.skills.skills_registry import skills_registry

            skills = skills_registry.list_skills(enabled_only=False)
            if not skills:
                return 0

            async with get_session() as session:
                for skill in skills:
                    text = f"{skill.name}: {skill.description}. Category: {skill.category}"
                    embedding = await embedding_service.embed_text(text)
                    await embedding_service.store_embedding(
                        db_session=session,
                        content=text,
                        embedding=embedding,
                        source_type="skill",
                        source_id=skill.name,
                    )
                    count += 1

            logger.info(f"Skills: indexed {count} skills to PGvector")

        except Exception as e:
            logger.error(f"Skills PGvector indexing failed: {e}")

        return count

    def suggest_for_query(self, query: str, top_k: int = 3) -> list[SkillMatch]:
        """
        Suggest skills based on user query intent.

        Similar to search but optimized for proactive suggestions.
        """
        if not query:
            return []
        return self.search(query, top_k=top_k)

    def detect_capability_gap(self, query: str) -> str | None:
        """
        Check if a query needs a skill that isn't installed or enabled.

        Returns a suggestion string if a gap is detected, None otherwise.
        """
        from src.skills.skills_registry import skills_registry

        matches = self.search(query, top_k=1)

        if not matches:
            # No skill found at all
            query_short = query[:80]
            logger.debug(f"Skills gap: no skills match query '{query_short}'")
            return f"No skills found for: {query_short}. Consider installing a new skill."

        top = matches[0]
        skill = skills_registry.get(top.skill_name)

        if skill and not skill.enabled:
            return f"Skill '{top.skill_name}' exists but is disabled. Enable it for this task."

        if top.relevance_score < 0.1:
            return f"Low confidence match: '{top.skill_name}' ({top.relevance_score:.0%}). May need a new skill."

        return None

    def scan_skill_files(self, base_dir: str = "src/skills") -> list[Path]:
        """
        Auto-discover SKILL.md files in the project.

        Returns a list of paths to discovered skill files.
        """
        discovered: list[Path] = []
        base = Path(base_dir)

        if not base.exists():
            return discovered

        for skill_md in base.rglob("SKILL.md"):
            discovered.append(skill_md)
            logger.debug(f"Skills: discovered {skill_md}")

        logger.info(f"Skills: scanned {base_dir}, found {len(discovered)} SKILL.md files")
        return discovered

    def get_stats(self) -> dict:
        """Get discovery engine statistics."""
        if not self._index:
            self._rebuild_index()

        return {
            "indexed_skills": len(self._index),
            "total_terms": sum(sum(tf.values()) for tf in self._index.values()),
            "categories": list({
                cat
                for tf in self._index.values()
                for cat in tf.keys()
            })[:10],
        }


# Singleton
skills_discovery = SkillsDiscovery()
