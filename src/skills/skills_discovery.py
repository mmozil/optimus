"""
Agent Optimus — Skills Auto-Discovery (Fase 10: Proactive Intelligence).
Semantic search and auto-discovery of skills in the registry.
Includes file watcher for hot-reload when SKILL.md changes.
"""

import logging
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from src.skills.skills_registry import Skill, skills_registry

logger = logging.getLogger(__name__)


@dataclass
class SkillMatch:
    """A skill match result from search."""

    skill_name: str
    description: str
    relevance_score: float  # 0.0 to 1.0
    category: str = ""


class SkillsDiscovery:
    """
    Semantic search and auto-discovery for the skills registry.

    Features:
    - Keyword + TF-IDF-like search across skill descriptions
    - Intent-based suggestions (query → recommended skills)
    - Directory watcher for hot-reload of SKILL.md files
    """

    def __init__(self):
        self._index: dict[str, Counter] = {}  # skill_name -> term frequencies
        self._rebuild_index()

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into normalized words."""
        text = text.lower()
        text = re.sub(r"[^a-záàâãéêíóôõúüç\w\s]", " ", text)
        words = text.split()
        # Filter stopwords (minimal list)
        stopwords = {
            "a", "o", "e", "de", "da", "do", "em", "um", "uma", "para",
            "the", "a", "an", "is", "are", "in", "on", "for", "with", "and",
        }
        return [w for w in words if w not in stopwords and len(w) > 2]

    def _rebuild_index(self) -> None:
        """Rebuild the search index from current registry."""
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

    def suggest_for_query(self, query: str) -> list[str]:
        """
        Suggest skill names based on an intent query.

        Returns a list of skill names that might be relevant.
        """
        matches = self.search(query, top_k=3)
        return [m.skill_name for m in matches if m.relevance_score > 0.05]

    def detect_capability_gap(self, query: str) -> str | None:
        """
        Check if a query needs a skill that isn't installed or enabled.

        Returns a suggestion string if a gap is detected, None otherwise.
        """
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

    def watch_directory(self, skills_dir: str) -> int:
        """
        Scan a directory for SKILL.md changes and reload.
        Returns count of skills loaded.

        Note: For MVP, this is a manual scan (not a live file watcher).
        A live watcher (watchdog) can be added in a future iteration.
        """
        dir_path = Path(skills_dir)
        if not dir_path.exists():
            logger.warning(f"Skills dir not found: {skills_dir}")
            return 0

        count = 0
        for skill_md in dir_path.rglob("SKILL.md"):
            try:
                skills_registry.load_from_directory(str(skill_md.parent))
                count += 1
            except Exception as e:
                logger.error(f"Failed to load skill from {skill_md}: {e}")

        if count > 0:
            self._rebuild_index()
            logger.info(f"Skills watcher: reloaded {count} skills from {skills_dir}")

        return count

    def get_stats(self) -> dict:
        """Get discovery index statistics."""
        total_skills = len(self._index)
        total_terms = sum(sum(c.values()) for c in self._index.values())
        categories = set()
        for skill in skills_registry.list_skills(enabled_only=False):
            categories.add(skill.category)

        return {
            "indexed_skills": total_skills,
            "total_terms": total_terms,
            "categories": sorted(categories),
        }


# Singleton
skills_discovery = SkillsDiscovery()
