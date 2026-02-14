"""
Agent Optimus — Performance Manager.
Session pruning, context compacting, and caching utilities.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


@dataclass
class SessionInfo:
    """Metadata for a chat session."""
    session_id: str
    agent_name: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    message_count: int = 0
    total_tokens: int = 0
    compacted: bool = False


class SessionPruner:
    """
    Automatically prunes inactive sessions to free memory.
    Configurable TTL and max sessions per agent.
    """

    def __init__(self, ttl_hours: int = 24, max_sessions: int = 100):
        self._sessions: dict[str, SessionInfo] = {}
        self.ttl_hours = ttl_hours
        self.max_sessions = max_sessions

    def register_session(self, session_id: str, agent_name: str = "") -> SessionInfo:
        """Register a new session."""
        info = SessionInfo(session_id=session_id, agent_name=agent_name)
        self._sessions[session_id] = info
        return info

    def touch_session(self, session_id: str, tokens: int = 0):
        """Update last_active timestamp and token count."""
        if session_id in self._sessions:
            self._sessions[session_id].last_active = datetime.now(timezone.utc)
            self._sessions[session_id].message_count += 1
            self._sessions[session_id].total_tokens += tokens

    async def prune(self) -> int:
        """Remove expired sessions. Returns count of pruned sessions."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.ttl_hours)
        expired = [
            sid for sid, info in self._sessions.items()
            if info.last_active < cutoff
        ]

        for sid in expired:
            del self._sessions[sid]

        # Also enforce max sessions (remove oldest)
        if len(self._sessions) > self.max_sessions:
            sorted_sessions = sorted(
                self._sessions.items(),
                key=lambda x: x[1].last_active,
            )
            to_remove = len(self._sessions) - self.max_sessions
            for sid, _ in sorted_sessions[:to_remove]:
                del self._sessions[sid]
                expired.append(sid)

        if expired:
            logger.info(f"Pruned {len(expired)} sessions")

        return len(expired)

    def get_active_count(self) -> int:
        return len(self._sessions)

    def get_stats(self) -> dict:
        total_tokens = sum(s.total_tokens for s in self._sessions.values())
        total_messages = sum(s.message_count for s in self._sessions.values())
        return {
            "active_sessions": len(self._sessions),
            "total_tokens": total_tokens,
            "total_messages": total_messages,
            "ttl_hours": self.ttl_hours,
        }


class ContextCompactor:
    """
    Compacts conversation context to save tokens.
    Summarizes long message histories into concise context.
    """

    def __init__(self, max_messages: int = 20, max_tokens_estimate: int = 4000):
        self.max_messages = max_messages
        self.max_tokens_estimate = max_tokens_estimate

    async def compact(self, messages: list[dict], agent_name: str = "") -> dict:
        """
        Compact a message history.
        Keeps recent messages and summarizes older ones.
        """
        if len(messages) <= self.max_messages:
            return {
                "messages": messages,
                "compacted": False,
                "original_count": len(messages),
            }

        # Keep the last N messages intact
        keep_count = self.max_messages // 2
        recent = messages[-keep_count:]
        older = messages[:-keep_count]

        # Create a summary of older messages
        summary = self._summarize_messages(older)

        # Build compacted context
        compacted_messages = [
            {"role": "system", "content": f"[Contexto resumido de {len(older)} mensagens anteriores]\n{summary}"},
            *recent,
        ]

        logger.info(f"Context compacted: {len(messages)} → {len(compacted_messages)} messages", extra={
            "props": {"agent": agent_name, "original": len(messages), "compacted": len(compacted_messages)}
        })

        return {
            "messages": compacted_messages,
            "compacted": True,
            "original_count": len(messages),
            "compacted_count": len(compacted_messages),
            "summarized_count": len(older),
        }

    def _summarize_messages(self, messages: list[dict]) -> str:
        """Create a brief summary of message history."""
        if not messages:
            return ""

        lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:200]
            lines.append(f"- [{role}]: {content}")

        # Limit summary length
        summary = "\n".join(lines[:30])
        if len(lines) > 30:
            summary += f"\n... e mais {len(lines) - 30} mensagens."

        return summary

    def estimate_tokens(self, messages: list[dict]) -> int:
        """Rough token estimation (4 chars ≈ 1 token)."""
        total_chars = sum(len(msg.get("content", "")) for msg in messages)
        return total_chars // 4


class QueryCache:
    """
    In-memory LRU cache for frequent queries.
    Reduces redundant LLM calls for repeated questions.
    """

    def __init__(self, max_size: int = 500, ttl_seconds: int = 3600):
        self._cache: dict[str, dict] = {}  # key → {value, timestamp}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> str | None:
        """Get cached value if exists and not expired."""
        entry = self._cache.get(key)
        if not entry:
            self._misses += 1
            return None

        age = (datetime.now(timezone.utc) - entry["timestamp"]).total_seconds()
        if age > self.ttl_seconds:
            del self._cache[key]
            self._misses += 1
            return None

        self._hits += 1
        return entry["value"]

    def set(self, key: str, value: str):
        """Cache a value."""
        # Evict oldest if at capacity
        if len(self._cache) >= self.max_size:
            oldest = min(self._cache, key=lambda k: self._cache[k]["timestamp"])
            del self._cache[oldest]

        self._cache[key] = {
            "value": value,
            "timestamp": datetime.now(timezone.utc),
        }

    def invalidate(self, key: str):
        """Remove a specific cache entry."""
        self._cache.pop(key, None)

    def clear(self):
        """Clear entire cache."""
        self._cache.clear()

    def get_stats(self) -> dict:
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.1f}%",
        }


# Singletons
session_pruner = SessionPruner()
context_compactor = ContextCompactor()
query_cache = QueryCache()
