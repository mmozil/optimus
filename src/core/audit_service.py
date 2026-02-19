"""
Agent Optimus — Audit Service (FASE 12).
Persists react_steps from the ReAct loop to audit_log for observability and debug.

Call Path:
  gateway.route_message() → agent.think() → result (with react_steps)
    → asyncio.create_task(audit_service.save(session_id, agent, steps, usage))
      → INSERT INTO audit_log (per step + summary row)

Query:
  GET /api/v1/audit/{session_id}
    → audit_service.get_steps(session_id)
      → SELECT FROM audit_log WHERE session_id = :sid ORDER BY created_at
"""

import logging
from dataclasses import asdict
from uuid import UUID

logger = logging.getLogger(__name__)


class AuditService:
    """
    Persists ReAct loop steps to audit_log table.
    Falls back gracefully if DB is unavailable.
    """

    async def save(
        self,
        session_id: str,
        agent: str,
        steps: list,
        usage: dict | None = None,
        model: str = "",
    ) -> None:
        """
        Persist all react_steps + a summary row to audit_log.
        Fire-and-forget: caller uses asyncio.create_task().
        """
        if not steps and not usage:
            return

        try:
            from src.infra.supabase_client import get_async_session
            from sqlalchemy import text

            # Convert session_id to UUID safely
            try:
                sid = str(UUID(session_id))
            except (ValueError, AttributeError):
                logger.debug(f"FASE 12: Invalid session_id for audit: {session_id}")
                return

            rows = []

            # One row per ReActStep
            for step in steps:
                # Support both dataclass and dict
                if hasattr(step, "__dataclass_fields__"):
                    step_dict = asdict(step)
                else:
                    step_dict = dict(step)

                # Truncate content to avoid huge DB rows
                content = str(step_dict.get("result", "") or step_dict.get("error", ""))[:4000]
                if not content:
                    content = step_dict.get("type", "")

                rows.append({
                    "session_id": sid,
                    "agent": agent[:100],
                    "step_type": step_dict.get("type", "unknown")[:50],
                    "tool_name": (step_dict.get("tool_name") or "")[:100],
                    "content": content,
                    "success": bool(step_dict.get("success", True)),
                    "duration_ms": float(step_dict.get("duration_ms", 0)),
                    "iteration": int(step_dict.get("iteration", 0)),
                })

            # Summary row with token usage
            if usage:
                prompt_t = usage.get("prompt_tokens", 0)
                comp_t = usage.get("completion_tokens", 0)
                rows.append({
                    "session_id": sid,
                    "agent": agent[:100],
                    "step_type": "summary",
                    "tool_name": model[:100] if model else "",
                    "content": (
                        f"tokens: {prompt_t + comp_t} total "
                        f"(prompt={prompt_t}, completion={comp_t})"
                    ),
                    "success": True,
                    "duration_ms": 0,
                    "iteration": 0,
                })

            if not rows:
                return

            async with get_async_session() as db:
                await db.execute(
                    text("""
                        INSERT INTO audit_log
                            (session_id, agent, step_type, tool_name, content, success, duration_ms, iteration)
                        VALUES
                            (:session_id, :agent, :step_type, :tool_name, :content, :success, :duration_ms, :iteration)
                    """),
                    rows,
                )
                await db.commit()

            logger.debug(f"FASE 12: Saved {len(rows)} audit rows for session {sid[:8]}")

        except Exception as e:
            # Graceful fallback — audit failure must not disrupt main flow
            logger.warning(f"FASE 12: Audit save failed (non-critical): {e}")

    async def get_steps(
        self,
        session_id: str,
        limit: int = 200,
    ) -> list[dict]:
        """
        Retrieve audit log rows for a given session_id.
        Returns list of dicts, ordered by created_at ASC.
        """
        try:
            from src.infra.supabase_client import get_async_session
            from sqlalchemy import text

            try:
                sid = str(UUID(session_id))
            except (ValueError, AttributeError):
                return []

            async with get_async_session() as db:
                result = await db.execute(
                    text("""
                        SELECT
                            id,
                            session_id,
                            agent,
                            step_type,
                            tool_name,
                            content,
                            success,
                            duration_ms,
                            iteration,
                            created_at
                        FROM audit_log
                        WHERE session_id = :sid
                        ORDER BY created_at ASC
                        LIMIT :lim
                    """),
                    {"sid": sid, "lim": limit},
                )
                rows = result.fetchall()

            return [
                {
                    "id": str(r[0]),
                    "session_id": str(r[1]),
                    "agent": r[2],
                    "step_type": r[3],
                    "tool_name": r[4],
                    "content": r[5],
                    "success": r[6],
                    "duration_ms": r[7],
                    "iteration": r[8],
                    "created_at": r[9].isoformat() if r[9] else None,
                }
                for r in rows
            ]

        except Exception as e:
            logger.warning(f"FASE 12: Audit query failed: {e}")
            return []

    async def get_sessions_summary(self, limit: int = 50) -> list[dict]:
        """
        Returns the most recent sessions with step counts (for a dashboard view).
        """
        try:
            from src.infra.supabase_client import get_async_session
            from sqlalchemy import text

            async with get_async_session() as db:
                result = await db.execute(
                    text("""
                        SELECT
                            session_id,
                            MAX(agent) AS agent,
                            COUNT(*) AS step_count,
                            MIN(created_at) AS started_at,
                            MAX(created_at) AS last_at
                        FROM audit_log
                        GROUP BY session_id
                        ORDER BY last_at DESC
                        LIMIT :lim
                    """),
                    {"lim": limit},
                )
                rows = result.fetchall()

            return [
                {
                    "session_id": str(r[0]),
                    "agent": r[1],
                    "step_count": r[2],
                    "started_at": r[3].isoformat() if r[3] else None,
                    "last_at": r[4].isoformat() if r[4] else None,
                }
                for r in rows
            ]

        except Exception as e:
            logger.warning(f"FASE 12: Audit sessions query failed: {e}")
            return []


# Singleton
audit_service = AuditService()
