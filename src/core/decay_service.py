"""
Agent Optimus — Temporal Decay Service (FASE 14).
Aplica decaimento temporal no score de relevância dos embeddings.

Fórmula:
    recency_factor = exp(-LAMBDA * days_since_access)
    access_factor  = min(2.0, 1.0 + 0.1 * access_count)   # boost por uso, max 2x
    final_score    = similarity * recency_factor * access_factor

Onde:
    LAMBDA = 0.01 → half-life ~69 dias (ao fim de 6 meses, fator ≈ 0.16)

Call Path:
    embedding_service.semantic_search() → decay_service.apply_decay(results)
      → resultados reordenados por final_score

    asyncio.create_task(decay_service.record_access(ids))
      → UPDATE embeddings SET last_accessed_at=now(), access_count+=1

Cron:
    CRON_TRIGGERED("decay_archiving") → decay_service.archive_stale(threshold=0.05)
      → UPDATE embeddings SET archived=true WHERE final_score_estimate < threshold
"""

import logging
import math
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Decay constant: exp(-LAMBDA * days) → half-life = ln(2)/LAMBDA ≈ 69 days
LAMBDA = 0.01
# Archive threshold: entries with estimated score below this are archived
ARCHIVE_THRESHOLD = 0.05
# Minimum days before an entry can be archived (avoid archiving fresh entries)
MIN_AGE_DAYS = 30


def _days_since(dt: datetime | None) -> float:
    """Days elapsed since a datetime (defaults to 0 if None = never accessed)."""
    if dt is None:
        return 0.0
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0.0, (now - dt).total_seconds() / 86400.0)


def recency_factor(last_accessed_at: datetime | None, created_at: datetime | None = None) -> float:
    """
    Recency factor: exp(-LAMBDA * days_since_last_access).
    Uses created_at as fallback if never accessed.
    """
    ref_dt = last_accessed_at or created_at
    days = _days_since(ref_dt)
    return math.exp(-LAMBDA * days)


def access_factor(access_count: int) -> float:
    """
    Access boost: entries accessed more often are more relevant.
    Scales from 1.0 (never accessed) to 2.0 (accessed 10+ times).
    """
    return min(2.0, 1.0 + 0.1 * access_count)


def compute_score(
    similarity: float,
    last_accessed_at: datetime | None,
    access_count: int,
    created_at: datetime | None = None,
) -> float:
    """
    Final relevance score combining similarity, recency, and access frequency.

    final_score = similarity * recency_factor * access_factor
    """
    rf = recency_factor(last_accessed_at, created_at)
    af = access_factor(access_count)
    return similarity * rf * af


def apply_decay(results: list[dict]) -> list[dict]:
    """
    Re-rank semantic search results by decay-adjusted score.

    Each result dict should have:
        similarity, last_accessed_at (str/datetime/None), access_count (int), created_at

    Returns the same list sorted by final_score DESC, with final_score added.
    """
    for r in results:
        # Parse datetimes from ISO strings if needed
        laa = r.get("last_accessed_at")
        if isinstance(laa, str):
            try:
                laa = datetime.fromisoformat(laa)
            except (ValueError, TypeError):
                laa = None

        cat = r.get("created_at")
        if isinstance(cat, str):
            try:
                cat = datetime.fromisoformat(cat)
            except (ValueError, TypeError):
                cat = None

        sim = float(r.get("similarity", 0.0))
        cnt = int(r.get("access_count") or 0)
        r["final_score"] = round(compute_score(sim, laa, cnt, cat), 4)
        r["recency_factor"] = round(recency_factor(laa, cat), 4)

    results.sort(key=lambda x: x["final_score"], reverse=True)
    return results


class DecayService:
    """
    Manages temporal decay for the embeddings table.

    Methods:
        record_access(ids)    — fire-and-forget: updates last_accessed_at + access_count
        archive_stale(thresh) — weekly cron: archives entries below threshold
        get_stats()           — monitoring: returns decay statistics
    """

    async def record_access(self, embedding_ids: list[str]) -> None:
        """
        Update access metadata for returned embeddings.
        Called fire-and-forget from semantic_search.
        """
        if not embedding_ids:
            return
        try:
            from src.infra.supabase_client import get_async_session
            from sqlalchemy import text

            async with get_async_session() as db:
                await db.execute(
                    text("""
                        UPDATE embeddings
                        SET last_accessed_at = now(),
                            access_count     = access_count + 1
                        WHERE id = ANY(:ids)
                    """),
                    {"ids": embedding_ids},
                )
                await db.commit()
            logger.debug(f"FASE 14: access recorded for {len(embedding_ids)} embeddings")
        except Exception as e:
            logger.warning(f"FASE 14: record_access failed (non-critical): {e}")

    async def archive_stale(self, threshold: float = ARCHIVE_THRESHOLD) -> dict:
        """
        Weekly cron task: archive embeddings with low relevance score.

        An entry is considered stale when:
          - age >= MIN_AGE_DAYS
          - recency_factor is low AND access_count is 0
          - estimated final_score (at similarity=1.0) < threshold

        Marks entries with archived=true (soft delete, recoverable).
        Returns summary dict.
        """
        try:
            from src.infra.supabase_client import get_async_session
            from sqlalchemy import text

            # threshold = exp(-LAMBDA * days) → solve for days
            # days_threshold = -ln(threshold) / LAMBDA
            if threshold <= 0:
                threshold = ARCHIVE_THRESHOLD
            days_threshold = -math.log(max(threshold, 1e-9)) / LAMBDA

            async with get_async_session() as db:
                result = await db.execute(
                    text("""
                        UPDATE embeddings
                        SET archived = TRUE
                        WHERE archived = FALSE
                          AND access_count = 0
                          AND EXTRACT(EPOCH FROM (
                              now() - COALESCE(last_accessed_at, created_at)
                          )) / 86400.0 >= :days_threshold
                        RETURNING id
                    """),
                    {"days_threshold": days_threshold},
                )
                archived_ids = result.fetchall()
                await db.commit()

            count = len(archived_ids)
            logger.info(
                f"FASE 14: Archived {count} stale embeddings "
                f"(threshold={threshold}, min_age={days_threshold:.0f} days)"
            )
            return {
                "archived": count,
                "threshold": threshold,
                "min_age_days": round(days_threshold, 1),
            }

        except Exception as e:
            logger.error(f"FASE 14: archive_stale failed: {e}")
            return {"archived": 0, "error": str(e)}

    async def get_stats(self) -> dict:
        """Return decay statistics for monitoring."""
        try:
            from src.infra.supabase_client import get_async_session
            from sqlalchemy import text

            async with get_async_session() as db:
                row = (await db.execute(text("""
                    SELECT
                        COUNT(*) FILTER (WHERE archived = FALSE) AS active,
                        COUNT(*) FILTER (WHERE archived = TRUE)  AS archived,
                        AVG(access_count) FILTER (WHERE archived = FALSE) AS avg_access,
                        AVG(EXTRACT(EPOCH FROM (now() - COALESCE(last_accessed_at, created_at)))/86400.0)
                            FILTER (WHERE archived = FALSE) AS avg_age_days
                    FROM embeddings
                """))).fetchone()

            return {
                "active": int(row[0] or 0),
                "archived": int(row[1] or 0),
                "avg_access_count": round(float(row[2] or 0), 2),
                "avg_age_days": round(float(row[3] or 0), 1),
                "lambda": LAMBDA,
                "archive_threshold": ARCHIVE_THRESHOLD,
            }
        except Exception as e:
            logger.warning(f"FASE 14: get_stats failed: {e}")
            return {"error": str(e)}


# Singleton
decay_service = DecayService()
