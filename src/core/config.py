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

    # === Multi-Provider LLM (Phase 12) ===
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    MODEL_MAPPINGS: str = "{}"  # JSON string mapping short names to LiteLLM names
    MODEL_FALLBACKS: str = "{}"  # JSON string mapping chain names to lists of short names

    # === ReAct Loop ===
    REACT_MAX_ITERATIONS: int = 10
    REACT_TIMEOUT_SECONDS: int = 120

    # === Rate Limiting ===
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_CHAT: str = "30/minute"

    # === CORS ===
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # === JWT Authentication (Phase 15) ===
    JWT_SECRET: str = "CHANGE-ME-IN-PRODUCTION-use-openssl-rand-hex-32"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours — enough for a full workday
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # === Search APIs ===
    TAVILY_API_KEY: str = ""  # https://tavily.com — best for real-time web search

    # === Sentry ===
    SENTRY_DSN: str = ""

    # === OpenTelemetry (Phase 16) ===
    TRACING_ENABLED: bool = False
    OTEL_SERVICE_NAME: str = "agent-optimus"
    OTEL_EXPORTER_ENDPOINT: str = "http://localhost:4317"  # OTLP gRPC
    OTEL_EXPORTER_TYPE: str = "console"  # console | otlp

    # === Cost Tracking (Phase 16) ===
    COST_TRACKING_ENABLED: bool = True
    DEFAULT_DAILY_BUDGET_USD: float = 10.0
    DEFAULT_MONTHLY_BUDGET_USD: float = 200.0

    model_config = {"env_file": ".env", "case_sensitive": True}

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"


settings = Settings()
