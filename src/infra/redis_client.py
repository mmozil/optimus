"""
Agent Optimus — Redis client.
Connection pool, rate limiting, and session cache.
"""

import redis.asyncio as aioredis

from src.core.config import settings

redis_pool = aioredis.ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=20,
    decode_responses=True,
)

redis_client = aioredis.Redis(connection_pool=redis_pool)


async def get_redis() -> aioredis.Redis:
    """Dependency injection for Redis."""
    return redis_client


def current_minute() -> str:
    """Returns current minute as string for rate limit keys."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M")


# ============================================
# Agent Rate Limiter (Anti-429)
# ============================================
RATE_LIMITS = {
    "lead": {"rpm": 10, "rpd": 500},
    "specialist": {"rpm": 5, "rpd": 200},
    "intern": {"rpm": 2, "rpd": 50},
}


class AgentRateLimiter:
    """Per-agent rate limiter using Redis counters."""

    def __init__(self, redis: aioredis.Redis):
        self.redis = redis

    async def can_call_llm(self, agent_id: str, level: str = "specialist") -> bool:
        """Check if agent is within rate limits. Returns True if allowed."""
        limits = RATE_LIMITS.get(level, RATE_LIMITS["specialist"])

        # Check per-minute limit
        minute_key = f"rate:{agent_id}:{current_minute()}"
        current = await self.redis.incr(minute_key)
        if current == 1:
            await self.redis.expire(minute_key, 120)  # 2min TTL for safety

        if current > limits["rpm"]:
            return False

        # Check daily limit
        from datetime import datetime, timezone
        day_key = f"rate:daily:{agent_id}:{datetime.now(timezone.utc).strftime('%Y%m%d')}"
        daily = await self.redis.incr(day_key)
        if daily == 1:
            await self.redis.expire(day_key, 86400 + 60)  # 24h + 1min buffer

        return daily <= limits["rpd"]

    async def get_usage(self, agent_id: str, level: str = "specialist") -> dict:
        """Get current usage stats for an agent."""
        limits = RATE_LIMITS.get(level, RATE_LIMITS["specialist"])

        minute_key = f"rate:{agent_id}:{current_minute()}"
        minute_count = int(await self.redis.get(minute_key) or 0)

        from datetime import datetime, timezone
        day_key = f"rate:daily:{agent_id}:{datetime.now(timezone.utc).strftime('%Y%m%d')}"
        daily_count = int(await self.redis.get(day_key) or 0)

        return {
            "agent_id": agent_id,
            "level": level,
            "minute": {"used": minute_count, "limit": limits["rpm"]},
            "daily": {"used": daily_count, "limit": limits["rpd"]},
        }
