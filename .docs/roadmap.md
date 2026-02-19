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
- [x] Web Research (Tavily)
- [x] Browser Automation (Playwright/CDP)
- [x] Dynamic Agents (criação sob demanda)
- [x] Google OAuth + IMAP/SMTP (email)
- [x] Memory Sync to DB
- [x] Apple iCloud integration
- [x] Multimodal Input (imagens, áudio, PDF, CSV)
- [x] Onboarding + Settings page
- [x] A2A Protocol (API REST)
- [x] Collective Intelligence (cross-agent learning)
- [x] ToT Engine conectado (pre-reasoning no ReAct loop)
- [x] UncertaintyQuantifier conectado (🔴 warning no gateway)

---

## FASE 10 — Chat Commands & Thread System

**Objetivo:** Conectar `chat_commands.py` e `thread_manager.py` ao fluxo principal.
**Por quê:** 9 comandos implementados (`/status`, `/think`, `/agents`, `/task`, `/learn`, etc.) mas NUNCA chamados pelo endpoint `/api/v1/chat`. Thread manager órfão.

- [ ] **10.1** Interceptar mensagens com `/` no gateway antes de enviar ao agent
  - Call path: `gateway.route_message()` → detecta prefixo `/` → `chat_commands.handle()`
- [ ] **10.2** Conectar thread_manager ao task_manager
  - Call path: `chat_commands /task` → `task_manager.create()` → `thread_manager.subscribe()`
- [ ] **10.3** Conectar notification_service ao frontend via SSE
  - Call path: `notification_service.notify()` → SSE push → frontend toast
- [ ] **10.4** Testes E2E: enviar `/status` via API e validar resposta formatada
- [ ] **10.5** Testar em produção

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

## FASE 12 — Audit Trail & Observabilidade

**Objetivo:** Persistir react_steps, tool calls e decisões para debug e melhoria contínua.
**Por quê:** `react_steps` são computados no ReAct loop mas nunca salvos. Sem audit trail, não há como debugar respostas ruins.
**Ref:** `agent-claude.md` seção "Audit Trail"

- [ ] **12.1** Criar tabela `audit_log` (session_id, agent, step_type, content, timestamp)
  - Migration SQL + modelo SQLAlchemy
- [ ] **12.2** Salvar react_steps no audit_log após cada resposta
  - Call path: `gateway.route_message()` → resultado do agent → `audit_service.save(react_steps)`
- [ ] **12.3** Endpoint GET `/api/v1/audit/{session_id}` para consultar histórico
- [ ] **12.4** Dashboard simples no frontend (colapsável, para debug)
- [ ] **12.5** Testes E2E + produção

---

## FASE 13 — Embeddings na Collective Intelligence

**Objetivo:** Substituir busca por substring por busca semântica (PGvector) no knowledge sharing.
**Por quê:** `collective_intelligence.py` usa `in` (substring) para buscar conhecimento. Com >100 entries, precisão cai drasticamente.
**Ref:** `agent-claude.md` seção "Embeddings"

- [ ] **13.1** Gerar embedding (768d) ao salvar knowledge entry
  - Call path: `collective_intelligence.share_knowledge()` → `embedding_service.embed()` → INSERT com vector
- [ ] **13.2** Busca por similaridade coseno ao consultar
  - Call path: `collective_intelligence.get_relevant_knowledge()` → `SELECT ... ORDER BY embedding <=> query_vec LIMIT 5`
- [ ] **13.3** Migrar entries existentes (batch embedding)
- [ ] **13.4** Testes E2E: compartilhar knowledge + buscar semanticamente
- [ ] **13.5** Testar em produção

---

## FASE 14 — Temporal Memory & Decay

**Objetivo:** Implementar decaimento temporal na memória para que conhecimento obsoleto perca relevância.
**Por quê:** Memória acumula sem limite. Informações de 6 meses atrás têm mesmo peso que de hoje.
**Ref:** `agent-claude.md` seção "Temporal Decay"

- [ ] **14.1** Adicionar `last_accessed_at` e `access_count` nas tabelas de knowledge/memory
- [ ] **14.2** Score de relevância: `similarity * recency_factor * access_factor`
  - `recency_factor = exp(-lambda * days_since_access)`
- [ ] **14.3** Cron job semanal para arquivar entries com score < threshold
- [ ] **14.4** Testes E2E
- [ ] **14.5** Testar em produção

---

## FASE 15 — Contradiction Detection

**Objetivo:** Detectar quando novo conhecimento contradiz conhecimento existente.
**Por quê:** Sem detecção, agente pode ter informações conflitantes e dar respostas inconsistentes.
**Ref:** `agent-claude.md` seção "Contradiction Detection"

- [ ] **15.1** Ao salvar novo knowledge, buscar top-5 similares (coseno > 0.8)
- [ ] **15.2** Usar LLM para classificar: `complementary | update | contradiction`
- [ ] **15.3** Se contradiction: notificar usuário, pedir resolução antes de salvar
- [ ] **15.4** Testes E2E
- [ ] **15.5** Testar em produção

---

## FASE 16 — Proactive Insights

**Objetivo:** Agente sugere ações baseado em padrões detectados (não apenas responde).
**Por quê:** Transforma o agente de reativo para proativo — diferencial competitivo.
**Ref:** `agent-claude.md` seção "Proactive"

- [ ] **16.1** Conectar `proactive_researcher.py` ao cron (1x/dia)
  - Call path: `cron_scheduler` → `proactive_researcher.check_patterns()` → `notification_service.notify()`
- [ ] **16.2** Fonte de dados: emails recentes, tarefas pendentes, calendar
- [ ] **16.3** Apresentar como "suggestion chips" no frontend
- [ ] **16.4** Testes E2E
- [ ] **16.5** Testar em produção

---

## FASE 17 — Prompt Engineering Avançado

**Objetivo:** Aplicar técnicas de `prompt-avancado.md` e `Prompt-COT.md` no system prompt e ReAct loop.
**Por quê:** Melhora qualidade das respostas sem custo de infra.

- [ ] **17.1** Chain-of-Thought explícito no system prompt dos agents
  - Adicionar instrução "Pense passo a passo antes de responder" no SOUL.md template
- [ ] **17.2** Few-shot examples no prompt de tools complexas (db_query, browser)
- [ ] **17.3** Output primers — terminar prompt com início da resposta esperada
- [ ] **17.4** Delimiters claros (###, ```) para separar contexto/instrução/exemplos
- [ ] **17.5** Validar melhoria com testes A/B em produção (comparar respostas antes/depois)

---

## FASE 18 — User Profile & Settings Completo

**Objetivo:** Completar perfil do usuário com avatar, preferências e configurações do agente.
**Por quê:** `planning-optimus.md` item 2 — onboarding personalizado.

- [ ] **18.1** Avatar upload (Gravatar fallback)
- [ ] **18.2** Alteração de senha
- [ ] **18.3** Configurações do agente: nome, tom de voz, idioma preferido
- [ ] **18.4** Persistir preferências no PostgreSQL (tabela `user_preferences`)
- [ ] **18.5** Carregar preferências no session bootstrap
- [ ] **18.6** Testes E2E + produção

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

### Pendente:
- [ ] **21.4** `reflection_engine.py` — Conectar ao cron semanal
  - Call path: `cron_scheduler` (semanal) → `reflection_engine.analyze_week()` → `collective_intelligence.share()`
- [ ] **21.5** `working_memory.py` — Injetar no session context
  - Call path: `session_bootstrap.load_context()` → carregar `WORKING.md` do agent → `context["working_memory"]`
- [ ] **21.6** `tools_manifest.py` — Gerar TOOLS.md no startup
  - Call path: `main.py lifespan startup` → `tools_manifest.generate()` → salvar em `workspace/TOOLS.md`
- [ ] **21.7** `context_awareness.py` — Fuso horário + greeting no bootstrap
  - Call path: `gateway.route_message()` → `context_awareness.get_context()` → injetar em context
- [ ] **21.8** `security.py` — Enforcement real no gateway
  - Call path: `gateway.route_message()` → `security.check_permission(user, action)` → bloquear se negado
- [ ] **21.9** Frontend: renderizar `suggestions` do intent predictor como chips clicáveis

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

## Priorização Recomendada

| Prioridade | Fase | Impacto | Esforço |
|-----------|------|---------|---------|
| **P0** | FASE 10 — Chat Commands | Alto (funcionalidade existente, só conectar) | Baixo |
| **P0** | FASE 21 — Limpeza Código Morto | Alto (reduz complexidade) | Médio |
| **P1** | FASE 12 — Audit Trail | Alto (debug + melhoria contínua) | Médio |
| **P1** | FASE 13 — Embeddings CI | Alto (qualidade do knowledge) | Baixo |
| **P1** | FASE 17 — Prompt Engineering | Alto (qualidade sem custo) | Baixo |
| **P2** | FASE 18 — User Profile | Médio (UX) | Baixo |
| **P2** | FASE 14 — Temporal Decay | Médio (relevância da memória) | Médio |
| **P2** | FASE 19 — PWA | Médio (mobile access) | Médio |
| **P2** | FASE 11 — Telegram | Médio (novo canal) | Médio |
| **P3** | FASE 15 — Contradiction | Médio (consistência) | Médio |
| **P3** | FASE 16 — Proactive | Alto (diferencial) | Alto |
| **P3** | FASE 20 — Browser Streaming | Baixo (nice-to-have) | Médio |
| **P3** | FASE 22 — Redis | Médio (performance) | Médio |
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
