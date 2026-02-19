"""
Agent Optimus — Knowledge API (FASE 0 #10: Collective Intelligence).
REST endpoints for cross-agent knowledge sharing.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.core.contradiction_service import ContradictionDetected
from src.memory.collective_intelligence import SharedKnowledge, collective_intelligence

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


# ============================================
# Request/Response Models
# ============================================


class ShareKnowledgeRequest(BaseModel):
    """Request to share knowledge."""

    agent: str = Field(..., description="Agent sharing the knowledge")
    topic: str = Field(..., description="Topic of the learning")
    learning: str = Field(..., description="Learning content")


class SharedKnowledgeResponse(BaseModel):
    """Response containing shared knowledge."""

    source_agent: str
    topic: str
    learning: str
    timestamp: str
    used_by: list[str]
    upvotes: int

    @classmethod
    def from_shared_knowledge(cls, sk: SharedKnowledge) -> "SharedKnowledgeResponse":
        return cls(
            source_agent=sk.source_agent,
            topic=sk.topic,
            learning=sk.learning,
            timestamp=sk.timestamp,
            used_by=sk.used_by,
            upvotes=sk.upvotes,
        )


class KnowledgeStatsResponse(BaseModel):
    """Response containing knowledge statistics."""

    total_shared: int
    unique_agents: int
    unique_topics: int
    most_used: list[dict]


# ============================================
# API Endpoints
# ============================================


@router.post("/share", response_model=SharedKnowledgeResponse | dict)
async def share_knowledge(
    request: ShareKnowledgeRequest,
    force: bool = Query(False, description="Se true, ignora detecção de contradição e salva mesmo assim"),
) -> Any:
    """
    Share a learning to the collective intelligence.

    FASE 15: Detecta contradições com conhecimento existente antes de salvar.
    - Se contradição detectada → HTTP 409 com detalhes (existing, new, explanation).
    - Use ?force=true para salvar mesmo assim.

    Returns the SharedKnowledge if new, or {"duplicate": true} if already exists.
    """
    try:
        # FASE 11: use async_share so learning is persisted to PGvector embeddings table
        # FASE 15: contradiction check happens inside async_share (unless force=True)
        sk = await collective_intelligence.async_share(
            agent_name=request.agent,
            topic=request.topic,
            learning=request.learning,
            force=force,
        )

        if sk is None:
            return {"duplicate": True, "message": "Learning already exists (duplicate content)"}

        logger.info(f"Knowledge shared via API: {request.agent} → {request.topic}")
        return SharedKnowledgeResponse.from_shared_knowledge(sk)

    except ContradictionDetected as exc:
        r = exc.result
        logger.warning(
            f"FASE 15: API rejecting contradictory knowledge from '{request.agent}' "
            f"on '{request.topic}' — {r.explanation[:80]}"
        )
        raise HTTPException(
            status_code=409,
            detail={
                "type": "contradiction",
                "existing": r.existing_content[:300],
                "new": r.new_content[:300],
                "similarity": round(r.similarity, 3),
                "explanation": r.explanation,
                "hint": "Use ?force=true para salvar mesmo assim",
            },
        )


@router.get("/query", response_model=list[SharedKnowledgeResponse])
async def query_knowledge(
    topic: str = Query(..., description="Topic to search for"),
    agent: str = Query("", description="Requesting agent (for usage tracking)"),
    semantic: bool = Query(True, description="Use semantic search (PGvector); falls back to keyword if unavailable"),
) -> list[SharedKnowledgeResponse]:
    """
    Query shared knowledge by topic.

    FASE 13: Semantic search (PGvector cosine similarity) is now the DEFAULT.
    Falls back automatically to keyword search if embeddings service is unavailable.
    Set semantic=false to force keyword-only search.
    """
    if semantic:
        results = await collective_intelligence.query_semantic(topic, requesting_agent=agent)
    else:
        results = collective_intelligence.query(topic, requesting_agent=agent)

    logger.info(f"Knowledge query: topic='{topic}', results={len(results)}, semantic={semantic}")

    return [SharedKnowledgeResponse.from_shared_knowledge(sk) for sk in results]


@router.post("/index")
async def index_knowledge_to_pgvector() -> dict:
    """
    FASE 13: Batch-index all in-memory knowledge entries to PGvector.

    Use this endpoint once to migrate existing knowledge entries that were
    shared before PGvector persistence was added (i.e., via sync share()).
    Call path: POST /api/v1/knowledge/index → collective_intelligence.index_knowledge()
    """
    try:
        count = await collective_intelligence.index_knowledge()
        logger.info(f"FASE 13: Batch indexed {count} knowledge entries to PGvector")
        return {
            "status": "success",
            "indexed": count,
            "message": f"{count} knowledge entries indexadas no PGvector.",
        }
    except Exception as e:
        logger.error(f"FASE 13: Batch index failed: {e}")
        raise HTTPException(status_code=500, detail=f"Indexação falhou: {e}")


@router.get("/stats", response_model=KnowledgeStatsResponse)
async def get_knowledge_stats() -> KnowledgeStatsResponse:
    """
    Get collective intelligence statistics.

    Returns total shared knowledge, unique agents, unique topics, and most used learnings.
    """
    stats = collective_intelligence.get_stats()

    # Convert most_used SharedKnowledge objects to dicts
    most_used_dicts = []
    for sk in stats.get("most_used", []):
        most_used_dicts.append({
            "source_agent": sk.source_agent,
            "topic": sk.topic,
            "learning": sk.learning[:100] + "..." if len(sk.learning) > 100 else sk.learning,
            "used_by_count": len(sk.used_by),
        })

    return KnowledgeStatsResponse(
        total_shared=stats["total_shared"],
        unique_agents=stats["unique_agents"],
        unique_topics=stats["unique_topics"],
        most_used=most_used_dicts,
    )


@router.get("/expert")
async def find_expert(topic: str = Query(..., description="Topic to find expert for")) -> dict:
    """
    Find the agent with most knowledge on a topic.

    Returns the expert agent name or null if no knowledge exists.
    """
    expert = collective_intelligence.find_expert(topic)

    if expert is None:
        raise HTTPException(status_code=404, detail=f"No knowledge found for topic: {topic}")

    logger.info(f"Expert query: topic='{topic}', expert='{expert}'")

    return {"topic": topic, "expert": expert}


@router.get("/graph")
async def get_knowledge_graph() -> dict[str, list[str]]:
    """
    Get the knowledge graph mapping agents to their topics.

    Returns a dict: agent_name → list of topics.
    """
    graph = collective_intelligence.get_knowledge_graph()

    logger.info(f"Knowledge graph requested: {len(graph)} agents")

    return graph
