"""
Agent Optimus — Long-Term Memory.
Curated knowledge persisted to Supabase, queryable via semantic search.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

LONG_TERM_DIR = Path(__file__).parent.parent.parent / "workspace" / "memory" / "long_term"


class LongTermMemory:
    """
    Manages MEMORY.md — curated long-term knowledge per agent.
    Stores learnings, patterns, preferences extracted from interactions.
    Optionally synced to Supabase for cross-agent access.
    """

    def __init__(self, memory_dir: Path | None = None):
        self.memory_dir = memory_dir or LONG_TERM_DIR
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def _file_path(self, agent_name: str) -> Path:
        return self.memory_dir / f"{agent_name}.md"

    async def load(self, agent_name: str) -> str:
        """Load long-term memory for an agent."""
        path = self._file_path(agent_name)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    async def add_learning(self, agent_name: str, category: str, learning: str, source: str = ""):
        """
        Add a curated learning to long-term memory.

        Args:
            agent_name: Agent name
            category: Category (técnico, padrões, preferências, erros, etc.)
            learning: The learning itself
            source: Where this learning came from
        """
        path = self._file_path(agent_name)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Create file with header if new
        if not path.exists():
            header = f"# MEMORY.md — {agent_name}\n_Memória de longo prazo curada._\n\n"
            path.write_text(header, encoding="utf-8")

        # Append learning
        entry = f"\n### [{timestamp}] {category}\n{learning}\n"
        if source:
            entry += f"_Fonte: {source}_\n"

        with open(path, "a", encoding="utf-8") as f:
            f.write(entry)

        logger.info(f"Learning added for {agent_name}: {category}")

    async def search_local(self, agent_name: str, query: str) -> list[str]:
        """Simple keyword search in local memory (fallback for no DB)."""
        content = await self.load(agent_name)
        if not content:
            return []

        query_lower = query.lower()
        results = []

        # Split by entries and search
        entries = content.split("\n### ")
        for entry in entries:
            if query_lower in entry.lower():
                results.append(entry.strip()[:500])

        return results[:10]

    async def get_categories(self, agent_name: str) -> list[str]:
        """Get all learning categories for an agent."""
        content = await self.load(agent_name)
        if not content:
            return []

        categories = set()
        for line in content.split("\n"):
            if line.startswith("### ["):
                # Extract category from "### [date] category"
                parts = line.split("] ", 1)
                if len(parts) > 1:
                    categories.add(parts[1].strip())

        return sorted(categories)


# Singleton
long_term_memory = LongTermMemory()
