"""
Apply SQL migration file to database.
Usage: python scripts/apply_migrations.py <path_to_sql_file>
"""
import sys
import os
import asyncio
from sqlalchemy import text

# Add project root to path
sys.path.append(os.getcwd())

# Add local libs
libs_path = os.path.join(os.getcwd(), "libs")
if os.path.exists(libs_path):
    sys.path.insert(0, libs_path)

from src.infra.supabase_client import get_async_session

async def apply_migration(sql_path):
    if not os.path.exists(sql_path):
        print(f"File not found: {sql_path}")
        return

    print(f"Applying migration: {sql_path}")
    with open(sql_path, "r", encoding="utf-8") as f:
        sql = f.read()

    # Split by some logic if needed, or run as block if supported
    # asyncpg usually supports multiple statements in one execute block
    try:
        async with get_async_session() as session:
            await session.execute(text(sql))
            await session.commit()
        print("✅ Migration applied successfully.")
    except Exception as e:
        print(f"❌ Migration failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/apply_migrations.py <path_to_sql_file>")
        sys.exit(1)
    
    asyncio.run(apply_migration(sys.argv[1]))
