# 🤖 Agent Optimus

[![CI](https://github.com/mmozil/maestro/actions/workflows/ci.yml/badge.svg)](https://github.com/mmozil/maestro/actions/workflows/ci.yml)
[![Deploy](https://github.com/mmozil/maestro/actions/workflows/deploy.yml/badge.svg)](https://github.com/mmozil/maestro/actions/workflows/deploy.yml)

**AI Agent Platform — Multi-channel, Event-driven, MCP-first**

---

## Quick Start (Local Dev)

```bash
# 1. Clone
git clone https://github.com/mmozil/maestro.git
cd maestro

# 2. Environment
cp .env.example .env
# Edit .env with your API keys

# 3. Services (PostgreSQL + Redis via Docker)
docker compose -f docker-compose.dev.yml up -d

# 4. Python env
python -m venv .venv
source .venv/bin/activate      # Linux/Mac
.venv\Scripts\activate         # Windows

pip install -r requirements.txt

# 5. Run
uvicorn src.main:app --reload --port 8000
```

Access at [http://localhost:8000](http://localhost:8000)

---

## Self-Host em VPS (Produção)

### Requisitos

| Item | Mínimo | Recomendado |
|------|--------|-------------|
| CPU | 2 vCPU | 4 vCPU |
| RAM | 2 GB | 4 GB |
| Disco | 20 GB SSD | 40 GB SSD |
| OS | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |
| Docker | 24+ | 26+ |
| Docker Compose | v2.20+ | v2.27+ |

### Passo a Passo

#### 1. Instalar Docker na VPS

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

#### 2. Clonar o Repositório

```bash
git clone https://github.com/mmozil/maestro.git
cd maestro
```

#### 3. Configurar Variáveis de Ambiente

```bash
cp .env.example .env
nano .env
```

Variáveis obrigatórias:

```env
# ── Segurança ──────────────────────────────────────
JWT_SECRET=<gere com: openssl rand -hex 32>
POSTGRES_PASSWORD=<senha forte>
REDIS_PASSWORD=<senha forte>

# ── LLM Principal ──────────────────────────────────
GEMINI_API_KEY=<sua chave Gemini>

# ── Domínio ────────────────────────────────────────
BASE_URL=https://seu-dominio.com
```

Variáveis opcionais (ativam features):

```env
# Pesquisa web
TAVILY_API_KEY=tvly-...

# Voice (STT)
GROQ_API_KEY=gsk_...

# Google OAuth (Gmail, Calendar, Drive)
GOOGLE_OAUTH_CLIENT_ID=...
GOOGLE_OAUTH_CLIENT_SECRET=...
GOOGLE_OAUTH_REDIRECT_URI=https://seu-dominio.com/api/v1/oauth/google/callback

# Canais (Telegram, WhatsApp, Slack)
TELEGRAM_BOT_TOKEN=...
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...

# Email IMAP/SMTP corporativo
# (configurado via Settings UI — não precisa de env vars)
```

#### 4. Deploy com Docker Compose

```bash
# Build e start (primeira vez — pode levar 3-5 min)
docker compose up -d --build

# Verificar status
docker compose ps

# Ver logs em tempo real
docker compose logs -f app
```

#### 5. Verificar Health

```bash
curl http://localhost:8000/health
# Esperado: {"status": "ok", ...}
```

#### 6. Configurar Reverse Proxy (Nginx + SSL)

```bash
# Instalar Nginx
sudo apt install -y nginx certbot python3-certbot-nginx

# Configurar site
sudo nano /etc/nginx/sites-available/optimus
```

Conteúdo do arquivo:

```nginx
server {
    listen 80;
    server_name seu-dominio.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE (Server-Sent Events) — manter conexão aberta
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/optimus /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# SSL gratuito com Let's Encrypt
sudo certbot --nginx -d seu-dominio.com
```

#### 7. Atualizar para Nova Versão

```bash
cd maestro
git pull
docker compose up -d --build app
```

---

### Deploy via Coolify (Recomendado)

[Coolify](https://coolify.io) automatiza build + deploy + SSL + reverse proxy:

1. Conectar repositório GitHub no Coolify
2. Configurar variáveis de ambiente no painel
3. Enable "Auto deploy on push" para CI/CD automático

O projeto já inclui `docker-compose.yml` pronto para Coolify.

---

## PWA — Instalar no Celular

O Agent Optimus é um Progressive Web App (PWA) instalável como app nativo:

### Android (Chrome)
1. Abra `https://seu-dominio.com` no Chrome
2. Toque no menu (⋮) → **"Adicionar à tela inicial"**
3. Confirme → ícone aparece na tela inicial

### iOS (Safari)
1. Abra `https://seu-dominio.com` no Safari
2. Toque em **Compartilhar** (ícone de caixa com seta)
3. Role e toque em **"Adicionar à Tela de Início"**
4. Confirme → ícone aparece na tela inicial

O app abre em modo standalone (sem barra do navegador) e funciona como app nativo.

---

## API Reference

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/health` | GET | Health check |
| `/api/v1/chat` | POST | Enviar mensagem ao agente |
| `/api/v1/agents` | GET | Listar agentes ativos |
| `/api/v1/user/me` | GET | Perfil do usuário |
| `/docs` | GET | Swagger UI (todos endpoints) |

```bash
# Exemplo: chat via cURL
curl -X POST https://seu-dominio.com/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"message": "Quais emails não li hoje?", "agent": "optimus"}'
```

---

## Arquitetura

```
Agent Optimus
├── Channels (Telegram, WhatsApp, Slack, WebChat)
├── Gateway (routing, sessions, rate limiting)
├── Agents (Optimus, Friday, Fury, Analyst, Writer, Guardian)
├── Intelligence (ToT Engine, Uncertainty, Intent Classifier)
├── Memory (Working, Daily Notes, Long-Term, RAG + PostgreSQL sync)
├── Collaboration (Tasks, Threads, Notifications, Standup)
├── Orchestration (ADK Orchestrator, A2A Protocol)
├── Skills (MCP Tools — 40+ tools, Plugin System)
├── Integrations (Gmail OAuth, Google Calendar, Drive, IMAP/SMTP)
├── Voice (Groq Whisper STT + Edge TTS)
└── Data (PostgreSQL + PGvector + Redis)
```

## Tech Stack

| Camada | Tecnologia |
|--------|-----------|
| **LLM** | Gemini 2.0 Flash (principal) |
| **Orchestration** | Google ADK + A2A Protocol |
| **Tools** | MCP (40+ tools) |
| **Database** | PostgreSQL 16 + PGvector |
| **Cache** | Redis 7 |
| **API** | FastAPI + Uvicorn |
| **CI/CD** | GitHub Actions → Coolify |
| **Infra** | Docker Compose |
| **Voice** | Groq Whisper (STT) + Edge TTS |

---

## Development

```bash
# Lint
ruff check src/ tests/

# Format
ruff format src/ tests/

# Tests (locais — sem DB)
pytest tests/ -v -k "not requires_db"

# Todos os testes (requer DB rodando)
pytest tests/ -v
```

---

## Docs

- [Roadmap](/.docs/roadmap-optimus-v2.md)
- [Engineering Guide](/.docs/ENGINEERING-OPTIMUS.md)
- [Agents](workspace/AGENTS.md)
- [Swagger UI](https://optimus.tier.finance/docs) (produção)

## License

MIT
