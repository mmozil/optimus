"""
Agent Optimus — Files Service.
Handles uploading files to Supabase Storage and tracking metadata in PostgreSQL.
"""

import logging
import uuid
from pathlib import Path

from sqlalchemy import text

from src.core.config import settings

logger = logging.getLogger(__name__)

# Allowed MIME types and max file size
ALLOWED_MIME_TYPES = {
    # Images
    "image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml",
    # Documents
    "application/pdf",
    # Data
    "text/csv", "text/plain",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # xlsx
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # docx
}
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB


class FilesService:
    """
    Manages file uploads to Supabase Storage and metadata in PostgreSQL.
    Bucket: 'attachments'
    """

    def __init__(self, bucket: str = "attachments"):
        self.bucket = bucket

    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        user_id: str = "default_user",
        conversation_id: str | None = None,
        mime_type: str | None = None,
    ) -> dict:
        """Upload a file to Supabase Storage and record metadata in DB."""
        from src.infra.supabase_client import supabase_client, get_async_session

        # --- Validations ---
        if not supabase_client:
            raise RuntimeError(
                "Supabase client not configured. Set SUPABASE_URL and SUPABASE_KEY."
            )

        if mime_type and mime_type not in ALLOWED_MIME_TYPES:
            raise ValueError(
                f"Tipo de arquivo '{mime_type}' não permitido. "
                f"Tipos aceitos: {', '.join(sorted(ALLOWED_MIME_TYPES))}"
            )

        if len(file_content) > MAX_FILE_SIZE_BYTES:
            raise ValueError(
                f"Arquivo muito grande ({len(file_content)} bytes). "
                f"Máximo: {MAX_FILE_SIZE_BYTES // (1024*1024)} MB."
            )

        if len(file_content) == 0:
            raise ValueError("Arquivo vazio.")

        # 1. Generate unique storage path
        file_id = str(uuid.uuid4())
        extension = Path(filename).suffix
        storage_path = f"{user_id}/{file_id}{extension}"

        # 2. Upload to Supabase Storage
        try:
            supabase_client.storage.from_(self.bucket).upload(
                path=storage_path,
                file=file_content,
                file_options={"content-type": mime_type or "application/octet-stream"},
            )
        except Exception as e:
            logger.error(f"Upload to Supabase Storage failed: {e}")
            raise RuntimeError(f"Falha ao enviar arquivo para o storage: {e}") from e

        # 3. Get public URL
        public_url = supabase_client.storage.from_(self.bucket).get_public_url(
            storage_path
        )

        # 4. Persist metadata in PostgreSQL
        async with get_async_session() as session:
            query = text("""
                INSERT INTO files (user_id, conversation_id, storage_path, filename, mime_type, size_bytes, public_url)
                VALUES (:user_id, :conversation_id, :storage_path, :filename, :mime_type, :size_bytes, :public_url)
                RETURNING id
            """)
            params = {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "storage_path": storage_path,
                "filename": filename,
                "mime_type": mime_type,
                "size_bytes": len(file_content),
                "public_url": public_url,
            }
            result = await session.execute(query, params)
            db_id = result.scalar_one()
            await session.commit()

        logger.info(f"File uploaded: {filename} ({mime_type}, {len(file_content)} bytes) -> {storage_path}")

        return {
            "id": str(db_id),
            "filename": filename,
            "storage_path": storage_path,
            "public_url": public_url,
            "mime_type": mime_type,
            "size_bytes": len(file_content),
        }

    async def get_file_info(self, file_id: str) -> dict | None:
        """Fetch file metadata from the database by UUID."""
        from src.infra.supabase_client import get_async_session

        async with get_async_session() as session:
            query = text("SELECT * FROM files WHERE id = :id")
            result = await session.execute(query, {"id": file_id})
            row = result.fetchone()
            if not row:
                return None

            return dict(row._mapping)

    async def list_files_for_conversation(self, conversation_id: str) -> list[dict]:
        """List all files attached to a conversation."""
        from src.infra.supabase_client import get_async_session

        async with get_async_session() as session:
            query = text(
                "SELECT * FROM files WHERE conversation_id = :cid ORDER BY created_at DESC"
            )
            result = await session.execute(query, {"cid": conversation_id})
            rows = result.fetchall()
            return [dict(r._mapping) for r in rows]


# Singleton
files_service = FilesService()
