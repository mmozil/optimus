"""
Agent Optimus — Session Bootstrap (Fase 10: Proactive Intelligence).
Memory-aware startup: loads SOUL.md + MEMORY.md + daily notes on session init.
Injects accumulated context into the system prompt before any response.
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.identity.soul_loader import SoulLoader
from src.memory.daily_notes import daily_notes
from src.memory.long_term import long_term_memory

logger = logging.getLogger(__name__)

WORKSPACE_DIR = Path(__file__).parent.parent.parent / "workspace"
SOULS_DIR = WORKSPACE_DIR / "souls"
USER_FILE = WORKSPACE_DIR / "USER.md"


@dataclass
class BootstrapContext:
    """Full context loaded at session start."""

    agent_name: str
    soul: str = ""
    memory: str = ""
    daily_today: str = ""
    daily_yesterday: str = ""
    user_prefs: str = ""
    loaded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_loaded(self) -> bool:
        return bool(self.soul or self.memory)

    def build_prompt(self) -> str:
        """Build the bootstrap context block for injection into system prompt."""
        sections: list[str] = []

        if self.soul:
            sections.append(f"## Identity\n{self.soul}")

        if self.user_prefs:
            sections.append(f"## User Preferences\n{self.user_prefs}")

        if self.memory:
            # Limit memory to last 2000 chars to avoid token bloat
            mem_preview = self.memory[-2000:] if len(self.memory) > 2000 else self.memory
            sections.append(f"## Long-Term Memory (recent)\n{mem_preview}")

        if self.daily_today:
            sections.append(f"## Today's Activity Log\n{self.daily_today[-1000:]}")

        if self.daily_yesterday:
            sections.append(f"## Yesterday's Activity Log\n{self.daily_yesterday[-500:]}")

        if not sections:
            return ""

        return "# Session Context (auto-loaded)\n\n" + "\n\n---\n\n".join(sections)


class SessionBootstrap:
    """
    Loads full context at session start.

    On init: reads SOUL.md + MEMORY.md + daily notes (today + yesterday).
    Caches results with hash-based invalidation — only re-reads if file changed.
    """

    def __init__(self):
        self._cache: dict[str, BootstrapContext] = {}
        self._file_hashes: dict[str, str] = {}

    def _hash_file(self, path: Path) -> str:
        """Compute quick hash to detect file changes."""
        if not path.exists():
            return ""
        content = path.read_bytes()
        return hashlib.md5(content).hexdigest()

    def _is_stale(self, agent_name: str) -> bool:
        """Check if cached context is stale (files changed since last load)."""
        if agent_name not in self._cache:
            return True

        soul_path = SOULS_DIR / f"{agent_name}.md"
        memory_path = long_term_memory._file_path(agent_name)

        for path in [soul_path, memory_path, USER_FILE]:
            key = str(path)
            current_hash = self._hash_file(path)
            if self._file_hashes.get(key) != current_hash:
                return True

        return False

    async def load_context(self, agent_name: str, force: bool = False) -> BootstrapContext:
        """
        Load full bootstrap context for an agent.

        Args:
            agent_name: Name of the agent (e.g., 'optimus', 'friday')
            force: Force reload even if cached

        Returns:
            BootstrapContext with all loaded sections
        """
        if not force and not self._is_stale(agent_name):
            logger.debug(f"Bootstrap cache hit for {agent_name}")
            return self._cache[agent_name]

        logger.info(f"Loading bootstrap context for {agent_name}")

        ctx = BootstrapContext(agent_name=agent_name)

        # 1. Load SOUL.md
        soul_path = SOULS_DIR / f"{agent_name}.md"
        if soul_path.exists():
            ctx.soul = SoulLoader.load(str(soul_path))
            self._file_hashes[str(soul_path)] = self._hash_file(soul_path)

        # 2. Load MEMORY.md (long-term)
        ctx.memory = await long_term_memory.load(agent_name)
        memory_path = long_term_memory._file_path(agent_name)
        self._file_hashes[str(memory_path)] = self._hash_file(memory_path)

        # 3. Load today's daily notes
        ctx.daily_today = await daily_notes.get_today(agent_name)

        # 4. Load yesterday's daily notes
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        ctx.daily_yesterday = await daily_notes.get_date(agent_name, yesterday)

        # 5. Load USER.md (user preferences)
        if USER_FILE.exists():
            ctx.user_prefs = USER_FILE.read_text(encoding="utf-8")
            self._file_hashes[str(USER_FILE)] = self._hash_file(USER_FILE)

        # Cache the result
        self._cache[agent_name] = ctx

        logger.info(
            f"Bootstrap loaded for {agent_name}: "
            f"soul={len(ctx.soul)}c, memory={len(ctx.memory)}c, "
            f"today={len(ctx.daily_today)}c, yesterday={len(ctx.daily_yesterday)}c"
        )

        return ctx

    def invalidate(self, agent_name: str) -> None:
        """Invalidate cached context for an agent."""
        self._cache.pop(agent_name, None)
        logger.debug(f"Bootstrap cache invalidated for {agent_name}")

    def invalidate_all(self) -> None:
        """Invalidate all cached contexts."""
        self._cache.clear()
        self._file_hashes.clear()
        logger.info("Bootstrap cache fully cleared")


# Singleton
session_bootstrap = SessionBootstrap()
