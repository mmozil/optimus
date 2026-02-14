# 🏗️ Engineering Guide — Agent Optimus

Documento de engenharia de software para o Agent Optimus. Define arquitetura, padrões, convenções e diretrizes com qualidade de startup unicórnio. Derivado do [ENGINEERING-GUIDE.md](file:///d:/Project/AgentCrew/.docs/ENGINEERING-GUIDE.md) (template genérico), adaptado à realidade específica do projeto.

**Stack:** Python (FastAPI) · Agno (agents) · Google ADK (orchestration) · Supabase (PostgreSQL + PGvector + Real-time) · Redis · Docker · Hetzner + Coolify

---

## Índice

1. [Princípios fundamentais](#1-princípios-fundamentais)
2. [Estrutura do repositório](#2-estrutura-do-repositório)
3. [Arquitetura de serviços](#3-arquitetura-de-serviços)
4. [Comunicação entre serviços](#4-comunicação-entre-serviços)
5. [Banco de dados (Supabase)](#5-banco-de-dados-supabase)
6. [Redis — cache, filas e rate limiting](#6-redis--cache-filas-e-rate-limiting)
7. [Autenticação e autorização](#7-autenticação-e-autorização)
8. [Design de API](#8-design-de-api)
9. [Arquitetura de agentes de IA](#9-arquitetura-de-agentes-de-ia)
10. [RAG — Retrieval-Augmented Generation](#10-rag--retrieval-augmented-generation)
11. [Observabilidade](#11-observabilidade)
12. [CI/CD e qualidade de código](#12-cicd-e-qualidade-de-código)
13. [Segurança](#13-segurança)
14. [Infraestrutura — Hetzner + Coolify](#14-infraestrutura--hetzner--coolify)
15. [Testes](#15-testes)
16. [Padrões de código Python](#16-padrões-de-código-python)
17. [Convenções de projeto](#17-convenções-de-projeto)
18. [Checklist de novo agent](#18-checklist-de-novo-agent)
19. [Anti-patterns a evitar](#19-anti-patterns-a-evitar)

---

## 1. Princípios fundamentais

### 1.1 Filosofia Optimus

- **Born cloud-native:** Todo componente roda em container desde o dia 1.
- **API-first:** Toda funcionalidade exposta via API REST ou MCP antes de ter UI.
- **12-Factor App:** Configuração por env vars, processos stateless, logs como streams.
- **Event-driven first:** Supabase Real-time + Redis Pub/Sub. Polling é último recurso.
- **Agent-as-a-Platform:** Agents são plugáveis via MCP. Qualquer API vira agent.
- **Fail fast, recover gracefully:** Circuit breakers, retries com backoff, health checks.
- **Observability from day 1:** Structured logging, correlation IDs, métricas Prometheus.

### 1.2 Regras inegociáveis

| Regra | Motivo |
|-------|--------|
| Zero secrets no código | Usar env vars ou Coolify secrets |
| Toda mudança de schema via Alembic migration | Nunca `create_all()` em produção |
| Testes antes de merge | CI bloqueia merge sem testes passando |
| Correlation ID em todo request | Rastreabilidade ponta a ponta |
| Rate limiter em todo agent | Prevenir 429 e custo descontrolado |
| Event-driven > polling | Supabase Real-time primeiro, heartbeat como fallback |
| SOUL.md por agent | Personalidade documentada, versionada, auditável |
| MCP para toda integração externa | Padrão aberto, descobrível, testável |
| Backwards-compatible API changes | Nunca quebrar contratos sem versionamento |
| Docker tags semânticas | Nunca `latest` em produção |

### 1.3 Tomada de decisão

1. **Simplicidade > Elegância.** Código simples que funciona vence arquitetura perfeita que não entrega.
2. **Composição > Herança.** Preferir injeção de dependência e composição de funções.
3. **Explícito > Implícito.** Configuração, imports e erros explícitos.
4. **Convenção > Configuração.** Seguir as convenções deste guia; só desviar com ADR documentado.

---

## 2. Estrutura do repositório

### 2.1 Monorepo com serviços isolados

```
AgentOptimus/
├── services/
│   ├── ai-svc/                    # Serviço principal de IA/Agentes
│   │   ├── app/
│   │   │   ├── agents/            # Definições de agents (Agno)
│   │   │   │   ├── base.py        # BaseAgent (wrapper Agno)
│   │   │   │   ├── optimus.py     # Lead Orchestrator
│   │   │   │   ├── friday.py      # Developer
│   │   │   │   ├── fury.py        # Researcher
│   │   │   │   └── ...
│   │   │   ├── engine/            # Inteligência (ToT, Uncertainty)
│   │   │   │   ├── tot_engine.py
│   │   │   │   ├── tot_service.py
│   │   │   │   ├── uncertainty.py
│   │   │   │   └── intent_classifier.py
│   │   │   ├── memory/            # Sistema de memória
│   │   │   │   ├── working_memory.py
│   │   │   │   ├── daily_notes.py
│   │   │   │   ├── long_term.py
│   │   │   │   ├── embeddings.py
│   │   │   │   └── rag.py
│   │   │   ├── identity/          # SOUL.md, Personas
│   │   │   │   ├── soul_loader.py
│   │   │   │   ├── personas.py
│   │   │   │   └── tools_manifest.py
│   │   │   ├── skills/            # MCP Tools
│   │   │   │   ├── browser.py
│   │   │   │   ├── database.py
│   │   │   │   ├── filesystem.py
│   │   │   │   ├── research.py
│   │   │   │   ├── terminal.py
│   │   │   │   └── mcp_plugin.py  # Loader dinâmico MCP externo
│   │   │   ├── collaboration/     # Tasks, Threads, Notifications
│   │   │   │   ├── task_manager.py
│   │   │   │   ├── thread_manager.py
│   │   │   │   ├── notification_service.py
│   │   │   │   ├── activity_feed.py
│   │   │   │   └── standup_generator.py
│   │   │   ├── shared/            # Código compartilhado do serviço
│   │   │   │   ├── config.py      # Settings (Pydantic BaseSettings)
│   │   │   │   ├── supabase_client.py
│   │   │   │   ├── redis_client.py
│   │   │   │   ├── model_router.py
│   │   │   │   ├── sandbox.py
│   │   │   │   └── middleware/
│   │   │   │       ├── correlation.py
│   │   │   │       ├── request_log.py
│   │   │   │       ├── rate_limit.py
│   │   │   │       └── security_headers.py
│   │   │   └── main.py            # ~50 linhas: app + middleware + routers
│   │   ├── alembic/
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── pyproject.toml
│   │
│   ├── channel-svc/               # Canais de comunicação
│   │   ├── app/
│   │   │   ├── channels/
│   │   │   │   ├── telegram.py
│   │   │   │   ├── whatsapp.py
│   │   │   │   ├── webchat.py
│   │   │   │   └── webhook.py
│   │   │   ├── commands/          # Chat commands (/status, /think, etc.)
│   │   │   ├── shared/
│   │   │   └── main.py
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   └── gateway/                   # API Gateway (Traefik)
│       ├── traefik.yml
│       └── dynamic/
│
├── libs/                          # Bibliotecas compartilhadas
│   ├── shared-schemas/            # Pydantic models (events, contracts)
│   │   ├── events.py
│   │   ├── agent_schemas.py
│   │   └── common.py
│   └── shared-utils/              # Utilidades comuns
│       ├── logging.py             # JSONFormatter + correlation
│       ├── redis_client.py
│       └── http_client.py         # Client com retry + circuit breaker
│
├── workspace/                     # Workspace dos agents
│   ├── AGENTS.md                  # Manual operacional global
│   ├── HEARTBEAT.md               # Checklist de wake-up
│   ├── souls/                     # SOUL.md por agent
│   │   ├── optimus.md
│   │   ├── friday.md
│   │   └── fury.md
│   └── memory/                    # Memória persistente
│       ├── working/
│       ├── daily/
│       └── long_term/
│
├── migrations/                    # Supabase migrations SQL
│   ├── 001_agents.sql
│   ├── 002_tasks.sql
│   └── ...
│
├── infra/
│   ├── docker-compose.yml         # Dev local
│   ├── docker-compose.prod.yml    # Produção
│   ├── monitoring/
│   │   ├── prometheus.yml
│   │   └── grafana/dashboards/
│   └── scripts/
│       ├── backup-db.sh
│       └── seed-dev.sh
│
├── .docs/                         # Documentação viva
│   ├── Roadmap-Optimus.md
│   ├── ENGINEERING-OPTIMUS.md     # Este arquivo
│   ├── ENGINEERING-GUIDE.md       # Template genérico (referência)
│   ├── Prompt-COT.md
│   └── ADR/                       # Architecture Decision Records
│
├── .github/workflows/
│   ├── ci.yml
│   ├── deploy-staging.yml
│   └── deploy-prod.yml
│
├── .pre-commit-config.yaml
├── .env.example
├── docker-compose.yml
├── requirements.txt
├── pyproject.toml
└── README.md
```

### 2.2 Regras de organização

- **Cada serviço é independente:** tem seu próprio `Dockerfile`, `requirements.txt`, `tests/`.
- **`workspace/` é versionado:** SOUL.md, memória e notas diárias vão no git.
- **`libs/` é compartilhado:** Schemas Pydantic e utilidades comuns.
- **Nunca commitar:** `.env`, `*.db`, `__pycache__/`, `node_modules/`, `.venv/`.

---

## 3. Arquitetura de serviços

### 3.1 Serviços do Agent Optimus

| Serviço | Responsabilidade | Porta dev | Quando |
|---------|-----------------|-----------|--------|
| `ai-svc` | Agents, ToT, RAG, memória, collaboration | 8001 | Dia 1 |
| `channel-svc` | Telegram, WhatsApp, WebChat, Webhooks | 8002 | Fase 4 |
| `gateway` | Roteamento, TLS, rate limiting | 80/443 | Dia 1 |

> [!TIP]
> Começar com `ai-svc` + `gateway`. Extrair `channel-svc` apenas na Fase 4.

### 3.2 Diagrama de comunicação

```
         Internet
            │
      ┌─────▼─────┐
      │  Gateway   │  (Traefik)
      │  :80/443   │
      └─────┬──────┘
            │ HTTP/HTTPS
     ┌──────┼──────┐
     ▼             ▼
┌─────────┐  ┌──────────┐
│  ai-svc │  │channel-  │
│  :8001  │  │svc :8002 │
└────┬────┘  └────┬─────┘
     │            │
     │  ┌─────────▼──────────┐
     │  │ Redis               │
     │  │ Cache + Pub/Sub +   │
     │  │ Rate Limiting       │
     │  └────────────────────┘
     │
┌────▼───────────────────────┐
│  Supabase (PostgreSQL)      │
│  + PGvector + Real-time     │
│  Tables: agents, tasks,     │
│  messages, embeddings, etc. │
└────────────────────────────┘
```

### 3.3 Regras de comunicação

| Tipo | Quando usar | Implementação |
|------|-------------|---------------|
| **Supabase Real-time** | Notificações entre agents | `supabase.channel('agents').on('INSERT', ...)` |
| **Redis Pub/Sub** | Broadcast (cache invalidation) | `PUBLISH` / `SUBSCRIBE` |
| **HTTP síncrono** | channel-svc → ai-svc | `httpx.AsyncClient` com retry |
| **MCP Protocol** | Integração com APIs externas | MCP Server por API |

---

## 4. Comunicação entre serviços

### 4.1 HTTP Client padronizado

```python
# libs/shared-utils/http_client.py
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

class ServiceClient:
    """Client HTTP com retry, timeout e propagação de correlation_id."""

    def __init__(self, base_url: str, service_name: str, internal_key: str):
        self.base_url = base_url
        self.service_name = service_name
        self.internal_key = internal_key

    def _headers(self) -> dict:
        from libs.shared_utils.logging import get_correlation_id
        return {
            "X-Internal-Key": self.internal_key,
            "X-Request-ID": get_correlation_id() or "",
            "X-Source-Service": self.service_name,
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.5, max=5))
    async def post(self, path: str, **kwargs) -> httpx.Response:
        async with httpx.AsyncClient(
            base_url=self.base_url, timeout=httpx.Timeout(30.0, connect=5.0)
        ) as client:
            response = await client.post(path, headers=self._headers(), **kwargs)
            response.raise_for_status()
            return response
```

### 4.2 Circuit Breaker

```python
# libs/shared-utils/circuit_breaker.py
class CircuitBreaker:
    """5 falhas = circuito abre por 30s. Protege contra cascading failures."""
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.state = "closed"  # closed | open | half_open
```

### 4.3 Supabase Real-time (Event-driven)

```python
# Agent wake-up via Supabase Real-time (ZERO tokens)
from supabase import create_client

supabase = create_client(url, key)

# Inscrever agent em mudanças de tasks
channel = supabase.channel('agent-tasks')
channel.on('postgres_changes',
    event='INSERT',
    schema='public',
    table='tasks',
    filter=f'assignee_ids=cs.{{{agent_id}}}',
    callback=on_new_task_assigned
).subscribe()

async def on_new_task_assigned(payload):
    """Agent acorda quando task é atribuída — ZERO tokens gastos no wake-up."""
    task = payload['new']
    await agent.process_task(task)
```

---

## 5. Banco de dados (Supabase)

### 5.1 Por que Supabase e não PostgreSQL raw

| Feature | PostgreSQL raw | Supabase |
|---------|---------------|----------|
| Real-time push | ❌ Precisa implementar | ✅ Built-in |
| Auth | ❌ Implementar do zero | ✅ Built-in |
| Storage | ❌ Implementar do zero | ✅ Built-in |
| PGvector | ✅ Extension | ✅ Extension (pré-instalado) |
| Dashboard | ❌ pgAdmin | ✅ Web UI |
| Edge Functions | ❌ | ✅ Deno runtime |
| Free tier | ❌ | ✅ 500MB DB |

### 5.2 Schema do Agent Optimus

Ver [Roadmap-Optimus.md](file:///d:/Project/AgentCrew/.docs/Roadmap-Optimus.md) seção `Schema Supabase` para as 9 tabelas completas.

**Convenções de schema:**

| Regra | Exemplo |
|-------|---------|
| Tabelas em `snake_case` plural | `agents`, `tasks`, `embeddings` |
| Colunas em `snake_case` | `created_at`, `agent_id` |
| UUID como primary key | `id UUID PRIMARY KEY DEFAULT gen_random_uuid()` |
| Foreign keys explícitas com ondelete | `REFERENCES tasks(id) ON DELETE CASCADE` |
| Sempre `TIMESTAMPTZ` | Armazenar em UTC |
| Status como `VARCHAR` | Flexível, sem ALTER nos enums |
| JSONB para dados dinâmicos | `metadata JSONB DEFAULT '{}'` |

### 5.3 Migrações

**Regra: Usar migrations SQL em `migrations/` e aplicar via Supabase CLI ou Alembic.**

```bash
# Aplicar migrations via supabase CLI
supabase db push

# Ou via Alembic (se usar AsyncSession local)
alembic upgrade head
```

**Regras de migrações:**

1. **Nunca editar migrações já aplicadas em produção.**
2. **Uma migração por feature/PR.**
3. **Nomes descritivos:** `003_add_thread_subscriptions.sql`.
4. **Sempre testável:** `alembic upgrade head && alembic downgrade -1 && alembic upgrade head`.

---

## 6. Redis — cache, filas e rate limiting

### 6.1 Padrões de uso

| Uso | Key pattern | TTL | Exemplo |
|-----|-------------|-----|---------|
| Session de agent | `agent:session:{agent_id}` | 24h | `agent:session:optimus-uuid` |
| Rate limiting | `rate:{agent_id}:{minute}` | 60s | `rate:friday-uuid:202602131523` |
| Cache de query | `cache:tasks:{hash}` | 5min | `cache:tasks:abc123` |
| Lock distribuído | `lock:task:{task_id}` | 30s | `lock:task:uuid` |
| Conversation history | `memory:conv:{conv_id}` | 24h | `memory:conv:uuid` |

### 6.2 Rate Limiter para Agents (Anti-429)

```python
# shared/rate_limiter.py
import redis.asyncio as aioredis

RATE_LIMITS = {
    "lead":       {"rpm": 10, "rpd": 500},
    "specialist": {"rpm": 5,  "rpd": 200},
    "intern":     {"rpm": 2,  "rpd": 50},
}

class AgentRateLimiter:
    def __init__(self, redis: aioredis.Redis):
        self.redis = redis

    async def can_call_llm(self, agent_id: str, level: str) -> bool:
        limits = RATE_LIMITS.get(level, RATE_LIMITS["specialist"])
        minute_key = f"rate:{agent_id}:{current_minute()}"
        current = await self.redis.incr(minute_key)
        if current == 1:
            await self.redis.expire(minute_key, 60)
        return current <= limits["rpm"]
```

---

## 7. Autenticação e autorização

### 7.1 Arquitetura

Para o Agent Optimus, segurança opera em 2 níveis:

| Nível | Mecanismo | Contexto |
|-------|-----------|----------|
| **User → API** | Supabase Auth (JWT) | Quando usuário acessa via WebChat |
| **Agent → Agent** | `X-Internal-Key` + SOUL.md level | Comunicação interna |
| **Channel → ai-svc** | Webhook secret | Telegram/WhatsApp → ai-svc |

### 7.2 Permission Matrix por nível de agent

```python
PERMISSIONS = {
    "lead": {
        "can_delegate": True,
        "can_create_tasks": True,
        "can_access_all_tools": True,
        "max_tokens_per_call": 8192,
    },
    "specialist": {
        "can_delegate": False,
        "can_create_tasks": True,
        "can_access_all_tools": False,
        "max_tokens_per_call": 4096,
    },
    "intern": {
        "can_delegate": False,
        "can_create_tasks": False,
        "can_access_all_tools": False,
        "max_tokens_per_call": 2048,
        "sandbox": True,  # Docker isolado
    },
}
```

---

## 8. Design de API

### 8.1 Convenções REST

| Ação | Método | Path | Status |
|------|--------|------|--------|
| Chat com agent | POST | `/api/v1/chat` | 200 |
| Listar agents | GET | `/api/v1/agents` | 200 |
| Status do agent | GET | `/api/v1/agents/{id}/status` | 200 |
| Criar task | POST | `/api/v1/tasks` | 201 |
| RAG query | POST | `/api/v1/rag/query` | 200 |
| Health check | GET | `/health` | 200 |
| Métricas | GET | `/metrics` | 200 |

### 8.2 Response envelope

```python
class ApiResponse(BaseModel, Generic[T]):
    status: str = "success"
    data: T | None = None
    meta: dict | None = None
    errors: list[dict] | None = None
    request_id: str | None = None
```

---

## 9. Arquitetura de agentes de IA

### 9.1 Stack de agents

```
                    ┌─────────────────┐
                    │  Optimus (Lead)  │  ← Orquestra, delega
                    │   Agno Agent    │
                    └────────┬────────┘
                             │ classifica intent
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │  Friday  │  │   Fury   │  │  Shuri   │
        │(Developer│  │(Research)│  │(Analyst) │
        └────┬─────┘  └────┬─────┘  └────┬─────┘
             │              │              │
        ┌────▼─────┐  ┌────▼─────┐  ┌────▼─────┐
        │MCP Tools │  │MCP Tools │  │MCP Tools │
        └──────────┘  └──────────┘  └──────────┘
             │              │              │
        ┌────▼──────────────▼──────────────▼────┐
        │        Shared Memory Layer             │
        │  (Redis short-term + Supabase long)    │
        │  + WORKING.md + Daily Notes + RAG     │
        └───────────────────────────────────────┘
```

### 9.2 Base Agent (Agno wrapper)

```python
# agents/base.py
from agno.agent import Agent
from agno.models.google import Gemini
from identity.soul_loader import SoulLoader

class OptimusAgent:
    """Wrapper que conecta Agno agent com SOUL.md + memória + tools."""

    def __init__(self, name: str, soul_path: str, level: str = "specialist",
                 model: str = "gemini-2.5-flash"):
        self.name = name
        self.level = level
        self.soul = SoulLoader.load(soul_path)

        self.agent = Agent(
            name=name,
            model=Gemini(id=model),
            instructions=self.soul,
            show_tool_calls=True,
            markdown=True,
        )

    async def process(self, message: str, context: dict = None) -> str:
        """Processa mensagem com rate limiting e memória."""
        # 1. Check rate limit
        if not await self.rate_limiter.can_call_llm(self.name, self.level):
            return "⏳ Rate limit atingido. Aguarde."

        # 2. Carregar memória de trabalho
        working = await self.memory.load_working(self.name)

        # 3. Executar
        response = self.agent.run(message)

        # 4. Salvar na memória
        await self.memory.update_working(self.name, response)

        return response.content
```

### 9.3 Agent Factory

```python
# agents/factory.py
from agents.base import OptimusAgent

class AgentFactory:
    """Factory para criar agents com configuração padrão."""

    _registry: dict[str, OptimusAgent] = {}

    @classmethod
    def create(cls, name: str, role: str, soul_path: str,
               level: str = "specialist", model: str = "gemini-2.5-flash",
               tools: list = None) -> OptimusAgent:
        agent = OptimusAgent(
            name=name, soul_path=soul_path, level=level, model=model,
        )
        if tools:
            agent.agent.tools = tools
        cls._registry[name] = agent
        return agent

    @classmethod
    def get(cls, name: str) -> OptimusAgent | None:
        return cls._registry.get(name)
```

### 9.4 SOUL.md Pattern

Cada agent tem um SOUL.md em `workspace/souls/`:

```markdown
# SOUL.md — Friday

**Nome:** Friday
**Papel:** Developer Agent
**Nível:** Specialist
**Modelo:** Gemini 2.5 Flash

## Personalidade
Pragmático, focado em entregas. Código limpo, testes sempre.
Comunica de forma técnica e direta.

## O Que Você Faz
- Escrever e debugar código Python
- Criar migrations SQL
- Configurar Docker e CI/CD
- Code review com sugestões construtivas

## O Que Você NÃO Faz
- Decisões de produto (delegar para Shuri)
- Pesquisa acadêmica (delegar para Fury)
- Textos de marketing (delegar para Loki)

## Formato de Resposta
- Sempre incluir código com syntax highlighting
- Explicar o "porquê" de cada decisão
- Avisar se confidence < 70%
```

### 9.5 Memory System

| Camada | Storage | TTL | Sincronização |
|--------|---------|-----|---------------|
| **Session** | Redis | 24h | Automática |
| **Working** | WORKING.md + Supabase | Persistente | Bi-direcional |
| **Daily** | `daily/YYYY-MM-DD.md` | Persistente | Write no final do dia |
| **Long-term** | MEMORY.md + PGvector | Persistente | RAG indexado |

### 9.6 Tree-of-Thought Engine

```python
# engine/tot_engine.py
class ToTEngine:
    """Gera 3 hipóteses com perspectivas diferentes, avalia e sintetiza."""

    STRATEGIES = {
        "conservative": "Análise cautelosa focada em riscos e precedentes",
        "creative": "Abordagem inovadora e soluções não-convencionais",
        "analytical": "Análise quantitativa com dados e métricas",
    }

    async def think(self, query: str, context: str = "") -> dict:
        # 1. Gerar 3 hipóteses paralelas
        hypotheses = await asyncio.gather(*[
            self._generate_hypothesis(query, strategy, context)
            for strategy in self.STRATEGIES.values()
        ])

        # 2. Meta-avaliação (scoring 0-10 em 4 critérios)
        scores = await self._evaluate(hypotheses)

        # 3. Síntese das melhores perspectivas
        synthesis = await self._synthesize(hypotheses, scores)

        return {"hypotheses": hypotheses, "scores": scores, "synthesis": synthesis}
```

---

## 10. RAG — Retrieval-Augmented Generation

### 10.1 Pipeline

```
Documento → Chunking (semântico) → Embedding (Gemini 004) → Store (PGvector)
Query → Embedding → Busca vetorial (cosine > 0.7) → Re-rank → Contexto + LLM
```

### 10.2 Configuração

| Config | Valor | Motivo |
|--------|-------|--------|
| Embedding model | Gemini Text Embedding 004 | Performance + custo |
| Dimensões | 768 | Suficiente para recall |
| Chunk size | 512-1000 tokens | Semântico por parágrafos |
| Overlap | 50 tokens | Manter contexto |
| Top K | 5 | Balancear relevância vs tokens |
| Threshold | 0.7 | Filtrar ruído |
| Índice | IVFFlat (<100K) / HNSW (>100K) | Performance |

---

## 11. Observabilidade

### 11.1 Structured Logging (JSON)

Todo log é JSON com campos obrigatórios:

```python
{
    "timestamp": "2026-02-13T23:00:00Z",
    "level": "INFO",
    "message": "Task assigned",
    "service": "ai-svc",
    "agent": "optimus",
    "correlation_id": "uuid",
    "tokens_used": 150,
    "model": "gemini-2.5-flash",
    "duration_ms": 340
}
```

### 11.2 Métricas Prometheus

```python
AI_TOKENS_USED = Counter("ai_tokens_total", "Tokens consumed", ["agent", "model", "type"])
AI_LATENCY = Histogram("ai_response_seconds", "Agent response time", ["agent"])
AGENT_WAKEUPS = Counter("agent_wakeups_total", "Agent activations", ["agent", "trigger"])
TASKS_CREATED = Counter("tasks_total", "Tasks created", ["status"])
RAG_SEARCHES = Counter("rag_searches_total", "RAG searches", ["source"])
RATE_LIMIT_HITS = Counter("rate_limit_hits_total", "Rate limit blocks", ["agent"])
```

### 11.3 Stack de monitoring

```yaml
# Prometheus (métricas) + Grafana (dashboards) + Loki (logs)
# Ver infra/monitoring/ para configs completos.
```

---

## 12. CI/CD e qualidade de código

### 12.1 GitHub Actions

```yaml
# .github/workflows/ci.yml
name: CI
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install ruff
      - run: ruff check services/ai-svc/
      - run: ruff format --check services/ai-svc/

  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env: { POSTGRES_USER: test, POSTGRES_PASSWORD: test, POSTGRES_DB: test_db }
        ports: ["5432:5432"]
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r services/ai-svc/requirements.txt
      - run: pytest services/ai-svc/tests/ -v --cov
```

### 12.2 Pre-commit hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: check-yaml
      - id: detect-private-key
```

### 12.3 Ruff config

```toml
# pyproject.toml
[tool.ruff]
target-version = "py312"
line-length = 120

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "C4", "UP", "SIM"]
ignore = ["E501", "B008"]  # B008 = Depends()

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

---

## 13. Segurança

### 13.1 Checklist

| Item | Implementação |
|------|---------------|
| Secrets em env vars | Coolify secrets, nunca no código |
| Rate limiting | Por agent (Redis) + por IP (Traefik) |
| Input validation | Pydantic em todo input |
| SQL injection | SQLAlchemy ORM ou parameterized queries |
| Agent sandboxing | Docker sandbox por nível (intern = isolado) |
| Token budget | `max_tokens` + daily budget por agent |
| Logs sanitizados | Nunca logar tokens, API keys, PII |
| HTTPS | TLS obrigatório + HSTS |
| Backup | Diário automático do Supabase |
| Dependency audit | `pip-audit` no CI |

### 13.2 Dockerfile seguro

```dockerfile
FROM python:3.12-slim AS base
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ app/
RUN adduser --disabled-password --gecos "" appuser
USER appuser
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8001/health').raise_for_status()"
EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "4"]
```

---

## 14. Infraestrutura — Hetzner + Coolify

### 14.1 Sizing

| Server | Tipo | RAM | Uso | Custo |
|--------|------|-----|-----|-------|
| Produção | CX41 | 16 GB | Todos os containers | ~€15/mês |
| Staging | CX21 | 4 GB | Testes | ~€5/mês |
| Backup | BX11 | 1 TB | Backups Supabase | ~€4/mês |

### 14.2 Docker Compose (Dev)

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: dev
      POSTGRES_PASSWORD: dev
      POSTGRES_DB: optimus_dev
    ports: ["5432:5432"]
    volumes: [pg-data:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
    ports: ["6379:6379"]

  ai-svc:
    build: { context: services/ai-svc }
    ports: ["8001:8001"]
    env_file: .env.dev
    volumes: [./services/ai-svc/app:/app/app]
    command: uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
    depends_on: [postgres, redis]

volumes:
  pg-data:
```

---

## 15. Testes

### 15.1 Pirâmide

```
      ┌────────┐
      │  E2E   │  ← 5-10: fluxos críticos (chat → task → response)
      ├────────┤
      │Integra-│  ← 20-50: endpoints + DB real
      │  ção   │
      ├────────┤
      │Unitá-  │  ← 100+: ToT engine, memory, rate limiter
      │  rios  │
      └────────┘
```

### 15.2 Testes de agents (mock LLM)

```python
@pytest.mark.asyncio
async def test_tot_engine_generates_3_hypotheses(mock_llm):
    engine = ToTEngine(llm=mock_llm)
    result = await engine.think("Como otimizar custo de tokens?")
    assert len(result["hypotheses"]) == 3
    assert all(h["strategy"] in ToTEngine.STRATEGIES for h in result["hypotheses"])

@pytest.mark.asyncio
async def test_rate_limiter_blocks_after_limit(redis):
    limiter = AgentRateLimiter(redis)
    for _ in range(5):
        assert await limiter.can_call_llm("friday", "specialist")
    assert not await limiter.can_call_llm("friday", "specialist")  # 6th call blocked
```

### 15.3 Regras

| Regra | Detalhe |
|-------|---------|
| Nomear com `test_` + ação | `test_agent_routes_to_correct_specialist` |
| Mocks para LLM calls | Nunca chamar LLM real em testes |
| DB de teste isolado | Cada teste em transação com rollback |
| CI bloqueia merge sem testes | Cobertura mínima: 60% |

---

## 16. Padrões de código Python

### 16.1 Resumo

- **Python:** 3.12+, type hints modernos (`dict` não `Dict`)
- **Formatter:** Ruff (120 chars)
- **Async por padrão:** Todos endpoints, DB, Redis, LLM
- **Config:** `pydantic_settings.BaseSettings` com `.env`

### 16.2 Type hints obrigatórios

```python
# ✅ BOM
async def process_task(task_id: str, agent: OptimusAgent) -> AgentResponse:
    ...

# ❌ RUIM
async def process_task(task_id, agent):
    ...
```

### 16.3 Imports

```python
# Ordem: stdlib → third-party → local
import asyncio
from datetime import datetime, timezone

from agno.agent import Agent
from fastapi import Depends

from app.agents.base import OptimusAgent
from app.shared.config import settings
```

---

## 17. Convenções de projeto

### 17.1 Git

| Convenção | Exemplo |
|-----------|---------|
| Branch naming | `feature/add-fury-agent`, `fix/rate-limit-429` |
| Commits | Conventional: `feat(agents): add Fury researcher agent` |
| Merge strategy | Squash merge para features |
| Tags | Semantic: `v1.0.0` |

### 17.2 Naming

| Item | Convenção | Exemplo |
|------|-----------|---------|
| Arquivos Python | `snake_case.py` | `tot_engine.py` |
| Classes | `PascalCase` | `OptimusAgent`, `ToTEngine` |
| Funções | `snake_case` | `process_task()` |
| Constantes | `UPPER_SNAKE_CASE` | `RATE_LIMITS` |
| Env vars | `UPPER_SNAKE_CASE` | `SUPABASE_URL` |
| Tabelas DB | `snake_case` plural | `agents`, `tasks` |
| Endpoints | `kebab-case` | `/api/v1/agent-status` |
| Docker images | `kebab-case` | `ai-svc`, `channel-svc` |
| SOUL.md | Agent name lowercase | `souls/friday.md` |

### 17.3 ADR (Architecture Decision Records)

```markdown
# ADR-001: Agno + ADK como framework de agents

## Status: Aceito

## Contexto
Precisamos de um framework para multi-agent orchestration com performance, learning e RAG.

## Decisão
Agno para agents core (2μs, learning, RAG nativo). Google ADK para orchestration (A2A, MCP, Debug UI).

## Consequências
- (+) Performance superior (2μs vs 10s CrewAI)
- (+) RAG nativo sem implementação manual
- (-) Dois frameworks para manter
- (-) Documentação do ADK ainda evolving
```

---

## 18. Checklist de novo agent

Ao criar um novo agent para qualquer setor:

### Identidade
- [ ] Criar `workspace/souls/{name}.md` — SOUL.md com personalidade
- [ ] Definir nível: `intern` | `specialist` | `lead`
- [ ] Definir modelo LLM (Flash para rotina, Pro para complexo)

### Código
- [ ] Criar `services/ai-svc/app/agents/{name}.py`
- [ ] Usar `AgentFactory.create()` — não instanciar Agent diretamente
- [ ] Registrar no orchestrator (`orchestrator.register_agent(name, agent)`)
- [ ] Definir MCP tools que o agent pode usar

### MCP (se conecta a API externa)
- [ ] Criar MCP Server para a API (`@mcp_server.tool()`)
- [ ] Documentar tools em TOOLS.md
- [ ] Rate limiter configurado para a API externa

### Database
- [ ] Registro na tabela `agents` com `INSERT`
- [ ] Verificar se precisa nova migration

### Testes
- [ ] `test_{name}_processes_message()` — happy path com mock LLM
- [ ] `test_{name}_rate_limited()` — verifica rate limiter
- [ ] `test_{name}_uses_correct_tools()` — verifica skill selection

### Observabilidade
- [ ] Métricas Prometheus (`AI_TOKENS_USED`, `AI_LATENCY` com label do agent)
- [ ] Logs com `agent` field no JSON
- [ ] Daily standup inclui o novo agent

---

## 19. Anti-patterns a evitar

### 19.1 Agents/IA

| Anti-pattern | Consequência | Fazer |
|--------------|-------------|-------|
| Heartbeat 15min chamando LLM | 429 + custo alto | Event-driven + query Supabase direto |
| Sem rate limiter por agent | Custo descontrolado, API bloqueada | `AgentRateLimiter` com Redis |
| SQL gerado por LLM direto no DB | SQL injection | Skills com queries parametrizadas |
| Sem token budget diário | Fatura surpresa | `max_tokens` + budget Redis counter |
| Embedding de documento inteiro | Baixo recall, alto custo | Chunking semântico (512-1000 tokens) |
| RAG sem threshold | Retorna lixo | Threshold 0.7 + "não encontrei" |
| Prompt hardcoded no código | Impossível iterar | SOUL.md + prompt files versionados |
| Agent sem timeout | Request infinito | 30-60s timeout por agent |
| Logar mensagens completas | Privacidade + storage | Preview (100 chars) + length |

### 19.2 Arquitetura

| Anti-pattern | Consequência | Fazer |
|--------------|-------------|-------|
| Microserviço prematuro | Complexidade sem necessidade | Começar modular em 1 serviço; extrair quando doer |
| Polling para notificações | Custo de CPU + latência | Supabase Real-time (push) |
| Sem circuit breaker | 1 serviço fora derruba todos | CircuitBreaker + fallback |
| Deploy manual | Inconsistente | CI/CD com Coolify |
| Sem health check | Não sabe se está saudável | `/health` + Docker HEALTHCHECK |
| `datetime.utcnow()` | Deprecado 3.12+ | `datetime.now(timezone.utc)` |
| `print()` para logs | Sem estrutura | `logger.info()` com JSONFormatter |
| Código > 100 linhas/função | Impossível testar | Extrair em funções menores |
| `.env` no git | Secrets expostos | `.env.example` + Coolify secrets |

---

> [!IMPORTANT]
> **Este guia é um documento vivo.** Atualize-o conforme o projeto evolui. Toda decisão arquitetural significativa deve gerar um ADR em `.docs/ADR/`.
>
> **Referência completa:** Para detalhes adicionais sobre qualquer seção (Alembic async setup, Prometheus config, Sentry integration, etc.), consulte o [ENGINEERING-GUIDE.md](file:///d:/Project/AgentCrew/.docs/ENGINEERING-GUIDE.md) template genérico (3330 linhas).
