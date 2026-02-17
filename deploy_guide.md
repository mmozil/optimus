# Agent Optimus — Deployment Guide 🚀

This guide outlines the steps to deploy Agent Optimus to **Coolify** (or any Docker-based platform).

## 1. Prerequisites
- **PostgreSQL 15+** (with `pgvector` extension enabled).
- **Redis 7+**.
- **Google Gemini API Key** (Required).
- **OpenAI/Groq API Key** (Optional, for Whisper).

## 2. Coolify Setup

1.  **Create Service**: Select "Docker Compose" or "Dockerfile" source (GitHub Repo).
2.  **Build Pack**: Docker Compose is recommended to orchestrate App + DB + Redis.
    - If deploying App only (connecting to external DB), use Dockerfile.

## 3. Environment Variables (.env)

Configure these in Coolify's "Environment Variables" section:

```ini
# Production Settings
ENVIRONMENT=production
LOG_LEVEL=INFO

# Database (Must match your DB service credentials)
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
REDIS_URL=redis://:pass@host:6379/0

# AI Keys
GOOGLE_API_KEY=AI...
OPENAI_API_KEY=sk-... (Optional)
GROQ_API_KEY=gsk_... (Optional)

# Security (Generate a random secret)
SECRET_KEY=...
```

## 4. Database Migrations

**Important**: The application uses raw SQL migrations located in `migrations/`. You must apply them on the first deploy.

### Option A: Post-Deployment Command (Coolify)
Add this to the "Post-deployment command" in Coolify settings:
```bash
python scripts/apply_migrations.py migrations/012_knowledge.sql
```
*Note: This script currently runs a specific file. You might want to run them all sequentially if setting up from scratch.*

### Option B: Manual Run (Console)
1.  Open the **Terminal/Console** of the running `optimus-app` container.
2.  Run:
    ```bash
    # Apply latest schema changes
    python scripts/apply_migrations.py migrations/012_knowledge.sql
    ```

## 5. Verification

Check the health endpoint after deployment:
```
GET https://your-domain.com/health
```
Should return `{"status": "ok", ...}`.

## 6. Features Checklist

- [ ] **Chat**: Test regular text chat.
- [ ] **Vision**: Send an image URL.
- [ ] **RAG**: Upload a PDF via API/Postman to `/api/v1/knowledge/upload`.
- [ ] **Voice**: Send a `.wav` file to `/api/v1/knowledge/upload`.
