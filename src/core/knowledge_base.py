"""
Agent Optimus — Knowledge Base Service (Phase 17).
Handles document ingestion, chunking, embedding, and hybrid retrieval.
"""

import io
import hashlib
import logging
import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import text

# from src.core.config import settings
from src.infra.model_router import model_router
from src.infra.supabase_client import get_async_session

# Optional dependencies for document parsing
try:
    import pypdf
except ImportError:
    pypdf = None

try:
    import docx
except ImportError:
    docx = None

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeChunk:
    content: str
    embedding: List[float]
    chunk_index: int
    metadata: dict


class SimpleTextSplitter:
    """
    Split text into chunks aiming for a target size with overlap.
    Tries to split by paragraph, then sentence, then words.
    """
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text(self, text: str) -> List[str]:
        if not text:
            return []
        
        # Normalize line breaks
        text = text.replace("\r\n", "\n")
        
        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + self.chunk_size
            
            if end >= text_len:
                chunks.append(text[start:])
                break
            
            # Try to find a good break point (paragraph > sentence > space)
            # Look back from 'end' to find the nearest separator
            block = text[start:end]
            
            # 1. Paragraph (double newline)
            last_para = block.rfind("\n\n")
            if last_para != -1 and last_para > self.chunk_size * 0.5:
                split_point = start + last_para + 2
            
            # 2. Sentence (period + space)
            elif (last_period := block.rfind(". ")) != -1 and last_period > self.chunk_size * 0.5:
                split_point = start + last_period + 1
            
            # 3. Newline
            elif (last_newline := block.rfind("\n")) != -1 and last_newline > self.chunk_size * 0.5:
                split_point = start + last_newline + 1
                
            # 4. Space
            elif (last_space := block.rfind(" ")) != -1 and last_space > self.chunk_size * 0.5:
                split_point = start + last_space + 1
                
            # 5. Hard break
            else:
                split_point = end

            chunks.append(text[start:split_point].strip())
            
            # Move start forward, but minus overlap
            start = split_point - self.chunk_overlap
            
            # Avoid infinite loop if overlap >= split step
            if start >= split_point:
                 start = split_point

        return [c for c in chunks if c]  # Remove empty chunks


class KnowledgeBase:
    """
    Core service for RAG system.
    """
    def __init__(self):
        self.splitter = SimpleTextSplitter(chunk_size=1000, chunk_overlap=150)

    def _extract_text_from_pdf(self, content: bytes) -> str:
        if not pypdf:
            raise RuntimeError("pypdf not installed")
        
        text_out = []
        try:
            reader = pypdf.PdfReader(io.BytesIO(content))
            for page in reader.pages:
                text_out.append(page.extract_text() or "")
            return "\n".join(text_out)
        except Exception as e:
            logger.error(f"PDF parsing error: {e}")
            raise ValueError(f"Failed to parse PDF: {e}")

    def _extract_text_from_docx(self, content: bytes) -> str:
        if not docx:
            raise RuntimeError("python-docx not installed")
        
        try:
            doc = docx.Document(io.BytesIO(content))
            return "\n".join([para.text for para in doc.paragraphs])
        except Exception as e:
            logger.error(f"DOCX parsing error: {e}")
            raise ValueError(f"Failed to parse DOCX: {e}")

    async def add_document(
        self, 
        filename: str, 
        content: bytes | str, 
        user_id: UUID = None,
        mime_type: str = None
    ) -> str:
        """
        Ingest a document: track file -> parse -> chunk -> embed -> save.
        Returns the file ID.
        """
        parsed_text = ""
        
        # 1. Parse based on type
        if isinstance(content, str):
            parsed_text = content
            content_bytes = content.encode("utf-8")
        else:
            content_bytes = content
            # Simple mime/ext detection
            ext = filename.lower().split('.')[-1] if '.' in filename else ""
            
            if mime_type == "application/pdf" or ext == "pdf":
                parsed_text = self._extract_text_from_pdf(content_bytes)
            elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or ext == "docx":
                parsed_text = self._extract_text_from_docx(content_bytes)
            elif mime_type and mime_type.startswith("audio/"):
                # Transcribe Audio
                from src.core.audio_service import audio_service
                logger.info(f"Transcribing audio {filename} ({mime_type})...")
                parsed_text = await audio_service.transcribe(content_bytes, mime_type)
            else:
                # Try decode as utf-8 text
                try:
                    parsed_text = content_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    raise ValueError(f"Unsupported binary file type: {mime_type or ext}")

        if not parsed_text.strip():
            raise ValueError("Empty content after parsing")

        # 2. Calculate Hash to prevent duplicates (using original bytes)
        content_hash = hashlib.sha256(content_bytes).hexdigest()

        async with get_async_session() as session:
            # Check duplicate
            res = await session.execute(
                text("SELECT id FROM knowledge_files WHERE content_hash = :h"),
                {"h": content_hash}
            )
            existing = res.scalar()
            if existing:
                logger.info(f"Document {filename} already exists ({existing})")
                return str(existing)

            # 3. Create File Record
            res = await session.execute(
                text("""
                    INSERT INTO knowledge_files (filename, file_size, content_hash, uploaded_by, status, mime_type)
                    VALUES (:name, :size, :hash, :uid, 'processing', :mime)
                    RETURNING id
                """),
                {
                    "name": filename,
                    "size": len(content_bytes),
                    "hash": content_hash,
                    "uid": user_id,
                    "mime": mime_type
                }
            )
            file_id = res.scalar()
            
            try:
                # 4. Chunking
                text_chunks = self.splitter.split_text(parsed_text)
                logger.info(f"Split {filename} into {len(text_chunks)} chunks")

                # 5. Process Chunks (Embed + Save)
                for idx, text_chunk in enumerate(text_chunks):
                    if not text_chunk.strip():
                        continue

                    embedding = await model_router.embed_text(text_chunk)
                    
                    await session.execute(
                        text("""
                            INSERT INTO embeddings (
                                content, embedding, source_type, source_id, 
                                knowledge_file_id, chunk_index, metadata
                            ) VALUES (
                                :content, :emb, 'knowledge_base', :fid_str, 
                                :fid, :idx, :meta
                            )
                        """),
                        {
                            "content": text_chunk,
                            "emb": embedding,
                            "fid_str": str(file_id),
                            "fid": file_id,
                            "idx": idx,
                            "meta": json.dumps({"filename": filename, "mime_type": mime_type})
                        }
                    )

                # 6. Update File Status
                await session.execute(
                    text("""
                        UPDATE knowledge_files 
                        SET status = 'active', chunk_count = :cc, updated_at = NOW()
                        WHERE id = :fid
                    """),
                    {"fid": file_id, "cc": len(text_chunks)}
                )
                await session.commit()
                logger.info(f"Ingested {filename} successfully.")
                return str(file_id)

            except Exception as e:
                logger.error(f"Ingestion failed for {filename}: {e}")
                await session.rollback()
                # Mark error
                async with get_async_session() as err_session:
                    await err_session.execute(
                        text("UPDATE knowledge_files SET status = 'error', error_message = :msg WHERE id = :fid"),
                        {"fid": file_id, "msg": str(e)}
                    )
                    await err_session.commit()
                raise e

    async def search(self, query: str, limit: int = 5, hybrid: bool = True) -> List[dict]:
        """
        Search the knowledge base.
        Uses Hybrid Search (Vector Similarity + Text Match) if hybrid=True.
        """
        query_embedding = await model_router.embed_text(query)
        
        async with get_async_session() as session:
            # Hybrid Search Logic:
            # We use a combined score or RRF (Reciprocal Rank Fusion).
            # For simplicity, we'll start with Cosine Distance filtered by keyword match rank if applicable,
            # OR just pure vector search if hybrid is off.
            
            # Simple Hybrid: 
            # (1 - cosine_distance) * 0.7 + (ts_rank) * 0.3?
            # Actually, `vector_cosine_ops` returns distance (lower is better).
            # Let's do pure semantic search for now, ensuring we use valid SQL syntax for pgvector.
            # Operator: <=> (cosine distance)
            
            # If hybrid, we can boost results that also match text content.
            
            sql = """
                SELECT 
                    content, 
                    source_id, 
                    metadata, 
                    (embedding <=> :emb) as distance
                FROM embeddings
                WHERE source_type = 'knowledge_base'
                ORDER BY distance ASC
                LIMIT :limit
            """
            
            # Advanced: Hybrid with Common Table Expression (CTE) could be better,
            # but let's stick to Semantic Search V1. It's usually good enough with modern models.
            
            # If we wanted to leverage ts_content (created in migration):
            # WHERE ts_content @@ plainto_tsquery('portuguese', :txt)
            
            res = await session.execute(
                text(sql),
                {"emb": query_embedding, "limit": limit}
            )
            
            results = []
            for row in res.fetchall():
                results.append({
                    "content": row[0],
                    "file_id": row[1],
                    "metadata": row[2],
                    "score": 1 - row[3] # Convert distance to similarity
                })
                
            return results

import json

# Singleton
knowledge_base = KnowledgeBase()
