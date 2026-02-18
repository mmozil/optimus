# ==========================================
# Agent Optimus — Multi-stage Dockerfile
# ==========================================
# Build:  docker build -t agent-optimus .
# Run:    docker run -p 8000:8000 --env-file .env agent-optimus
# ==========================================

# ────────────────────────────────────────────
# Stage 1: Builder — instala dependências
# ────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# System deps para compilação
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Instala dependências Python em venv isolado
COPY requirements.txt .
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt && \
    /opt/venv/bin/playwright install --with-deps chromium

# ────────────────────────────────────────────
# Stage 2: Runner — imagem slim de produção
# ────────────────────────────────────────────
FROM python:3.12-slim AS runner

# Metadata
LABEL maintainer="Agent Optimus Team"
LABEL version="0.1.0"
LABEL description="Agent Optimus — AI Agent Platform"

# Runtime deps (libpq para asyncpg + Chromium libs para Playwright)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 curl \
        libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
        libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
        libxrandr2 libgbm1 libasound2 && \
    rm -rf /var/lib/apt/lists/*

# Non-root user para segurança
RUN groupadd --gid 1000 optimus && \
    useradd --uid 1000 --gid 1000 --create-home optimus

# Copia venv do builder (inclui Playwright + Chromium binários)
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /root/.cache/ms-playwright /home/optimus/.cache/ms-playwright
RUN chown -R optimus:optimus /home/optimus/.cache
ENV PATH="/opt/venv/bin:$PATH" \
    PLAYWRIGHT_BROWSERS_PATH="/home/optimus/.cache/ms-playwright"

# Working directory
WORKDIR /app

# Copia código fonte
COPY --chown=optimus:optimus pyproject.toml .
COPY --chown=optimus:optimus src/ src/
COPY --chown=optimus:optimus migrations/ migrations/
COPY --chown=optimus:optimus workspace/ workspace/
COPY --chown=optimus:optimus scripts/ scripts/

# Cria diretórios para dados
RUN mkdir -p /app/logs /app/data /app/plugins && \
    chown -R optimus:optimus /app

# Muda para non-root user
USER optimus

# Expõe porta da API
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Variáveis de ambiente defaults
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=production \
    LOG_LEVEL=INFO

# Entrypoint: uvicorn com FastAPI
CMD ["uvicorn", "src.main:app", \
    "--host", "0.0.0.0", \
    "--port", "8000", \
    "--workers", "2", \
    "--loop", "uvloop", \
    "--http", "httptools", \
    "--log-level", "info"]
