"""
Agent Optimus — Long-Term Memory.
Curated knowledge persisted to file system AND synced to PostgreSQL (FASE 6).

DB sync: enables cross-agent queries, semantic search, and container-restart recovery.
Call path:
  add_learning() → file append + DB INSERT (background, non-blocking)
  search_local() → file keyword search + DB full-text search (fallback)
  load()         → file → DB fallback (cold start)
"""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

LONG_TERM_DIR = Path(__file__).parent.parent.parent / "workspace" / "memory" / "long_term"


class LongTermMemory:
    """
    Manages MEMORY.md — curated long-term knowledge per agent.
    Stores learnings, patterns, preferences extracted from interactions.

    Persisted to file (fast) AND synced to PostgreSQL (reliable + queryable).
    """

    def __init__(self, memory_dir: Path | None = None):
        self.memory_dir = memory_dir or LONG_TERM_DIR
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def _file_path(self, agent_name: str) -> Path:
        return self.memory_dir / f"{agent_name}.md"

    async def load(self, agent_name: str) -> str:
        """Load long-term memory for an agent.

        Priority: file → DB fallback (container-restart recovery).
        """
        path = self._file_path(agent_name)
        if path.exists():
            return path.read_text(encoding="utf-8")

        # FASE 6: fallback — reconstruct file from DB entries
        db_content = await self._rebuild_from_db(agent_name)
        if db_content:
            header = f"# MEMORY.md — {agent_name}\n_Memória de longo prazo curada._\n\n"
            full_content = header + db_content
            path.write_text(full_content, encoding="utf-8")
            logger.info(f"✅ [LongTermMemory] Rebuilt {agent_name} from DB")
            return full_content

        return ""

    async def add_learning(self, agent_name: str, category: str, learning: str, source: str = ""):
        """
        Add a curated learning to long-term memory.

        Appends to file (sync) and inserts to DB (background).

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

        # Append learning to file
        entry = f"\n### [{timestamp}] {category}\n{learning}\n"
        if source:
            entry += f"_Fonte: {source}_\n"

        with open(path, "a", encoding="utf-8") as f:
            f.write(entry)

        logger.info(f"Learning added for {agent_name}: {category}")

        # FASE 6: sync to DB in background (non-blocking)
        try:
            asyncio.create_task(
                self._insert_to_db(agent_name, category, learning, source)
            )
        except RuntimeError:
            # No running event loop (e.g., test/sync context) — skip background task
            pass

    async def search_local(self, agent_name: str, query: str) -> list[str]:
        """Keyword search in memory — file first, DB fallback."""
        content = await self.load(agent_name)

        results = []
        if content:
            query_lower = query.lower()
            entries = content.split("\n### ")
            for entry in entries:
                if query_lower in entry.lower():
                    results.append(entry.strip()[:500])

        # FASE 6: also search DB for entries not yet in file (multi-worker scenario)
        if len(results) < 5:
            db_results = await self._search_db(agent_name, query)
            seen = set(results)
            for r in db_results:
                if r not in seen:
                    results.append(r)
                    seen.add(r)

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

    # ============================================
    # FASE 6: DB sync helpers
    # ============================================

    async def _insert_to_db(self, agent_name: str, category: str, learning: str, source: str):
        """Insert a learning entry into DB (background task)."""
        try:
            from src.infra.supabase_client import get_async_session
            from sqlalchemy import text
            async with get_async_session() as session:
                await session.execute(
                    text("""
                        INSERT INTO agent_long_term_memory
                            (agent_name, category, learning, source, created_at)
                        VALUES (:agent, :category, :learning, :source, NOW())
                    """),
                    {
                        "agent": agent_name,
                        "category": category,
                        "learning": learning,
                        "source": source,
                    },
                )
                await session.commit()
                logger.info(f"[LongTermMemory] DB insert for {agent_name}: {category}")
        except Exception as e:
            logger.warning(f"[LongTermMemory] DB insert failed for {agent_name}: {e}")

    async def _rebuild_from_db(self, agent_name: str) -> str:
        """Rebuild MEMORY.md content from DB entries (cold start recovery)."""
        try:
            from src.infra.supabase_client import get_async_session
            from sqlalchemy import text
            async with get_async_session() as session:
                result = await session.execute(
                    text("""
                        SELECT category, learning, source,
                               TO_CHAR(created_at, 'YYYY-MM-DD') AS date
                        FROM agent_long_term_memory
                        WHERE agent_name = :agent
                        ORDER BY created_at ASC
                    """),
                    {"agent": agent_name},
                )
                rows = result.fetchall()
                if not rows:
                    return ""

                lines = []
                for row in rows:
                    entry = f"\n### [{row.date}] {row.category}\n{row.learning}\n"
                    if row.source:
                        entry += f"_Fonte: {row.source}_\n"
                    lines.append(entry)
                return "".join(lines)
        except Exception as e:
            logger.debug(f"[LongTermMemory] DB rebuild skipped for {agent_name}: {e}")
            return ""

    async def _search_db(self, agent_name: str, query: str) -> list[str]:
        """Keyword search in DB entries."""
        try:
            from src.infra.supabase_client import get_async_session
            from sqlalchemy import text
            async with get_async_session() as session:
                result = await session.execute(
                    text("""
                        SELECT category, learning
                        FROM agent_long_term_memory
                        WHERE agent_name = :agent
                          AND (LOWER(learning) LIKE :q OR LOWER(category) LIKE :q)
                        ORDER BY created_at DESC
                        LIMIT 5
                    """),
                    {"agent": agent_name, "q": f"%{query.lower()}%"},
                )
                rows = result.fetchall()
                return [f"{row.category}\n{row.learning}" for row in rows]
        except Exception as e:
            logger.debug(f"[LongTermMemory] DB search skipped for {agent_name}: {e}")
            return []


# Singleton
long_term_memory = LongTermMemory()
