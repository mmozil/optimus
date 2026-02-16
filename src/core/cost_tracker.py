"""
Agent Optimus — Cost Tracker (Phase 16).
Tracks token usage and calculates costs in USD based on model pricing.
Enforces daily/monthly budgets per tenant.
"""

import logging
from datetime import datetime
from sqlalchemy import text

from src.core.config import settings
from src.infra.supabase_client import get_async_session

logger = logging.getLogger(__name__)


# ============================================
# Pricing Table (USD per 1M tokens)
# Source: Google/OpenAI pricing pages (approx)
# ============================================
PRICING = {
    "gemini-2.0-flash-exp": {"input": 0.00, "output": 0.00},  # Free preview
    "gemini-1.5-pro-002":   {"input": 1.25, "output": 5.00},
    "gemini-1.5-flash-002": {"input": 0.075, "output": 0.30},
    "gemini-1.5-pro":       {"input": 3.50, "output": 10.50},
    "gemini-1.5-flash":     {"input": 0.075, "output": 0.30},
    "gpt-4o":               {"input": 2.50, "output": 10.00},
    "gpt-4o-mini":          {"input": 0.15, "output": 0.60},
}


class CostTracker:
    """
    Tracks and enforces cost limits for AI usage.
    """

    def calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost in USD for a given usage."""
        price = PRICING.get(model)
        if not price:
            # Fallback to flash pricing if unknown
            price = PRICING["gemini-1.5-flash"]
            logger.warning(f"Sort of unknown model '{model}', using fallback pricing.")

        input_cost = (prompt_tokens / 1_000_000) * price["input"]
        output_cost = (completion_tokens / 1_000_000) * price["output"]
        
        return input_cost + output_cost

    async def track_usage(
        self,
        user_id: str,
        agent_name: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ):
        """
        Record usage and update budgets.
        Fire-and-forget (async) to not block the main response path ideally.
        """
        if not settings.COST_TRACKING_ENABLED:
            return

        cost = self.calculate_cost(model, prompt_tokens, completion_tokens)

        try:
            async with get_async_session() as session:
                # 1. Insert entry
                await session.execute(
                    text("""
                        INSERT INTO cost_entries (user_id, agent_name, model, prompt_tokens, completion_tokens, cost_usd)
                        VALUES (:uid, :agent, :model, :pt, :ct, :cost)
                    """),
                    {
                        "uid": user_id,
                        "agent": agent_name,
                        "model": model,
                        "pt": prompt_tokens,
                        "ct": completion_tokens,
                        "cost": cost,
                    }
                )

                # 2. Update budget aggregates (simplified upsert logic)
                # In robust prod, use separate ticker/worker or Postgres triggers
                await session.execute(
                    text("""
                        INSERT INTO user_budgets (user_id, current_day_spend, current_month_spend)
                        VALUES (:uid, :cost, :cost)
                        ON CONFLICT (user_id) DO UPDATE SET
                            current_day_spend = user_budgets.current_day_spend + :cost,
                            current_month_spend = user_budgets.current_month_spend + :cost,
                            updated_at = NOW()
                    """),
                    {"uid": user_id, "cost": cost}
                )
                await session.commit()

        except Exception as e:
            logger.error(f"Failed to track cost: {e}")

    async def check_budget(self, user_id: str) -> bool:
        """
        Check if user has exceeded their budget.
        Returns True if ALLOWED, False if BLOCKED.
        """
        if not settings.COST_TRACKING_ENABLED:
            return True

        try:
            async with get_async_session() as session:
                result = await session.execute(
                    text("""
                        SELECT daily_limit_usd, monthly_limit_usd, current_day_spend, current_month_spend
                        FROM user_budgets WHERE user_id = :uid
                    """),
                    {"uid": user_id}
                )
                row = result.fetchone()
                
                if not row:
                    return True  # No budget = unlimited (or default logic)

                daily_limit, monthly_limit, day_spend, month_spend = row
                
                if day_spend > daily_limit:
                    logger.warning(f"User {user_id} exceeded daily budget")
                    return False
                
                if month_spend > monthly_limit:
                    logger.warning(f"User {user_id} exceeded monthly budget")
                    return False

                return True

        except Exception as e:
            logger.error(f"Failed to check budget: {e}")
            return True  # Fail open to avoid blocking reliable users on DB error


# Singleton
cost_tracker = CostTracker()
