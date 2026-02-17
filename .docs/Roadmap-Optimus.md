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

### Fase 10: Proactive Intelligence (Semana 16-18) 🟡 EM PROGRESSO
> Boot sequence, auto-journaling, cron persistente, skills auto-discovery — superar o OpenClaw

- [x] **Boot Sequence (Memory-Aware Startup)** — P0 ✅
  - [x] `session_bootstrap.py` — Ao iniciar sessão, ler automaticamente: `SOUL.md` + `MEMORY.md` + daily notes (hoje + ontem)
  - [x] Injetar contexto de memória no system prompt antes de qualquer resposta (`build_prompt()`)
  - [x] Suportar `USER.md` (preferências do usuário: idioma, estilo, restrições)
  - [x] Cache inteligente — só re-ler se arquivo mudou (hash check MD5)
  - [x] Hot-reload via `invalidate()` / `invalidate_all()` sem restart

- [x] **Auto-Journaling (Aprendizado Contínuo)** — P1 ✅
  - [x] `auto_journal.py` — Hook pós-resposta que extrai automaticamente:
    - [x] Decisões tomadas → `MEMORY.md` (categoria: decisões)
    - [x] Preferências detectadas → `MEMORY.md` (categoria: preferências)
    - [x] Erros/falhas → `MEMORY.md` (categoria: lições aprendidas)
    - [x] Novos fatos relevantes → `MEMORY.md` (categoria: conhecimento)
  - [x] Classificador de relevância (keyword-based, zero LLM tokens)
  - [x] Deduplicação via SHA-256 hash
  - [x] `summarize_day()` — consolida daily notes em key insights

- [x] **Self-Reflection Engine** — P1 ✅
  - [x] `reflection_engine.py` — Análise periódica das interações recentes:
    - [x] Análise de falhas via failure indicators (keyword-based)
    - [x] Frequência de tópicos (Counter-based, 10 categorias)
    - [x] Confiança média por tópico (gap detection)
    - [x] Sugestões de melhoria automáticas
  - [x] Relatório semanal salvo em `workspace/memory/reflections/YYYY-WW.md`
  - [x] Knowledge Gap Detector — identifica tópicos com ≥2 falhas

- [x] **Cron Persistente (Self-Scheduling)** — P2 ✅
  - [x] `cron_scheduler.py` — Scheduler persistente em JSON:
    - [x] Jobs sobrevivem a restarts (JSON persistence `workspace/cron/jobs.json`)
    - [x] Suporta: one-shot (`at`), recurring (`every`), interval (`30m/1h/7d`)
    - [x] 2 modos: session_target `main` ou `isolated`
    - [x] `run_now()` para execução imediata
  - [x] API completa: `add()` / `remove()` / `list_jobs()` / `get()` / `run_now()`
  - [x] Emite `EventType.CRON_TRIGGERED` com payload (channel, session_target)
  - [ ] Use cases nativos (aguardando integração com channels):
    - [ ] Morning briefing (resumo do dia anterior)
    - [ ] Monitoring alerts (check periódico de APIs/serviços)
    - [ ] Scheduled research (buscar novidades sobre tópicos definidos)
    - [ ] Reminder system (lembretes criados pelo agent ou usuário)

- [x] **Skills Auto-Discovery** — P3 ✅
  - [x] `skills_discovery.py` — TF-IDF-like search no catálogo:
    - [x] `search(query)` com scoring de relevância (0.0-1.0)
    - [x] `detect_capability_gap(query)` — detecta quando falta skill
    - [x] `suggest_for_query(query)` — sugere skills por intent
  - [x] `watch_directory()` — hot-reload quando `SKILL.md` muda
  - [ ] Upgrade para PGvector embeddings (futuro)
  - [ ] Community skills directory (futuro: OptimusHub)

- [x] **Testes** ✅
  - [x] 30 testes em `tests/test_proactive.py` (Bootstrap 9, AutoJournal 8, Reflection 7, Cron 10, Discovery 6)

---

### Fase 11: Jarvis Mode (Semana 19-22) � EM PROGRESSO
> Além do OpenClaw — o assistente que antecipa, aprende, e evolui sozinho

- [x] **Proactive Research Engine** ✅
  - [x] `proactive_researcher.py` — Motor de pesquisa proativa:
    - [x] Sources configuráveis (RSS, GitHub, URL, API) com persistência JSON
    - [x] Rate limiting por fonte (`check_interval`: 1h/6h/24h/7d)
    - [x] `is_due_for_check()` verifica freshness automática
    - [x] `generate_briefing()` com relevance scoring e markdown formatado
  - [x] `add_source()`/`remove_source()`/`list_sources()`/`get_due_sources()`
  - [ ] Integração real com RSS parser e GitHub API (futuro)

- [x] **Predictive Actions (Antecipar Necessidades)** ✅
  - [x] `intent_predictor.py` — Baseado em padrões históricos:
    - [x] Detecta rotinas (day-of-week + time-of-day frequency analysis)
    - [x] `predict_next()` sugere ações proativamente em português
    - [x] 9 categorias de ação (deploy, bug_fix, meeting, research, etc.)
  - [x] Pattern learning via keyword analysis nas daily notes
  - [x] `save_patterns()` persistência em JSON

- [x] **Ambient Awareness (Consciência de Contexto)** ✅
  - [x] `context_awareness.py` — O agent sabe:
    - [x] Fuso horário + horário local do usuário (configurável, default BRT)
    - [x] Dia da semana com sugestões contextuais em português
    - [x] Business hours detection (Seg-Sex 9-18h)
    - [x] Time sensitivity (urgent/normal/relaxed)
  - [x] `generate_greeting()` com dados de atividade de ontem
  - [x] `build_context_prompt()` para injeção no system prompt

- [x] **Emotional Intelligence (Tom Adaptativo)** ✅
  - [x] `emotional_adapter.py` — Análise de sentimento keyword-based (zero LLM):
    - [x] Frustrado/estressado → DIRETO e SOLUCIONADOR
    - [x] Curioso/exploratório → DETALHADO e EDUCATIVO
    - [x] Com pressa → ULTRA-CONCISO
    - [x] Celebrando → compartilhar entusiasmo
  - [x] Tone instructions em português para injeção no prompt
  - [x] `log_mood()` persiste humor nas daily notes para continuidade

- [x] **Voice Interface (Talk Mode)** ✅
  - [x] `voice_interface.py` — Abstração com providers plugáveis:
    - [x] STT: Stub + Google Cloud Speech + Whisper (stubs prontos)
    - [x] TTS: Stub + Google TTS + ElevenLabs (stubs prontos)
    - [x] Wake word detection: "optimus" / "hey optimus"
    - [x] `strip_wake_word()` extrai comando do áudio
  - [x] Config: language, voice_name, speed, wake_words
  - [ ] Implementações reais dos providers (futuro: API keys)

- [x] **Autonomous Task Execution** ✅
  - [x] `autonomous_executor.py` — Para tasks de alta confiança, executar sem pedir permissão:
    - [x] Confidence threshold configurável (default: 0.9)
    - [x] Risk classification: LOW/MEDIUM/HIGH/CRITICAL
    - [x] CRITICAL sempre requer aprovação (nunca auto-executa)
    - [x] Audit trail completo em JSONL
  - [x] Daily budget (default: 50/dia) para evitar runaway
  - [x] Emite `EventType.TASK_COMPLETED` no EventBus

- [x] **Cross-Agent Learning (Inteligência Coletiva)** ✅
  - [x] `collective_intelligence.py` — Agents aprendem uns com os outros:
    - [x] `share()` publica knowledge com deduplicação SHA-256
    - [x] `query()` busca cross-agent com tracking de `used_by`
    - [x] `find_expert()` identifica qual agent sabe mais sobre um tópico
  - [x] `get_knowledge_graph()` visualiza quem sabe o quê
  - [ ] Upgrade para PGvector embeddings (futuro)

- [x] **Testes** ✅
  - [x] 42 testes em `tests/test_jarvis.py` (Researcher 10, Predictor 11, Context 8, Emotional 9, Voice 6, Executor 10, Collective 8)

---

### Comparação Final: OpenClaw vs Agent Optimus (Pós Fase 11)

| Capacidade | OpenClaw | Agent Optimus |
|------------|----------|---------------|
| Canais de comunicação | 14+ | 4+ (extensível via MCP) |
| **Boot sequence com memória** | ✅ | ✅ (Fase 10) |
| **Cron persistente** | ✅ | ✅ + Self-scheduling (Fase 10) |
| **Skills auto-discovery** | ✅ ClawHub | ✅ + Semântico (Fase 10) |
| **Self-Reflection** | ❌ | ✅ Knowledge Gap Detector (Fase 10) |
| **Proactive Research** | ❌ | ✅ Pesquisa autônoma (Fase 11) |
| **Predictive Actions** | ❌ | ✅ Antecipa necessidades (Fase 11) |
| **Emotional Intelligence** | ❌ | ✅ Tom adaptativo (Fase 11) |
| **Cross-Agent Learning** | ❌ | ✅ Inteligência coletiva (Fase 11) |
| **Autonomous Execution** | ❌ | ✅ Piloto automático (Fase 11) |
| **Voice Interface** | ✅ (ElevenLabs) | ✅ Wake word + streaming (Fase 11) |
| **Tree-of-Thought** | ❌ | ✅ 3 estratégias + meta-avaliação |
| **Uncertainty Quantifier** | ❌ | ✅ Calibração por PGvector |
| **Multi-setor via MCP** | ❌ (single-user) | ✅ Qualquer API plugável |
| **A2A Protocol** | ✅ sessions_* tools | ✅ Google ADK A2A |

> [!IMPORTANT]
> **Optimus = Jarvis.** Não apenas responde — *antecipa, aprende, evolui, e age*.
> OpenClaw é um excelente assistente pessoal. Optimus é um **sistema operacional de inteligência**.

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

### Fase 12: Agent Real — Tool Calling + ReAct Loop ✅ CONCLUÍDA
> Transformação para agent real que FAZ coisas

- [x] **Function Calling Nativo**
  - [x] Migrado para `generate_content_async()`
  - [x] Schema JSON para tools (Gemini `FunctionDeclaration`)
  - [x] Execução de tools segura com permission check

- [x] **ReAct Loop — Reason + Act + Observe**
  - [x] Loop agentic implementado em `BaseAgent.process()`
  - [x] Suporte multi-step (raciocínio → tool → observação → resposta)

- [x] **Multi-Provider LLM**
  - [x] Suporte a OpenAI, Groq e Anthropic via `model_router.py`

---

### Fase 13: Code Execution + Streaming ✅ CONCLUÍDA
> Agent Developer executa código e streaming real

- [x] **Code Execution Sandbox**
  - [x] `run_python` tool implementada (execução segura local)
  - [x] Timeout e sanitização de output

- [x] **Streaming Token-by-Token**
  - [x] Endpoint SSE implementado para chat real-time

---

### Fase 14: Vision & Multimodal Files ✅ CONCLUÍDA
> Olhos para o Optimus

- [x] **Vision Capabilities**
  - [x] Análise de imagens via URL (Gemini Flash/Pro)
  - [x] Upload de imagens para contexto multimodal

---

### Fase 15: Production Hardening ✅ CONCLUÍDA
> Segurança e Autenticação

- [x] **Autenticação Multi-Tenant**
  - [x] JWT middleware implementado
  - [x] Separação de contexto por usuário

---

### Fase 16: World-Class Polish ✅ CONCLUÍDA
> Observabilidade e Refinamento

- [x] **Observabilidade Total**
  - [x] Logs estruturados, métricas e tracing
  - [x] Dashboards de performance e custo

---

### Fase 17: Advanced RAG Knowledge Base ✅ CONCLUÍDA
> Cérebro Long-Term

- [x] **Advanced RAG**
  - [x] PGvector integration aprimorada
  - [x] Chunking semântico para melhor retrieval

---

### Fase 18: Multimodal Vision ✅ CONCLUÍDA
> Refinamento de Visão

- [x] **Vision 2.0**
  - [x] Suporte nativo a múltiplas imagens
  - [x] Integração com tools de browser para "ver" sites

---

### Fase 19: Advanced Document Ingestion ✅ CONCLUÍDA
> Leitura de Documentos Complexos

- [x] **Docs Support**
  - [x] Ingestão de PDF (pypdf)
  - [x] Ingestão de DOCX (python-docx)
  - [x] Processamento de binários via API

---

### Fase 20: Voice & Audio Capabilities ✅ CONCLUÍDA
> Ouvidos para o Optimus

- [x] **Audio Service**
  - [x] Transcrição via Gemini Flash (Multimodal nativo)
  - [x] Transcrição via Whisper (OpenAI/Groq)
  - [x] Ingestão de arquivos de áudio para o Knowledge Base

---

### Fase 21: Pre-Flight & Deploy ✅ CONCLUÍDA
> Decolagem

- [x] **Deployment Prep**
  - [x] Dockerfile Production-Ready (scripts incluídos)
  - [x] Guia de Deploy (`deploy_guide.md`)
  - [x] Configuração de Variáveis de Ambiente
  - [x] Commit final para CI/CD (Coolify)

---

## ✅ Status Atual: Em Produção (Fases 1-21 Concluídas)
O Agent Optimus atingiu a maturidade de **Plataforma Multimodal de Inteligência Artificial**.
Core funcional em produção. Fase 22 em andamento (hardening e features reais).

---

### Fase 22: Production Hardening & Real Integrations 🔴 EM ANDAMENTO
> Fechar gaps encontrados no primeiro deploy real em produção

#### 🐛 Bugs Corrigidos (Deploy)
- [x] `uuid_generate_v4()` → `gen_random_uuid()` na migration 011
- [x] Import errado `async_session` → `get_async_session` (session_manager + mcp_tools)
- [x] `session_bootstrap.load_context()` sem `agent_name` no gateway
- [x] `session_bootstrap.build_prompt()` → chamado no `BootstrapContext` retornado, não no objeto SessionBootstrap
- [x] `auto_journal.process_interaction()` → método correto é `extract_and_save()`
- [x] Migração `google.generativeai` → `google.genai` (pacote depreciado)
- [x] ReAct loop: fallback para `_process_simple` em vez de retornar erro ao usuário
- [x] `search_knowledge_base` MCPTool: parâmetros em formato JSON Schema em vez de flat dict (causava `AttributeError: 'str' object has no attribute 'get'`)
- [x] Chain `complex`: `claude-sonnet` (sem chave Anthropic) → `gemini-2.5-flash`
- [x] LiteLLM pricing warnings suprimidos em produção
- [x] **Frontend: `data.data.response` → `data.data.content`** (bug crítico — chat retornava 200 OK mas UI mostrava "Resposta vazia")
- [x] `sse-starlette` adicionado ao requirements.txt (faltava para endpoint de streaming)

#### 🔧 Gaps Conhecidos a Implementar

**P0 — Chat & Core (bloqueia uso)**
- [ ] **Busca Web Real** — `research_search` é stub; integrar [Tavily API](https://tavily.com) ou [SerpAPI](https://serpapi.com)
- [ ] **Suprimir warning `GOOGLE_API_KEY + GEMINI_API_KEY`** — LiteLLM detecta as duas variáveis; remover `GEMINI_API_KEY` do ambiente Coolify ou do `_configure_api_keys()`

**P1 — Features (melhora experiência)**
- [ ] **Busca semântica na memória de longo prazo** — atualmente é keyword-based; migrar para PGvector (embeddings já existem)
- [ ] **WORKING.md sincronizado com Supabase** — atualmente file-based apenas; sincronizar com tabela `agents.learning_data`
- [ ] **Chat Commands no WebChat** — `/status`, `/think`, `/agents`, `/learn` — já implementados em `chat_commands.py` mas não conectados ao chat endpoint
- [ ] **Sessão persistente entre reloads** — usuário perde histórico ao recarregar a página

**P2 — Canais (expansão)**
- [ ] **Telegram Bot** — código existe em `channels/telegram.py`; configurar webhook no Coolify com `TELEGRAM_TOKEN`
- [ ] **WhatsApp via Evolution API** — código existe em `channels/whatsapp.py`; requer deploy da Evolution API
- [ ] **Cron Jobs nativos** — `cron_scheduler.py` implementado mas não inicializado no `lifespan` do main.py

**P3 — Agentes adicionais (squad completo)**
- [ ] Registrar `analyst` (Shuri), `writer` (Loki), `guardian` (Vision) no Gateway
- [ ] Criar `souls/analyst.md`, `souls/writer.md`, `souls/guardian.md`
- [ ] Routing automático por intent (ex: perguntas de código → Friday, pesquisa → Fury)

**P4 — Observabilidade (produção saudável)**
- [ ] Grafana Dashboard com métricas Prometheus (já coletadas, falta visualização)
- [ ] Alertas Telegram para erros CRITICAL em produção (`TelegramAlertHandler`)
- [ ] Daily Standup automático às 09:00 BRT

---

### Comparação Final: Pré vs Pós Fases 12-15

| Capacidade | Pré (Fase 11) | Pós (Fase 15) |
|------------|---------------|---------------|
| **Tool Calling** | Simulado via prompt | Nativo (LLM decide) |
| **Agentic Loop** | Single round-trip | ReAct multi-step |
| **Code Execution** | Não executa | Sandbox isolado |
| **LLM Providers** | Só Gemini | Gemini + OpenAI + Anthropic + Ollama + Groq |
| **Streaming** | Resposta completa | Token-by-token SSE |
| **Auth** | Nenhuma | JWT + API keys + RBAC |
| **Conversation Memory** | Stateless | Persistente com compressão |
| **Multimodal** | Só texto | Imagens + PDFs + CSVs |
| **Planning** | Não planeja | Decomposição + aprovação |
| **Self-Correction** | Falha e para | Analisa + ajusta + retenta |
| **Human-in-the-Loop** | Não pede confirmação | Pausa em ações destrutivas |
| **Observabilidade** | Logs + métricas básicas | OpenTelemetry + traces + dashboards |
| **Eval** | Sem benchmark | Suite automatizada no CI |
| **RAG** | Básico (similarity) | Hybrid search + re-ranking |
| **Cost Control** | Rate limit por request | Budget em $ por tenant |
| **Voice** | Stubs | Whisper + ElevenLabs real |
| **Classificação** | Chatbot sofisticado (7/10) | **Agent estado da arte (10/10)** |

> [!IMPORTANT]
> **Fases 12-15 transformam o Optimus de um chatbot com arquitetura de agent em um agent REAL.**
> A ordem é intencional: primeiro o agent precisa FAZER coisas (Fase 12), depois fazer BEM (Fase 13-14), depois fazer com EXCELÊNCIA (Fase 15).

---

## ✅ Critérios de Sucesso

### Fases 1-11 (Fundação)

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

### Fases 12-15 (Estado da Arte)

| Critério | Meta |
|----------|------|
| Tool calling accuracy | > 95% (LLM seleciona tool correta) |
| ReAct loop completion | > 90% das tarefas multi-step concluídas |
| Code execution success rate | > 85% (executa, testa, corrige) |
| Streaming TTFB | < 200ms (time to first byte) |
| Concurrent users sem degradação | 50+ requests paralelos |
| Auth + multi-tenant | 100% das requests autenticadas em prod |
| Eval benchmark score | > 80% no suite de avaliação |
| RAG hybrid search accuracy | > 90% relevância (BM25 + semantic) |
| Cost tracking accuracy | < 2% margem de erro no custo calculado |
| Voice latency (end-to-end) | < 500ms (fala → resposta) |
| Self-correction rate | > 70% dos erros corrigidos automaticamente |
| Zero blocking async calls | 100% (nenhuma chamada síncrona no event loop) |

---

> [!IMPORTANT]
> **Agent Optimus = Sistema Operacional de AI Agents**
> Uma plataforma onde agents se conectam a **qualquer API** via MCP, operam em **qualquer setor**, aprendem entre sessões, e colaboram entre si.

### Fase 23: Authentication UI (Semana 23) ✅ CONCLUÍDA
> Interface visual de Login e Registro para persistência de usuários SaaS.

- [x] **Auth Pages** (HTML/Tailwind)
  - [x] `login.html` — Email/Password + "Esqueci a senha"
  - [x] `register.html` — Nome, Email, Senha, Confirmação
  - [x] Integração com `/api/v1/auth/login` e `/api/v1/auth/register`
- [x] **Session Logic** (JS)
  - [x] `auth.js` — Gerenciamento de JWT (localStorage)
  - [x] Redirect automático (Guest → Login → Dashboard)
  - [x] Logout flow
- [ ] **User Profile**
  - [ ] Avatar upload (Gravatar fallback)
  - [ ] Alteração de senha

---

## ⚠️ REGRA DE OURO — CHECKLIST OBRIGATÓRIO ANTES DE QUALQUER IMPLEMENTAÇÃO

> **NÃO pode desenvolver sem validar isso primeiro.**
> **Se algum checkpoint falhar, a feature NÃO é implementada até passar.**
> **LEIA ISSO ANTES DE QUALQUER PULL REQUEST.**

### Antes de Escrever Uma Linha de Código

```
┌─────────────────────────────────────────────────────────────┐
│ CHECKLIST: Essa feature será realmente CHAMADA?             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ 1️⃣  CALL PATH DOCUMENTADO                                   │
│    ❓ Qual função/classe vai chamar esse código?            │
│    ❓ Em qual arquivo (main.py / gateway.py / base.py)?     │
│    ❓ Em que condição? (startup / per-request / cron?)      │
│    → Se não conseguir responder: NÃO IMPLEMENTE             │
│                                                             │
│ 2️⃣  TESTE QUE FALHA SEM A FEATURE                           │
│    ❓ Criar teste que quebra se o código não for chamado?   │
│    ❓ O teste será executado no CI?                         │
│    ❓ Test falha se remover a chamada? (sanity check)       │
│    → Se o teste passa mesmo com código morto: NÃO SERVE     │
│                                                             │
│ 3️⃣  FLUXO END-TO-END TESTADO EM PRODUÇÃO                    │
│    ❓ Usuário toca em algo? (botão, comando, requisição)    │
│    ❓ Feature é REALMENTE chamada pelo fluxo?               │
│    ❓ Testado em produção (optimus.tier.finance)?           │
│    ❓ Não falhou? Então está pronto                         │
│    → Se não testou em prod: NÃO ESTÁ PRONTO                │
│                                                             │
│ 4️⃣  INTEGRAÇÃO NO ROADMAP DOCUMENTADA                       │
│    ❓ Feature está listada em uma FASE?                     │
│    ❓ Call path está documentado nesta seção?               │
│    ❓ Status marcado como [x] completo ou [] pendente?      │
│    → Sem isso: é código perdido                             │
│                                                             │
│ 5️⃣  NENHUM IMPORT/CÓDIGO MORTO SOBREVIVE                    │
│    ❓ Rodar: grep -r "import nome_modulo" src/ | grep -v ".pyc"
│    ❓ Cada import tem pelo menos 1 call site real?          │
│    ❓ Ou será que apenas herança/base class (ok)?           │
│    → Se importado mas NUNCA chamado: DELETE OU INTEGRAR     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### ❌ Exemplo: Feature REJEITADA

```python
# src/engine/tot_engine.py (REJEITADO)
class ToTEngine:
    def think(self, question):
        # 500 linhas de código sofisticado
        return hypotheses

# PROBLEMA: Ninguém chama tot_engine.think()
# - Não está em BaseAgent.process() ❌
# - Não está em gateway.py ❌
# - Não está em react_loop.py ❌
# - Nenhum teste valida que é chamado ❌
# - Nenhum usuário real vê efeito ❌
# = CÓDIGO MORTO = DELETE
```

### ✅ Exemplo: Feature APROVADA

```python
# src/core/gateway.py (linha 144-145) — APROVADO
sentiment = await emotional_adapter.analyze(message)
if sentiment.is_frustrated:
    system_prompt += " [Tone: Direct & Solution-Focused]"

# APROVADO porque:
# ✅ 1. Call path: gateway.py linha 144 → emotional_adapter.analyze()
# ✅ 2. Teste: test_gateway.py::test_emotional_adapter_called()
# ✅ 3. Teste falha se remover a linha ✅
# ✅ 4. E2E: user frustrado → sentiment detectado → tom muda → funciona
# ✅ 5. Roadmap: Fase 22 "Emotional Adapter" [x] completo
# ✅ 6. Usado toda vez que usuário envia mensagem
# ✅ 7. Nada de código morto
```

### Consequence of Violation

Se código for desenvolvido **violando essa regra**:
- 🗑️ **DELETE** do codebase na próxima review
- 🚫 **Não aprova** PR sem call path claro
- 📊 **CI futura**: lint que falha se module importado mas nunca chamado

---

## DIAGNÓSTICO REAL DE PRODUÇÃO (Fevereiro 2026)

> **Avaliação honesta.** Código auditado linha a linha.
> Separação entre o que FUNCIONA em produção vs o que é código morto.

---

### O que FUNCIONA de verdade (testado em prod)

- [x] Chat básico — pergunta → resposta via Gemini (ReAct loop + fallback `_process_simple`)
- [x] Login/Registro JWT — `login.html`, `register.html`, `auth.js`, middleware JWT
- [x] Histórico de mensagens — últimas 30 carregadas no page load (tabela `conversations`)
- [x] STT (Speech-to-Text) — Mic → MediaRecorder → Groq Whisper → transcrição
- [x] TTS (Text-to-Speech) — Edge TTS (`pt-BR-FranciscaNeural`) via backend, on-demand
- [x] Migrations SQL — rodam no boot com parser de dollar-quoted strings
- [x] Multi-model failover — chains: default, complex, economy (Gemini Flash → Pro → GPT-4o)
- [x] Session Bootstrap — SOUL.md + MEMORY.md carregados no system prompt
- [x] Tool Calling nativo — Gemini function calling (db_query, run_python, etc.)
- [x] Emotional Adapter — análise de sentimento injetada no prompt via gateway
- [x] Planning Engine — decomposição de tarefas complexas via gateway
- [x] Auto-Journal — extração de aprendizados pós-resposta no Optimus
- [x] Persona Selector — seleção dinâmica de persona por intent no Optimus
- [x] Agent Factory — instanciação de agents com registry
- [x] Session Manager — histórico de conversa + add_message
- [x] Cost Tracker — tracking assíncrono de uso (fire-and-forget)
- [x] UI redesenhada — Chat "Como posso ajudar?", seletor de agente, mic inline
- [x] Deploy CI/CD — Push → Coolify → Docker → produção automática

---

### O que EXISTE como código mas NÃO funciona / NÃO é chamado

> **54% dos módulos (28 de 52) estão órfãos — nunca chamados no fluxo real.**

#### ENGINE (7 de 11 não usados = 73% morto)

- [ ] `tot_engine.py` / `tot_service.py` — Tree-of-Thought (3 estratégias + meta-avaliação) — **nunca chamado por nenhum agent**
- [ ] `uncertainty.py` — UncertaintyQuantifier (calibração via PGvector) — **nunca chamado**
- [ ] `intent_classifier.py` — Classificação de intent (8 tipos) — **substituído por planning_engine, mas não removido**
- [ ] `intent_predictor.py` — Predição de padrões comportamentais — **stub Jarvis Phase 11, nunca chamado**
- [ ] `autonomous_executor.py` — Execução autônoma de tarefas confiantes — **nunca chamado**
- [ ] `proactive_researcher.py` — Pesquisa proativa (RSS, GitHub) — **stub sem API real, nunca chamado**
- [ ] `reflection_engine.py` — Análise semanal de interações — **gera markdown que ninguém lê**

#### MEMORY (3 de 8 não usados = 38% morto)

- [ ] `working_memory.py` — WORKING.md manager (scratchpad por agent) — **nunca integrado no session context**
- [ ] `rag.py` — RAG Pipeline (chunking + similarity + augment_prompt) — **nunca chamado; knowledge_tool existe separado**
- [ ] `collective_intelligence.py` — Cross-agent knowledge sharing — **nunca chamado**

#### CHANNELS (6 de 7 não usados = 86% morto)

- [ ] `telegram.py` — TelegramChannel (python-telegram-bot) — **código existe, zero config, não inicializado**
- [ ] `whatsapp.py` — WhatsAppChannel (Evolution API) — **código existe, sem Evolution API deployada**
- [ ] `slack.py` — SlackChannel (Bolt) — **código existe, zero config**
- [ ] `webchat.py` — WebChatChannel (REST+SSE) — **código existe, não chamado (UI usa API direto)**
- [ ] `chat_commands.py` — 9 comandos (`/status`, `/think`, `/agents`, etc.) — **implementados, não conectados ao endpoint `/api/v1/chat`**
- [ ] `voice_interface.py` — VoiceInterface (wake word + providers) — **todos providers são stubs; STT/TTS real é pelo audio_service.py**

#### SKILLS (3 de 6 não usados = 50% morto)

- [ ] `mcp_plugin.py` — Loader dinâmico de MCP externo — **nunca chamado**
- [ ] `skills_discovery.py` — Busca semântica de skills (TF-IDF) — **nunca chamado**
- [ ] `tools_manifest.py` — Gerador de TOOLS.md — **nunca chamado**

#### COLLABORATION (2 de 5 não usados, 3 só via chat_commands = 100% fora do fluxo principal)

- [ ] `thread_manager.py` — Comentários em tasks + subscriptions — **nunca chamado**
- [ ] `notification_service.py` — Fila de notificações — **nunca chamado**
- [ ] `task_manager.py` — CRUD de tasks — **só chamado pelo chat_commands (que também não é chamado)**
- [ ] `activity_feed.py` — Log de eventos — **só chamado pelo standup_generator (que não é chamado)**
- [ ] `standup_generator.py` — Daily standup — **só chamado pelo chat_commands (que não é chamado)**

#### CORE/INFRA (6 de 12 não usados = 50% morto)

- [ ] `orchestrator.py` — ADK-style Sequential/Parallel/Loop — **nunca chamado**
- [ ] `a2a_protocol.py` — Agent-to-Agent discovery + messaging — **nunca chamado**
- [ ] `cron_scheduler.py` — Scheduler persistente (JSON) — **framework existe, nenhum job registrado**
- [ ] `cron_jobs_native.py` — Jobs pré-definidos (morning briefing, alerts) — **nunca chamado**
- [ ] `context_awareness.py` — Fuso horário + business hours + greeting — **nunca chamado**
- [ ] `confirmation_service.py` — Human-in-the-loop confirmations — **nunca chamado**
- [ ] `performance.py` — SessionPruner + ContextCompactor + QueryCache — **nunca chamado**
- [ ] `security.py` — Permission matrix (8 perms × 3 levels) — **importado no gateway mas nunca enforcement real**

---

### Bugs Corrigidos em Produção (Fase 22)

- [x] `uuid_generate_v4()` → `gen_random_uuid()` na migration 011
- [x] Import errado `async_session` → `get_async_session`
- [x] `session_bootstrap.load_context()` sem `agent_name`
- [x] `session_bootstrap.build_prompt()` chamado no objeto errado
- [x] `auto_journal.process_interaction()` → `extract_and_save()`
- [x] Migração `google.generativeai` → `google.genai`
- [x] ReAct loop: fallback para `_process_simple`
- [x] `search_knowledge_base` MCPTool: formato de parâmetros errado
- [x] Chain `complex`: `claude-sonnet` → `gemini-2.5-flash`
- [x] LiteLLM pricing warnings suprimidos
- [x] Frontend: `data.data.response` → `data.data.content`
- [x] `sse-starlette` adicionado ao requirements.txt
- [x] Auth 404: rotas `/login.html` e `/register.html`
- [x] Auth 422: `auth.js` form-urlencoded → JSON, `username` → `email`
- [x] SQL parser: `migrate_all.py` dollar-quoted strings
- [x] Mic: MediaRecorder sem timeslice + send desabilitado durante gravação

