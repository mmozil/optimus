"""
Agent Optimus — Embedding Service.
Generates embeddings using Gemini Text Embedding 004.
Handles batching, caching, and storage in PGvector.

FASE 13 fix: migrado de google-generativeai (descontinuado)
para google-genai (novo SDK) — API client-based.
"""

import logging
from typing import Any

from src.core.config import settings

logger = logging.getLogger(__name__)

# Try new google-genai SDK (google-genai package)
try:
    from google import genai as _google_genai
    # gemini-embedding-001 is available on v1beta (SDK default) — no http_options needed
    _genai_client = _google_genai.Client(
        api_key=settings.GOOGLE_API_KEY,
    ) if settings.GOOGLE_API_KEY else None
    GENAI_AVAILABLE = _genai_client is not None
except Exception:
    _genai_client = None
    GENAI_AVAILABLE = False

if not GENAI_AVAILABLE:
    logger.warning("EmbeddingService: google-genai client unavailable — embeddings disabled")


class EmbeddingService:
    """
    Generates and manages text embeddings.
    Uses Gemini Text Embedding 004 (768 dimensions).
    Uses the new google-genai SDK (google-genai package).
    """

    def __init__(self):
        self.model = settings.EMBEDDING_MODEL      # "text-embedding-004"
        self.dimensions = settings.EMBEDDING_DIMENSIONS  # 768

    async def embed_text(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed
            task_type: RETRIEVAL_DOCUMENT | RETRIEVAL_QUERY | SEMANTIC_SIMILARITY
        """
        if not GENAI_AVAILABLE or not _genai_client:
            logger.warning("embed_text skipped: google-genai client not available")
            return []

        try:
            result = _genai_client.models.embed_content(
                model=self.model,
                contents=text,
            )
            embedding = list(result.embeddings[0].values)
            # Truncate to target dimensions for schema compatibility (vector(768))
            if len(embedding) > self.dimensions:
                embedding = embedding[:self.dimensions]
            logger.debug(f"Embedding generated: {len(text)} chars → {len(embedding)} dims")
            return embedding

        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            return []

    async def embed_batch(
        self,
        texts: list[str],
        task_type: str = "RETRIEVAL_DOCUMENT",
        batch_size: int = 100,
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts in batches."""
        if not GENAI_AVAILABLE or not _genai_client:
            logger.warning("embed_batch skipped: google-genai client not available")
            return [[] for _ in texts]

        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                result = _genai_client.models.embed_content(
                    model=self.model,
                    contents=batch,
                )
                for emb in result.embeddings:
                    vals = list(emb.values)
                    if len(vals) > self.dimensions:
                        vals = vals[:self.dimensions]
                    all_embeddings.append(vals)
            except Exception as e:
                logger.error(f"Batch embedding failed at index {i}: {e}")
                all_embeddings.extend([[] for _ in batch])

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
        if not embedding:
            logger.warning("store_embedding skipped: empty embedding vector")
            return

        from sqlalchemy import text

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

        # Guard: empty embedding means API failed — skip DB query
        if not query_embedding:
            logger.warning("Semantic search skipped: empty query embedding")
            return []

        from sqlalchemy import text

        # NOTE: explicit CAST required — PGvector <=> operator does not
        # auto-cast text parameters, causing silent failure without it.
        where_clause = ""
        params: dict = {"query_embedding": str(query_embedding), "threshold": threshold, "limit": limit}

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
