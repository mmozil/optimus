# 🤖 Agent Optimus

[![CI](https://github.com/mmozil/maestro/actions/workflows/ci.yml/badge.svg)](https://github.com/mmozil/maestro/actions/workflows/ci.yml)
[![Deploy](https://github.com/mmozil/maestro/actions/workflows/deploy.yml/badge.svg)](https://github.com/mmozil/maestro/actions/workflows/deploy.yml)

**AI Agent Platform — Multi-sector, Event-driven, MCP-first**

## Quick Start

```bash
# 1. Clone
git clone https://github.com/mmozil/maestro.git
cd maestro

# 2. Environment
cp .env.example .env
# Edit .env with your API keys

# 3. Services (dev: PostgreSQL + Redis)
docker compose -f docker-compose.dev.yml up -d

# 4. Python env
python -m venv .venv
.venv\Scripts\activate    # Windows
pip install -r requirements.txt

# 5. Run
uvicorn src.core.gateway:app --reload --port 8000
```

### Production Deploy

```bash
# Build & deploy everything
docker compose up -d --build
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/v1/agents` | GET | List active agents |
| `/api/v1/chat` | POST | Send message to agent |

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Analise a arquitetura do projeto", "agent": "optimus"}'
```

## Architecture

```
Agent Optimus
├── Channels (Telegram, WhatsApp, Slack, WebChat)
├── Gateway (routing, sessions, rate limiting)
├── Agents (Optimus, Friday, Fury, Analyst, Writer, Guardian)
├── Intelligence (ToT Engine, Uncertainty, Intent Classifier)
├── Memory (Working, Daily Notes, Long-Term, RAG)
├── Collaboration (Tasks, Threads, Notifications, Standup)
├── Orchestration (ADK Orchestrator, A2A Protocol)
├── Skills (MCP Tools, Plugin System, Registry)
├── Security (Permissions, Audit Trail, Sandbox)
└── Data (PostgreSQL + PGvector + Redis)
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Agents** | Agno (2μs instantiation, learning, RAG) |
| **Orchestration** | Google ADK (Sequential/Parallel/Loop) |
| **Protocols** | MCP (tools) + A2A (agent-to-agent) |
| **Database** | PostgreSQL 16 + PGvector + Supabase |
| **Cache** | Redis 7 (sessions, rate limiting, query cache) |
| **API** | FastAPI + Uvicorn |
| **CI/CD** | GitHub Actions → Coolify |
| **Infra** | Docker + Hetzner |

## Development

```bash
# Lint
ruff check src/ tests/

# Format
ruff format src/ tests/

# Tests
pytest tests/ -v

# Tests with coverage
pytest tests/ --cov=src --cov-report=term-missing
```

## Docs

- [Roadmap](/.docs/Roadmap-Optimus.md)
- [Engineering Guide](/.docs/ENGINEERING-OPTIMUS.md)
- [AGENTS.md](/workspace/AGENTS.md)

## License

MIT
