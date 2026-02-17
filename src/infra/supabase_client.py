"""
Agent Optimus — Database client.
Async SQLAlchemy engine + session factory for PostgreSQL+PGvector.
Supabase Native Client for Storage + Auth.
"""

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import settings

# ============================================
# 1. SQLAlchemy Engine (PostgreSQL)
# ============================================
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """Dependency injection for database sessions (FastAPI)."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def get_async_session():
    """Async context manager for non-FastAPI code (services, scripts)."""
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()


# ============================================
# 2. Supabase Native Client (Storage + Auth)
# ============================================
supabase_client = None

try:
    from supabase import create_client, Client
    if settings.SUPABASE_URL and settings.SUPABASE_KEY:
        supabase_client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
except ImportError:
    pass  # supabase-py not installed — Storage features disabled
