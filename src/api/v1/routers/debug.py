from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from src.infra.supabase_client import get_async_session
from src.infra.migrate_all import run_migrations
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/fix-db")
async def trigger_migrations():
    """Manually trigger database migrations."""
    try:
        await run_migrations()
        return {"status": "success", "message": "Migrations triggered successfully. Check logs."}
    except Exception as e:
        logger.error(f"Manual migration triggering failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tables")
async def list_tables():
    """List all tables in the database."""
    try:
        async with get_async_session() as session:
            result = await session.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            )
            tables = [row[0] for row in result.fetchall()]
        return {"status": "success", "tables": tables}
    except Exception as e:
        logger.error(f"Failed to list tables: {e}")
        raise HTTPException(status_code=500, detail=str(e))
