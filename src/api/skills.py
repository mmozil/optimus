"""
Agent Optimus — Skills API (FASE 0 #12: Skills Discovery).
REST endpoints for skill search, suggestions, and capability gap detection.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.skills.skills_discovery import skills_discovery

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/skills", tags=["skills"])


# ============================================
# Request/Response Models
# ============================================


class SkillSearchRequest(BaseModel):
    """Request to search skills."""

    query: str = Field(..., description="Search query")
    limit: int = Field(10, description="Maximum results to return", ge=1, le=50)


class SkillMatch(BaseModel):
    """A skill match result."""

    name: str
    description: str
    category: str
    score: float
    keywords: list[str] = []


class SkillStatsResponse(BaseModel):
    """Response containing skill statistics."""

    indexed_skills: int
    total_terms: int
    categories: dict[str, int]


# ============================================
# API Endpoints
# ============================================


@router.post("/search", response_model=list[SkillMatch])
async def search_skills(request: SkillSearchRequest) -> list[SkillMatch]:
    """
    Search skills using TF-IDF keyword matching.

    Returns ranked list of skills matching the query.
    """
    try:
        results = skills_discovery.search(request.query, limit=request.limit)

        logger.info(f"Skills search: query='{request.query[:50]}', results={len(results)}")

        return [
            SkillMatch(
                name=r["name"],
                description=r.get("description", ""),
                category=r.get("category", "general"),
                score=r.get("score", 0.0),
                keywords=r.get("keywords", []),
            )
            for r in results
        ]

    except Exception as e:
        logger.error(f"Skills search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")


@router.post("/search/semantic", response_model=list[SkillMatch])
async def search_skills_semantic(request: SkillSearchRequest) -> list[SkillMatch]:
    """
    Search skills using PGvector semantic similarity.

    Falls back to keyword search if PGvector/embeddings are unavailable.
    """
    try:
        results = await skills_discovery.search_semantic(request.query, limit=request.limit)

        logger.info(
            f"Skills semantic search: query='{request.query[:50]}', results={len(results)}"
        )

        return [
            SkillMatch(
                name=r["name"],
                description=r.get("description", ""),
                category=r.get("category", "general"),
                score=r.get("score", 0.0),
                keywords=r.get("keywords", []),
            )
            for r in results
        ]

    except Exception as e:
        logger.error(f"Semantic skills search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Semantic search failed: {e}")


@router.get("/suggest", response_model=list[str])
async def suggest_skills(
    query: str = Query(..., description="User query to analyze for skill suggestions"),
) -> list[str]:
    """
    Suggest relevant skills based on a user query.

    Analyzes the query and returns skill names that might be helpful.
    """
    try:
        suggestions = skills_discovery.suggest_for_query(query)

        logger.info(f"Skills suggestions: query='{query[:50]}', suggestions={len(suggestions)}")

        return suggestions

    except Exception as e:
        logger.error(f"Skills suggestion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Suggestion failed: {e}")


@router.get("/gaps")
async def detect_capability_gaps(
    available: str = Query(..., description="Comma-separated list of available skills"),
) -> dict[str, Any]:
    """
    Detect capability gaps based on available skills.

    Suggests missing skills that complement the current skill set.
    """
    try:
        available_skills = [s.strip() for s in available.split(",") if s.strip()]

        gaps = skills_discovery.detect_capability_gap(available_skills)

        logger.info(
            f"Capability gap detection: available={len(available_skills)}, gaps={len(gaps)}"
        )

        return {
            "available_skills": available_skills,
            "missing_skills": gaps,
            "suggestions_count": len(gaps),
        }

    except Exception as e:
        logger.error(f"Capability gap detection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Gap detection failed: {e}")


@router.get("/stats", response_model=SkillStatsResponse)
async def get_skills_stats() -> SkillStatsResponse:
    """
    Get skills discovery statistics.

    Returns indexed skills count, total terms, and category breakdown.
    """
    try:
        stats = skills_discovery.get_stats()

        logger.info(f"Skills stats requested: {stats['indexed_skills']} skills indexed")

        return SkillStatsResponse(
            indexed_skills=stats["indexed_skills"],
            total_terms=stats["total_terms"],
            categories=stats["categories"],
        )

    except Exception as e:
        logger.error(f"Skills stats failed: {e}")
        raise HTTPException(status_code=500, detail=f"Stats retrieval failed: {e}")
