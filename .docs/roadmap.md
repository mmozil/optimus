# AgentOptimus — Roadmap Unificado

> **Última atualização:** 2026-02-19
> **Fonte:** Consolidação de `planning-optimus.md`, `Roadmap-Optimus.md`, `roadmap-optimus-v2.md`, `agent-claude.md`, `prompt-avancado.md`, `Prompt-COT.md`
> **Regra:** Toda implementação DEVE seguir a Regra de Ouro + Regra de Blindagem abaixo.

---

## REGRA DE OURO — Obrigatório em TODA implementação

Nenhuma feature é implementada sem passar nos 5 checkpoints:

| # | Checkpoint | Pergunta-chave |
|---|-----------|----------------|
| 1 | **Call Path Documentado** | Qual função chama esse código? Em qual arquivo? Em que condição (startup/request/cron)? |
| 2 | **Teste que Falha** | Existe teste E2E que quebra se o código não for chamado? |
| 3 | **Implementação Integrada** | O código está conectado ao fluxo real (gateway/react_loop/main.py)? |
| 4 | **Testado em Produção** | Validado em https://optimus.tier.finance com evidência? |
| 5 | **Roadmap Atualizado** | Status marcado neste documento com data e evidência? |

**Se algum checkpoint falhar → feature NÃO é entregue.**

---

## REGRA DE BLINDAGEM — Proteção contra regressão

Toda alteração DEVE garantir que não quebra funcionalidades existentes:

| # | Regra | Como |
|---|-------|------|
| 1 | **Testes existentes passam** | Rodar `pytest tests/test_e2e.py` antes e depois da mudança |
| 2 | **Imports não quebram** | Verificar que nenhum import existente foi removido ou renomeado sem atualizar chamadores |
| 3 | **Contratos de API preservados** | Endpoints existentes mantêm mesma assinatura (query params, body, response) |
| 4 | **Fallback graceful** | Se novo código falhar, o fluxo anterior continua funcionando (try/except com log) |
| 5 | **Sem efeitos colaterais** | Mudança em módulo X não altera comportamento de módulo Y sem documentação explícita |

---

## Estado Atual — O que FUNCIONA em produção

- [x] Chat via Gemini (ReAct loop + tool calling + fallback)
- [x] Login/Registro JWT + Auth pages
- [x] Histórico de mensagens (PostgreSQL)
- [x] STT — Groq Whisper (whisper-large-v3)
- [x] TTS — Edge TTS (pt-BR-AntonioNeural)
- [x] Multi-model failover (Gemini Flash → Pro → GPT-4o)
- [x] SOUL.md + MEMORY.md no system prompt
- [x] Emotional Adapter (sentimento → tom do prompt)
- [x] Planning Engine (decomposição de tarefas)
- [x] Auto-Journal (aprendizado pós-resposta)
- [x] Persona Selector (persona por intent)
- [x] Agent Factory + BaseAgent
- [x] Session Manager + Session Compacting
- [x] Cost Tracker
- [x] Deploy CI/CD (Push → Coolify → Docker)
- [⚠️] Web Research — stub (`research_search` retorna mock, Tavily NÃO integrado — ver FASE 26)
- [x] Browser Automation (Playwright/CDP)
- [x] Dynamic Agents (criação sob demanda)
- [x] Google OAuth + IMAP/SMTP (email)
- [x] Memory Sync to DB
- [x] Apple iCloud integration
- [x] Multimodal Input (imagens, áudio, PDF, CSV)
- [x] Onboarding + Settings page
- [x] A2A Protocol (API REST)
- [x] Collective Intelligence (cross-agent learning)
- [⚠️] ToT Engine — parcial (pre-reasoning injetado em queries complexas, mas `think()` completo nunca chamado em conversa real — ver FASE 25)
- [⚠️] UncertaintyQuantifier — parcial (🔴 warning via heurística simples, quantifier real nunca chamado — ver FASE 25)
- [x] Chat Commands (10 comandos: /status /help /agents /task /learn /think /compact /new /standup /cron)
- [x] Thread Manager (task → thread → subscribe → @mentions)
- [x] Notification Service (send → polling REST → toast no frontend)
- [x] Working Memory (WORKING.md por agent no contexto)
- [x] Context Awareness (hora/dia/saudação no prompt)
- [x] Intent Routing (smart agent routing por intent)
- [x] Audit Trail (react_steps persistidos em audit_log → painel debug no frontend)
- [x] Embeddings Collective Intelligence (PGvector coseno, semantic=True por padrão, batch index)

---

## FASE 10 — Chat Commands & Thread System ✅ CONCLUÍDA (2026-02-19)

**Objetivo:** Conectar `chat_commands.py`, `thread_manager.py` e `notification_service.py` ao fluxo principal.

- [x] **10.1** `/status`, `/help`, `/agents`, `/task`, `/learn`, `/cron`, `/standup` — JÁ INTEGRADO
  - Call path: `gateway.route_message()` linha 163 → `chat_commands.is_command()` → `execute()`
- [x] **10.2** thread_manager conectado ao `/task create`
  - Call path: `_cmd_task("create")` → `task_manager.create()` → `thread_manager.subscribe(creator)` + `post_message()`
- [x] **10.3** notification_service → polling REST + frontend toast
  - API: `GET /api/v1/notifications` + `POST /api/v1/notifications/{id}/read`
  - API: `GET /api/v1/tasks` + `GET /api/v1/tasks/{id}/thread`
  - Frontend: polling a cada 30s → `showToast()` → auto-dismiss 6s + click para dispensar
- [x] **10.4** Testes E2E — `TestFase10ChatCommandsAndNotifications` (9 testes)
  - `/help`, `/status`, `/task create`, `notification_service`, `thread_manager`, `gateway intercept`
- [ ] **10.5** Testar em produção (https://optimus.tier.finance)

---

## FASE 11 — Channels (Telegram + WhatsApp)

**Objetivo:** Ativar pelo menos 1 canal além do web.
**Por quê:** 86% do código de channels é morto. Telegram é o mais viável (sem dependência externa).

- [ ] **11.1** Telegram — configurar bot token + webhook
  - Call path: `main.py startup` → `telegram.start()` → recebe update → `gateway.route_message(channel="telegram")`
- [ ] **11.2** Telegram — testar envio e recebimento de mensagem em produção
- [ ] **11.3** WhatsApp (Evolution API) — avaliar se vale o custo de deploy separado
  - Decisão: só implementar se houver demanda real do usuário
- [ ] **11.4** Testes E2E para channel routing

---

## FASE 12 — Audit Trail & Observabilidade ✅ CONCLUÍDA (2026-02-19)

**Objetivo:** Persistir react_steps, tool calls e decisões para debug e melhoria contínua.
**Por quê:** `react_steps` são computados no ReAct loop mas nunca salvos. Sem audit trail, não há como debugar respostas ruins.
**Ref:** `agent-claude.md` seção "Audit Trail"

- [x] **12.1** Criar tabela `audit_log` (session_id, agent, step_type, content, timestamp)
  - `migrations/022_audit_log.sql` + `src/core/audit_service.py`
- [x] **12.2** Salvar react_steps no audit_log após cada resposta
  - Call path: `gateway.route_message()` → `asyncio.create_task(audit_service.save(session_id, agent, steps, usage))`
  - `conversation_id` retornado no resultado para o frontend consultar
- [x] **12.3** Endpoints REST:
  - `GET /api/v1/audit/{session_id}` — steps de uma sessão
  - `GET /api/v1/audit` — últimas sessões com contagem
- [x] **12.4** Painel colapsável no frontend (botão "🔍 Audit" no canto inferior direito)
  - Mostra step_type (reason/act/observe/summary) com ícones e duração
  - Atualiza automaticamente após cada mensagem
- [x] **12.5** Testes E2E: `TestFase12AuditTrail` (6 passed, 1 skipped sem DB local)
- [ ] **12.6** Testar em produção (https://optimus.tier.finance)

---

## FASE 13 — Embeddings na Collective Intelligence ✅ CONCLUÍDA (2026-02-19)

**Objetivo:** Substituir busca por substring por busca semântica (PGvector) no knowledge sharing.
**Por quê:** `collective_intelligence.py` usava `in` (substring) para buscar. Com >100 entries, precisão cai drasticamente.
**Ref:** `agent-claude.md` seção "Embeddings"

- [x] **13.1** Embedding ao salvar knowledge entry
  - Call path: `collective_intelligence.async_share()` → `embedding_service.embed_text()` → `store_embedding()` → PGvector
  - Já chamado desde FASE 11: `gateway._auto_share_learning()` usa `async_share()`
- [x] **13.2** Busca por similaridade coseno (padrão agora)
  - `query_semantic()` usa `embedding_service.semantic_search()` → `SELECT ... ORDER BY embedding <=> query_vec`
  - **`semantic=True` agora é o DEFAULT** em `GET /api/v1/knowledge/query`
  - Fallback automático para keyword se PGvector indisponível
- [x] **13.3** Batch migration de entries existentes
  - `POST /api/v1/knowledge/index` → `collective_intelligence.index_knowledge()`
- [x] **13.4** Testes E2E: `TestFase13Embeddings` (9 passed, 2 skipped sem fastapi local)
- [x] **13.5** Testado em produção ✅ (2026-02-19)
  - "como validar dados em API" → FastAPI/Pydantic (similarity=0.86)
  - "busca semantica postgres" → PGvector entry (similarity>0.5)
  - Keyword fallback (`semantic=false`) continua funcional
  - Bugs corrigidos: SDK google-genai, modelo gemini-embedding-001, CAST vector, json.dumps metadata

---

## FASE 14 — Temporal Memory & Decay ✅ CONCLUÍDA

**Objetivo:** Implementar decaimento temporal na memória para que conhecimento obsoleto perca relevância.
**Por quê:** Memória acumula sem limite. Informações de 6 meses atrás têm mesmo peso que de hoje.
**Ref:** `agent-claude.md` seção "Temporal Decay"

- [x] **14.1** Adicionar `last_accessed_at`, `access_count` e `archived` na tabela `embeddings`
  - Migration: `migrations/023_embeddings_temporal.sql`
- [x] **14.2** Score de relevância: `similarity * recency_factor * access_factor`
  - `recency_factor = exp(-LAMBDA * days_since_access)` (LAMBDA=0.01, half-life~69 dias)
  - `access_factor = min(2.0, 1.0 + 0.1 * access_count)`
  - Implementado em `src/core/decay_service.py`
- [x] **14.3** Cron job semanal para arquivar entries com score < 0.05
  - Handler: `src/engine/decay_handlers.py` → `on_decay_archiving_triggered`
  - Agendado em `lifespan()` via `_schedule_decay_archiving(cron_scheduler)` (every 168h)
  - `semantic_search()` atualizado: filtra `archived=FALSE`, re-rank por `final_score`, fire-and-forget `record_access()`
- [x] **14.4** Testes E2E — 18/18 passando (`TestFase14TemporalDecay`)
- [ ] **14.5** Testar em produção (deploy automático via push)

---

## FASE 15 — Contradiction Detection ✅ CONCLUÍDA

**Objetivo:** Detectar quando novo conhecimento contradiz conhecimento existente.
**Por quê:** Sem detecção, agente pode ter informações conflitantes e dar respostas inconsistentes.
**Ref:** `agent-claude.md` seção "Contradiction Detection"

- [x] **15.1** Ao salvar novo knowledge, buscar top-5 similares (coseno >= 0.8)
  - `contradiction_service._find_similar()` → `embedding_service.semantic_search(threshold=0.8)`
- [x] **15.2** LLM classifica relação: `complementary | update | contradiction`
  - Prompt para `LLM_FALLBACK_MODEL` (Gemini Flash) → parse `CLASSIFICACAO | explicacao`
  - Graceful fallback: se LLM falhar → retorna `None` (nao bloqueia o save)
  - Implementado em `src/core/contradiction_service.py`
- [x] **15.3** Se contradiction: HTTP 409 com detalhes; `force=True` bypassa
  - Call path: `async_share(force=False)` → `contradiction_service.check()` → `raise ContradictionDetected` → `knowledge.py` → HTTP 409
  - `POST /api/v1/knowledge/share?force=true` para salvar mesmo assim
- [x] **15.4** Testes E2E — 14/14 passando (`TestFase15ContradictionDetection`)
- [ ] **15.5** Testar em producao (deploy automatico via push)

---

## FASE 16 — Proactive Insights ✅ CONCLUÍDA

**Objetivo:** Agente sugere ações baseado em padrões detectados (não apenas responde).
**Por quê:** Transforma o agente de reativo para proativo — diferencial competitivo.
**Ref:** `agent-claude.md` seção "Proactive"

- [x] **16.1** Bridging research → notification_service (usuário agora vê os findings)
  - Call path: `cron "proactive_research"` → `on_research_cron_triggered()` → `proactive_researcher.run_check_cycle()` → se relevance >= 0.7 → `notification_service.send(target_agent="optimus", type="system")` → toast no frontend
  - Implementado em `src/engine/research_handlers.py` (FASE 16)
- [x] **16.2** Fontes de insights internas agregadas
  - `intent_predictor` — padrões comportamentais por dia/hora (já existia)
  - `proactive_researcher` briefing files — findings de hoje/ontem (🔴 e 🟡)
  - `long_term_memory` — últimas 3 entradas de alta relevância (últimos 7 dias)
  - Implementado em `src/engine/insights_service.py` (`InsightsService.get_insights()`)
- [x] **16.3** Suggestion chips no frontend (já existia, agora alimentado pelo InsightsService)
  - `GET /api/v1/autonomous/suggestions` → usa `insights_service.get_insights()` (antes: só `intent_predictor`)
  - Frontend renderiza chips clicáveis que pre-preenchem o input (FASE 11, já funcionava)
  - Resposta agora inclui campo `type` (pattern | research | learning)
- [x] **16.4** Testes E2E — 14/14 passando (`TestFase16ProactiveInsights`)
- [ ] **16.5** Testar em produção (deploy automático via push)

---

## FASE 17 — Prompt Engineering Avançado ✅

**Objetivo:** Aplicar técnicas de `prompt-avancado.md` e `Prompt-COT.md` no system prompt e ReAct loop.
**Por quê:** Melhora qualidade das respostas sem custo de infra.
**Status:** CONCLUÍDA — 2026-02-19

- [x] **17.1** Chain-of-Thought explícito no system prompt (`### Processo de Raciocínio` com 4 passos obrigatórios)
- [x] **17.2** Few-shot examples para `db_query` (SQL correto), `browser` (navegação estruturada), `research_search` (query específica)
- [x] **17.3** Output primers por tipo de tarefa: análise técnica, plano, pesquisa, código
- [x] **17.4** Delimiters `---` e `###` em `_build_system_prompt()` + `_build_user_content()`
- [ ] **17.5** Validar melhoria em produção (testes A/B manuais — comparar respostas antes/depois)

**Arquivos modificados:**
- `src/agents/base.py` — `_build_system_prompt()` com CoT, few-shot, primers, delimiters
- `src/engine/react_loop.py` — `_build_user_content()` com `###` headers e `---` separator
- `tests/test_e2e.py` — `TestFase17PromptEngineering` (15/15 ✅)

---

## FASE 18 — User Profile & Settings Completo ✅

**Objetivo:** Completar perfil do usuário com avatar, preferências e configurações do agente.
**Por quê:** `planning-optimus.md` item 2 — onboarding personalizado.
**Status:** CONCLUÍDA — 2026-02-19

- [x] **18.1** Gravatar fallback (MD5 inline + `setAvatarGravatar()` com fallback para iniciais)
- [x] **18.2** Alteração de senha (`PUT /api/v1/user/password` com verificação da senha atual)
- [x] **18.3** Configurações do agente: nome, tom de voz, idioma preferido (já existia)
- [x] **18.4** Persistir preferências no PostgreSQL (migration `014_user_preferences.sql` — já existia)
- [x] **18.5** Carregar preferências no session bootstrap (já existia em `main.py`)
- [x] **18.6** Testes E2E (14/14 ✅) + deploy

**Arquivos modificados:**
- `src/api/user_profile.py` — `ChangePasswordRequest` + `PUT /password` endpoint
- `src/static/settings.html` — MD5 + Gravatar fallback, seção "Alterar senha" + `changePassword()`
- `tests/test_e2e.py` — `TestFase18UserProfile` (14/14 ✅)

---

## FASE 19 — VPS & PWA (Completar)

**Objetivo:** Finalizar deploy em VPS próprio e PWA para mobile.
**Por quê:** `roadmap-optimus-v2.md` FASE 7 — parcialmente concluído.
**Ref:** `planning-optimus.md` item 7 — "estar em todo lugar"

- [ ] **19.1** PWA manifest + service worker para cache offline
- [ ] **19.2** Push notifications via web push API
- [ ] **19.3** Testar instalação PWA em Android e iOS
- [ ] **19.4** Otimizar para mobile (responsive, touch-friendly)

---

## FASE 20 — Browser Streaming (Completar)

**Objetivo:** Streaming visual do browser automation para o usuário.
**Por quê:** `roadmap-optimus-v2.md` FASE 2C — planejado mas não implementado.

- [ ] **20.1** CDP screenshots periódicos durante navegação
- [ ] **20.2** Stream via SSE para o frontend
- [ ] **20.3** UI: janela de preview do browser no chat
- [ ] **20.4** Testes E2E + produção

---

## FASE 21 — Integração de Módulos Órfãos ✅ PARCIAL

**Objetivo:** Integrar módulos que existiam mas não eram chamados no fluxo real.
**Análise (2026-02-19):** Diagnóstico inicial estava errado — nenhum módulo deve ser deletado. Todos têm valor, precisavam apenas ser conectados.

### Diagnóstico real por módulo:

| Módulo | Status Real | Integração | Próxima Ação |
|--------|-------------|-----------|--------------|
| `intent_classifier.py` | ✅ Integrado 100% | gateway.py:191 + smart routing FASE 21 | Nenhuma |
| `intent_predictor.py` | ✅ Integrado 80% | gateway.py: prediction chips na resposta | Frontend renderizar suggestions |
| `autonomous_executor.py` | ✅ Integrado 100% | react_loop.py:277-303 | Nenhuma |
| `rag.py` | ✅ Integrado 80% | gateway.py: auto-context para research/analysis | Auto-ingest de uploads |
| `webchat.py` | ✅ Integrado 100% | main.py:227, APIs 583-642 | Nenhuma |
| `voice_interface.py` | ✅ Integrado 100% | api/voice.py (todos endpoints) | Nenhuma |
| `reflection_engine.py` | ⚠️ 0% | Nunca chamado | INTEGRAR: cron semanal |
| `working_memory.py` | ⚠️ 0% | Nunca chamado | INTEGRAR: session context |
| `tools_manifest.py` | ⚠️ 0% | Nunca chamado | INTEGRAR: startup |
| `cron_scheduler.py` | ⚠️ 0% | Framework sem jobs | INTEGRAR: registrar jobs |
| `context_awareness.py` | ⚠️ 0% | Nunca chamado | INTEGRAR: session bootstrap |
| `security.py` | ⚠️ 20% | Import mas sem enforcement | INTEGRAR: gateway |

### O que foi integrado nesta sessão (2026-02-19):
- [x] **21.1** `intent_classifier.py` — Smart routing: quando confidence > 0.5, mensagens de code → `friday`, research → `fury`
  - Call path: `gateway.route_message()` linha ~283 → `AgentFactory.get(suggested_agent)`
- [x] **21.2** `intent_predictor.py` — Suggestion chips: padrões aprendidos viram sugestões proativas na resposta
  - Call path: `gateway.route_message()` linha ~340 → `predict_next()` → `result["suggestions"]`
- [x] **21.3** `rag.py` — RAG auto-context: queries de research/analysis enriquecem contexto automaticamente
  - Call path: `gateway.route_message()` linha ~261 → `rag_pipeline.augment_prompt()` → `context["rag_context"]`
  - Renderizado pelo `react_loop.py` em `_build_user_content()`

### Também já integrados (descobertos nesta sessão):
- [x] **21.4** `reflection_engine.py` — JÁ INTEGRADO (main.py:184 → reflection_handlers.py → cron weekly_reflection)
- [x] **21.6** `tools_manifest.py` — Módulo não existe; ignorado
- [x] **21.8** `security.py` — JÁ INTEGRADO (react_loop.py:252 → check_permission(MCP_EXECUTE) por tool call)

### Integrado nesta sessão (itens 21.5, 21.7, 21.9):
- [x] **21.5** `working_memory.py` — WORKING.md carregado em `context["working_memory"]` no gateway
  - Call path: `gateway.route_message()` → `wm_service.load(agent_name)` → `context["working_memory"]`
  - react_loop.py `_build_user_content()` já injetava se presente (checkpoint✓)
- [x] **21.7** `context_awareness.py` — Contexto de tempo/dia injetado em `context["time_context"]`
  - Call path: `gateway.route_message()` → `ContextAwareness().build_context()` → `context["time_context"]`
  - Injetado no prompt via react_loop.py `_build_user_content()` como linha de contexto
  - Exemplo: `[Boa tarde, 14:30 — sexta-feira. Sexta-feira! 🎉 Vamos fechar a semana. Algo para deploy?]`
- [x] **21.9** Frontend: chips renderizados após cada resposta que inclua `suggestions`
  - `data?.data?.suggestions` → `renderSuggestionChips()` → chips clicáveis preenchem o input

## FASE 21 — ✅ CONCLUÍDA (2026-02-19)

---

## FASE 22 — Redis Otimizado

**Objetivo:** Usar Redis para o que foi projetado — session cache e pub/sub.
**Por quê:** Redis está conectado mas subutilizado (só rate limiting).

- [ ] **22.1** Session cache: últimas 5 sessões ativas no Redis (TTL 30min)
- [ ] **22.2** Pub/Sub para notificações real-time entre workers
- [ ] **22.3** Cache de embeddings frequentes (top 100 queries)
- [ ] **22.4** Testes E2E + produção

---

## FASE 23 — Acesso à Máquina do Usuário

**Objetivo:** Permitir que o agente interaja com o computador do usuário (com autorização).
**Por quê:** `planning-optimus.md` item 5 — "ter acesso a tudo".

- [ ] **23.1** Avaliar arquitetura: CLI local + API bridge vs browser extension
- [ ] **23.2** MVP: CLI que conecta ao AgentOptimus via WebSocket
- [ ] **23.3** Permissões granulares (filesystem read, write, execute)
- [ ] **23.4** Sandbox de segurança (whitelist de comandos/paths)
- [ ] **23.5** Testes controlados antes de produção

---

## FASE 24 — Voice Assistant (Alexa/Siri-like)

**Objetivo:** Wake word + voice always-on.
**Por quê:** `planning-optimus.md` item 6 — "funcionar como Alexa/Siri".

- [ ] **24.1** Wake word detection no frontend (Web Speech API ou Picovoice)
- [ ] **24.2** Modo "always listening" com indicador visual
- [ ] **24.3** Resposta por voz automática (sem precisar clicar)
- [ ] **24.4** Testes em Chrome/Firefox/Safari

---

## FASE 25 — Intelligence Engine Real (ToT + Uncertainty)

**Objetivo:** Conectar `tot_engine.py` e `uncertainty.py` ao fluxo real de conversas.
**Por quê:** Ambos existem mas nunca são chamados. Estado Atual marcava como ✅ mas são stubs funcionais sem integração real.
**Evidência do gap:** `roadmap-optimus-v2.md` Bloco 5 — "NUNCA chamado. Nenhum agente chama think() durante conversa real."

- [ ] **25.1** Conectar `tot_engine.think()` ao `react_loop.py` para queries marcadas como complexas
  - Call path: `react_loop.process()` → detecta query complexa → `tot_service.think(query)` → injeta pre-reasoning no prompt
  - Critério de ativação: `is_complex_query()` já existe em `react_loop.py`
- [ ] **25.2** Substituir heurística de uncertainty pelo `UncertaintyQuantifier` real
  - Call path: `gateway.route_message()` → resposta gerada → `uncertainty.quantify(response, context)` → score real
  - Se score > threshold → adicionar 🔴 warning (atualmente calculado por regex simples)
- [ ] **25.3** Testes E2E — `TestFase25IntelligenceReal`
- [ ] **25.4** Testar em produção

---

## FASE 26 — Web Research Real (Tavily)

**Objetivo:** Substituir o stub `research_search` por chamada real à API Tavily.
**Por quê:** `research_search` em `mcp_tools.py` retorna mock. Estado Atual marcava "Web Research (Tavily) ✅" incorretamente.
**Evidência do gap:** `roadmap-optimus-v2.md` Bloco 6 — "research ❌ É um stub. Nenhuma API real integrada."

- [ ] **26.1** Integrar Tavily API em `mcp_tools.py`
  - Call path: `react_loop` → tool `research_search(query)` → `tavily_client.search(query)` → resultados reais
  - Graceful fallback: sem `TAVILY_API_KEY` → log warning + retorna mock (comportamento atual)
- [ ] **26.2** Adicionar `TAVILY_API_KEY` ao `config.py` e ao Coolify
- [ ] **26.3** Testes E2E — `TestFase26WebResearch`
- [ ] **26.4** Testar em produção

---

## FASE 27 — Agentic RAG Nativo

**Objetivo:** Conectar `rag.py` ao fluxo principal de forma transparente.
**Por quê:** `rag.py` existe e foi parcialmente conectado (FASE 21), mas o fluxo ainda usa `knowledge_tool` separado. O RAG deveria enriquecer automaticamente o contexto de qualquer query relevante.
**Evidência do gap:** `roadmap-optimus-v2.md` Bloco 4 — "Agentic RAG ⚠️ Parcial — rag.py existe mas é órfão."

- [ ] **27.1** Auto-ingest de uploads: ao receber PDF/CSV via multimodal, indexar automaticamente no PGvector
  - Call path: `files_service.process()` → `rag_pipeline.ingest(content, source)` → `embedding_service.store_embedding()`
- [ ] **27.2** Garantir que RAG augmentation está ativa para todos os intents relevantes (research, analysis, qa)
  - Verificar integração existente de FASE 21 e corrigir se necessário
- [ ] **27.3** Testes E2E — `TestFase27RAGNativo`
- [ ] **27.4** Testar em produção

---

## FASE 28 — Plugins MCP & Skills Auto-install

**Objetivo:** Ativar o sistema de plugins MCP e o auto-install de skills.
**Por quê:** `workspace/plugins/` está vazia. `skills_discovery.py` faz busca mas não instala. `tools_manifest.py` nunca gera TOOLS.md.
**Evidência do gap:** `roadmap-optimus-v2.md` Bloco 6 — "Plugin MCP ❌ pasta vazia. Skills auto-install ❌."

- [ ] **28.1** Criar pelo menos 1 plugin MCP de exemplo em `workspace/plugins/`
  - Estrutura: arquivo `.py` com `def register_tools() -> list[MCPTool]:`
  - Call path: `main.py startup` → `mcp_plugin.load_plugins()` → tools registradas no registry
- [ ] **28.2** Gerar `workspace/TOOLS.md` via `tools_manifest.py` no startup
  - Call path: `main.py startup` → `tools_manifest.generate()` → `workspace/TOOLS.md` (lista de tools disponíveis)
- [ ] **28.3** `skills_discovery.py` — ao encontrar skill compatível, instalar automaticamente (com confirmação do usuário)
- [ ] **28.4** Testes E2E — `TestFase28Plugins`
- [ ] **28.5** Testar em produção

---

## FASE 29 — Webhooks & Presence

**Objetivo:** Receber eventos externos (GitHub, Forms) e implementar status de presença.
**Por quê:** Nenhum WebhookReceiver ativo. Presence (online/offline) não existe.
**Evidência do gap:** `roadmap-optimus-v2.md` Bloco 1 — "Webhooks ❌". Bloco 2 — "Presence ❌."

- [ ] **29.1** Webhook receiver genérico
  - Call path: `POST /api/v1/webhooks/{source}` → valida secret → `event_bus.emit(WEBHOOK_RECEIVED, payload)` → handler processa
  - Sources iniciais: `github` (push/PR events), `generic` (qualquer JSON)
- [ ] **29.2** Presence: status online/offline por usuário
  - SSE heartbeat a cada 30s → atualiza `last_seen` no Redis (TTL 60s) → `GET /api/v1/presence/{user_id}`
- [ ] **29.3** Testes E2E — `TestFase29Webhooks`
- [ ] **29.4** Testar em produção

---

## FASE 30 — Eval CI & Debug Web UI

**Objetivo:** Integrar `eval_runner.py` ao CI e construir painel de debug da orquestração.
**Por quê:** `eval_runner.py` existe mas não está no CI. Debug Web UI prometido pelo Google ADK nunca foi construído.
**Evidência do gap:** `roadmap-optimus-v2.md` Bloco 3 — "Evaluation ⚠️ Parcial. Debug Web UI ❌."

- [ ] **30.1** Integrar `eval_runner.py` ao pipeline CI (GitHub Actions ou Coolify hooks)
  - Rodar suite de avaliação a cada push para `main`
  - Métricas: acurácia de tool calling, taxa de fallback, latência P95
- [ ] **30.2** Debug Web UI — painel em `/debug` (protegido por auth admin)
  - Visualizar: pipelines de orquestração ativos, fila de cron jobs, últimas 10 sessões de audit
  - Dados já existem: `audit_log`, `cron_scheduler.list_jobs()`, `decay_service.get_stats()`
- [ ] **30.3** Testes E2E — `TestFase30EvalDebug`
- [ ] **30.4** Testar em produção

---

## FASE 31 — Security Hardening (Argon2id + Secrets Guardrail)

**Objetivo:** Elevar segurança de senhas para padrão enterprise e bloquear boot com segredos fracos.
**Por quê:** SHA-256 é rápido demais para passwords — GPU quebra em segundos. Argon2id é o padrão OWASP. Bloqueador para venda enterprise e SOC2.
**Fonte:** `avaliacao-brutal-unicornio.md` P0 — "Password Hardening + Secrets Guardrail"
**Prazo sugerido:** 2 semanas

- [ ] **31.1** Migrar hashing de `SHA-256 + salt manual` para `Argon2id`
  - Instalar `argon2-cffi` no `requirements.txt`
  - Atualizar `auth_service._hash_password()` e `_verify_password()` para Argon2id
  - Migração progressiva: novos logins já em Argon2id; hashes antigos detectados pelo prefixo e migrados no próximo login
  - Call path: `auth_service.login()` → detecta hash antigo → rehashar → salvar
- [ ] **31.2** Secrets Guardrail — bloquear boot com JWT_SECRET default ou fraco
  - Check em `main.py` lifespan startup: `if settings.JWT_SECRET == "CHANGE-ME..." → raise RuntimeError`
  - Também bloquear se len(secret) < 32
- [ ] **31.3** Auth Observability — métricas básicas de autenticação
  - Contador de falhas de login por IP (Redis, TTL 1h)
  - Log estruturado: `login_failed`, `token_refresh_invalid`, `api_key_invalid`
  - `GET /api/v1/auth/metrics` (admin only) — total de falhas últimas 24h
- [ ] **31.4** Testes E2E — `TestFase31SecurityHardening`
- [ ] **31.5** Testar em produção

---

## FASE 32 — Agent Scorecard & Métricas

**Objetivo:** Medir sistematicamente se os agents estão funcionando bem.
**Por quê:** Sem métricas, qualquer "melhora" é impressão subjetiva. Blockeador para escala e confiança operacional.
**Fonte:** `avaliacao-brutal-unicornio.md` P0 — "Scorecard por agent + métricas mínimas"
**Prazo sugerido:** 2 semanas

- [ ] **32.1** Coletar métricas por agent em cada interação
  - KPIs: `success_rate` (sem fallback), `fallback_rate`, `latency_p95`, `cost_per_success`, `tool_error_rate`
  - Call path: `react_loop.process()` → ao final → `scorecard_service.record(agent, metrics)`
  - Tabela: `agent_metrics (agent_name, metric_name, value, recorded_at)`
  - Migration: `migrations/024_agent_metrics.sql`
- [ ] **32.2** Endpoint de scorecard
  - `GET /api/v1/metrics/agents` — score atual de cada agent (últimas 24h / 7d)
  - `GET /api/v1/metrics/agents/{name}` — histórico por agent
- [ ] **32.3** Painel básico no frontend (admin)
  - Tabela de agents com: success_rate, fallback_rate, latência média, custo médio
  - Atualiza a cada 60s
- [ ] **32.4** Alertas internos quando `fallback_rate > 10%` em intents cobertos
- [ ] **32.5** Testes E2E — `TestFase32AgentScorecard`
- [ ] **32.6** Testar em produção

---

## FASE 33 — Routing Policy Declarativa

**Objetivo:** Extrair regras de roteamento de agent para arquivo/serviço declarativo.
**Por quê:** Regras de roteamento estão dispersas em código. Dificulta auditoria, A/B testing e evolução.
**Fonte:** `avaliacao-brutal-unicornio.md` P1 — "Routing Policy v1 (declarativa)"
**Prazo sugerido:** 3 semanas

- [ ] **33.1** Criar `src/core/routing_policy.py` — serviço declarativo de routing
  - Regras em YAML/JSON: `{intent: "code", agent: "friday", confidence_min: 0.6}`
  - Carregar de `workspace/routing_policy.yaml`
  - Call path: `gateway.route_message()` → `routing_policy.resolve(intent, confidence)` → agent
- [ ] **33.2** Migrar regras hardcoded do gateway para o arquivo de política
- [ ] **33.3** Métrica de precisão: `routing_precision@intent` (avaliado via `eval_runner`)
  - Meta: `routing_precision >= 85%` em suite de avaliação fixa
- [ ] **33.4** Testes E2E — `TestFase33RoutingPolicy`
- [ ] **33.5** Testar em produção

---

## FASE 34 — Resilience SDK (Retry + Circuit Breaker)

**Objetivo:** Retry exponencial + circuit breaker + timeout padronizado para todas as integrações.
**Por quê:** Integrações falham silenciosamente ou com timeout longo. UX degradada e difícil debug.
**Fonte:** `avaliacao-brutal-unicornio.md` P1 — "Padrão Resilience SDK"
**Prazo sugerido:** 4 semanas

- [ ] **34.1** Criar `src/infra/resilience.py` — decorator `@resilient(retries=3, backoff=2, timeout=10, circuit_breaker=True)`
  - Retry exponencial com jitter
  - Circuit breaker: abre após 5 falhas em 60s, fecha após 30s
  - Timeout configurável por integração
- [ ] **34.2** Aplicar nos top-3 conectores mais críticos: Gmail API, IMAP/SMTP, modelo LLM
  - Call path: decorar handlers em `google_oauth_service.py`, `imap_service.py`, `model_router.py`
- [ ] **34.3** Métricas de resiliência: `circuit_open_count`, `retry_count`, `timeout_count`
  - Integrado ao scorecard da FASE 32
- [ ] **34.4** Testes E2E — `TestFase34Resilience`
- [ ] **34.5** Testar em produção

---

## FASE 35 — A2A Reliability (Fila Persistente + DLQ)

**Objetivo:** Migrar A2A de REST in-memory para fila persistente com retry e DLQ.
**Por quê:** Delegações A2A se perdem em restart. Sem replay e idempotência, falhas são silenciosas.
**Fonte:** `avaliacao-brutal-unicornio.md` P1 — "A2A com fila persistente + DLQ"
**Prazo sugerido:** 4–6 semanas

- [ ] **35.1** Substituir A2A REST direto por Redis Streams como transporte
  - Producer: `a2a_protocol.delegate()` → `XADD a2a_tasks *`
  - Consumer: worker em background → `XREADGROUP` → processa → ACK
  - Call path: `gateway.route_message()` → `a2a_protocol.delegate(task)` → Redis Stream
- [ ] **35.2** Idempotência: cada task tem `task_id` único; duplicatas ignoradas
- [ ] **35.3** DLQ: tasks que falham 3x vão para `a2a_dlq` stream
  - `GET /api/v1/a2a/dlq` — lista tasks em dead letter (admin)
  - Reprocessar manualmente via `POST /api/v1/a2a/dlq/{id}/retry`
- [ ] **35.4** Testes E2E — `TestFase35A2AReliability`
- [ ] **35.5** Testar em produção

---

## FASE 36 — SLOs + Load Testing + Runbooks

**Objetivo:** Definir e monitorar SLOs, executar load testing recorrente e criar runbooks de incidente.
**Por quê:** Sem SLOs, não há contrato de qualidade. Sem load testing, capacidade é desconhecida. Bloqueador enterprise.
**Fonte:** `avaliacao-brutal-unicornio.md` P2 — "SLOs oficiais + Load Testing + Incidente e recuperação"
**Prazo sugerido:** 3 semanas

- [ ] **36.1** Definir SLOs oficiais
  - API chat: `availability >= 99.5%`, `latency p95 <= 2.5s` (sem tool externa)
  - Healthcheck endpoint já existe: `GET /health`
  - Implementar `GET /api/v1/slo/status` — calcula SLO atual das últimas 24h com dados do audit_log
- [ ] **36.2** Load testing automatizado
  - Script `tests/load_test.py` com locust ou k6: cenários 50, 100, 200 usuários concorrentes
  - Rodar semanalmente via cron (ou CI) — relatório salvo em `workspace/reports/load-{date}.json`
- [ ] **36.3** Runbooks de incidente (documentação)
  - `docs/runbooks/db-down.md` — PostgreSQL indisponível
  - `docs/runbooks/redis-down.md` — Redis indisponível
  - `docs/runbooks/llm-quota.md` — quota de LLM esgotada
- [ ] **36.4** Testes E2E — `TestFase36SLOs`
- [ ] **36.5** Testar em produção

---

## Priorização Recomendada

| Prioridade | Fase | Impacto | Esforço |
|-----------|------|---------|---------|
| **P0** | FASE 10 — Chat Commands | Alto (funcionalidade existente, só conectar) | Baixo |
| **P0** | FASE 21 — Limpeza Código Morto | Alto (reduz complexidade) | Médio |
| **P1** | FASE 12 — Audit Trail | Alto (debug + melhoria contínua) | Médio |
| **P1** | FASE 13 — Embeddings CI | Alto (qualidade do knowledge) | Baixo |
| **P1** | FASE 25 — Intelligence Real (ToT+Uncertainty) | Alto (corrige falso ✅, impacto direto na qualidade) | Médio |
| **P1** | FASE 26 — Web Research Real (Tavily) | Alto (corrige falso ✅, pesquisa funcional) | Baixo |
| **P1** | FASE 17 — Prompt Engineering | Alto (qualidade sem custo) | Baixo |
| **P2** | FASE 27 — Agentic RAG Nativo | Alto (uploads indexados automaticamente) | Médio |
| **P2** | FASE 14 — Temporal Decay | Médio (relevância da memória) | Médio |
| **P2** | FASE 18 — User Profile | Médio (UX) | Baixo |
| **P2** | FASE 19 — PWA | Médio (mobile access) | Médio |
| **P2** | FASE 11 — Telegram | Médio (novo canal) | Médio |
| **P3** | FASE 15 — Contradiction | Médio (consistência) | Médio |
| **P3** | FASE 16 — Proactive | Alto (diferencial) | Alto |
| **P3** | FASE 28 — Plugins MCP & Skills | Médio (extensibilidade) | Médio |
| **P3** | FASE 29 — Webhooks & Presence | Médio (integrações externas) | Médio |
| **P3** | FASE 20 — Browser Streaming | Baixo (nice-to-have) | Médio |
| **P3** | FASE 22 — Redis | Médio (performance) | Médio |
| **P0** | FASE 31 — Security Hardening (Argon2id) | Alto (segurança real dos usuários) | Médio |
| **P0** | FASE 32 — Agent Scorecard & Métricas | Alto (voar sem instrumentos → voar com) | Médio |
| **P1** | FASE 34 — Resilience SDK | Alto (integrações param silenciosamente) | Alto |
| **P1** | FASE 33 — Routing Policy Declarativa | Médio (routing hoje funciona, mas frágil) | Médio |
| **P2** | FASE 36 — SLOs + Load Testing | Alto (exigência enterprise) | Médio |
| **P2** | FASE 35 — A2A Reliability (Redis Streams) | Médio (só importa com volume A2A real) | Alto |
| **P4** | FASE 30 — Eval CI & Debug UI | Médio (qualidade de engenharia) | Médio |
| **P4** | FASE 23 — Máquina do Usuário | Alto (ambicioso) | Alto |
| **P4** | FASE 24 — Voice Assistant | Médio (UX avançado) | Alto |

---

## Decisões Arquiteturais (NÃO fazer)

| Proposta | Decisão | Motivo |
|----------|---------|--------|
| Migrar para Google ADK | **NÃO** | Implementação custom é feature-complete, migração seria rewrite sem valor |
| Migrar para Agno | **NÃO** | Mesmo motivo. AgentFactory + BaseAgent atendem. |
| Graph DB (Neo4j) | **NÃO** | PostgreSQL + PGvector resolve. Complexidade não justificada. |
| Self-hosted LLM | **NÃO** | Custo de GPU > custo de API. Sem escala que justifique. |
| LangChain/LangGraph | **NÃO** | ReAct loop custom funciona. Adicionar framework = dependência sem ganho. |
| Supabase Realtime | **AVALIAR DEPOIS** | Só se polling se tornar gargalo mensurável. |

---

## Referências

- [planning-optimus.md](.docs/planning-optimus.md) — Visão do usuário e requisitos de produto
- [Roadmap-Optimus.md](.docs/Roadmap-Optimus.md) — Roadmap original (fases 1-23) + Regra de Ouro + Diagnóstico
- [roadmap-optimus-v2.md](.docs/roadmap-optimus-v2.md) — Roadmap v2 detalhado (FASE 0-9) + Análise de gaps
- [agent-claude.md](.docs/agent-claude.md) — Pesquisa de arquitetura + recomendações técnicas
- [prompt-avancado.md](.docs/prompt-avancado.md) — Técnica Syntopic Reading para prompts
- [Prompt-COT.md](.docs/Prompt-COT.md) — 26 princípios de prompt engineering
