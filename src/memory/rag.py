"""
Agent Optimus — RAG Pipeline.
Retrieval-Augmented Generation using semantic chunking + PGvector search.
"""

import logging
import re
from typing import Any

from src.memory.embeddings import embedding_service

logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    Complete RAG pipeline:
    1. Chunking (semantic)
    2. Embedding + storage
    3. Retrieval (similarity search)
    4. Context augmentation
    """

    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 100,
        similarity_threshold: float = 0.7,
        max_results: int = 5,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.similarity_threshold = similarity_threshold
        self.max_results = max_results

    # ============================================
    # Ingestion
    # ============================================

    def chunk_text(self, text: str) -> list[str]:
        """
        Split text into semantic chunks.
        Uses paragraph boundaries and heading boundaries for better coherence.
        """
        if not text.strip():
            return []

        # First, split by headings and double newlines (semantic boundaries)
        sections = re.split(r'\n(?=#{1,3}\s)|(?:\n\s*\n)', text)
        sections = [s.strip() for s in sections if s.strip()]

        chunks = []
        current_chunk = ""

        for section in sections:
            # If section fits in current chunk, append
            if len(current_chunk) + len(section) < self.chunk_size:
                current_chunk += "\n\n" + section if current_chunk else section
            else:
                # Save current chunk and start new one
                if current_chunk:
                    chunks.append(current_chunk)

                # If section itself is too long, split by sentences
                if len(section) > self.chunk_size:
                    sub_chunks = self._split_long_section(section)
                    chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = section

        # Don't forget last chunk
        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _split_long_section(self, text: str) -> list[str]:
        """Split a long section by sentences, respecting chunk_size."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current = ""

        for sentence in sentences:
            if len(current) + len(sentence) < self.chunk_size:
                current += " " + sentence if current else sentence
            else:
                if current:
                    chunks.append(current)
                current = sentence

        if current:
            chunks.append(current)

        return chunks

    async def ingest_document(
        self,
        db_session: Any,
        content: str,
        source_type: str = "document",
        source_id: str = "",
        agent_name: str | None = None,
    ) -> int:
        """
        Ingest a document into the RAG system.
        Chunks, embeds, and stores in PGvector.

        Returns:
            Number of chunks ingested.
        """
        chunks = self.chunk_text(content)
        if not chunks:
            return 0

        logger.info(f"RAG ingestion: {len(chunks)} chunks from {source_type}/{source_id}")

        # Batch embed all chunks
        embeddings = await embedding_service.embed_batch(chunks)

        # Store each chunk with its embedding
        stored = 0
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            if embedding is None:
                continue

            await embedding_service.store_embedding(
                db_session=db_session,
                content=chunk,
                embedding=embedding,
                source_type=source_type,
                source_id=f"{source_id}#chunk-{i}",
                agent_id=agent_name,
                metadata={"chunk_index": i, "total_chunks": len(chunks)},
            )
            stored += 1

        logger.info(f"RAG ingestion complete: {stored}/{len(chunks)} chunks stored")
        return stored

    # ============================================
    # Retrieval
    # ============================================

    async def retrieve(
        self,
        db_session: Any,
        query: str,
        source_type: str | None = None,
    ) -> list[dict]:
        """
        Retrieve relevant chunks for a query.
        Returns chunks sorted by similarity.
        """
        results = await embedding_service.semantic_search(
            db_session=db_session,
            query=query,
            source_type=source_type,
            limit=self.max_results,
            threshold=self.similarity_threshold,
        )

        if not results:
            logger.debug(f"RAG: No results above threshold {self.similarity_threshold} for query")
            return []

        logger.info(f"RAG: Retrieved {len(results)} chunks (best similarity: {results[0]['similarity']})")
        return results

    async def augment_prompt(
        self,
        db_session: Any,
        query: str,
        source_type: str | None = None,
    ) -> str:
        """
        Generate RAG-augmented context for a prompt.
        Returns formatted context string or empty string.
        """
        results = await self.retrieve(db_session, query, source_type)

        if not results:
            return ""

        context_parts = []
        for i, result in enumerate(results, 1):
            similarity_pct = f"{result['similarity'] * 100:.0f}%"
            context_parts.append(
                f"[Fonte {i} — {result['source_type']}, relevância {similarity_pct}]\n{result['content']}"
            )

        return "## Contexto RAG (informações relevantes encontradas)\n\n" + "\n\n---\n\n".join(context_parts)


# Singleton
rag_pipeline = RAGPipeline()
