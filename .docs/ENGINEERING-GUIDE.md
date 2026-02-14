# Guia de Engenharia de Software — Template Startup

Documento de referência para agentes de IA e desenvolvedores. Define arquitetura, padrões, convenções e diretrizes para projetos que nascem com microserviços, agentes de IA, RAG e infraestrutura production-ready.

**Stack principal:** Python (FastAPI) · PostgreSQL (pgvector) · Redis · Docker · Coolify · Hetzner
**Auth:** OAuth2/OIDC externo (Keycloak, Auth0, Supabase Auth)
**IA:** Multi-agent, RAG, embeddings, tool calling, memory

---

## Índice

1. [Princípios fundamentais](#1-princípios-fundamentais)
2. [Estrutura do repositório](#2-estrutura-do-repositório)
3. [Arquitetura de microserviços](#3-arquitetura-de-microserviços)
4. [Comunicação entre serviços](#4-comunicação-entre-serviços)
5. [Banco de dados e migrações](#5-banco-de-dados-e-migrações)
6. [Redis — cache, filas e pub/sub](#6-redis--cache-filas-e-pubsub)
7. [Autenticação e autorização (OAuth2/OIDC)](#7-autenticação-e-autorização-oauth2oidc)
8. [Design de API](#8-design-de-api)
9. [Arquitetura de agentes de IA](#9-arquitetura-de-agentes-de-ia)
10. [RAG — Retrieval-Augmented Generation](#10-rag--retrieval-augmented-generation)
11. [Embeddings e busca vetorial](#11-embeddings-e-busca-vetorial)
12. [Observabilidade (logs, métricas, traces)](#12-observabilidade-logs-métricas-traces)
13. [CI/CD e qualidade de código](#13-cicd-e-qualidade-de-código)
14. [Segurança](#14-segurança)
15. [Infraestrutura — Hetzner + Coolify](#15-infraestrutura--hetzner--coolify)
16. [Testes](#16-testes)
17. [Padrões de código Python/FastAPI](#17-padrões-de-código-pythonfastapi)
18. [Convenções de projeto](#18-convenções-de-projeto)
19. [Checklist de novo serviço](#19-checklist-de-novo-serviço)
20. [Anti-patterns a evitar](#20-anti-patterns-a-evitar)

---

## 1. Princípios fundamentais

### 1.1 Filosofia

- **Born cloud-native:** Cada componente roda em container desde o dia 1.
- **API-first:** Toda funcionalidade é exposta via API REST ou gRPC antes de ter UI.
- **12-Factor App:** Configuração por env vars, processos stateless, logs como streams, dev/prod parity.
- **Domain-Driven Design (DDD) pragmático:** Bounded contexts definem os limites dos serviços; não burocratizar com camadas desnecessárias.
- **Fail fast, recover gracefully:** Circuit breakers, retries com backoff, health checks.
- **Observability from day 1:** Structured logging, correlation IDs, métricas e distributed tracing desde o primeiro commit.

### 1.2 Regras inegociáveis

| Regra | Motivo |
|-------|--------|
| Zero secrets no código | Usar env vars ou secret manager (Coolify secrets, Vault) |
| Toda mudança de schema via Alembic | Nunca `Base.metadata.create_all()` em produção |
| Testes antes de merge | CI bloqueia merge sem testes passando |
| Correlation ID em todo request | Rastreabilidade ponta a ponta |
| Sem dependência circular entre serviços | Se A depende de B e B depende de A, extrair serviço C |
| Backwards-compatible API changes | Nunca quebrar contratos sem versionamento |
| Imagens Docker com tag semântica | Nunca `latest` em produção |

### 1.3 Tomada de decisão

Ao escolher entre abordagens:

1. **Simplicidade > Elegância.** Código simples que funciona vence arquitetura perfeita que não entrega.
2. **Composição > Herança.** Preferir injeção de dependência e composição de funções.
3. **Explícito > Implícito.** Configuração explícita, imports explícitos, erros explícitos.
4. **Convenção > Configuração.** Seguir as convenções deste guia; só desviar com justificativa documentada.

---

## 2. Estrutura do repositório

### 2.1 Monorepo com serviços isolados

```
project-root/
├── services/
│   ├── core-api/              # Serviço principal (FastAPI)
│   │   ├── app/
│   │   │   ├── modules/       # Bounded contexts
│   │   │   │   ├── auth/      # router, service, schemas, dependencies
│   │   │   │   ├── users/
│   │   │   │   ├── billing/
│   │   │   │   └── ...
│   │   │   ├── shared/        # Código compartilhado DENTRO do serviço
│   │   │   │   ├── database.py
│   │   │   │   ├── config.py
│   │   │   │   ├── security.py
│   │   │   │   ├── redis.py
│   │   │   │   ├── middleware/
│   │   │   │   └── utils/
│   │   │   └── main.py        # ~50 linhas: app + middleware + register_routers
│   │   ├── alembic/
│   │   │   ├── versions/
│   │   │   └── env.py
│   │   ├── tests/
│   │   │   ├── conftest.py
│   │   │   ├── test_health.py
│   │   │   └── ...
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── pyproject.toml
│   │   └── alembic.ini
│   │
│   ├── ai-svc/                # Serviço de IA/Agentes
│   │   ├── app/
│   │   │   ├── agents/        # Definição de agentes
│   │   │   ├── brain/         # Orquestração, memória, prompts
│   │   │   ├── rag/           # Pipeline RAG
│   │   │   ├── embeddings/    # Geração e busca vetorial
│   │   │   ├── skills/        # Tool definitions
│   │   │   ├── shared/
│   │   │   └── main.py
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   ├── market-svc/            # Exemplo: serviço de dados de mercado
│   │   └── ...
│   │
│   └── gateway/               # API Gateway (Traefik config ou Nginx)
│       ├── traefik.yml
│       ├── dynamic/
│       └── Dockerfile
│
├── libs/                      # Bibliotecas compartilhadas entre serviços
│   ├── shared-schemas/        # Pydantic models compartilhados
│   │   ├── events.py          # Schemas de eventos (Redis Streams)
│   │   ├── auth.py            # Token payload, user context
│   │   └── common.py          # Pagination, error responses
│   ├── shared-utils/          # Utilidades comuns
│   │   ├── logging.py         # JSONFormatter, correlation
│   │   ├── redis_client.py
│   │   └── http_client.py     # Client com retry, circuit breaker
│   └── pyproject.toml
│
├── infra/
│   ├── docker-compose.yml         # Dev local
│   ├── docker-compose.prod.yml    # Produção
│   ├── coolify/                   # Configs específicas Coolify
│   ├── monitoring/
│   │   ├── prometheus.yml
│   │   ├── grafana/
│   │   │   └── dashboards/
│   │   └── loki-config.yml
│   └── scripts/
│       ├── backup-db.sh
│       ├── restore-db.sh
│       └── seed-dev.sh
│
├── frontend/                  # SPA (React/Next.js/Vue)
├── mobile/                    # App mobile (React Native/Flutter)
│
├── .github/
│   └── workflows/
│       ├── ci.yml             # Lint + test + build
│       ├── deploy-staging.yml
│       └── deploy-prod.yml
│
├── .docs/                     # Documentação do projeto
│   ├── ROADMAP.md
│   ├── ADR/                   # Architecture Decision Records
│   │   ├── 001-monorepo.md
│   │   ├── 002-auth-oidc.md
│   │   └── ...
│   └── runbooks/              # Procedimentos operacionais
│
├── .pre-commit-config.yaml
├── .gitignore
└── README.md
```

### 2.2 Regras de organização

- **Cada serviço é independente:** tem seu próprio `Dockerfile`, `requirements.txt`, `alembic/`, `tests/`.
- **`libs/` é versionado junto** mas instalado como dependência local (`pip install -e ../libs/shared-schemas`).
- **`infra/` contém tudo de infra:** docker-compose, monitoring, scripts operacionais.
- **`.docs/` para documentação viva:** ROADMAP, ADRs (Architecture Decision Records), runbooks.
- **Nunca commitar:** `.env`, `*.db`, `__pycache__/`, `node_modules/`, `.venv/`.

### 2.3 Padrão de módulo (bounded context)

Cada módulo dentro de um serviço segue:

```
modules/users/
├── __init__.py
├── router.py          # Endpoints FastAPI (APIRouter)
├── service.py         # Lógica de negócio (puro Python, testável)
├── repository.py      # Acesso a dados (SQLAlchemy queries)
├── models.py          # SQLAlchemy ORM models
├── schemas.py         # Pydantic request/response models
├── dependencies.py    # FastAPI Depends (auth, permissions)
├── events.py          # Eventos emitidos/consumidos por este módulo
└── exceptions.py      # Exceções de domínio
```

**Regras de dependência dentro do módulo:**

```
router → service → repository → models
  ↓         ↓
schemas  dependencies
```

- `router.py` só importa `service`, `schemas`, `dependencies`.
- `service.py` recebe `repository` por injeção (Depends ou construtor).
- `repository.py` só importa `models` e retorna objetos de domínio ou dicts.
- `models.py` não importa nada do módulo (só SQLAlchemy e shared/database).
- **Nunca** importar `router` de dentro de `service` ou `repository`.

---

## 3. Arquitetura de microserviços

### 3.1 Serviços obrigatórios no dia 1

| Serviço | Responsabilidade | Porta dev | DB schema |
|---------|-----------------|-----------|-----------|
| `gateway` | Roteamento, TLS, rate limiting | 80/443 | — |
| `core-api` | Domínio principal, CRUD, regras de negócio | 8000 | `public` |
| `ai-svc` | Agentes, RAG, embeddings, chat | 8001 | `ai` |

### 3.2 Serviços adicionais (extrair quando necessário)

| Serviço | Trigger para extrair | Porta dev |
|---------|---------------------|-----------|
| `auth-svc` | Quando autenticação ficou complexa demais para o OIDC provider | 8002 |
| `notification-svc` | Quando tem email + push + SMS + webhook | 8003 |
| `worker-svc` | Quando tem jobs assíncronos pesados (relatórios, imports) | 8004 |
| `market-svc` | Quando consome APIs externas com cache próprio | 8005 |

### 3.3 Diagrama de comunicação

```
            Internet
               │
          ┌────▼────┐
          │ Gateway  │  (Traefik ou Nginx)
          │ :80/443  │
          └────┬─────┘
               │ HTTP/HTTPS
       ┌───────┼───────┐
       ▼       ▼       ▼
  ┌────────┐ ┌──────┐ ┌──────────┐
  │core-api│ │ai-svc│ │market-svc│
  │ :8000  │ │:8001 │ │  :8005   │
  └───┬────┘ └──┬───┘ └────┬─────┘
      │         │          │
      │    ┌────▼────┐     │
      │    │ Redis   │◄────┘
      │    │ Streams │
      │    │ + Cache │
      │    └─────────┘
      │
  ┌───▼──────────────────┐
  │  PostgreSQL           │
  │  schemas: public,     │
  │  ai, market, ...      │
  │  + pgvector extension │
  └───────────────────────┘
```

### 3.4 Regras de comunicação

| Tipo | Quando usar | Implementação |
|------|-------------|---------------|
| **HTTP síncrono** | Request-response simples, CRUD | `httpx.AsyncClient` com retry |
| **Redis Streams** | Eventos assíncronos, fire-and-forget | `XADD` / `XREADGROUP` com consumer groups |
| **Redis Pub/Sub** | Broadcast (invalidação de cache) | `PUBLISH` / `SUBSCRIBE` |
| **Chamada interna** | Serviço-a-serviço dentro do cluster | Header `X-Internal-Key` + `X-Request-ID` |

### 3.5 Contrato entre serviços

Schemas Pydantic em `libs/shared-schemas/` definem o contrato:

```python
# libs/shared-schemas/events.py
from pydantic import BaseModel
from datetime import datetime

class BaseEvent(BaseModel):
    event_id: str           # UUID
    event_type: str         # "user.created", "order.completed"
    timestamp: datetime
    correlation_id: str     # X-Request-ID propagado
    source_service: str     # "core-api", "ai-svc"
    payload: dict

class UserCreatedEvent(BaseEvent):
    event_type: str = "user.created"
    payload: dict  # {"user_id": int, "email": str, "plan": str}
```

---

## 4. Comunicação entre serviços

### 4.1 HTTP Client padronizado

Todo serviço que chama outro usa o client de `libs/shared-utils/`:

```python
# libs/shared-utils/http_client.py
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from contextvars import copy_context

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
            "Content-Type": "application/json",
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.5, max=5))
    async def get(self, path: str, **kwargs) -> httpx.Response:
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(10.0, connect=5.0),
        ) as client:
            response = await client.get(path, headers=self._headers(), **kwargs)
            response.raise_for_status()
            return response

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.5, max=5))
    async def post(self, path: str, **kwargs) -> httpx.Response:
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(30.0, connect=5.0),
        ) as client:
            response = await client.post(path, headers=self._headers(), **kwargs)
            response.raise_for_status()
            return response
```

### 4.2 Redis Streams — eventos assíncronos

```python
# Produtor (core-api)
import redis.asyncio as aioredis
import json

async def publish_event(redis: aioredis.Redis, event: BaseEvent):
    await redis.xadd(
        f"events:{event.event_type}",
        {"data": event.model_dump_json()},
        maxlen=10000,  # Limitar tamanho do stream
    )

# Consumidor (ai-svc)
async def consume_events(redis: aioredis.Redis, stream: str, group: str, consumer: str):
    # Criar consumer group se não existir
    try:
        await redis.xgroup_create(stream, group, id="0", mkstream=True)
    except aioredis.ResponseError:
        pass  # Grupo já existe

    while True:
        messages = await redis.xreadgroup(
            group, consumer, {stream: ">"}, count=10, block=5000
        )
        for stream_name, entries in messages:
            for msg_id, data in entries:
                event = json.loads(data[b"data"])
                await process_event(event)
                await redis.xack(stream, group, msg_id)
```

### 4.3 Circuit Breaker

```python
# libs/shared-utils/circuit_breaker.py
import time
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"        # Normal — requests passam
    OPEN = "open"            # Falhou demais — rejeita requests
    HALF_OPEN = "half_open"  # Testando — permite 1 request

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.last_failure_time = 0

    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        return True  # HALF_OPEN permite 1 tentativa

    def record_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
```

---

## 5. Banco de dados e migrações

### 5.1 PostgreSQL com pgvector

**Configuração base:**

```python
# shared/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from shared.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.DEBUG,
)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

### 5.2 Convenções de models

```python
# Modelo base com campos comuns
from sqlalchemy import Column, Integer, DateTime, func
from shared.database import Base

class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class BaseModel(Base, TimestampMixin):
    __abstract__ = True
    id = Column(Integer, primary_key=True, autoincrement=True)
```

**Regras de models:**

| Regra | Exemplo |
|-------|---------|
| Tabelas em `snake_case` plural | `users`, `order_items` |
| Colunas em `snake_case` | `created_at`, `user_id` |
| Foreign keys explícitas | `Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))` |
| Índices para queries frequentes | `Index("ix_users_email", "email", unique=True)` |
| Soft delete quando necessário | `deleted_at = Column(DateTime, nullable=True)` |
| Sempre `timezone=True` em DateTime | Armazenar em UTC |
| Enum como `String` ou `PostgreSQL ENUM` | Preferir `String` para flexibilidade |

### 5.3 Alembic — migrações

**Setup:**

```ini
# alembic.ini
[alembic]
script_location = alembic
sqlalchemy.url = driver://user:pass@localhost/dbname  # Override por env
```

```python
# alembic/env.py — async
from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine
from shared.config import settings
from shared.database import Base

# Importar TODOS os models para que Alembic os detecte
from modules.users.models import *
from modules.billing.models import *

target_metadata = Base.metadata

def run_migrations_online():
    connectable = create_async_engine(settings.DATABASE_URL)
    # ... (config async padrão do Alembic)
```

**Regras de migrações:**

1. **Nunca editar migrações já aplicadas em produção.**
2. **Uma migração por feature/PR.**
3. **Nomes descritivos:** `2026_02_07_add_user_preferences_table.py`.
4. **Sempre ter `downgrade()`** funcional.
5. **Testar migração ida e volta** antes de merge: `alembic upgrade head && alembic downgrade -1 && alembic upgrade head`.
6. **Dados sensíveis:** Nunca colocar seeds com dados reais nas migrações.
7. **Entrypoint de produção:** `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000`.

### 5.4 Schemas PostgreSQL por serviço

```sql
-- Isolamento por schema (Fase microserviços)
CREATE SCHEMA IF NOT EXISTS ai;
CREATE SCHEMA IF NOT EXISTS market;
CREATE SCHEMA IF NOT EXISTS notifications;

-- pgvector (necessário para RAG)
CREATE EXTENSION IF NOT EXISTS vector;

-- Índices vetoriais
CREATE INDEX ON ai.embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

Cada serviço configura seu `search_path`:

```python
# ai-svc/shared/database.py
engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args={"options": "-c search_path=ai,public"},
)
```

---

## 6. Redis — cache, filas e pub/sub

### 6.1 Configuração

```python
# shared/redis.py
import redis.asyncio as aioredis
from shared.config import settings

redis_pool = aioredis.ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=20,
    decode_responses=True,
)

async def get_redis() -> aioredis.Redis:
    return aioredis.Redis(connection_pool=redis_pool)
```

### 6.2 Padrões de uso

| Uso | Key pattern | TTL | Exemplo |
|-----|-------------|-----|---------|
| Cache de query | `cache:{service}:{entity}:{id}` | 5-15 min | `cache:core:user:42` |
| Cache de lista | `cache:{service}:{entity}:list:{hash}` | 2-5 min | `cache:core:products:list:abc123` |
| Session/Token | `session:{user_id}:{token_id}` | TTL do token | `session:42:uuid` |
| Rate limiting | `rate:{ip}:{endpoint}` | 1 min | `rate:1.2.3.4:/api/login` |
| Lock distribuído | `lock:{resource}:{id}` | 30s | `lock:order:789` |
| Eventos (Stream) | `events:{event_type}` | maxlen | `events:user.created` |
| Pub/Sub | `channel:{topic}` | — | `channel:cache_invalidation` |
| Queue (jobs) | `queue:{service}:{job_type}` | — | `queue:worker:report_generation` |

### 6.3 Cache decorator

```python
# shared/utils/cache.py
import json
import functools
from shared.redis import get_redis

def cached(prefix: str, ttl: int = 300):
    """Decorator para cache em Redis."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            redis = await get_redis()
            # Gerar key a partir dos argumentos
            key_parts = [str(a) for a in args[1:]]  # Skip self
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = f"cache:{prefix}:{':'.join(key_parts)}"

            # Tentar cache
            cached_value = await redis.get(cache_key)
            if cached_value:
                return json.loads(cached_value)

            # Executar e cachear
            result = await func(*args, **kwargs)
            await redis.setex(cache_key, ttl, json.dumps(result, default=str))
            return result
        return wrapper
    return decorator
```

### 6.4 Invalidação de cache

```python
# Invalidação por padrão (usar com cuidado — SCAN é O(N))
async def invalidate_cache(redis, pattern: str):
    """Invalida todas as keys que match o pattern."""
    async for key in redis.scan_iter(match=pattern, count=100):
        await redis.delete(key)

# Preferir invalidação explícita:
async def invalidate_user_cache(redis, user_id: int):
    keys = [
        f"cache:core:user:{user_id}",
        f"cache:core:user:{user_id}:profile",
        f"cache:core:user:{user_id}:preferences",
    ]
    if keys:
        await redis.delete(*keys)
```

---

## 7. Autenticação e autorização (OAuth2/OIDC)

### 7.1 Arquitetura com provedor externo

```
┌──────────┐     ┌─────────────┐     ┌──────────┐
│  Client   │────▶│ OIDC Provider│────▶│ core-api │
│ (SPA/App) │◀────│ (Keycloak/   │     │          │
│           │     │  Auth0/      │     │          │
│           │     │  Supabase)   │     │          │
└──────────┘     └─────────────┘     └──────────┘
     │                                      │
     │         Access Token (JWT)           │
     └──────────────────────────────────────┘
```

**Fluxo:**
1. Client redireciona para OIDC provider (Authorization Code + PKCE).
2. Provider autentica e retorna `access_token` + `refresh_token`.
3. Client envia `Authorization: Bearer <access_token>` em cada request.
4. Backend valida JWT (signature, expiry, audience, issuer).
5. Backend extrai claims (`sub`, `email`, `roles`) do token.

### 7.2 Validação de JWT no backend

```python
# shared/security.py
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from shared.config import settings
import httpx

security = HTTPBearer()

# Cache da JWKS (JSON Web Key Set)
_jwks_cache = None
_jwks_cache_time = 0

async def get_jwks():
    """Busca JWKS do provedor OIDC com cache."""
    global _jwks_cache, _jwks_cache_time
    import time
    if _jwks_cache and time.time() - _jwks_cache_time < 3600:  # 1h cache
        return _jwks_cache

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{settings.OIDC_ISSUER}/.well-known/jwks.json")
        _jwks_cache = response.json()
        _jwks_cache_time = time.time()
        return _jwks_cache

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Valida JWT e retorna payload do usuário."""
    token = credentials.credentials
    try:
        jwks = await get_jwks()
        # Decodificar header para pegar kid
        unverified_header = jwt.get_unverified_header(token)
        # Encontrar a key correta
        rsa_key = next(
            (key for key in jwks["keys"] if key["kid"] == unverified_header["kid"]),
            None,
        )
        if not rsa_key:
            raise HTTPException(status_code=401, detail="Key not found")

        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=settings.OIDC_AUDIENCE,
            issuer=settings.OIDC_ISSUER,
        )
        return payload

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {str(e)}",
        )

# Dependency para exigir roles específicas
def require_role(required_role: str):
    async def role_checker(user: dict = Depends(get_current_user)):
        roles = user.get("realm_access", {}).get("roles", [])
        if required_role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return role_checker
```

### 7.3 Propagação entre serviços

```python
# Serviço-a-serviço: propagar token ou usar X-Internal-Key
# Opção 1: Forward do token do usuário (quando ai-svc precisa saber quem é o user)
# Opção 2: X-Internal-Key (quando serviço age em nome próprio)

async def validate_internal_key(request: Request):
    """Valida chamada interna entre serviços."""
    internal_key = request.headers.get("X-Internal-Key")
    if internal_key != settings.INTERNAL_SERVICE_KEY:
        raise HTTPException(status_code=403, detail="Invalid internal key")
    return True
```

### 7.4 Config de env vars para OIDC

```env
# .env
OIDC_ISSUER=https://auth.example.com/realms/myapp
OIDC_AUDIENCE=my-api
OIDC_CLIENT_ID=my-spa
# Para serviço-a-serviço:
INTERNAL_SERVICE_KEY=random-secret-here
```

---

## 8. Design de API

### 8.1 Convenções REST

| Ação | Método | Path | Status |
|------|--------|------|--------|
| Listar | GET | `/api/v1/users` | 200 |
| Detalhe | GET | `/api/v1/users/{id}` | 200 |
| Criar | POST | `/api/v1/users` | 201 |
| Atualizar (full) | PUT | `/api/v1/users/{id}` | 200 |
| Atualizar (parcial) | PATCH | `/api/v1/users/{id}` | 200 |
| Deletar | DELETE | `/api/v1/users/{id}` | 204 |
| Ação customizada | POST | `/api/v1/users/{id}/activate` | 200 |
| Busca | GET | `/api/v1/users/search?q=...` | 200 |

### 8.2 Response envelope padrão

```python
# libs/shared-schemas/common.py
from pydantic import BaseModel
from typing import TypeVar, Generic, Optional, List
from datetime import datetime

T = TypeVar("T")

class PaginationMeta(BaseModel):
    page: int
    per_page: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool

class ApiResponse(BaseModel, Generic[T]):
    status: str = "success"       # "success" | "error"
    data: Optional[T] = None
    meta: Optional[dict] = None   # Pagination, etc.
    errors: Optional[List[dict]] = None
    timestamp: datetime = datetime.utcnow()
    request_id: Optional[str] = None  # Correlation ID

class ApiError(BaseModel):
    status: str = "error"
    code: str                     # "VALIDATION_ERROR", "NOT_FOUND"
    message: str
    details: Optional[List[dict]] = None
    request_id: Optional[str] = None
```

### 8.3 Paginação

```python
# Cursor-based (preferido para datasets grandes)
class CursorPagination(BaseModel):
    cursor: Optional[str] = None  # Base64 encoded ID
    limit: int = 20
    has_more: bool = False
    next_cursor: Optional[str] = None

# Offset-based (para UIs com número de página)
class OffsetPagination(BaseModel):
    page: int = 1
    per_page: int = 20
    total: int
    total_pages: int
```

### 8.4 Versionamento de API

```python
# main.py
from fastapi import FastAPI
from modules.users.router import router as users_router

app = FastAPI(title="Core API", version="1.0.0")

# Versão atual e legada apontam para os mesmos routers
app.include_router(users_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api")  # Sem versão = latest

# Quando v2 for necessário:
# from modules.users.router_v2 import router as users_v2_router
# app.include_router(users_v2_router, prefix="/api/v2")
```

### 8.5 Error handling global

```python
# shared/middleware/error_handler.py
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
import logging

logger = logging.getLogger(__name__)

async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "code": f"HTTP_{exc.status_code}",
            "message": exc.detail,
            "request_id": getattr(request.state, "request_id", None),
        },
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": exc.errors(),
            "request_id": getattr(request.state, "request_id", None),
        },
    )

async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception", extra={"props": {
        "request_id": getattr(request.state, "request_id", None),
        "path": request.url.path,
        "method": request.method,
    }})
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "request_id": getattr(request.state, "request_id", None),
        },
    )

---

## 9. Arquitetura de agentes de IA

### 9.1 Visão geral

O sistema de IA é baseado em **multi-agent orchestration**: um orquestrador central recebe a mensagem do usuário, classifica a intenção e delega para agentes especializados. Cada agente tem tools (skills), acesso a memória e pode chamar outros agentes.

```
                    ┌─────────────────┐
                    │   Orchestrator   │
                    │  (Router Agent)  │
                    └────────┬────────┘
                             │ classifica intenção
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │ Agent A  │  │ Agent B  │  │ Agent C  │
        │(Finance) │  │(Support) │  │(Analysis)│
        └────┬─────┘  └────┬─────┘  └────┬─────┘
             │              │              │
        ┌────▼─────┐  ┌────▼─────┐  ┌────▼─────┐
        │  Tools   │  │  Tools   │  │  Tools   │
        │(skills)  │  │(skills)  │  │(skills)  │
        └──────────┘  └──────────┘  └──────────┘
             │              │              │
        ┌────▼──────────────▼──────────────▼────┐
        │          Shared Memory Layer           │
        │  (Redis short-term + PG long-term)     │
        └───────────────────────────────────────┘
```

### 9.2 Estrutura do ai-svc

```
ai-svc/app/
├── agents/
│   ├── __init__.py
│   ├── base_agent.py          # Classe base para todos os agentes
│   ├── orchestrator.py        # Router/Orchestrator principal
│   ├── finance_agent.py       # Agente especializado exemplo
│   ├── analysis_agent.py
│   └── support_agent.py
│
├── brain/
│   ├── __init__.py
│   ├── llm_client.py          # Abstração sobre LLM (OpenAI, Anthropic, Gemini)
│   ├── prompt_manager.py      # Carrega e renderiza prompts
│   ├── context_builder.py     # Monta contexto para o LLM
│   └── response_parser.py     # Parseia output do LLM (tool calls, texto)
│
├── memory/
│   ├── __init__.py
│   ├── short_term.py          # Redis — contexto da conversa atual
│   ├── long_term.py           # PostgreSQL — histórico persistente
│   ├── episodic.py            # Memória episódica (eventos relevantes)
│   └── working.py             # Memória de trabalho (scratchpad do agente)
│
├── rag/
│   ├── __init__.py
│   ├── pipeline.py            # Pipeline completo de RAG
│   ├── chunker.py             # Estratégias de chunking
│   ├── retriever.py           # Busca vetorial + reranking
│   ├── indexer.py             # Indexação de documentos
│   └── sources/               # Conectores de fontes (files, URLs, APIs)
│       ├── file_source.py
│       ├── web_source.py
│       └── api_source.py
│
├── embeddings/
│   ├── __init__.py
│   ├── generator.py           # Gera embeddings (OpenAI, Sentence-Transformers)
│   ├── store.py               # CRUD vetorial (pgvector)
│   └── search.py              # Busca por similaridade
│
├── skills/                    # Tool definitions para os agentes
│   ├── __init__.py
│   ├── base_skill.py          # Interface base de skill
│   ├── database_skill.py      # Consultar banco do usuário
│   ├── calculation_skill.py   # Cálculos e projeções
│   ├── web_search_skill.py    # Busca na web
│   └── api_skill.py           # Chamar APIs externas
│
├── shared/
│   ├── config.py
│   ├── database.py
│   └── redis.py
│
├── main.py
└── router.py                  # Endpoints: /chat, /agents, /rag
```

### 9.3 Base Agent

```python
# agents/base_agent.py
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class AgentContext(BaseModel):
    user_id: int
    conversation_id: str
    correlation_id: str
    message: str
    history: List[dict] = []
    metadata: dict = {}

class AgentResponse(BaseModel):
    message: str
    tool_calls: List[dict] = []
    confidence: float = 1.0
    agent_name: str
    thinking: Optional[str] = None  # Chain-of-thought (debug only)
    sources: List[dict] = []        # Fontes RAG usadas

class BaseAgent(ABC):
    """Classe base para todos os agentes."""

    def __init__(self, name: str, description: str, llm_client, memory, skills=None):
        self.name = name
        self.description = description
        self.llm = llm_client
        self.memory = memory
        self.skills = skills or []

    @abstractmethod
    async def process(self, context: AgentContext) -> AgentResponse:
        """Processa uma mensagem e retorna resposta."""
        pass

    def get_system_prompt(self) -> str:
        """Retorna o system prompt do agente."""
        skill_descriptions = "\n".join(
            f"- {s.name}: {s.description}" for s in self.skills
        )
        return f"""Você é {self.name}. {self.description}

Ferramentas disponíveis:
{skill_descriptions}

Regras:
- Responda sempre em português brasileiro.
- Seja objetivo e preciso.
- Use ferramentas quando necessário para buscar dados reais.
- Nunca invente dados. Se não sabe, diga que não sabe.
"""

    async def execute_skill(self, skill_name: str, params: dict) -> Any:
        """Executa uma skill pelo nome."""
        skill = next((s for s in self.skills if s.name == skill_name), None)
        if not skill:
            raise ValueError(f"Skill '{skill_name}' not found")
        return await skill.execute(**params)
```

### 9.4 Orchestrator (Router Agent)

```python
# agents/orchestrator.py
from agents.base_agent import BaseAgent, AgentContext, AgentResponse
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class Orchestrator:
    """Roteia mensagens para o agente correto baseado na intenção."""

    def __init__(self, agents: Dict[str, BaseAgent], llm_client):
        self.agents = agents
        self.llm = llm_client

    async def route(self, context: AgentContext) -> AgentResponse:
        # 1. Classificar intenção
        intent = await self._classify_intent(context.message)
        logger.info("Intent classified", extra={"props": {
            "intent": intent["agent"],
            "confidence": intent["confidence"],
            "correlation_id": context.correlation_id,
        }})

        # 2. Selecionar agente
        agent = self.agents.get(intent["agent"])
        if not agent or intent["confidence"] < 0.3:
            agent = self.agents.get("default")

        # 3. Enriquecer contexto com memória
        context.history = await self._load_conversation_history(context)

        # 4. Executar agente
        response = await agent.process(context)

        # 5. Salvar na memória
        await self._save_interaction(context, response)

        return response

    async def _classify_intent(self, message: str) -> dict:
        """Usa LLM para classificar a intenção da mensagem."""
        agent_descriptions = "\n".join(
            f"- {name}: {agent.description}"
            for name, agent in self.agents.items()
        )
        prompt = f"""Classifique a intenção da mensagem do usuário.
Agentes disponíveis:
{agent_descriptions}

Mensagem: "{message}"

Responda em JSON: {{"agent": "nome", "confidence": 0.0-1.0}}"""

        result = await self.llm.generate(prompt, response_format="json")
        return result
```

### 9.5 LLM Client (abstração multi-provider)

```python
# brain/llm_client.py
from abc import ABC, abstractmethod
from typing import Optional, List
from pydantic import BaseModel

class LLMMessage(BaseModel):
    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_call_id: Optional[str] = None

class LLMConfig(BaseModel):
    model: str
    temperature: float = 0.7
    max_tokens: int = 4096
    provider: str = "openai"  # "openai", "anthropic", "google"

class LLMClient:
    """Client unificado para múltiplos provedores de LLM."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._client = self._create_client()

    def _create_client(self):
        if self.config.provider == "openai":
            from openai import AsyncOpenAI
            return AsyncOpenAI()
        elif self.config.provider == "anthropic":
            import anthropic
            return anthropic.AsyncAnthropic()
        elif self.config.provider == "google":
            import google.generativeai as genai
            return genai

    async def generate(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[dict]] = None,
        response_format: Optional[str] = None,
    ) -> dict:
        """Gera resposta do LLM."""
        if self.config.provider == "openai":
            return await self._generate_openai(messages, tools, response_format)
        elif self.config.provider == "anthropic":
            return await self._generate_anthropic(messages, tools)
        # ... outros providers

    async def _generate_openai(self, messages, tools, response_format):
        params = {
            "model": self.config.model,
            "messages": [m.model_dump() for m in messages],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
        if tools:
            params["tools"] = tools
        if response_format == "json":
            params["response_format"] = {"type": "json_object"}

        response = await self._client.chat.completions.create(**params)
        return {
            "content": response.choices[0].message.content,
            "tool_calls": response.choices[0].message.tool_calls or [],
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
            },
        }
```

### 9.6 Skills (Tools)

```python
# skills/base_skill.py
from abc import ABC, abstractmethod
from typing import Any, Dict
from pydantic import BaseModel

class SkillDefinition(BaseModel):
    """Definição da skill para enviar ao LLM como tool."""
    name: str
    description: str
    parameters: dict  # JSON Schema dos parâmetros

class BaseSkill(ABC):
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def get_definition(self) -> SkillDefinition:
        """Retorna a definição da skill em formato OpenAI tool."""
        pass

    @abstractmethod
    async def execute(self, **params) -> Any:
        """Executa a skill com os parâmetros dados."""
        pass

# skills/database_skill.py
class DatabaseQuerySkill(BaseSkill):
    def __init__(self, db_session):
        super().__init__(
            name="query_database",
            description="Consulta dados do banco do usuário (transações, saldos, etc.)"
        )
        self.db = db_session

    def get_definition(self) -> SkillDefinition:
        return SkillDefinition(
            name=self.name,
            description=self.description,
            parameters={
                "type": "object",
                "properties": {
                    "query_type": {
                        "type": "string",
                        "enum": ["transactions", "balance", "categories", "summary"],
                        "description": "Tipo de consulta"
                    },
                    "filters": {
                        "type": "object",
                        "description": "Filtros opcionais (date_from, date_to, category, etc.)"
                    }
                },
                "required": ["query_type"]
            }
        )

    async def execute(self, query_type: str, filters: dict = None) -> Any:
        # Implementar queries seguras (nunca SQL direto do LLM!)
        if query_type == "balance":
            return await self._get_balance(filters)
        elif query_type == "transactions":
            return await self._get_transactions(filters)
        # ...
```

### 9.7 Memory System

```python
# memory/short_term.py (Redis)
import json
from redis.asyncio import Redis

class ShortTermMemory:
    """Memória de curto prazo — conversa atual em Redis."""

    def __init__(self, redis: Redis, max_messages: int = 50):
        self.redis = redis
        self.max_messages = max_messages

    async def add_message(self, conversation_id: str, role: str, content: str):
        key = f"memory:conversation:{conversation_id}"
        message = json.dumps({"role": role, "content": content})
        await self.redis.rpush(key, message)
        await self.redis.ltrim(key, -self.max_messages, -1)
        await self.redis.expire(key, 3600 * 24)  # 24h TTL

    async def get_history(self, conversation_id: str, limit: int = 20) -> list:
        key = f"memory:conversation:{conversation_id}"
        messages = await self.redis.lrange(key, -limit, -1)
        return [json.loads(m) for m in messages]

    async def clear(self, conversation_id: str):
        await self.redis.delete(f"memory:conversation:{conversation_id}")


# memory/long_term.py (PostgreSQL)
from sqlalchemy import select
from shared.database import AsyncSessionLocal

class LongTermMemory:
    """Memória de longo prazo — histórico persistente em PostgreSQL."""

    async def save_interaction(self, user_id: int, conversation_id: str,
                                message: str, response: str, agent: str, metadata: dict):
        async with AsyncSessionLocal() as session:
            interaction = InteractionLog(
                user_id=user_id,
                conversation_id=conversation_id,
                user_message=message[:500],  # Preview para privacidade
                assistant_response=response[:500],
                agent_used=agent,
                metadata_json=metadata,
            )
            session.add(interaction)
            await session.commit()

    async def get_user_patterns(self, user_id: int, limit: int = 100) -> list:
        """Busca padrões de uso do usuário para personalização."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(InteractionLog)
                .where(InteractionLog.user_id == user_id)
                .order_by(InteractionLog.created_at.desc())
                .limit(limit)
            )
            return result.scalars().all()
```

---

## 10. RAG — Retrieval-Augmented Generation

### 10.1 Pipeline RAG completo

```
   Documento                  Query do usuário
      │                              │
      ▼                              ▼
┌───────────┐               ┌───────────────┐
│ Chunking  │               │  Embedding    │
│ (split)   │               │  da query     │
└─────┬─────┘               └───────┬───────┘
      │                              │
      ▼                              ▼
┌───────────┐               ┌───────────────┐
│ Embedding │               │ Busca vetorial│
│ dos chunks│               │ (pgvector)    │
└─────┬─────┘               └───────┬───────┘
      │                              │
      ▼                              ▼
┌───────────┐               ┌───────────────┐
│ Store em  │               │  Re-ranking   │
│ pgvector  │               │  (opcional)   │
└───────────┘               └───────┬───────┘
                                     │
                                     ▼
                            ┌───────────────┐
                            │ Contexto +    │
                            │ Query → LLM   │
                            └───────────────┘
```

### 10.2 Chunking strategies

```python
# rag/chunker.py
from typing import List
from pydantic import BaseModel

class Chunk(BaseModel):
    content: str
    metadata: dict  # source, page, position, etc.
    chunk_index: int
    total_chunks: int

class ChunkingStrategy:
    """Estratégias de chunking para diferentes tipos de conteúdo."""

    @staticmethod
    def fixed_size(text: str, chunk_size: int = 512, overlap: int = 50,
                   metadata: dict = None) -> List[Chunk]:
        """Chunks de tamanho fixo com overlap."""
        chunks = []
        start = 0
        total = (len(text) - overlap) // (chunk_size - overlap) + 1
        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end]
            chunks.append(Chunk(
                content=chunk_text,
                metadata=metadata or {},
                chunk_index=len(chunks),
                total_chunks=total,
            ))
            start += chunk_size - overlap
        return chunks

    @staticmethod
    def semantic(text: str, max_chunk_size: int = 1000,
                 metadata: dict = None) -> List[Chunk]:
        """Chunks por parágrafos/seções semânticas."""
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) > max_chunk_size and current_chunk:
                chunks.append(Chunk(
                    content=current_chunk.strip(),
                    metadata=metadata or {},
                    chunk_index=len(chunks),
                    total_chunks=0,  # Atualizado depois
                ))
                current_chunk = para
            else:
                current_chunk += "\n\n" + para if current_chunk else para

        if current_chunk.strip():
            chunks.append(Chunk(
                content=current_chunk.strip(),
                metadata=metadata or {},
                chunk_index=len(chunks),
                total_chunks=0,
            ))

        for c in chunks:
            c.total_chunks = len(chunks)

        return chunks

    @staticmethod
    def by_heading(text: str, metadata: dict = None) -> List[Chunk]:
        """Chunks por headings (Markdown)."""
        import re
        sections = re.split(r'\n(?=#{1,3}\s)', text)
        return [
            Chunk(
                content=section.strip(),
                metadata={**(metadata or {}), "heading": section.split("\n")[0].strip()},
                chunk_index=i,
                total_chunks=len(sections),
            )
            for i, section in enumerate(sections) if section.strip()
        ]
```

### 10.3 Pipeline completo

```python
# rag/pipeline.py
from rag.chunker import ChunkingStrategy, Chunk
from embeddings.generator import EmbeddingGenerator
from embeddings.store import VectorStore
from embeddings.search import VectorSearch
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

class RAGPipeline:
    """Pipeline completo de Retrieval-Augmented Generation."""

    def __init__(self, embedder: EmbeddingGenerator, store: VectorStore,
                 search: VectorSearch, llm_client):
        self.embedder = embedder
        self.store = store
        self.search = search
        self.llm = llm_client

    # --- INDEXAÇÃO ---
    async def index_document(self, content: str, source: str,
                              metadata: dict = None,
                              strategy: str = "semantic") -> int:
        """Indexa um documento: chunking → embedding → store."""
        # 1. Chunk
        if strategy == "semantic":
            chunks = ChunkingStrategy.semantic(content, metadata=metadata)
        elif strategy == "heading":
            chunks = ChunkingStrategy.by_heading(content, metadata=metadata)
        else:
            chunks = ChunkingStrategy.fixed_size(content, metadata=metadata)

        # 2. Gerar embeddings
        texts = [c.content for c in chunks]
        embeddings = await self.embedder.generate_batch(texts)

        # 3. Armazenar
        stored = 0
        for chunk, embedding in zip(chunks, embeddings):
            await self.store.upsert(
                content=chunk.content,
                embedding=embedding,
                metadata={
                    **chunk.metadata,
                    "source": source,
                    "chunk_index": chunk.chunk_index,
                },
            )
            stored += 1

        logger.info(f"Indexed {stored} chunks from {source}")
        return stored

    # --- RETRIEVAL ---
    async def retrieve(self, query: str, top_k: int = 5,
                       threshold: float = 0.7,
                       filters: dict = None) -> List[dict]:
        """Busca documentos relevantes para a query."""
        # 1. Embedding da query
        query_embedding = await self.embedder.generate(query)

        # 2. Busca vetorial
        results = await self.search.search(
            embedding=query_embedding,
            top_k=top_k,
            threshold=threshold,
            filters=filters,
        )

        return results

    # --- GERAÇÃO COM CONTEXTO ---
    async def generate(self, query: str, user_context: str = "",
                       top_k: int = 5) -> dict:
        """Pipeline completo: retrieve + generate."""
        # 1. Retrieve
        documents = await self.retrieve(query, top_k=top_k)

        # 2. Montar contexto
        context_parts = []
        for doc in documents:
            context_parts.append(
                f"[Fonte: {doc['metadata'].get('source', 'unknown')}]\n{doc['content']}"
            )
        context = "\n---\n".join(context_parts)

        # 3. Gerar resposta
        prompt = f"""Use o contexto abaixo para responder à pergunta do usuário.
Se a informação não estiver no contexto, diga que não encontrou.
Cite as fontes quando possível.

Contexto:
{context}

{f"Contexto do usuário: {user_context}" if user_context else ""}

Pergunta: {query}"""

        response = await self.llm.generate(
            messages=[{"role": "user", "content": prompt}]
        )

        return {
            "answer": response["content"],
            "sources": [
                {"content": d["content"][:200], "source": d["metadata"].get("source"),
                 "similarity": d["similarity"]}
                for d in documents
            ],
            "tokens_used": response.get("usage", {}),
        }
```

---

## 11. Embeddings e busca vetorial

### 11.1 Gerador de embeddings

```python
# embeddings/generator.py
from typing import List
from shared.config import settings

class EmbeddingGenerator:
    """Gera embeddings usando OpenAI ou modelos locais."""

    def __init__(self, model: str = "text-embedding-3-small", dimensions: int = 1536):
        self.model = model
        self.dimensions = dimensions

    async def generate(self, text: str) -> List[float]:
        """Gera embedding para um texto."""
        from openai import AsyncOpenAI
        client = AsyncOpenAI()
        response = await client.embeddings.create(
            model=self.model,
            input=text,
            dimensions=self.dimensions,
        )
        return response.data[0].embedding

    async def generate_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """Gera embeddings em batch."""
        from openai import AsyncOpenAI
        client = AsyncOpenAI()
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = await client.embeddings.create(
                model=self.model,
                input=batch,
                dimensions=self.dimensions,
            )
            all_embeddings.extend([d.embedding for d in response.data])

        return all_embeddings
```

### 11.2 Vector Store (pgvector)

```python
# embeddings/store.py
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, func, text
from pgvector.sqlalchemy import Vector
from shared.database import Base, AsyncSessionLocal
from typing import List, Optional

class EmbeddingRecord(Base):
    __tablename__ = "embeddings"
    __table_args__ = {"schema": "ai"}

    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536), nullable=False)
    metadata_json = Column(JSON, default={})
    source = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class VectorStore:
    async def upsert(self, content: str, embedding: List[float],
                     metadata: dict = None, source: str = None):
        async with AsyncSessionLocal() as session:
            record = EmbeddingRecord(
                content=content,
                embedding=embedding,
                metadata_json=metadata or {},
                source=source,
            )
            session.add(record)
            await session.commit()

    async def delete_by_source(self, source: str):
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("DELETE FROM ai.embeddings WHERE source = :source"),
                {"source": source},
            )
            await session.commit()
```

### 11.3 Busca vetorial

```python
# embeddings/search.py
from sqlalchemy import text
from shared.database import AsyncSessionLocal
from typing import List, Optional

class VectorSearch:
    async def search(self, embedding: List[float], top_k: int = 5,
                     threshold: float = 0.7,
                     filters: dict = None) -> List[dict]:
        """Busca por similaridade coseno no pgvector."""
        async with AsyncSessionLocal() as session:
            # Query com cosine similarity
            filter_clause = ""
            params = {
                "embedding": str(embedding),
                "top_k": top_k,
                "threshold": threshold,
            }

            if filters and filters.get("source"):
                filter_clause = "AND source = :source"
                params["source"] = filters["source"]

            query = text(f"""
                SELECT
                    id,
                    content,
                    metadata_json,
                    source,
                    1 - (embedding <=> :embedding::vector) AS similarity
                FROM ai.embeddings
                WHERE 1 - (embedding <=> :embedding::vector) >= :threshold
                {filter_clause}
                ORDER BY embedding <=> :embedding::vector
                LIMIT :top_k
            """)

            result = await session.execute(query, params)
            rows = result.fetchall()

            return [
                {
                    "id": row.id,
                    "content": row.content,
                    "metadata": row.metadata_json,
                    "source": row.source,
                    "similarity": round(float(row.similarity), 4),
                }
                for row in rows
            ]
```

### 11.4 Índices vetoriais

```sql
-- Para datasets < 100k vetores: IVFFlat (mais rápido de criar)
CREATE INDEX ON ai.embeddings
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

-- Para datasets > 100k vetores: HNSW (melhor recall, mais lento de criar)
CREATE INDEX ON ai.embeddings
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 200);

-- Para buscas filtradas, índice parcial:
CREATE INDEX ON ai.embeddings
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 50)
  WHERE source = 'knowledge_base';
```

---

## 12. Observabilidade (logs, métricas, traces)

### 12.1 Structured Logging

Todo log deve ser JSON estruturado com campos obrigatórios:

```python
# libs/shared-utils/logging.py
import logging
import json
from datetime import datetime, timezone
from contextvars import ContextVar
from typing import Any

# Context var para correlation ID
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")

def get_correlation_id() -> str:
    return correlation_id_var.get()

class JSONFormatter(logging.Formatter):
    def __init__(self, service_name: str = "unknown"):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        log_record: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "service": self.service_name,
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
            "correlation_id": get_correlation_id(),
        }

        if hasattr(record, "props"):
            log_record.update(record.props)

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record, default=str)

def setup_logging(service_name: str, level: str = None):
    import os
    log_level = level or os.getenv("LOG_LEVEL", "INFO")
    logger = logging.getLogger()
    logger.setLevel(log_level)

    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter(service_name))
    logger.addHandler(console_handler)
    return logger
```

### 12.2 Correlation ID Middleware

```python
# shared/middleware/correlation.py
import uuid
from contextvars import copy_context
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from libs.shared_utils.logging import correlation_id_var

class CorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Propagar ID existente ou gerar novo
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        correlation_id_var.set(request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

### 12.3 Request Log Middleware

```python
# shared/middleware/request_log.py
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("http.request")

class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        # Uma linha por request
        log_data = {
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "user_id": getattr(request.state, "user_id", None),
        }

        level = logging.INFO
        if response.status_code >= 500:
            level = logging.ERROR
        elif response.status_code >= 400:
            level = logging.WARNING

        logger.log(level, f"{request.method} {request.url.path} {response.status_code}",
                   extra={"props": log_data})

        return response
```

### 12.4 Métricas (Prometheus)

```python
# shared/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import Response

# Métricas padrão
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)
ACTIVE_REQUESTS = Gauge(
    "http_requests_active",
    "Active HTTP requests",
)
DB_CONNECTIONS = Gauge(
    "db_connections_active",
    "Active database connections",
)
AI_TOKENS_USED = Counter(
    "ai_tokens_total",
    "Total AI tokens consumed",
    ["model", "type"],  # type: prompt, completion
)
RAG_SEARCHES = Counter(
    "rag_searches_total",
    "Total RAG searches performed",
    ["source"],
)

async def metrics_endpoint():
    return Response(content=generate_latest(), media_type="text/plain")
```

### 12.5 Stack de monitoring (docker-compose)

```yaml
# infra/docker-compose.monitoring.yml
services:
  prometheus:
    image: prom/prometheus:v2.50.0
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
    restart: unless-stopped

  grafana:
    image: grafana/grafana:10.3.0
    volumes:
      - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards
      - grafana-data:/var/lib/grafana
    ports:
      - "3001:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD:-admin}
    restart: unless-stopped

  loki:
    image: grafana/loki:2.9.0
    volumes:
      - ./monitoring/loki-config.yml:/etc/loki/local-config.yaml
      - loki-data:/loki
    ports:
      - "3100:3100"
    restart: unless-stopped

  promtail:
    image: grafana/promtail:2.9.0
    volumes:
      - /var/log:/var/log
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
    restart: unless-stopped

volumes:
  grafana-data:
  loki-data:
```

### 12.6 Prometheus config

```yaml
# infra/monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: "core-api"
    static_configs:
      - targets: ["core-api:8000"]
    metrics_path: "/api/metrics"

  - job_name: "ai-svc"
    static_configs:
      - targets: ["ai-svc:8001"]
    metrics_path: "/metrics"

  - job_name: "market-svc"
    static_configs:
      - targets: ["market-svc:8005"]
    metrics_path: "/metrics"
```

### 12.7 Sentry (error tracking)

```python
# Em cada serviço, no main.py:
import sentry_sdk
from shared.config import settings

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=0.1,  # 10% dos requests para performance
        profiles_sample_rate=0.1,
        environment=settings.ENVIRONMENT,
        release=settings.VERSION,
    )

# Em cada request, associar correlation_id:
# (dentro do CorrelationMiddleware)
if settings.SENTRY_DSN:
    sentry_sdk.set_tag("request_id", request_id)
    sentry_sdk.set_user({"id": user_id}) if user_id else None
```

---

## 13. CI/CD e qualidade de código

### 13.1 GitHub Actions — Pipeline CI

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
        with:
          python-version: "3.12"
      - run: pip install ruff
      - run: ruff check services/core-api/
      - run: ruff format --check services/core-api/

  test-core-api:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_db
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r services/core-api/requirements.txt
      - run: pip install pytest pytest-asyncio pytest-cov httpx
      - run: pytest services/core-api/tests/ -v --cov=services/core-api/app --cov-report=xml
        env:
          DATABASE_URL: postgresql+asyncpg://test:test@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379/0
          ENVIRONMENT: test

  test-ai-svc:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_ai_db
        ports: ["5433:5432"]
      redis:
        image: redis:7-alpine
        ports: ["6380:6379"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r services/ai-svc/requirements.txt
      - run: pip install pytest pytest-asyncio
      - run: pytest services/ai-svc/tests/ -v

  docker-build:
    runs-on: ubuntu-latest
    needs: [lint, test-core-api]
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/build-push-action@v5
        with:
          context: services/core-api
          push: false
          tags: core-api:test
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

### 13.2 Deploy pipeline (Coolify)

```yaml
# .github/workflows/deploy-prod.yml
name: Deploy Production

on:
  push:
    branches: [main]
    paths:
      - "services/core-api/**"
      - "services/ai-svc/**"

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # Determinar quais serviços mudaram
      - id: changes
        uses: dorny/paths-filter@v3
        with:
          filters: |
            core-api:
              - 'services/core-api/**'
            ai-svc:
              - 'services/ai-svc/**'

      # Deploy via Coolify webhook
      - name: Deploy core-api
        if: steps.changes.outputs.core-api == 'true'
        run: |
          curl -X POST "${{ secrets.COOLIFY_WEBHOOK_CORE_API }}" \
            -H "Authorization: Bearer ${{ secrets.COOLIFY_TOKEN }}"

      - name: Deploy ai-svc
        if: steps.changes.outputs.ai-svc == 'true'
        run: |
          curl -X POST "${{ secrets.COOLIFY_WEBHOOK_AI_SVC }}" \
            -H "Authorization: Bearer ${{ secrets.COOLIFY_TOKEN }}"
```

### 13.3 Pre-commit hooks

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
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: ['--maxkb=1000']
      - id: detect-private-key
      - id: check-merge-conflict

  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v3.1.0
    hooks:
      - id: prettier
        types_or: [javascript, typescript, json, yaml, markdown]
```

### 13.4 pyproject.toml

```toml
# services/core-api/pyproject.toml
[tool.ruff]
target-version = "py312"
line-length = 120
src = ["app"]

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "B",    # flake8-bugbear
    "C4",   # flake8-comprehensions
    "UP",   # pyupgrade
    "SIM",  # flake8-simplify
]
ignore = [
    "E501",   # line too long (handled by formatter)
    "B008",   # do not perform function calls in argument defaults (Depends)
]

[tool.ruff.lint.isort]
known-first-party = ["app", "shared", "modules"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
filterwarnings = [
    "ignore::DeprecationWarning",
]
```

### 13.5 Dockerfile padrão

```dockerfile
# services/core-api/Dockerfile
FROM python:3.12-slim AS base

WORKDIR /app

# Dependências de sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Dependências Python (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código da aplicação
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .

# Libs compartilhadas (se monorepo)
COPY libs/ /libs/
RUN pip install -e /libs/shared-schemas /libs/shared-utils 2>/dev/null || true

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4"]
```

---

## 14. Segurança

### 14.1 Checklist de segurança

| Item | Implementação |
|------|---------------|
| **Secrets em env vars** | Nunca no código; usar Coolify secrets ou Vault |
| **CORS restritivo** | Lista explícita de origins; nunca `*` em prod |
| **Rate limiting** | slowapi ou Traefik rate limit por IP/user |
| **Input validation** | Pydantic em todo input; nunca confiar no client |
| **SQL injection** | Sempre SQLAlchemy ORM ou parameterized queries; nunca f-strings em SQL |
| **XSS** | Sanitizar output; CSP headers |
| **CSRF** | SameSite cookies; CSRF tokens para forms |
| **Auth** | JWT com validação de signature, expiry, audience, issuer |
| **Secrets rotation** | Processo documentado para rotacionar tokens e keys |
| **Dependency audit** | `pip-audit` no CI; Dependabot habilitado |
| **Docker** | Non-root user; imagem slim; scan com Trivy |
| **Logs** | Nunca logar passwords, tokens, PII completo |
| **HTTPS** | TLS obrigatório em produção; HSTS header |
| **Backup** | Backup diário automático do PostgreSQL; testar restore |

### 14.2 Headers de segurança (middleware)

```python
# shared/middleware/security_headers.py
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response
```

### 14.3 Rate limiting

```python
# shared/middleware/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],
    storage_uri="redis://redis:6379/1",
)

# No router:
@router.post("/api/v1/auth/login")
@limiter.limit("5/minute")  # Login: 5 tentativas por minuto
async def login(request: Request, ...):
    ...

@router.post("/api/v1/ai/chat")
@limiter.limit("30/minute")  # Chat AI: 30 por minuto
async def chat(request: Request, ...):
    ...
```

### 14.4 Validação de input

```python
# schemas.py — SEMPRE validar com Pydantic
from pydantic import BaseModel, field_validator, EmailStr
from typing import Optional
import re

class CreateUserRequest(BaseModel):
    email: EmailStr
    name: str
    phone: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if len(v) < 2 or len(v) > 100:
            raise ValueError("Name must be between 2 and 100 characters")
        if not re.match(r"^[\w\s\-\.]+$", v):
            raise ValueError("Name contains invalid characters")
        return v.strip()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        if v and not re.match(r"^\+?[\d\s\-\(\)]{8,20}$", v):
            raise ValueError("Invalid phone number format")
        return v
```

### 14.5 Dockerfile seguro

```dockerfile
# Usar non-root user
RUN adduser --disabled-password --gecos "" appuser
USER appuser

# Não copiar arquivos desnecessários (.dockerignore)
# Scan de vulnerabilidades: trivy image core-api:latest
```

---

## 15. Infraestrutura — Hetzner + Coolify

### 15.1 Arquitetura recomendada

```
┌─────────────────────────────────────────────────────────┐
│                    Hetzner Cloud                         │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │           Server 1 — Produção (CX41+)             │   │
│  │                                                    │   │
│  │   ┌──────────┐  ┌──────────┐  ┌──────────────┐  │   │
│  │   │ Coolify  │  │ Traefik  │  │ PostgreSQL   │  │   │
│  │   │ (mgmt)   │  │ (proxy)  │  │ + pgvector   │  │   │
│  │   └──────────┘  └────┬─────┘  └──────────────┘  │   │
│  │                      │                            │   │
│  │        ┌─────────────┼─────────────┐              │   │
│  │        ▼             ▼             ▼              │   │
│  │   ┌─────────┐  ┌─────────┐  ┌──────────┐        │   │
│  │   │core-api │  │ ai-svc  │  │market-svc│        │   │
│  │   │(container│  │(container│  │(container│        │   │
│  │   └─────────┘  └─────────┘  └──────────┘        │   │
│  │                                                    │   │
│  │   ┌─────────┐  ┌─────────┐  ┌──────────┐        │   │
│  │   │  Redis  │  │  Loki   │  │Prometheus│        │   │
│  │   └─────────┘  └─────────┘  └──────────┘        │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │         Server 2 — Staging (CX21)                 │   │
│  │   (Mesmo layout, dados de teste)                  │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │   Hetzner Storage Box — Backups (BX11)            │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 15.2 Sizing recomendado (Hetzner)

| Server | Tipo | vCPU | RAM | Disco | Uso | Custo aprox. |
|--------|------|------|-----|-------|-----|--------------|
| Produção | CX41 | 4 vCPU | 16 GB | 160 GB | Todos os containers | ~€15/mês |
| Staging | CX21 | 2 vCPU | 4 GB | 40 GB | Ambiente de teste | ~€5/mês |
| Backup | BX11 | — | — | 1 TB | Backups PostgreSQL | ~€4/mês |
| Scale-up | CX51 | 8 vCPU | 32 GB | 240 GB | Quando precisar | ~€30/mês |

**Nota:** Para projetos iniciais, **1 servidor CX41 roda tudo** (Coolify + todos os containers). Separar quando o uso de CPU/RAM justificar.

### 15.3 Setup Coolify

**1. Instalação:**
```bash
# No servidor Hetzner (Ubuntu 22.04+)
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash
```

**2. Configuração por serviço no Coolify:**

Cada serviço é um "recurso" no Coolify com:
- **Source:** GitHub repo (branch `main` para prod, `develop` para staging)
- **Build pack:** Dockerfile
- **Dockerfile path:** `services/core-api/Dockerfile`
- **Health check:** `/health` ou `/api/health/live`
- **Environment variables:** Configuradas no painel Coolify (secrets)
- **Domain:** `api.example.com` (Traefik gerenciado pelo Coolify)
- **Auto-deploy:** Webhook no GitHub → Coolify redeploy on push

**3. Variáveis de ambiente (template):**

```env
# Core API
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/mydb
REDIS_URL=redis://redis:6379/0
OIDC_ISSUER=https://auth.example.com/realms/myapp
OIDC_AUDIENCE=my-api
INTERNAL_SERVICE_KEY=generated-random-key
SENTRY_DSN=https://xxx@sentry.io/yyy
LOG_LEVEL=INFO
ENVIRONMENT=production
VERSION=1.0.0

# AI Service
OPENAI_API_KEY=sk-...
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
LLM_MODEL=gpt-4o-mini
LLM_PROVIDER=openai
```

### 15.4 Docker Compose (Produção)

```yaml
# infra/docker-compose.prod.yml
services:
  traefik:
    image: traefik:v3.0
    command:
      - "--api.dashboard=true"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.le.acme.httpchallenge.entrypoint=web"
      - "--certificatesresolvers.le.acme.email=admin@example.com"
      - "--certificatesresolvers.le.acme.storage=/letsencrypt/acme.json"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - traefik-certs:/letsencrypt
    restart: unless-stopped

  core-api:
    build:
      context: ../services/core-api
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.core-api.rule=Host(`api.example.com`)"
      - "traefik.http.routers.core-api.entrypoints=websecure"
      - "traefik.http.routers.core-api.tls.certresolver=le"
      - "traefik.http.services.core-api.loadbalancer.server.port=8000"
    env_file: .env.prod
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: "2.0"

  ai-svc:
    build:
      context: ../services/ai-svc
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.ai-svc.rule=Host(`api.example.com`) && PathPrefix(`/api/ai`, `/api/rag`, `/api/chat`)"
      - "traefik.http.routers.ai-svc.priority=10"
      - "traefik.http.routers.ai-svc.entrypoints=websecure"
      - "traefik.http.routers.ai-svc.tls.certresolver=le"
    env_file: .env.prod
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: "2.0"

  postgres:
    image: pgvector/pgvector:pg16
    volumes:
      - pg-data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 2G

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  pg-data:
  redis-data:
  traefik-certs:
```

### 15.5 Backup automatizado

```bash
#!/bin/bash
# infra/scripts/backup-db.sh
# Executar via cron: 0 3 * * * /path/to/backup-db.sh

set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/postgres"
RETENTION_DAYS=30

# Dump
docker exec postgres pg_dump -U $DB_USER -Fc $DB_NAME > "${BACKUP_DIR}/backup_${TIMESTAMP}.dump"

# Comprimir
gzip "${BACKUP_DIR}/backup_${TIMESTAMP}.dump"

# Upload para Hetzner Storage Box (via rsync/scp)
rsync -avz "${BACKUP_DIR}/backup_${TIMESTAMP}.dump.gz" \
  "u123456@u123456.your-storagebox.de:backups/"

# Cleanup local (manter últimos N dias)
find "${BACKUP_DIR}" -name "*.dump.gz" -mtime +${RETENTION_DAYS} -delete

echo "[$(date)] Backup completed: backup_${TIMESTAMP}.dump.gz"
```

### 15.6 Scaling strategy

| Fase | Approach | Trigger |
|------|----------|---------|
| **Início** | 1 servidor, todos os containers | 0–1000 users |
| **Growth** | Separar DB em servidor dedicado | CPU > 70% sustained |
| **Scale** | Réplicas do core-api (2-3 instances) | Latência p95 > 500ms |
| **Advanced** | Hetzner Load Balancer + múltiplos nodes | 10k+ users |

---

## 16. Testes

### 16.1 Pirâmide de testes

```
        ┌─────────┐
        │  E2E    │  ← Poucos (5-10): fluxos críticos
        │ (Pytest │     Login → Criar → Listar → Deletar
        │  + HTTP)│
        ├─────────┤
        │ Integra-│  ← Moderados (20-50): endpoints + DB real
        │  ção    │     POST /api/v1/users → verifica no DB
        ├─────────┤
        │ Unitá-  │  ← Muitos (100+): lógica de negócio pura
        │  rios   │     service.calculate_tax(100) == 15
        └─────────┘
```

### 16.2 conftest.py padrão

```python
# tests/conftest.py
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.shared.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "postgresql+asyncpg://test:test@localhost:5432/test_db"

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def engine():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def db_session(engine):
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()

@pytest.fixture
async def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest.fixture
def auth_headers():
    """Headers com JWT válido para testes."""
    # Gerar JWT de teste com claims fixas
    from jose import jwt
    token = jwt.encode(
        {"sub": "test-user-id", "email": "test@test.com", "roles": ["user"]},
        "test-secret",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}
```

### 16.3 Exemplos de testes

```python
# tests/test_health.py
import pytest

@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

@pytest.mark.asyncio
async def test_health_includes_version(client):
    response = await client.get("/health")
    data = response.json()
    assert "version" in data


# tests/test_users.py
@pytest.mark.asyncio
async def test_create_user(client, auth_headers):
    response = await client.post(
        "/api/v1/users",
        json={"email": "new@test.com", "name": "Test User"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["data"]["email"] == "new@test.com"

@pytest.mark.asyncio
async def test_create_user_invalid_email(client, auth_headers):
    response = await client.post(
        "/api/v1/users",
        json={"email": "not-an-email", "name": "Test"},
        headers=auth_headers,
    )
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_list_users_requires_auth(client):
    response = await client.get("/api/v1/users")
    assert response.status_code == 401  # ou 403
```

### 16.4 Testes de agentes IA

```python
# ai-svc/tests/test_orchestrator.py
@pytest.mark.asyncio
async def test_orchestrator_routes_to_correct_agent(mock_llm, mock_memory):
    orchestrator = Orchestrator(
        agents={"finance": mock_finance_agent, "default": mock_default_agent},
        llm_client=mock_llm,
    )
    mock_llm.classify_intent.return_value = {"agent": "finance", "confidence": 0.9}

    context = AgentContext(
        user_id=1,
        conversation_id="test",
        correlation_id="test-id",
        message="Qual meu saldo?",
    )
    response = await orchestrator.route(context)
    assert response.agent_name == "finance"

# ai-svc/tests/test_rag_pipeline.py
@pytest.mark.asyncio
async def test_rag_retrieve_returns_relevant_chunks(rag_pipeline, seeded_embeddings):
    results = await rag_pipeline.retrieve("Como configurar o sistema?", top_k=3)
    assert len(results) <= 3
    assert all(r["similarity"] >= 0.7 for r in results)
```

### 16.5 Regras de testes

| Regra | Detalhe |
|-------|---------|
| Nomear com `test_` + ação | `test_create_user_with_valid_data` |
| Um assert lógico por teste | Testar uma coisa de cada vez |
| Fixtures para setup | Nunca duplicar setup entre testes |
| Mocks para serviços externos | LLM, APIs externas, email — sempre mock |
| DB de teste isolado | Cada teste roda em transação com rollback |
| CI bloqueia merge sem testes | Cobertura mínima: 60% |
| Testes de contrato | Quando extrair microserviço, testar que o contrato não quebrou |

---

## 17. Padrões de código Python/FastAPI

### 17.1 Estilo e formatação

- **Formatter:** Ruff (substitui Black + isort).
- **Line length:** 120 caracteres.
- **Python version:** 3.12+ (usar type hints modernos: `dict` em vez de `Dict`, `list[str]` em vez de `List[str]`).
- **Strings:** Double quotes `"` para strings que o usuário vê; single quotes `'` para keys internas — ou consistente com Ruff default.
- **Imports:** Agrupados por: stdlib → third-party → local. Ruff organiza automaticamente.

### 17.2 Type hints obrigatórios

```python
# BOM — types explícitos
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)) -> UserResponse:
    ...

def calculate_tax(amount: float, rate: float = 0.15) -> float:
    ...

# RUIM — sem types
async def get_user(user_id, db):
    ...
```

### 17.3 Dependency Injection (FastAPI Depends)

```python
# dependencies.py
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from shared.database import get_db

class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = UserRepository(db)

    async def get_user(self, user_id: int) -> User:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundException(f"User {user_id} not found")
        return user

def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(db)

# router.py
@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
    current_user: dict = Depends(get_current_user),
) -> ApiResponse[UserResponse]:
    user = await service.get_user(user_id)
    return ApiResponse(data=UserResponse.model_validate(user))
```

### 17.4 Exceções de domínio

```python
# shared/exceptions.py
from fastapi import HTTPException

class DomainException(Exception):
    """Base para exceções de domínio."""
    def __init__(self, message: str, code: str = "DOMAIN_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)

class NotFoundException(DomainException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, "NOT_FOUND")

class ConflictException(DomainException):
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message, "CONFLICT")

class ForbiddenException(DomainException):
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, "FORBIDDEN")

class ValidationException(DomainException):
    def __init__(self, message: str = "Validation failed", details: list = None):
        super().__init__(message, "VALIDATION_ERROR")
        self.details = details or []

# Registrar no main.py:
@app.exception_handler(DomainException)
async def domain_exception_handler(request: Request, exc: DomainException):
    status_map = {
        "NOT_FOUND": 404,
        "CONFLICT": 409,
        "FORBIDDEN": 403,
        "VALIDATION_ERROR": 422,
    }
    return JSONResponse(
        status_code=status_map.get(exc.code, 400),
        content={"status": "error", "code": exc.code, "message": exc.message},
    )
```

### 17.5 Repository Pattern

```python
# modules/users/repository.py
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from modules.users.models import User
from typing import Optional

class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: int) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def list(self, skip: int = 0, limit: int = 20, filters: dict = None) -> tuple[list[User], int]:
        query = select(User)

        if filters:
            if filters.get("is_active") is not None:
                query = query.where(User.is_active == filters["is_active"])
            if filters.get("search"):
                query = query.where(User.name.ilike(f"%{filters['search']}%"))

        # Contagem total
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar()

        # Dados paginados
        query = query.offset(skip).limit(limit).order_by(User.created_at.desc())
        result = await self.db.execute(query)

        return result.scalars().all(), total

    async def create(self, **data) -> User:
        user = User(**data)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update(self, user_id: int, **data) -> Optional[User]:
        await self.db.execute(
            update(User).where(User.id == user_id).values(**data)
        )
        await self.db.commit()
        return await self.get_by_id(user_id)

    async def soft_delete(self, user_id: int) -> bool:
        from datetime import datetime, timezone
        result = await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(deleted_at=datetime.now(timezone.utc))
        )
        await self.db.commit()
        return result.rowcount > 0
```

### 17.6 Async por padrão

```python
# SEMPRE usar async para:
# - Endpoints FastAPI
# - Acesso a banco de dados (SQLAlchemy async)
# - Chamadas HTTP (httpx.AsyncClient)
# - Operações Redis (redis.asyncio)
# - Chamadas a LLM (OpenAI async)

# Usar sync apenas para:
# - Cálculos puros (CPU-bound) — e considerar run_in_executor
# - Leitura de arquivos locais (se rápido)
# - Operações in-memory

# Para CPU-bound dentro de async:
import asyncio
from concurrent.futures import ProcessPoolExecutor

async def heavy_computation(data):
    loop = asyncio.get_event_loop()
    with ProcessPoolExecutor() as pool:
        result = await loop.run_in_executor(pool, sync_heavy_function, data)
    return result
```

### 17.7 Config centralizada

```python
# shared/config.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # App
    ENVIRONMENT: str = "development"
    VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Auth (OIDC)
    OIDC_ISSUER: str
    OIDC_AUDIENCE: str
    OIDC_CLIENT_ID: Optional[str] = None

    # Inter-service
    INTERNAL_SERVICE_KEY: str = ""
    CORE_API_URL: str = "http://core-api:8000"
    AI_SVC_URL: str = "http://ai-svc:8001"

    # AI
    OPENAI_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_PROVIDER: str = "openai"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536

    # Sentry
    SENTRY_DSN: Optional[str] = None

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

---

## 18. Convenções de projeto

### 18.1 Git

| Convenção | Exemplo |
|-----------|---------|
| **Branch naming** | `feature/add-user-auth`, `fix/login-timeout`, `chore/update-deps` |
| **Commit messages** | Conventional Commits: `feat: add user registration endpoint` |
| **PR title** | Curto (<70 chars): `feat: add OAuth2 login with Keycloak` |
| **PR body** | Summary + Test plan + Screenshot (se UI) |
| **Merge strategy** | Squash merge para features; merge commit para releases |
| **Protected branches** | `main` e `develop` — require PR + CI passing |
| **Tags** | Semantic versioning: `v1.0.0`, `v1.1.0`, `v2.0.0-beta.1` |

### 18.2 Conventional Commits

```
feat:     Nova funcionalidade
fix:      Correção de bug
docs:     Documentação
style:    Formatação (sem mudança de lógica)
refactor: Refatoração de código
test:     Adição/correção de testes
chore:    Manutenção (deps, CI, configs)
perf:     Melhoria de performance
ci:       Mudanças no CI/CD
build:    Mudanças no build system
```

Formato: `tipo(escopo opcional): descrição curta`

```
feat(auth): add OAuth2 login with Keycloak
fix(billing): correct tax calculation for exempt items
refactor(ai): extract embedding generation to separate service
chore(deps): bump fastapi from 0.114 to 0.115
```

### 18.3 Naming conventions

| Item | Convenção | Exemplo |
|------|-----------|---------|
| Diretórios | `snake_case` | `shared_utils/`, `ai_svc/` |
| Arquivos Python | `snake_case.py` | `user_service.py` |
| Classes | `PascalCase` | `UserService`, `BaseAgent` |
| Funções/Métodos | `snake_case` | `get_user_by_id()` |
| Constantes | `UPPER_SNAKE_CASE` | `MAX_RETRIES`, `DEFAULT_PAGE_SIZE` |
| Env vars | `UPPER_SNAKE_CASE` | `DATABASE_URL`, `REDIS_URL` |
| Tabelas DB | `snake_case` plural | `users`, `order_items` |
| Colunas DB | `snake_case` | `created_at`, `user_id` |
| Endpoints | `kebab-case` path | `/api/v1/user-profiles` |
| Eventos | `domain.action` | `user.created`, `order.completed` |
| Docker images | `kebab-case` | `core-api`, `ai-svc` |

### 18.4 Documentação

- **ADR (Architecture Decision Record):** Para cada decisão arquitetural significativa, criar um arquivo em `.docs/ADR/`.

```markdown
# ADR-001: Usar monorepo com serviços isolados

## Status
Aceito

## Contexto
Precisamos decidir entre monorepo e multi-repo para o projeto.

## Decisão
Monorepo com serviços isolados em services/.

## Consequências
- (+) Um único PR pode mudar frontend + backend
- (+) CI/CD unificado
- (-) Clone maior
- (-) Precisa de path-based CI triggers
```

- **Runbooks:** Para operações comuns (deploy, rollback, backup, incident response).
- **README.md por serviço:** Como rodar localmente, endpoints principais, variáveis de ambiente.

---

## 19. Checklist de novo serviço

Ao criar um novo microserviço, seguir esta checklist:

### Setup básico
- [ ] Criar `services/nome-svc/` com estrutura padrão
- [ ] `Dockerfile` com multi-stage build, non-root user, health check
- [ ] `requirements.txt` com versões pinadas
- [ ] `pyproject.toml` com config de ruff e pytest
- [ ] `app/main.py` (~30 linhas: app + middleware + routers)
- [ ] `app/shared/config.py` com Settings (Pydantic BaseSettings)

### Banco e dados
- [ ] `app/shared/database.py` com engine async + `get_db()`
- [ ] `alembic/` configurado com env.py async
- [ ] Schema PostgreSQL isolado (ex.: `CREATE SCHEMA nome;`)
- [ ] Migração inicial com `alembic revision --autogenerate`

### Observabilidade
- [ ] `JSONFormatter` com `service_name` e `correlation_id`
- [ ] `CorrelationMiddleware` (propagar X-Request-ID)
- [ ] `RequestLogMiddleware`
- [ ] Endpoint `/health` (liveness) e `/health/ready` (readiness)
- [ ] Endpoint `/metrics` (Prometheus)
- [ ] Sentry SDK (condicionado a SENTRY_DSN)

### Segurança
- [ ] Auth via OIDC (validar JWT) ou X-Internal-Key (se só interno)
- [ ] Rate limiting configurado
- [ ] CORS configurado (se exposto externamente)
- [ ] SecurityHeadersMiddleware
- [ ] Input validation (Pydantic em todos os endpoints)

### Testes
- [ ] `tests/conftest.py` com fixtures (db, client, auth_headers)
- [ ] `tests/test_health.py`
- [ ] Pelo menos 1 teste por endpoint (happy path)
- [ ] Mock para serviços externos (LLM, APIs)

### Integração
- [ ] Registrar no `docker-compose.yml` (dev) e `docker-compose.prod.yml`
- [ ] Configurar rotas no Traefik (labels Docker)
- [ ] Adicionar job no CI (`.github/workflows/ci.yml`)
- [ ] Adicionar webhook de deploy no Coolify
- [ ] Prometheus scrape config atualizado
- [ ] Documentar no README do serviço

### Contratos
- [ ] Schemas de request/response em `libs/shared-schemas/` (se compartilhados)
- [ ] Eventos (Redis Streams) documentados em `libs/shared-schemas/events.py`
- [ ] Consumer group criado para eventos que consome

---

## 20. Anti-patterns a evitar

### 20.1 Código

| Anti-pattern | Por que é ruim | Fazer em vez disso |
|--------------|---------------|-------------------|
| `Base.metadata.create_all()` no boot | Cria tabelas sem controle; ignora migrações | Usar Alembic |
| `import *` | Namespace poluído; difícil rastrear origem | Imports explícitos |
| Catch genérico `except Exception: pass` | Esconde bugs; impossível debugar | Catch específico; logar o erro |
| SQL via f-string | SQL injection | SQLAlchemy ORM ou parameterized queries |
| Secrets no código | Exposição em git | Env vars + secret manager |
| `datetime.utcnow()` | Deprecado no Python 3.12+ | `datetime.now(timezone.utc)` |
| `print()` para logs | Sem estrutura, sem level, sem correlation | `logger.info()` com JSONFormatter |
| God function (>100 linhas) | Impossível de testar e manter | Extrair em funções menores |
| Dependência circular entre módulos | Acoplamento; impossível extrair serviço | Eventos ou módulo intermediário |
| Configuração hardcoded | Não adapta a diferentes ambientes | `Settings` com env vars |

### 20.2 Arquitetura

| Anti-pattern | Por que é ruim | Fazer em vez disso |
|--------------|---------------|-------------------|
| Microserviço prematuro | Complexidade sem necessidade | Começar modular dentro de 1 serviço; extrair quando doer |
| Banco compartilhado sem schema | Serviços acoplados pelo banco | Schema por serviço; contratos via API |
| Comunicação síncrona em cadeia | A→B→C→D: latência somada; falha em cascata | Eventos assíncronos (Redis Streams) quando possível |
| Sem circuit breaker | 1 serviço fora derruba todos | Circuit breaker + fallback |
| Deploy manual | Inconsistente; propenso a erro | CI/CD automatizado com Coolify |
| Sem health check | Não sabe se o serviço está saudável | `/health` + Docker HEALTHCHECK |
| Log sem correlation ID | Impossível rastrear request entre serviços | Middleware de correlation ID |
| Sem rate limiting | Vulnerable a abuse e DDoS | slowapi ou Traefik rate limit |

### 20.3 IA/Agentes

| Anti-pattern | Por que é ruim | Fazer em vez disso |
|--------------|---------------|-------------------|
| Enviar SQL gerado pelo LLM direto ao DB | SQL injection via prompt injection | Skills com queries predefinidas e parametrizadas |
| Sem limite de tokens | Custo descontrolado | `max_tokens` + budget tracking |
| Embedding sem chunk | Vetores de documentos inteiros; baixo recall | Chunking semântico (512-1000 tokens) |
| RAG sem threshold | Retorna lixo quando não há match | Threshold mínimo (0.7) + "não encontrei" |
| Prompt no código | Difícil iterar e versionare | Arquivos de prompt separados; prompt versioning |
| Sem fallback de LLM | Provider fora = sistema fora | Multi-provider (OpenAI → Anthropic → local) |
| Logar mensagens completas do usuário | Privacidade; custo de storage | Preview (primeiros 100 chars) + comprimento |
| Agente sem timeout | Request infinito se LLM trava | Timeout por agente (30-60s) |

---

## Apêndice A: main.py template

```python
"""
Core API — Main entrypoint.
~50 linhas: app, middleware, routers.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.shared.config import settings
from app.shared.middleware.correlation import CorrelationMiddleware
from app.shared.middleware.request_log import RequestLogMiddleware
from app.shared.middleware.security_headers import SecurityHeadersMiddleware
from app.shared.middleware.error_handler import (
    http_exception_handler,
    validation_exception_handler,
    unhandled_exception_handler,
)
from app.shared.exceptions import DomainException, domain_exception_handler
from app.shared.logging import setup_logging
from starlette.exceptions import HTTPException
from fastapi.exceptions import RequestValidationError

# Logging
setup_logging(service_name="core-api")

# Sentry (opcional)
if settings.SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown

app = FastAPI(title="Core API", version=settings.VERSION, lifespan=lifespan)

# Middleware (ordem inversa de execução)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLogMiddleware)
app.add_middleware(CorrelationMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(DomainException, domain_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# Routers
from app.modules.auth.router import router as auth_router
from app.modules.users.router import router as users_router
# ... demais módulos

app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")

# Health
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "core-api", "version": settings.VERSION}
```

---

## Apêndice B: docker-compose.yml (desenvolvimento local)

```yaml
# infra/docker-compose.yml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: dev
      POSTGRES_PASSWORD: dev
      POSTGRES_DB: myapp_dev
    ports:
      - "5432:5432"
    volumes:
      - pg-dev-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dev"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  core-api:
    build:
      context: ../services/core-api
    ports:
      - "8000:8000"
    env_file: ../.env.dev
    volumes:
      - ../services/core-api/app:/app/app  # Hot reload
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  ai-svc:
    build:
      context: ../services/ai-svc
    ports:
      - "8001:8001"
    env_file: ../.env.dev
    volumes:
      - ../services/ai-svc/app:/app/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
    depends_on:
      - postgres
      - redis

volumes:
  pg-dev-data:
```

---

## Apêndice C: .env.dev template

```env
# === App ===
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
VERSION=0.1.0

# === Database ===
DATABASE_URL=postgresql+asyncpg://dev:dev@localhost:5432/myapp_dev

# === Redis ===
REDIS_URL=redis://localhost:6379/0

# === Auth (OIDC) ===
OIDC_ISSUER=http://localhost:8080/realms/myapp
OIDC_AUDIENCE=my-api
OIDC_CLIENT_ID=my-spa

# === Inter-service ===
INTERNAL_SERVICE_KEY=dev-internal-key-change-in-prod

# === AI ===
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
LLM_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536

# === CORS ===
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]

# === Sentry (opcional em dev) ===
# SENTRY_DSN=
```
```
