"""
Agent Optimus — Working Memory Manager.
Manages WORKING.md per agent — persisted in file system AND synced to PostgreSQL.

DB sync (FASE 6): enables multi-worker consistency and container-restart recovery.
Call path:
  load()  → cache → file → DB (fallback cold start)
  save()  → file  → DB upsert (background task, non-blocking)
"""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# Default workspace path
WORKSPACE_DIR = Path(__file__).parent.parent.parent / "workspace" / "memory" / "working"


class WorkingMemory:
    """
    Manages WORKING.md — the agent's scratchpad.
    Current state, active tasks, recent decisions, temporary notes.

    Persisted to file system (fast) AND synced to PostgreSQL (reliable).
    Priority on load: memory cache → file → DB.
    Priority on save: file (sync) → DB upsert (background).
    """

    _cache: dict[str, str] = {}

    def __init__(self, workspace_dir: Path | None = None):
        self.workspace_dir = workspace_dir or WORKSPACE_DIR
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

    def _file_path(self, agent_name: str) -> Path:
        return self.workspace_dir / f"{agent_name}.md"

    async def load(self, agent_name: str) -> str:
        """Load working memory for an agent.

        Priority: in-memory cache → file → DB → create default.
        """
        if agent_name in self._cache:
            return self._cache[agent_name]

        path = self._file_path(agent_name)
        if path.exists():
            content = path.read_text(encoding="utf-8")
            self._cache[agent_name] = content
            return content

        # FASE 6: fallback to DB (container restart recovery)
        db_content = await self._load_from_db(agent_name)
        if db_content:
            # Restore file from DB
            path.write_text(db_content, encoding="utf-8")
            self._cache[agent_name] = db_content
            logger.info(f"[WorkingMemory] Restored {agent_name} from DB ({len(db_content)} chars)")
            return db_content

        # Create default working memory
        default = self._default_content(agent_name)
        await self.save(agent_name, default)
        return default

    async def save(self, agent_name: str, content: str):
        """Save working memory — file (sync) + DB upsert (background)."""
        path = self._file_path(agent_name)
        path.write_text(content, encoding="utf-8")
        self._cache[agent_name] = content
        logger.debug(f"Working memory saved for {agent_name} ({len(content)} chars)")

        # FASE 6: sync to DB in background (non-blocking — does not slow down agent)
        try:
            asyncio.get_event_loop().create_task(self._save_to_db(agent_name, content))
        except RuntimeError:
            # No event loop (e.g., test environment) — skip background task
            pass

    async def update(self, agent_name: str, section: str, content: str):
        """Update a specific section of working memory."""
        current = await self.load(agent_name)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        # Find and replace section, or append
        section_header = f"## {section}"
        if section_header in current:
            # Replace section content (until next ## or end)
            lines = current.split("\n")
            new_lines = []
            in_section = False
            replaced = False

            for line in lines:
                if line.strip().startswith("## ") and section.lower() in line.lower():
                    in_section = True
                    new_lines.append(line)
                    new_lines.append(f"_Atualizado: {timestamp}_\n")
                    new_lines.append(content)
                    replaced = True
                    continue
                elif line.strip().startswith("## ") and in_section:
                    in_section = False
                    new_lines.append("")
                    new_lines.append(line)
                    continue
                elif not in_section:
                    new_lines.append(line)

            if replaced:
                current = "\n".join(new_lines)
        else:
            # Append new section
            current += f"\n\n## {section}\n_Atualizado: {timestamp}_\n\n{content}"

        await self.save(agent_name, current)

    async def append_note(self, agent_name: str, note: str):
        """Quick append a note to the Notas Rápidas section."""
        timestamp = datetime.now(timezone.utc).strftime("%H:%M")
        await self.update(agent_name, "Notas Rápidas", f"- [{timestamp}] {note}")

    async def clear(self, agent_name: str):
        """Reset working memory to default."""
        default = self._default_content(agent_name)
        await self.save(agent_name, default)

    # ============================================
    # FASE 6: DB sync helpers
    # ============================================

    async def _load_from_db(self, agent_name: str) -> str | None:
        """Load working memory from DB (cold start / file missing)."""
        try:
            from src.infra.supabase_client import get_async_session
            from sqlalchemy import text
            async with get_async_session() as session:
                result = await session.execute(
                    text("SELECT content FROM agent_working_memory WHERE agent_name = :name"),
                    {"name": agent_name},
                )
                row = result.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.debug(f"[WorkingMemory] DB load skipped for {agent_name}: {e}")
            return None

    async def _save_to_db(self, agent_name: str, content: str):
        """Upsert working memory to DB (background — called via create_task)."""
        try:
            from src.infra.supabase_client import get_async_session
            from sqlalchemy import text
            async with get_async_session() as session:
                await session.execute(
                    text("""
                        INSERT INTO agent_working_memory (agent_name, content, updated_at)
                        VALUES (:name, :content, NOW())
                        ON CONFLICT (agent_name) DO UPDATE
                        SET content = EXCLUDED.content, updated_at = NOW()
                    """),
                    {"name": agent_name, "content": content},
                )
                await session.commit()
                logger.debug(f"[WorkingMemory] DB synced for {agent_name}")
        except Exception as e:
            logger.debug(f"[WorkingMemory] DB sync skipped for {agent_name}: {e}")

    def _default_content(self, agent_name: str) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        return f"""# WORKING.md — {agent_name}
_Criado: {timestamp}_

## Status Atual
Idle — aguardando tarefas.

## Tasks Ativas
Nenhuma task em andamento.

## Contexto
- Sem contexto adicional.

## Notas Rápidas
"""


# Singleton
working_memory = WorkingMemory()
