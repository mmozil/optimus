# Agent Optimus — Manual Operacional

## Squad Ativo

| Agent | Codename | Papel | Nível | Modelo |
|-------|----------|-------|-------|--------|
| **Optimus** | Lead | Orquestra, delega, monitora | Lead | Gemini 2.5 Pro |
| **Friday** | Developer | Código, debugging, deploy | Specialist | Gemini 2.5 Flash |
| **Fury** | Researcher | Pesquisa com evidências | Specialist | Gemini 2.5 Flash |

## Regras Operacionais

1. **Optimus decide, especialistas executam.**
2. **Event-driven first** — Supabase Real-time para notificações, heartbeat como fallback.
3. **Rate Limiter** — Cada agent tem limite por minuto e por dia. Nunca ultrapassar.
4. **SOUL.md** — Cada agent tem personalidade definida, versionada e auditável.
5. **Escalação** — Se confiança < 70%, escalar para Optimus decidir.
6. **Zero 429** — Rate limiter impede burst de chamadas LLM.

## Comunicação

- `@optimus` — Escalar para o Lead
- `@friday` — Tasks de código/debugging
- `@fury` — Tasks de pesquisa

## Endpoints

- `POST /api/v1/chat` — Enviar mensagem para um agent
- `GET /api/v1/agents` — Listar agents ativos
- `GET /health` — Health check
