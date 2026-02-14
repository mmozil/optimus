"""
Agent Optimus — Centralized Configuration.
Uses pydantic-settings to load from .env with type safety.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All configuration loaded from environment variables."""

    # === App ===
    ENVIRONMENT: str = "development"
    VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # === Database ===
    DATABASE_URL: str = "postgresql+asyncpg://optimus:optimus_dev@localhost:5432/optimus_dev"

    # === Supabase (cloud — optional for local dev) ===
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""

    # === Redis ===
    REDIS_URL: str = "redis://localhost:6379/0"

    # === AI Models ===
    GOOGLE_API_KEY: str = ""
    LLM_MODEL: str = "gemini-2.5-flash"
    LLM_FALLBACK_MODEL: str = "gemini-2.0-flash"
    EMBEDDING_MODEL: str = "text-embedding-004"
    EMBEDDING_DIMENSIONS: int = 768

    # === Rate Limiting ===
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_CHAT: str = "30/minute"

    # === CORS ===
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # === Sentry ===
    SENTRY_DSN: str = ""

    model_config = {"env_file": ".env", "case_sensitive": True}

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"


settings = Settings()
