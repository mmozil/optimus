"""
Agent Optimus — Embedding Service.
Generates embeddings using Gemini Text Embedding 004.
Handles batching, caching, and storage in PGvector.
"""

import logging
from typing import Any

# Optional dependency - gracefully degrade if not available
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None

from src.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Generates and manages text embeddings.
    Uses Gemini Text Embedding 004 (768 dimensions).
    """

    def __init__(self):
        if GENAI_AVAILABLE and settings.GOOGLE_API_KEY:
            genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.model = settings.EMBEDDING_MODEL
        self.dimensions = settings.EMBEDDING_DIMENSIONS

    async def embed_text(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed
            task_type: RETRIEVAL_DOCUMENT | RETRIEVAL_QUERY | SEMANTIC_SIMILARITY
        """
        if not GENAI_AVAILABLE:
            logger.warning("google.generativeai not available, returning empty embedding")
            return []

        try:
            result = genai.embed_content(
                model=f"models/{self.model}",
                content=text,
                task_type=task_type,
            )
            embedding = result["embedding"]

            logger.debug(f"Embedding generated: {len(text)} chars → {len(embedding)} dims")
            return embedding

        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            raise

    async def embed_batch(
        self,
        texts: list[str],
        task_type: str = "RETRIEVAL_DOCUMENT",
        batch_size: int = 100,
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts in batches."""
        if not GENAI_AVAILABLE:
            logger.warning("google.generativeai not available, returning empty embeddings")
            return [[] for _ in texts]

        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                result = genai.embed_content(
                    model=f"models/{self.model}",
                    content=batch,
                    task_type=task_type,
                )
                all_embeddings.extend(result["embedding"])
            except Exception as e:
                logger.error(f"Batch embedding failed at index {i}: {e}")
                # Fill failed batch with None
                all_embeddings.extend([None] * len(batch))

        return all_embeddings

    async def store_embedding(
        self,
        db_session: Any,
        content: str,
        embedding: list[float],
        source_type: str,
        source_id: str = "",
        agent_id: str | None = None,
        metadata: dict | None = None,
    ):
        """Store an embedding in the database."""
        from sqlalchemy import text

        if not embedding:
            logger.warning("store_embedding skipped: empty embedding vector")
            return

        try:
            await db_session.execute(
                text("""
                    INSERT INTO embeddings (content, embedding, source_type, source_id, agent_id, metadata)
                    VALUES (:content, CAST(:embedding AS vector), :source_type, :source_id,
                            (SELECT id FROM agents WHERE name = :agent_name),
                            :metadata)
                """),
                {
                    "content": content,
                    "embedding": str(embedding),  # '[0.1, -0.2, ...]' → cast to vector
                    "source_type": source_type,
                    "source_id": source_id,
                    "agent_name": agent_id or "",
                    "metadata": str(metadata or {}),
                },
            )
            await db_session.commit()
        except Exception as e:
            logger.error(f"Failed to store embedding: {e}")
            await db_session.rollback()

    async def semantic_search(
        self,
        db_session: Any,
        query: str,
        source_type: str | None = None,
        limit: int = 5,
        threshold: float = 0.7,
    ) -> list[dict]:
        """
        Search for similar content using cosine similarity.

        Args:
            db_session: Async DB session
            query: Search query
            source_type: Filter by source type (optional)
            limit: Max results
            threshold: Minimum similarity (0.0-1.0)
        """
        # Generate query embedding
        query_embedding = await self.embed_text(query, task_type="RETRIEVAL_QUERY")

        from sqlalchemy import text

        # Guard: empty embedding means API failed — skip DB query
        if not query_embedding:
            logger.warning("Semantic search skipped: empty query embedding")
            return []

        # Build query with optional source filter
        # NOTE: explicit ::vector cast required — PGvector <=> operator does not
        # auto-cast text parameters, causing silent failure without it.
        where_clause = ""
        params = {"query_embedding": str(query_embedding), "threshold": threshold, "limit": limit}

        if source_type:
            where_clause = "AND source_type = :source_type"
            params["source_type"] = source_type

        sql = text(f"""
            SELECT content, source_type, source_id, metadata,
                   1 - (embedding <=> CAST(:query_embedding AS vector)) as similarity
            FROM embeddings
            WHERE 1 - (embedding <=> CAST(:query_embedding AS vector)) > :threshold
            {where_clause}
            ORDER BY similarity DESC
            LIMIT :limit
        """)

        try:
            result = await db_session.execute(sql, params)
            rows = result.fetchall()

            return [
                {
                    "content": row.content,
                    "source_type": row.source_type,
                    "source_id": row.source_id,
                    "similarity": round(row.similarity, 4),
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []


# Singleton
embedding_service = EmbeddingService()
