
import os
import logging
import asyncio
from sqlalchemy import text
from src.infra.supabase_client import get_async_session

logger = logging.getLogger(__name__)

async def run_migrations():
    """
    Executes all SQL files in the migrations/ directory in alphabetical order.
    Designed to be idempotent (files should use IF NOT EXISTS).
    """
    migrations_dir = os.path.join(os.getcwd(), "migrations")
    if not os.path.exists(migrations_dir):
        logger.warning(f"Migrations directory not found at {migrations_dir}")
        return

    # Get sorted list of sql files
    files = sorted([f for f in os.listdir(migrations_dir) if f.endswith(".sql")])
    
    logger.info(f"Found {len(files)} migration files in {migrations_dir}")

    async with get_async_session() as session:
        for filename in files:
            filepath = os.path.join(migrations_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    sql_content = f.read()
                
                logger.info(f"Applying migration: {filename}...")
                
                # Split by statements if needed, but usually executemany or execute block works
                # For simplicity and support of pgvector extension, we execute as block if possible
                # or split by semicolon if we encounter issues. 
                # SQLAlchemy execute() usually handles multi-statement if the driver supports it.
                # asyncpg supports it.
                
                await session.execute(text(sql_content))
                await session.commit()
                
                logger.info(f"✅ Migration {filename} applied successfully.")
                
            except Exception as e:
                logger.error(f"❌ Failed to apply migration {filename}: {e}")
                # We do not raise here to allow later phases to potentially retry or partial success
                # But for a robust system, we might want to stop. 
                # Given this is a auto-fix attempt, we log and re-raise to fail fast on startup.
                raise e

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_migrations())
