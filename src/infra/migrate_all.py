
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
    Include retry logic for DB startup.
    """
    migrations_dir = os.path.join(os.getcwd(), "migrations")
    if not os.path.exists(migrations_dir):
        logger.warning(f"Migrations directory not found at {migrations_dir}")
        return

    # Get sorted list of sql files
    files = sorted([f for f in os.listdir(migrations_dir) if f.endswith(".sql")])
    
    logger.info(f"Found {len(files)} migration files in {migrations_dir}")

    def split_sql_statements(sql: str) -> list[str]:
        """Split SQL by semicolons, correctly ignoring semicolons inside dollar-quoted strings."""
        statements: list[str] = []
        current: list[str] = []
        in_dollar_quote = False
        dollar_tag = ""
        i = 0
        while i < len(sql):
            ch = sql[i]
            if not in_dollar_quote:
                if ch == "$":
                    j = sql.find("$", i + 1)
                    if j != -1:
                        tag = sql[i : j + 1]
                        in_dollar_quote = True
                        dollar_tag = tag
                        current.append(sql[i : j + 1])
                        i = j + 1
                        continue
                elif ch == ";":
                    stmt = "".join(current).strip()
                    if stmt:
                        statements.append(stmt)
                    current = []
                    i += 1
                    continue
            else:
                if sql[i : i + len(dollar_tag)] == dollar_tag:
                    current.append(dollar_tag)
                    i += len(dollar_tag)
                    in_dollar_quote = False
                    dollar_tag = ""
                    continue
            current.append(ch)
            i += 1
        last = "".join(current).strip()
        if last:
            statements.append(last)
        return statements

    # Retry logic
    max_retries = 10
    retry_interval = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            async with get_async_session() as session:
                # Test connection
                await session.execute(text("SELECT 1"))
                
                # If success, proceed to migrations
                for filename in files:
                    filepath = os.path.join(migrations_dir, filename)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            sql_content = f.read()
                        
                        logger.info(f"Applying migration: {filename}...")
                        
                        # Split statements by semicolon, respecting dollar-quoted strings
                        statements = split_sql_statements(sql_content)
                        
                        for stmt in statements:
                            # Skip comments-only statements
                            if stmt.startswith("--"):
                                lines = stmt.split("\n")
                                stmt = "\n".join([l for l in lines if not l.strip().startswith("--")])
                            
                            if stmt.strip():
                                try:
                                    await session.execute(text(stmt))
                                except Exception as e:
                                    msg = str(e).lower()
                                    if "already exists" in msg or "duplicate" in msg:
                                        logger.warning(f"⚠️ Skipping duplicate object in {filename}: {stmt[:50]}...")
                                    else:
                                        raise e
                        
                        await session.commit()
                        logger.info(f"✅ Migration {filename} applied successfully.")
                        
                    except Exception as e:
                        logger.error(f"❌ Failed to apply migration {filename}: {e}")
                        # Depending on severity, we might want to stop or continue.
                        # For now, we log and re-raise to stop startup on critical DB error.
                        raise e
                
                # If we get here, all good
                logger.info("🎉 All migrations applied successfully.")
                return

        except (OSError, Exception) as e:
            # Catch connection errors (ConnectionRefusedError is subclass of OSError)
            if attempt < max_retries - 1:
                logger.warning(f"⚠️ DB Connection failed ({e}). Retrying in {retry_interval}s... ({attempt + 1}/{max_retries})")
                await asyncio.sleep(retry_interval)
            else:
                logger.error(f"❌ Could not connect to DB after {max_retries} attempts.")
                raise e

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_migrations())
