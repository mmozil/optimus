# 🤖 Agent Optimus — Roadmap Completo

## O Transformer dos AI Agents

---

## 📌 Visão Geral

**Agent Optimus** é uma **plataforma de AI agents multi-setor** que combina o melhor de **5 fontes** pesquisadas e validadas:

| Fonte | Relação | O Que Inspirou |
|-------|---------|----------------|
| **Maestro** | 🔵 Inspiração (continua separado no Tier Finance) | Conceitos de ToT, Uncertainty, Personas, AgentFactory — **reimplementados** nativamente no Optimus |
| **Mission Control** | 🔵 Referência arquitetural | SOUL.md, WORKING.md, Daily Notes, Thread Subscriptions, Task Lifecycle |
| **OpenClaw** | 🔵 Referência de infra | Multi-Channel, Chat Commands, Session Pruning, Skills Registry, Cron/Webhooks |
| **Agno** | 🟢 Framework adotado | Performance 2μs, Learning Agents, RAG Nativo, Model Agnostic, Multimodal |
| **Google ADK** | 🟢 Framework adotado | A2A Protocol, MCP Server, SequentialAgent/ParallelAgent, Debug Web UI |

> [!IMPORTANT]
> **O Maestro NÃO é migrado para o Optimus.** Ele continua como produto independente para finance.
> O Optimus **reimplementa** os conceitos (ToT, Uncertainty, Personas, etc.) de forma **generalizada** para funcionar em **qualquer setor**.

**Stack Final:**
```yaml
Orquestração:  Google ADK (A2A + MCP + Debug UI)
Agents:        Agno (2μs instanciação + Learning + RAG)
Database:      Supabase + PGvector (PostgreSQL + Vetores + Real-time)
Cache:         Redis (Sessions + Cache rápido)
Channels:      WhatsApp + Telegram + WebChat (inspirado OpenClaw)
Inteligência:  ToT Engine + UncertaintyQuantifier (reimplementados do Maestro)
```

---

## 🔍 Análise Crítica: O Que o Mission Control Faz BEM e ONDE Melhoramos

### ✅ Conceitos Adotados (Mission Control → Optimus)

| Conceito | Mission Control | Agent Optimus (Melhoria) |
|----------|----------------|--------------------------|
| **SOUL.md** | Personalidade estática em texto | + **Personas dinâmicas por intent** (Maestro) + Learning (Agno) |
| **WORKING.md** | Estado atual em markdown | + **Persistido no Supabase** + real-time sync entre agents |
| **Daily Notes** | Logs manuais por dia | + **Automáticos** via hooks + queryable por data/agent |
| **Heartbeats** | Cron 15min (poll) | + **Event-driven** (webhooks Supabase real-time) + heartbeat como fallback 30min |
| **AGENTS.md** | Manual operacional | + **TOOLS.md** (OpenClaw) + auto-gerado do schema de MCP |
| **Task Lifecycle** | Inbox→Assigned→InProgress→Review→Done | + **Subtasks** + **Dependencies** + **Priority** + **Estimativa** |
| **Thread Subscriptions** | Auto-subscribe ao interagir | **Mantido** — excelente design, adotado 100% |
| **@Mentions** | Notificação no próximo heartbeat | + **Real-time via Supabase** (< 2s vs 15min) |
| **Daily Standup** | Cron 23:30 via Telegram | + **Multi-channel** + **Métricas** (tokens, custo, rate) |
| **Níveis (Intern/Specialist/Lead)** | Controle de autonomia | + **Permission matrix** + **Sandbox** por nível |

### ❌ Problemas do Mission Control Que Resolvemos

| Problema | Mission Control | Agent Optimus |
|----------|----------------|---------------|
| **Sem RAG** | Agentes não buscam conhecimento | ✅ **Agno Agentic RAG** nativo + PGvector |
| **Sem Learning** | Cada sessão começa "zerada" | ✅ **Agno Learning** — agents melhoram entre sessões |
| **Sem ToT/COT** | Resposta direta (single-shot) | ✅ **ToT Engine** — 3 hipóteses + meta-avaliação + síntese |
| **Sem Uncertainty** | Sem noção de confiança | ✅ **UncertaintyQuantifier** — calibra confiança por resposta |
| **Convex limitado** | Sem vetores, sem SQL complex | ✅ **Supabase** — PostgreSQL + PGvector + SQL + Real-time |
| **Heartbeat caro (15min)** | 10 agents × 96/dia = 960 wakeups → **429 rate limit** + custo alto | ✅ **Event-driven** (zero tokens) + heartbeat 60min (fallback) + **Rate Limiter** anti-429 |
| **Polling 2s notificações** | Daemon fazendo poll constante | ✅ **Supabase Real-time** — push, zero polling |
| **Sem MCP** | Tools hardcoded, não extensível | ✅ **MCP first-class** — qualquer API vira tool via MCP Server |
| **Sem Model Failover** | Depende de 1 provider | ✅ **Multi-Model** — Gemini → Deepseek → Groq |
| **Sem Multimodal** | Apenas texto | ✅ **Agno Multimodal** — text/image/audio/video |
| **Sem Sandboxing** | Agentes com acesso total | ✅ **Docker sandbox** por nível (Intern isolado) |
| **10 instâncias separadas** | 10 processos = 10x recursos | ✅ **Agno Team** — N agents em 1 processo (3.75 KiB/agent) |
| **Só marketing** | Squad fixo para 1 setor | ✅ **Multi-setor** — qualquer API/DB via MCP plugin |

### 💡 Melhorias Exclusivas do Optimus

| Feature | Descrição |
|---------|-----------|
| **Persona por Intent** | Agent muda estilo baseado no tipo de pergunta (análise/educação/alerta) |
| **Session Compacting** | Comprime histórico longo em summary (do OpenClaw, economiza tokens) |
| **Chat Commands** | `/status`, `/think`, `/agents`, `/task`, `/learn` nos canais |
| **Skills Registry** | Agents podem descobrir e instalar novas skills (inspirado ClawHub) |
| **A2A Protocol** | Agents se descobrem e comunicam via protocolo padrão (Google ADK) |
| **Debug Web UI** | Interface visual para debug em tempo real (Google ADK) |
| **Webhook Triggers** | Ações externas disparam agents (GitHub push, form submit, etc.) |

---

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│              🤖 AGENT OPTIMUS — Arquitetura                  │
│                                                             │
│  ┌─── CHANNELS ──────────────────────────────────────────┐ │
│  │ WhatsApp (Baileys) · Telegram (grammY) · WebChat      │ │
│  │ Chat Commands: /status /think /agents /task /learn     │ │
│  │ Webhooks (GitHub, Forms, Custom)                       │ │
│  └───────────────────────────────────────────────────────┘ │
│                           ↕                                 │
│  ┌─── GATEWAY (Control Plane) ───────────────────────────┐ │
│  │ Session Router · Channel Routing · Presence            │ │
│  │ Cron Jobs · @Mentions · Thread Subscriptions           │ │
│  │ Daily Standup Generator                                │ │
│  └───────────────────────────────────────────────────────┘ │
│                           ↕                                 │
│  ┌─── ORCHESTRATION ─────────────────────────────────────┐ │
│  │ Google ADK                                             │ │
│  │ • A2A Protocol (agent discovery + communication)      │ │
│  │ • MCP Server (tools padronizadas)                     │ │
│  │ • Sequential / Parallel / Loop Agents                 │ │
│  │ • Debug Web UI + Evaluation Built-in                  │ │
│  └───────────────────────────────────────────────────────┘ │
│                           ↕                                 │
│  ┌─── AGENT CORE ────────────────────────────────────────┐ │
│  │ Agno Framework                                         │ │
│  │ • Teams (leader + members)        ~2μs / agent        │ │
│  │ • Learning (melhora entre sessões)                    │ │
│  │ • Agentic RAG nativo                                  │ │
│  │ • Multimodal (text/image/audio/video)                 │ │
│  │ • Model Agnostic (Gemini/Claude/GPT/Local)            │ │
│  │                                                       │ │
│  │ Identity Layer:                                       │ │
│  │ ├── SOUL.md (personalidade persistente)               │ │
│  │ ├── AGENTS.md (manual operacional)                    │ │
│  │ ├── TOOLS.md (capabilities disponíveis)               │ │
│  │ └── Personas (seleção dinâmica por intent)            │ │
│  │                                                       │ │
│  │ Memory Stack:                                         │ │
│  │ ├── WORKING.md (estado atual — Supabase synced)       │ │
│  │ ├── Daily Notes (automáticos)                         │ │
│  │ ├── MEMORY.md (long-term curado)                      │ │
│  │ └── Agno Learning (auto-evolução)                     │ │
│  └───────────────────────────────────────────────────────┘ │
│                           ↕                                 │
│  ┌─── INTELLIGENCE ENGINE ───────────────────────────────┐ │
│  │ • ToT Engine (Conservador + Criativo + Analítico)     │ │
│  │ • Meta-Avaliação (scoring 0-10 em 4 critérios)        │ │
│  │ • Síntese automática das melhores hipóteses           │ │
│  │ • UncertaintyQuantifier (calibração via pgvector)     │ │
│  │ • Multi-Model Fallback (Gemini → Deepseek → Groq)    │ │
│  │ • Session Compacting (resume contexto longo)          │ │
│  └───────────────────────────────────────────────────────┘ │
│                           ↕                                 │
│  ┌─── TOOLS & SKILLS (MCP Plugin System) ───────────────┐ │
│  │ Built-in MCP Tools:                                    │ │
│  │ ├── browser (CDP control)                             │ │
│  │ ├── database (Supabase queries)                       │ │
│  │ ├── filesystem (read/write)                           │ │
│  │ ├── research (web search)                             │ │
│  │ └── terminal (command exec)                           │ │
│  │                                                       │ │
│  │ Plugin MCP (qualquer API externa):                    │ │
│  │ ├── ERP (SAP, TOTVS, Odoo)                           │ │
│  │ ├── CRM (Salesforce, HubSpot, Pipedrive)             │ │
│  │ ├── E-commerce (Shopify, WooCommerce)                 │ │
│  │ ├── DevOps (GitHub, AWS, Docker)                      │ │
│  │ └── Qualquer REST/GraphQL API → MCP Server            │ │
│  │                                                       │ │
│  │ Skills Registry (inspirado ClawHub):                  │ │
│  │ └── Agents descobrem e instalam novas skills          │ │
│  └───────────────────────────────────────────────────────┘ │
│                           ↕                                 │
│  ┌─── DATA LAYER ────────────────────────────────────────┐ │
│  │ Supabase                                               │ │
│  │ ├── PostgreSQL (agents, tasks, messages, activities)   │ │
│  │ ├── PGvector (embeddings 768d, RAG, similarity)       │ │
│  │ ├── Real-time (subscriptions, push notifications)     │ │
│  │ ├── Auth (API keys, user management)                  │ │
│  │ └── Storage (documentos, attachments)                 │ │
│  │                                                       │ │
│  │ Redis                                                  │ │
│  │ ├── Session cache (fast read/write)                   │ │
│  │ └── Rate limiting + queue                             │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Estrutura do Projeto

```
AgentOptimus/
├── .docs/                          # Documentação
│   ├── Roadmap-Optimus.md          # Este arquivo
│   ├── Prompt-COT.md               # Princípios de prompts
│   └── complete-guide-control.md   # Referência Mission Control
│
├── src/
│   ├── core/                       # Núcleo do sistema
│   │   ├── gateway.py              # Control plane (WebSocket)
│   │   ├── orchestrator.py         # Google ADK orchestration
│   │   ├── agent_factory.py        # Factory de agents (Agno)
│   │   ├── session_manager.py      # Gerenciamento de sessões
│   │   └── config.py               # Configurações centralizadas
│   │
│   ├── agents/                     # Definições de agents
│   │   ├── base.py                 # BaseAgent (Agno)
│   │   ├── maestro.py              # Lead Orchestrator
│   │   ├── developer.py            # Developer (Friday)
│   │   ├── researcher.py           # Researcher (Fury)
│   │   ├── analyst.py              # Product Analyst (Shuri)
│   │   ├── writer.py               # Content Writer (Loki)
│   │   └── guardian.py             # QA / Security (Vision)
│   │
│   ├── engine/                     # Motor de inteligência
│   │   ├── tot_engine.py           # Tree-of-Thought (generalizado)
│   │   ├── tot_service.py          # Serviço ToT com pipeline
│   │   ├── uncertainty.py          # UncertaintyQuantifier
│   │   └── intent_classifier.py    # Classificação de intent
│   │
│   ├── memory/                     # Sistema de memória
│   │   ├── working_memory.py       # WORKING.md manager
│   │   ├── daily_notes.py          # Daily notes automáticos
│   │   ├── long_term.py            # MEMORY.md curado
│   │   ├── embeddings.py           # Embedding service (Gemini)
│   │   └── rag.py                  # RAG pipeline (Agno + PGvector)
│   │
│   ├── identity/                   # Sistema de identidade
│   │   ├── soul_loader.py          # Carrega SOUL.md
│   │   ├── personas.py             # Personas dinâmicas por intent
│   │   └── tools_manifest.py       # TOOLS.md auto-gerado
│   │
│   ├── channels/                   # Canais de comunicação
│   │   ├── telegram.py             # Telegram (grammY adapter)
│   │   ├── whatsapp.py             # WhatsApp (Baileys adapter)
│   │   ├── webchat.py              # WebChat UI
│   │   └── webhook.py              # Webhook receiver
│   │
│   ├── skills/                     # MCP Tools
│   │   ├── browser.py              # Browser control (CDP)
│   │   ├── database.py             # Supabase queries
│   │   ├── filesystem.py           # File operations
│   │   ├── research.py             # Web search
│   │   ├── terminal.py             # Command execution
│   │   └── mcp_plugin.py           # Loader dinâmico de MCP externo
│   │
│   ├── collaboration/              # Sistema de colaboração
│   │   ├── task_manager.py         # Task lifecycle (CRUD)
│   │   ├── thread_manager.py       # Comentários + subscriptions
│   │   ├── notification_service.py # @mentions (real-time)
│   │   ├── activity_feed.py        # Feed de atividades
│   │   └── standup_generator.py    # Daily standup automático
│   │
│   └── infra/                      # Infraestrutura
│       ├── supabase_client.py      # Supabase connection
│       ├── redis_client.py         # Redis connection
│       ├── model_router.py         # Multi-model failover
│       └── sandbox.py              # Docker sandbox por nível
│
├── workspace/                      # Workspace dos agents
│   ├── AGENTS.md                   # Manual operacional global
│   ├── HEARTBEAT.md                # Checklist de wake-up
│   ├── souls/                      # SOUL.md por agent
│   │   ├── maestro.md
│   │   ├── friday.md
│   │   ├── fury.md
│   │   └── ...
│   └── memory/                     # Memória persistente
│       ├── working/                # WORKING.md por agent
│       ├── daily/                  # Daily notes por data
│       └── long_term/              # MEMORY.md por agent
│
├── migrations/                     # Supabase migrations
│   ├── 001_agents.sql
│   ├── 002_tasks.sql
│   ├── 003_messages.sql
│   ├── 004_activities.sql
│   ├── 005_documents.sql
│   ├── 006_notifications.sql
│   └── 007_embeddings.sql
│
├── tests/                          # Testes
│   ├── test_agents.py
│   ├── test_tot_engine.py
│   ├── test_memory.py
│   └── test_collaboration.py
│
├── docker-compose.yml              # Dev environment
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variables
└── README.md                       # Getting started
```

---

## 🗄️ Schema Supabase (PostgreSQL)

```sql
-- 1. AGENTS
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE,
    role VARCHAR(100) NOT NULL,
    soul_md TEXT,
    status VARCHAR(20) DEFAULT 'idle',  -- idle | active | blocked
    level VARCHAR(20) DEFAULT 'specialist',  -- intern | specialist | lead
    current_task_id UUID REFERENCES tasks(id),
    model_config JSONB DEFAULT '{}',
    last_heartbeat TIMESTAMPTZ,
    learning_data JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 2. TASKS
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'inbox',  -- inbox|assigned|in_progress|review|done|blocked
    priority VARCHAR(10) DEFAULT 'medium',
    parent_task_id UUID REFERENCES tasks(id),
    assignee_ids UUID[] DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    due_date TIMESTAMPTZ,
    estimated_effort VARCHAR(20),
    created_by UUID REFERENCES agents(id),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 3. MESSAGES (comentários em tasks)
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id) NOT NULL,
    from_agent_id UUID REFERENCES agents(id) NOT NULL,
    content TEXT NOT NULL,
    attachments UUID[] DEFAULT '{}',
    mentions UUID[] DEFAULT '{}',
    confidence_score FLOAT,
    thinking_mode VARCHAR(20),  -- standard | tot | compact
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 4. ACTIVITIES (log de eventos)
CREATE TABLE activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type VARCHAR(50) NOT NULL,  -- task_created|message_sent|status_changed|heartbeat
    agent_id UUID REFERENCES agents(id),
    task_id UUID REFERENCES tasks(id),
    message TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 5. DOCUMENTS
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    type VARCHAR(30),  -- deliverable|research|protocol|report
    task_id UUID REFERENCES tasks(id),
    created_by UUID REFERENCES agents(id),
    version INT DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 6. NOTIFICATIONS
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mentioned_agent_id UUID REFERENCES agents(id) NOT NULL,
    source_agent_id UUID REFERENCES agents(id),
    task_id UUID REFERENCES tasks(id),
    content TEXT NOT NULL,
    delivered BOOLEAN DEFAULT false,
    delivered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 7. THREAD SUBSCRIPTIONS
CREATE TABLE thread_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id) NOT NULL,
    task_id UUID REFERENCES tasks(id) NOT NULL,
    subscribed_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(agent_id, task_id)
);

-- 8. EMBEDDINGS (RAG + Memória Semântica)
CREATE TABLE embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    embedding vector(768),  -- Gemini 004
    source_type VARCHAR(30),  -- knowledge|conversation|document
    source_id VARCHAR(255),
    agent_id UUID REFERENCES agents(id),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ON embeddings USING ivfflat (embedding vector_cosine_ops);

-- 9. ERROR PATTERNS (UncertaintyQuantifier)
CREATE TABLE error_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_text TEXT NOT NULL,
    pattern_embedding vector(768),
    error_type VARCHAR(50),
    frequency INT DEFAULT 1,
    agent_id UUID REFERENCES agents(id),
    created_at TIMESTAMPTZ DEFAULT now()
);
```

---

## 🗺️ Fases de Implementação

### Fase 1: Foundation (Semana 1-2) ✅ CONCLUÍDA
> Setup do projeto, agents básicos, Supabase

- [x] **Setup do Projeto**
  - [x] Inicializar repo (`AgentOptimus/`)
  - [x] `docker-compose.yml` (PostgreSQL+PGvector + Redis)
  - [x] `requirements.txt` (agno, google-adk, supabase-py, redis, fastapi)
  - [x] `.env.example` com todas as variáveis
  - [x] Migrations Supabase (9 tabelas + índices + seed)
  - [x] `pyproject.toml` (Ruff + pytest config)
  - [x] `.gitignore`, `README.md`

- [x] **Core Agents**
  - [x] `agent_factory.py` — Factory pattern com registry
  - [x] `base.py` — BaseAgent com rate limiting + model failover + prompt builder
  - [x] `optimus.py` — Lead Orchestrator com personas dinâmicas
  - [x] `developer.py` — Developer agent (Friday)
  - [x] `researcher.py` — Researcher agent (Fury)
  - [x] `gateway.py` — Control plane (routing, init)
  - [x] `main.py` — FastAPI app (/health, /agents, /chat)

- [x] **Identity Layer**
  - [x] `soul_loader.py` — Carrega SOUL.md com cache + seções + hot-reload
  - [x] Criar `souls/optimus.md`, `souls/friday.md`, `souls/fury.md`
  - [x] `personas.py` — 6 personas dinâmicas por intent (keyword v1)
  - [x] `AGENTS.md` — Manual operacional global
  - [x] `HEARTBEAT.md` — Checklist de wake-up

- [x] **Infraestrutura**
  - [x] `supabase_client.py` — Async SQLAlchemy engine
  - [x] `redis_client.py` — Pool + AgentRateLimiter anti-429
  - [x] `model_router.py` — Multi-model failover (Pro → Flash → Economy)

- [x] **Testes**
  - [x] 15 unit tests (SoulLoader, PersonaSelector, AgentConfig, BaseAgent, AgentFactory)

---

### Fase 2: Inteligência (Semana 3-4) ✅ CONCLUÍDA
> ToT Engine, memória, RAG

- [x] **Tree-of-Thought Engine** (reimplementado do zero, generalizado)
  - [x] `tot_engine.py` — 3 estratégias (Conservador/Criativo/Analítico) + geração paralela + meta-avaliação JSON + síntese
  - [x] `tot_service.py` — 3 níveis de pensamento (quick/standard/deep)
  - [x] Scoring em 4 critérios (Precisão, Completude, Praticidade, Originalidade)
  - [x] Síntese automática das melhores hipóteses

- [x] **UncertaintyQuantifier** (reimplementado para Supabase)
  - [x] Auto-avaliação LLM (confiança 0-1)
  - [x] Busca de error patterns via PGvector similarity
  - [x] Calibração baseada em histórico + recomendações por risco

- [x] **Intent Classifier**
  - [x] 8 tipos de intent (code, research, analysis, planning, creative, urgent, content, general)
  - [x] Routing automático para agents + thinking level

- [x] **Memory Stack**
  - [x] `working_memory.py` — WORKING.md synced por agent (cache + update por seção)
  - [x] `daily_notes.py` — Logs automáticos por agent/dia (markdown)
  - [x] `long_term.py` — MEMORY.md curado (learnings categorizados)
  - [x] `HEARTBEAT.md` — Checklist de wake-up

- [x] **RAG Pipeline**
  - [x] `embeddings.py` — Gemini Text Embedding 004 + batch + PGvector storage
  - [x] `rag.py` — Chunking semântico + similarity search + augment_prompt
  - [x] Threshold 0.7 + "não encontrei" pattern

- [x] **Testes**
  - [x] 22 unit tests (IntentClassifier, ToT, Uncertainty, RAG chunking)

---

### Fase 3: Colaboração (Semana 5-6) ✅ CONCLUÍDA
> Tasks, notificações, comunicação entre agents

- [x] **Task System**
  - [x] `task_manager.py` — CRUD completo (Pydantic models)
  - [x] Task lifecycle (6 status: Inbox→Assigned→InProgress→Review→Done+Blocked)
  - [x] Transições validadas + subtasks + filtros + ordenação por prioridade
  - [x] Priority (low/medium/high/urgent) + estimativas + tags + due_date

- [x] **Thread System**
  - [x] `thread_manager.py` — Mensagens em tasks com timestamps
  - [x] Thread subscriptions (auto-subscribe ao postar ou ser mencionado)
  - [x] @mentions parsing via regex + unread mentions query

- [x] **Notifications**
  - [x] `notification_service.py` — Fila in-memory (preparado para Supabase Real-time)
  - [x] 5 tipos (mention, task_assigned, task_status, new_message, system)
  - [x] Delivery tracking + mark_delivered + send_to_subscribers

- [x] **Activity Feed & Standup**
  - [x] `activity_feed.py` — 10 event types + consultas por agent/task/type + daily summary
  - [x] `standup_generator.py` — Standup agent (feito/fazendo/bloqueios/métricas) + time

- [x] **Testes**
  - [x] 30 testes async (TaskManager 10, ThreadManager 6, NotificationService 4, ActivityFeed 5, StandupGenerator 3)

---

### Fase 4: Canais (Semana 7-8) ✅ CONCLUÍDA
> WhatsApp, Telegram, Slack, WebChat, Chat Commands

- [x] **Base Channel**
  - [x] `base_channel.py` — Interface abstrata (IncomingMessage/OutgoingMessage normalizados + handler pattern)

- [x] **Telegram Channel**
  - [x] `telegram.py` — python-telegram-bot (polling + /start + text + media + groups)

- [x] **WhatsApp Channel**
  - [x] `whatsapp.py` — Evolution API (webhook + QR + text/media + groups)

- [x] **Slack Channel**
  - [x] `slack.py` — Slack Bolt (Socket Mode + DMs + channels + @mentions + threads + /optimus slash)

- [x] **WebChat**
  - [x] `webchat.py` — REST API + SSE streaming + session management (create/close/list/history)

- [x] **Chat Commands**
  - [x] 9 comandos: /status, /think, /agents, /task, /learn, /compact, /new, /help, /standup
  - [x] Integrados com TaskManager, AgentFactory, LongTermMemory, StandupGenerator

- [x] **Testes**
  - [x] 25 testes (Messages 5, WebChat 8, ChatCommands 9, definitions 3)

---

### Fase 5: Orquestração (Semana 9-10) ✅ CONCLUÍDA
> Google ADK, MCP, A2A, multi-model

- [x] **Google ADK Integration**
  - [x] `orchestrator.py` — 3 modos: Sequential (pipe output→input), Parallel (gather), Loop (convergência)
  - [x] Pipeline registration + conditional steps + timeouts + transforms
  - [x] Integrado com AgentFactory para execução multi-agent

- [x] **MCP Server**
  - [x] `mcp_tools.py` — 8 tools nativos (db_query/execute, fs_read/write/list, research_search/fetch, memory_search/learn)
  - [x] `mcp_plugin.py` — Loader dinâmico (módulo Python + auto-discovery por diretório)
  - [x] `tools_manifest.py` — TOOLS.md auto-gerado com categorias e permissões
  - [x] Permission matrix: requires_approval para operações destrutivas + agent level filtering

- [x] **A2A Protocol**
  - [x] `a2a_protocol.py` — Agent discovery (capabilities + load balancing)
  - [x] Messaging (request/response/broadcast/delegation)
  - [x] Delegation tracking com load counters automáticos
  - [x] find_best_agent para routing inteligente

- [x] **Multi-Model Router** (implementado em Fase 1, aprimorado aqui)
  - [x] Failover chain já implementada no `model_router.py`
  - [x] Modelo barato para heartbeats / caro para ToT integrado via ToTService

- [x] **Testes**
  - [x] 32 testes (Orchestrator 5, MCP Tools 9, MCP Plugin 4, A2A Protocol 11, + extras)

---

### Fase 6: Polish (Semana 11-12) ✅ CONCLUÍDA
> Segurança, performance, mais agents

- [x] **Security**
  - [x] `security.py` — Permission matrix (8 perms × 3 levels) + sandbox (full/restricted/isolated)
  - [x] Audit trail completo com queries + denied actions + stats
  - [x] Grant/revoke customizado por agent

- [x] **Performance**
  - [x] `performance.py` — SessionPruner (TTL + max sessions)
  - [x] ContextCompactor (summarize older + keep recent)
  - [x] QueryCache LRU (TTL + hit/miss stats + eviction)

- [x] **Mais Agents**
  - [x] `analyst.py` — Shuri (métricas, BI, insights, reports)
  - [x] `writer.py` — Loki (conteúdo, copy, docs, social posts)
  - [x] `guardian.py` — Vision (security audit, code review, compliance OWASP)

- [x] **Event System + Webhooks**
  - [x] `events.py` — EventBus pub/sub (wildcard + concurrent handlers)
  - [x] HeartbeatManager (60min intervals + alive check + background loop)
  - [x] WebhookReceiver (GitHub/forms + custom processors)

- [x] **Skills Registry**
  - [x] `skills_registry.py` — 8 skills nativos + install/uninstall dinâmico
  - [x] Auto-discovery via SKILL.md + catalogue generation
  - [x] Filtering por category/agent + enable/disable

- [x] **Testes**
  - [x] 40 testes (Security 12, Performance 13, Events 10, Skills 8)

---

### Fase 7: Deploy & Docker (Semana 13) ✅ CONCLUÍDA
> Containerização, Docker Compose, Deploy no Hetzner/Coolify

- [x] **Dockerfile**
  - [x] Multi-stage build (builder + runner slim)
  - [x] Python 3.12 + pip (venv isolado)
  - [x] Health check endpoint `/health` (curl)
  - [x] Non-root user `optimus` + `.dockerignore`

- [x] **Docker Compose (Produção)**
  - [x] `docker-compose.yml` — App + PostgreSQL 16/pgvector + Redis 7
  - [x] Rede isolada `optimus-network` + volumes nomeados
  - [x] Redis com senha + depends_on com health conditions
  - [x] `.env.example` com 30+ variáveis (channels, deploy, observability)

- [x] **Docker Compose (Dev)**
  - [x] `docker-compose.dev.yml` — PostgreSQL + Redis sem senha
  - [x] Portas expostas para debug local

- [ ] **Deploy Hetzner/Coolify** _(requer acesso ao servidor)_
  - [ ] Configurar repositório no Coolify (`ssh root@46.224.220.223`)
  - [ ] Configuração de build no Coolify
  - [ ] Variáveis de ambiente no Coolify
  - [ ] Domínio + SSL/TLS

---

### Fase 8: CI/CD & GitHub (Semana 14) ✅ CONCLUÍDA
> Pipeline automatizado, testes, linting, deploy automático

- [x] **GitHub Actions — CI**
  - [x] `.github/workflows/ci.yml`
  - [x] Lint (ruff check + format check)
  - [x] Testes unitários (pytest) com coverage report + PostgreSQL/Redis services
  - [x] Build Docker image (verificação com cache GHA)

- [x] **GitHub Actions — CD**
  - [x] `.github/workflows/deploy.yml`
  - [x] Deploy automático via Coolify webhook
  - [x] Notificação pós-deploy no Telegram e Slack

- [x] **Qualidade de Código**
  - [x] `pyproject.toml` — coverage config (fail_under=60%) + pytest markers (slow, e2e)
  - [x] Badges CI/CD no README
  - [x] README completo com arquitetura final + tech stack + comandos dev

---

### Fase 9: Integração & Testes E2E (Semana 15) ✅ CONCLUÍDA
> Conectar APIs reais, fluxo completo mensagem→agent→resposta

- [x] **Guia de Setup dos Canais** — `CHANNELS-SETUP.md`
  - [x] Telegram: @BotFather + webhook + polling
  - [x] Slack: api.slack.com + Socket Mode + 9 scopes + slash commands
  - [x] WhatsApp: Evolution API Docker + QR Code + webhook config

- [x] **Testes End-to-End** — `test_e2e.py` (30 testes)
  - [x] Fluxo: Command → Handler → Response
  - [x] Fluxo: Task Create → Lifecycle → Notification
  - [x] Fluxo: A2A Delegation completa (delegate → complete → response)
  - [x] Fluxo: Security enforcement + audit trail
  - [x] Fluxo: Event-driven (task.created → handler → notify)
  - [x] Fluxo: Performance (cache hit/miss + context compacting)
  - [x] Fluxo: Full Pipeline (Telegram → Command → Security → Event)

- [x] **Observability**
  - [x] `logging_config.py` — Structured JSON logging + rotation (10MB × 5) + errors.log separado
  - [x] `metrics.py` — 15+ métricas Prometheus (requests, agents, tokens, channels, cache, tasks, MCP)
  - [x] `TelegramAlertHandler` — Alertas CRITICAL/ERROR direto no Telegram
  - [x] `prometheus.yml` + Grafana provisioning config
  - [x] Decorators `@track_agent_request` e `@track_mcp_tool`

---

## 🌍 Plataforma Multi-Setor (MCP Plugin System)

**Agent Optimus não é um agent — é uma PLATAFORMA.** Qualquer API, database ou sistema pode ser plugado via MCP Server.

### Como Funciona: Plugar em Qualquer Sistema

```
┌──────────────────────────────────────────────────────────┐
│                  AGENT OPTIMUS (Plataforma)               │
│                                                          │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐      │
│  │Agent1│  │Agent2│  │Agent3│  │AgentN│  │ ... N│      │
│  └──┬───┘  └──┬───┘  └──┬───┘  └──┬───┘  └──┬───┘      │
│     └─────────┴────────┬┴─────────┴─────────┘           │
│                   MCP Client                             │
└──────────────────────┬───────────────────────────────────┘
                       │ MCP Protocol (padrão aberto)
       ┌───────────────┼───────────────┐
       ↓               ↓               ↓
┌──────────┐    ┌──────────┐    ┌──────────┐
│ MCP: ERP │    │MCP: CRM  │    │MCP: DevOp│
│ (SAP,    │    │(Salesforce│    │(GitHub,  │
│  TOTVS)  │    │ HubSpot) │    │ AWS)     │
└──────────┘    └──────────┘    └──────────┘
```

### Exemplos Por Setor

| Setor | Agent | Conecta em (MCP) | O que faz |
|-------|-------|-------------------|-----------|
| **E-commerce** | Commerce Agent | Shopify, WooCommerce API | Gestão de produtos, preços, estoque |
| **Saúde** | Health Agent | FHIR API, prontuários | Triagem, alertas médicos |
| **Jurídico** | Legal Agent | APIs de tribunais | Pesquisa de jurisprudência |
| **Marketing** | Growth Agent | Google Ads, Meta API | Campanhas, analytics |
| **DevOps** | Ops Agent | GitHub, AWS, Docker | CI/CD, monitoring, deploy |
| **RH** | People Agent | Gupy, LinkedIn API | Recrutamento, onboarding |
| **Atendimento** | Support Agent | Zendesk, Intercom | Suporte L1/L2 automático |
| **Financeiro** | Finance Agent | APIs bancárias, B3 | Análise, relatórios |

### Adicionar um Novo Agent (3 passos)

**Passo 1:** Criar MCP Server para a API do sistema
```python
# Template: qualquer REST API → MCP Server
@mcp_server.tool()
def query_customers(filter: str):
    """Busca clientes no sistema"""
    return api.get("/customers", params={"q": filter})
```

**Passo 2:** Criar SOUL.md para o agent
```markdown
# SOUL.md — Support Agent
Paciente, empático, resolutivo. Resolve no primeiro contato.
```

**Passo 3:** Plugar no Optimus
```python
support = Agent(
    name="Support",
    instructions=SoulLoader.load("souls/support.md"),
    tools=[MCPTools(url="http://zendesk-mcp:8080/mcp")],
)
squad.add_member(support)  # Pronto! ~2μs, ~3.75 KiB
```

> [!TIP]
> **Escalar agents é trivial:** ~2μs para instanciar, ~3.75 KiB de RAM. Adicionar 100 agents = ~375 KiB. O MCP é o padrão aberto que permite plugar em qualquer coisa.

---

## ⚡ Sistema Event-Driven (Anti-429)

> **Lição aprendida na prática:** Heartbeats tradicionais (15min) causam erro 429, custo alto e performance zero.

### Arquitetura de Wake-up

```
         PRIORIDADE DE ATIVAÇÃO DOS AGENTS
         ═══════════════════════════════════

    1º │ EVENT-DRIVEN (Supabase Real-time)     ← Custo: ZERO tokens
       │ • Task atribuída → agent acorda
       │ • @Mention → agent acorda
       │ • Webhook externo → agent acorda
       │
    2º │ SMART HEARTBEAT (60min, fallback)      ← Custo: ~$0.001
       │ • Query Supabase DIRETO (sem chamar LLM)
       │ • Só chama LLM se detectar trabalho pendente
       │ • Rate limiter impede burst
       │
    3º │ MANUAL (/agents wake <name>)           ← Custo: sob demanda
       │ • Usuário acorda agent via chat command
```

### Anti-429: Rate Limiter Built-in

```python
# Cada agent tem rate limit independente
RATE_LIMITS = {
    "lead":       {"rpm": 10, "rpd": 500},   # Mais ativo
    "specialist": {"rpm": 5,  "rpd": 200},   # Moderado
    "intern":     {"rpm": 2,  "rpd": 50},    # Conservador
}

# Smart heartbeat: SEM chamar LLM
async def heartbeat(agent_id):
    pending = await supabase.rpc('check_pending_work', {'agent_id': agent_id})
    if not pending:
        return  # ZERO tokens consumidos!
    await agent.wake_and_process(pending)  # Só aqui usa LLM
```

### Comparação de Custo

| Abordagem | Wakeups/dia | Tokens/dia | Custo/mês | Rate Limit |
|-----------|-------------|------------|-----------|------------|
| Mission Control (15min) | 960 | ~500K-1M | ~$144 | ❌ 429 frequente |
| **Optimus Event-driven** | ~24 (fallback) + events | ~5K-10K | **~$0.72** | ✅ Rate Limiter |

---

## 🤖 Squad Inicial (5 Agents)

| Agent | Codename | Papel | Nível | Modelo |
|-------|----------|-------|-------|--------|
| **Optimus** | Lead | Orquestra, delega, monitora | Lead | Gemini 2.5 Pro |
| **Friday** | Developer | Código, debugging, deploy | Specialist | Gemini 2.5 Flash |
| **Fury** | Researcher | Pesquisa com evidências | Specialist | Gemini 2.5 Flash |
| **Shuri** | Analyst | UX, edge cases, testes | Specialist | Gemini 2.5 Flash |
| **Loki** | Writer | Conteúdo, documentação | Specialist | Gemini 2.5 Flash |

> [!TIP]
> Começar com 2-3 agents (Optimus + Friday + Fury) e expandir. Depois, plugar novos agents para **qualquer setor** via MCP.

---

## 💰 Estimativa de Custos

| Recurso | Custo/mês | Notas |
|---------|-----------|-------|
| Supabase Free | $0 | 500MB DB, 1GB storage |
| Supabase Pro | $25 | 8GB DB, 100GB storage |
| Redis (Upstash) | $0-10 | Free tier generoso |
| Gemini 2.5 Flash | ~$15-30 | Para agents rotineiros |
| Gemini 2.5 Pro | ~$30-50 | Para ToT e trabalho complexo |
| Deepseek V3 | ~$5-10 | Fallback barato |
| **Total estimado** | **~$50-100/mês** | Para 5 agents ativos |

> [!IMPORTANT]
> Mission Control custa ~$144-400/mês só em heartbeats. Nosso Event-driven + Rate Limiter + modelo barato para fallback reduz **99.5%** do custo de heartbeats.

---

## ✅ Critérios de Sucesso

| Critério | Meta |
|----------|------|
| Instanciação de agent | < 5μs (Agno target: 2μs) |
| Memória por agent | < 10 KiB |
| Latência de notificação | < 5s (vs 15min Mission Control) |
| Uptime | > 99% |
| Token cost por heartbeat | < $0.001 (query Supabase, zero LLM) |
| Resposta com ToT | < 15s (3 hipóteses + síntese) |
| Learning entre sessões | Mensurável após 1 semana |
| RAG accuracy | > 80% relevância |
| Rate limit 429 errors | **ZERO** (rate limiter built-in) |
| Novos setores plugados | < 1h por MCP Server |

---

> [!IMPORTANT]
> **Agent Optimus = Sistema Operacional de AI Agents**
> Uma plataforma onde agents se conectam a **qualquer API** via MCP, operam em **qualquer setor**, aprendem entre sessões, e colaboram entre si.
> **Sem limites de setor. Sem limites de escala. Sem 429.**
