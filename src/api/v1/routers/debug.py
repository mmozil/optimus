from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from src.infra.supabase_client import get_async_session
from src.infra.migrate_all import run_migrations
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/fix-db")
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


@router.get("/config")
async def inspect_config():
    """Inspect loaded configuration (masked)."""
    from src.core.config import settings
    
    # Mask password in DB URL
    db_url = settings.DATABASE_URL
    if ":" in db_url and "@" in db_url:
        try:
            part1 = db_url.split("@")[0]
            part2 = db_url.split("@")[1]
            # user:pass -> user:***
            if ":" in part1:
                protocol = part1.split("://")[0]
                user_pass = part1.split("://")[1]
                if ":" in user_pass:
                    user = user_pass.split(":")[0]
                    masked_part1 = f"{protocol}://{user}:******"
                else:
                    masked_part1 = part1
            else:
                masked_part1 = part1
            
            safe_db_url = f"{masked_part1}@{part2}"
        except:
            safe_db_url = "Error masking URL"
    else:
        safe_db_url = db_url

    return {
        "status": "success",
        "config": {
            "ENVIRONMENT": settings.ENVIRONMENT,
            "DATABASE_URL": safe_db_url,
            "VERSION": settings.VERSION,
        }
    }
