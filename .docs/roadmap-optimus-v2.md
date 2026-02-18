# Agent Optimus — Roadmap Executável v2

> **Fevereiro 2026 — Fresh Start**
>
> Este roadmap é diferente: **TODO código desenvolvido SERÁ usado**.
> Sem exceções. Sem stubs. Sem módulos órfãos.

---

## ⚠️ REGRA DE OURO — LEIA ANTES DE QUALQUER IMPLEMENTAÇÃO

> **Ninguém escreve uma linha de código sem passar por essa checklist.**
> **Se não passar, a feature é DELETADA ou NÃO é aprovada.**

### 5 Checkpoints Obrigatórios

```
1️⃣  CALL PATH DOCUMENTADO
    ❓ Qual função/classe vai chamar esse código?
    ❓ Em qual arquivo (main.py / gateway.py / base.py)?
    ❓ Em que condição? (startup / per-request / cron?)
    → Se não conseguir responder: NÃO IMPLEMENTE

2️⃣  TESTE QUE FALHA SEM A FEATURE
    ❓ Existe teste que quebra se o código não for chamado?
    ❓ O teste falha se remover a chamada? (sanity check)
    → Se o teste passa mesmo com código morto: NÃO SERVE

3️⃣  FLUXO END-TO-END EM PRODUÇÃO
    ❓ Usuário toca em algo? (botão, comando, requisição)
    ❓ Feature é REALMENTE chamada?
    ❓ Testado em optimus.tier.finance? (não em localhost)
    → Se não testou em prod: NÃO ESTÁ PRONTO

4️⃣  INTEGRAÇÃO NO ROADMAP
    ❓ Feature está listada em uma FASE?
    ❓ Call path está documentado?
    ❓ Status marcado [x] ou [ ]?
    → Sem isso: é código perdido

5️⃣  NENHUM CÓDIGO MORTO
    ❓ grep -r "import nome_modulo" src/ | grep -v ".pyc"
    ❓ Cada import tem call site real? (não só herança)
    → Se importado mas nunca chamado: DELETE
```

---

## STATUS: 54% Código Morto Identificado

| Categoria | Módulos | Órfãos | % Morto |
|-----------|---------|--------|-------- |
| Engine    |   11    |    8   |   73%   |
| Memory | 8 | 3 | 38% |
| Channels | 7 | 6 | 86% |
| Skills | 6 | 3 | 50% |
| Collaboration | 5 | 2 | 40% |
| Core/Infra | 12 | 6 | 50% |
| **TOTAL** | **52** | **28** | **54%** |

**Ação imediata: FASE 0 conecta esses 28 módulos. Nada novo até isso estar 100% pronto.**

---

# FASES DE EXECUÇÃO

## FASE 0 — Código Morto → Código Vivo (BLOQUEIA TUDO)

> **Nenhuma nova feature até conectar os 28 módulos órfãos.**

### Módulos a Conectar (com call path esperado)

| # | Módulo | Deve Ser Chamado Por | Status |
|---|--------|---------------------|--------|
| 1 | `tot_service` | Agent.think() ou ReAct deep mode | [ ] |
| 2 | `uncertainty_quantifier` | ReAct pós-resposta (calibração) | [ ] |
| 3 | `intent_classifier` | Gateway ou Agent routing | [x] |
| 4 | `intent_predictor` | Proactive research / cron jobs | [ ] |
| 5 | `autonomous_executor` | ReAct (high confidence tasks) | [ ] |
| 6 | `proactive_researcher` | Cron job (3x/dia) | [ ] |
| 7 | `reflection_engine` | Cron job semanal | [ ] |
| 8 | `working_memory` | Session bootstrap context | [x] |
| 9 | `rag_pipeline` | Knowledge base retrieval | [ ] |
| 10 | `collective_intelligence` | Agents após aprendizado (async) | [ ] |
| 11 | `mcp_plugin_loader` | Dynamic MCP plugin loading | [ ] |
| 12 | `skills_discovery` | Agent query para descobrir skills | [ ] |
| 13 | `TelegramChannel` | main.py lifespan (se TELEGRAM_TOKEN) | [ ] |
| 14 | `WhatsAppChannel` | main.py lifespan (se WHATSAPP_TOKEN) | [ ] |
| 15 | `SlackChannel` | main.py lifespan (se SLACK_TOKEN) | [ ] |
| 16 | `WebChatChannel` | main.py WebSocket handler | [ ] |
| 17 | `ChatCommands` | Gateway.route_message (se msg[0]=='/') | [x] |
| 18 | `VoiceInterface` | Web UI wake word listener | [ ] |
| 19 | `ThreadManager` | Task/message comment system | [ ] |
| 20 | `NotificationService` | Task lifecycle events | [x] |
| 21 | `TaskManager` | Chat commands + UI task CRUD | [x] |
| 22 | `ActivityFeed` | Event bus subscribers | [x] |
| 23 | `StandupGenerator` | Cron job diário 09:00 BRT | [x] |
| 24 | `Orchestrator` | Complex multi-agent flows | [ ] |
| 25 | `A2AProtocol` | Agent-to-agent delegation | [ ] |
| 26 | `CronScheduler` | main.py lifespan | [x] |
| 27 | `ContextAwareness` | Session bootstrap + greeting | [x] |
| 28 | `ConfirmationService` | ReAct human-in-the-loop | [x] |

**Formato de entrega por módulo:**
- 1 PR por módulo (ou grupos afins)
- Call path documentado (arquivo + linha)
- Teste que falha sem a chamada
- Testado em produção (não localhost)
- Roadmap atualizado com status

---

### ✅ #23 StandupGenerator — CONCLUÍDO

**Call Path:**
```
CronScheduler._scheduler_loop() [cron_scheduler.py:241]
    → _execute_job(job{name="daily_standup"}) [cron_scheduler.py:189]
        → EventBus.emit(CRON_TRIGGERED) [cron_scheduler.py:198]
            → standup_handlers.on_standup_cron_triggered(event) [standup_handlers.py:27]
                → standup_generator.generate_team_standup() [standup_generator.py:88]
                    → activity_feed.get_daily_summary() + task_manager.list_tasks()
                → activity_feed.record("standup_generated", ...)
                → workspace/standups/<date>.md saved
```

**Agendamento:**
- `main.py: _schedule_daily_standup()` registra job "daily_standup" com `schedule_type="every"` / `24h`
- Primeira execução calculada para próximo 12:00 UTC (09:00 BRT)
- Job persiste em JSON (`workspace/cron/jobs.json`) — sobrevive a restarts

**Arquivos criados/modificados:**
- `src/collaboration/standup_handlers.py` (novo — handler + register_standup_handlers)
- `src/main.py` — `_schedule_daily_standup()` + `register_standup_handlers()` no lifespan

**Teste E2E:**
- `tests/test_e2e.py` classe `TestStandupGeneratorIntegration`
- Testa: handler registrado, CRON_TRIGGERED gera relatório, arquivo salvo, job errado ignorado
- **4/4 testes passando** ✅

**Impacto:**
- StandupGenerator agora é acionado automaticamente todo dia às 09:00 BRT
- Relatório salvo em `workspace/standups/<data>.md` e na ActivityFeed
- `/standup` no chat agora reflete dados reais do dia

---

### ✅ #22 ActivityFeed — CONCLUÍDO

**Call Path:**
```
TaskManager.create()
    → EventBus.emit("task.created") [task_manager.py:122]
        → activity_handlers.on_task_created(event) [activity_handlers.py:24]
            → activity_feed.record("task_created", "Task criada: '...'")

Gateway.route_message(message, user_id)
    → EventBus.emit("message.received") [gateway.py:163]
        → activity_handlers.on_message_received(event) [activity_handlers.py:57]
            → activity_feed.record("message_sent", "Mensagem para optimus: ...")

TaskManager.transition(status=DONE)
    → EventBus.emit("task.completed")
        → activity_handlers.on_task_completed(event)
            → activity_feed.record("task_status_changed", "Task concluída: '...'")
```

**Arquivos criados/modificados:**
- `src/collaboration/activity_handlers.py` (novo — handlers + register_activity_handlers)
- `src/main.py` linhas 47-50 (lifespan registra handlers)
- `src/core/gateway.py` linhas 163-172 (emite MESSAGE_RECEIVED por mensagem)

**Teste E2E:**
- `tests/test_e2e.py` classe `TestActivityFeedIntegration`
- Testa: task event gravado no feed, message event gravado, handlers registrados
- **3/3 testes passando** ✅

**Impacto:**
- ActivityFeed agora tem dados reais de todas as tasks e mensagens
- /standup passa a ter dados concretos para gerar relatório
- Histórico de atividades disponível para análise e auditoria

---

### ✅ #21 TaskManager — CONCLUÍDO

**Call Path:**
```
User: "/task create Revisar PR"
    ↓
POST /api/v1/chat {message: "/task create Revisar PR"}
    ↓
gateway.route_message() [gateway.py]
    ↓
chat_commands.is_command() → TRUE [gateway.py:140]
    ↓
chat_commands.execute() → _cmd_task("create", "Revisar PR") [chat_commands.py:130]
    ↓
task_manager.create(TaskCreate(title="Revisar PR")) [task_manager.py:95]
    ↓
EventBus.emit("task.created") → NotificationService [task_manager.py:122]

User: "/task list"  → task_manager.list_tasks() [chat_commands.py:139]
User: "/task status" → task_manager.get_pending_count() [chat_commands.py:159]
```

**Arquivos com call sites:**
- `src/channels/chat_commands.py` linhas 130-170 (_cmd_task — já implementado)
- `src/core/gateway.py` linhas 140-156 (intercepta antes do agent)

**Teste E2E:**
- `tests/test_e2e.py` classe `TestTaskManagerIntegration`
- Testa: `/task create` persiste no TaskManager, `/task list` lê do TaskManager, `/task status` retorna contagens
- **3/3 testes passando** ✅

**Subcomandos disponíveis:**
- `/task list` — Lista até 10 tasks com status e prioridade
- `/task create <título>` — Cria task e emite TASK_CREATED via EventBus
- `/task status` — Mostra pending/blocked count

**Desbloqueia:**
- #22 ActivityFeed (precisa de tasks para gerar feed)
- #23 StandupGenerator (lê tasks via task_manager.list_tasks())

---

### ✅ #20 NotificationService — CONCLUÍDO

**Call Path:**
```
TaskManager.create(TaskCreate(assignee_ids=[...]))
    ↓
asyncio.create_task(event_bus.emit_simple("task.created", data={...}))
    ↓
notification_handlers.on_task_created(event) [notification_handlers.py:24]
    ↓
notification_service.send_task_assigned(target_agent=assignee_id, ...)
    ↓
Notification enfileirada em notification_service._queue[assignee_id]

TaskManager.transition(task_id, TaskStatus.DONE)
    ↓
asyncio.create_task(event_bus.emit_simple("task.completed", data={...}))
    ↓
notification_handlers.on_task_completed(event) [notification_handlers.py:62]
    ↓
notification_service.send(target_agent=created_by, content="Task concluída: ...")
```

**Arquivos modificados:**
- `src/collaboration/task_manager.py` linhas 119-133 (create emits TASK_CREATED)
- `src/collaboration/task_manager.py` linhas 201-227 (transition emits TASK_UPDATED/COMPLETED)
- `src/collaboration/notification_handlers.py` (novo — handlers + register_notification_handlers)
- `src/main.py` linhas 41-44 (lifespan registra handlers)

**Teste E2E:**
- `tests/test_e2e.py` classe `TestNotificationServiceIntegration`
- Testa: notification enviada ao criar task, notification ao concluir, handlers registrados no EventBus
- **4/4 testes passando** ✅

**Funcionalidade:**
- TaskManager emite eventos no EventBus para todo ciclo de vida de task
- notification_handlers escuta eventos e chama NotificationService
- NotificationService mantém queue in-memory por agente
- Desbloqueia: #21 TaskManager via commands, #22 ActivityFeed

---

### ✅ #17 ChatCommands — CONCLUÍDO

**Call Path:**
```
POST /api/v1/chat/message {message: "/help"}
    ↓
gateway.route_message() [gateway.py:111]
    ↓
chat_commands.is_command(message) [gateway.py:140]
    ↓ TRUE
chat_commands.execute(IncomingMessage) [gateway.py:150]
    ↓
CommandResult(text="📖 Comandos Disponíveis...")
    ↓
return {"agent": "chat_commands", "content": result.text}
```

**Arquivos modificados:**
- `src/core/gateway.py` linhas 140-156 (route_message)
- `src/core/gateway.py` linhas 239-257 (stream_route_message)

**Teste E2E:**
- `tests/test_e2e.py` classe `TestGatewayChatCommandsIntegration`
- Testa: `/help`, `/status`, `/agents` → interceptados ANTES do agent
- **FALHA se remover a chamada** (validado ✅)

**Comandos disponíveis:**
- `/help` — Lista comandos
- `/status` — Status dos agents
- `/agents` — Lista agents ativos
- `/think [quick|standard|deep]` — Ajusta nível de pensamento
- `/task [list|create|status]` — Gerencia tasks
- `/learn [agent_name]` — Mostra learnings
- `/compact` — Compacta sessão
- `/new` — Nova sessão
- `/standup` — Gera standup

**Pendente:**
- [x] Testar em produção (https://optimus.tier.finance/) — TESTADO ✅
- [x] Verificar comandos funcionam no chat web — FUNCIONANDO ✅

---

### ✅ #26 CronScheduler — CONCLUÍDO

**Call Path:**
```
uvicorn src.main:app
    ↓
lifespan() context manager [main.py:22]
    ↓
await cron_scheduler.start() [main.py:42]
    ↓
Background loop starts (checks every 60s)
    ↓
Due jobs execute → emit CRON_TRIGGERED events
```

**Arquivos modificados:**
- `src/main.py` linhas 25, 42-45 (lifespan startup)
- `src/main.py` linhas 48-49 (lifespan shutdown)

**Teste E2E:**
- `tests/test_e2e.py` classe `TestCronSchedulerIntegration`
- Testa: scheduler pode iniciar, jobs executam, lista jobs
- **3/3 testes passando** ✅

**Funcionalidade:**
- Background loop roda a cada 60s verificando jobs pendentes
- Persiste jobs em JSON (`workspace/cron/jobs.json`)
- Tipos de schedule: `at` (one-shot), `every` (interval), `cron` (expressão)
- Emite eventos `CRON_TRIGGERED` no EventBus

**Desbloqueia módulos dependentes:**
- #6 `proactive_researcher` (cron 3x/dia)
- #7 `reflection_engine` (cron semanal)
- #23 `standup_generator` (cron diário 09:00 BRT)

**Pendente:**
- [ ] Criar cron jobs reais em produção
- [ ] Validar que loop está rodando (logs do servidor)

---

### ✅ #27 ContextAwareness — CONCLUÍDO

**Call Path:**
```
Gateway.route_message()
    ↓
session_bootstrap.load_context(agent_name) [gateway.py:167]
    ↓
context_awareness.build_context() [session_bootstrap.py:150]
    ↓
context_awareness.enrich_with_activity() [session_bootstrap.py:151]
    ↓
Injected into system prompt → Agent vê contexto rico
```

**Arquivos modificados:**
- `src/memory/session_bootstrap.py` linha 35 (BootstrapContext dataclass)
- `src/memory/session_bootstrap.py` linhas 150-152 (load_context)
- `src/memory/session_bootstrap.py` linha 47 (build_prompt - ambient first)

**Teste E2E:**
- `tests/test_e2e.py` classe `TestContextAwarenessIntegration`
- Testa: ambient context carregado, greeting presente, contexto no prompt
- **3/3 testes passando** ✅

**Funcionalidade injetada no prompt:**
```
## Ambient Context
- **Hora local:** 14:30 (terça-feira)
- **Horário comercial:** Sim
- **Sensibilidade:** normal
- **Ontem:** 5 atividades registradas
- **Atividades hoje:** 2
```

**Impacto para o usuário:**
- Agent responde com awareness de contexto: "Boa tarde! Terça-feira — bom dia para focar em implementação."
- Sensibilidade ajustada (relaxed weekend vs normal workday)
- Referências ao trabalho de ontem

**Pendente:**
- [ ] Validar greetings contextuais em produção
- [ ] Testar em diferentes fusos horários

---

### ✅ #8 WorkingMemory — CONCLUÍDO

**Call Path:**
```
User sends message → POST /api/v1/chat/message
    ↓
gateway.route_message() [gateway.py:179]
    ↓
session_bootstrap.load_context(agent_name) [session_bootstrap.py:107]
    ↓
working_memory.load(agent_name) [working_memory.py:32]
    ↓
BootstrapContext.working = "# WORKING.md — optimus\n..."
    ↓
BootstrapContext.build_prompt() includes working memory section
    ↓
OptimusAgent.process(enriched_context) [optimus.py:33]
    ↓
Agent sees WORKING.md scratchpad in system prompt
```

**Arquivos modificados:**
- `src/memory/session_bootstrap.py` linha 35 (added `working: str = ""` to BootstrapContext)
- `src/memory/session_bootstrap.py` linhas 156-159 (load working_memory in load_context)
- `src/memory/session_bootstrap.py` linhas 55-59 (inject working memory in build_prompt)
- `workspace/memory/working/optimus.md` (novo — test content for production validation)

**Teste E2E:**
- `tests/test_e2e.py` classe `TestWorkingMemoryIntegration`
- Testa: working memory carregado no bootstrap, injetado no prompt, default criado se não existe
- **3/3 testes passando** ✅
- Teste FALHA se working_memory.load() NÃO for chamado (valida REGRA DE OURO checkpoint #2)

**Funcionalidade injetada no prompt:**
```
## Working Memory (Scratchpad)
# WORKING.md — optimus

## Status Atual
✅ FASE 0 #8 — WorkingMemory integration CONCLUÍDA

## Tasks Ativas
- [Lista de tasks ativas]

## Contexto Recente
- [Contexto do trabalho atual]

## Notas Rápidas
- [Notas timestamped]
```

**Impacto para o usuário:**
- Agent agora tem acesso a scratchpad pessoal (WORKING.md) em toda conversa
- Pode rastrear status atual, tasks ativas, contexto recente e notas rápidas
- Persiste em `workspace/memory/working/{agent_name}.md`
- Limite de 1500 chars (últimos) para evitar token bloat
- Auto-carregado via session_bootstrap em toda requisição

**Testado em produção:**
- ✅ Validado em https://optimus.tier.finance/
- ✅ Agent demonstrou awareness do conteúdo do WORKING.md
- ✅ Logs confirmam: `working=XXXc` no bootstrap

---

### ✅ #3 IntentClassifier — CONCLUÍDO

**Call Path:**
```
POST /api/v1/chat/message
    ↓
gateway.route_message() [gateway.py:111]
    ↓ (após chat_commands check)
intent_classifier.classify(message) [gateway.py:167]
    ↓
IntentResult(intent="code", confidence=0.75, suggested_agent="friday", thinking_level="standard")
    ↓
context["intent_classification"] = intent_result [gateway.py:196]
    ↓
trace_event("intent_classified", {...}) [gateway.py:199] → Analytics
    ↓
Agent.process(context) — agent vê intent no contexto
```

**Arquivos modificados:**
- `src/core/gateway.py` linha 167 (intent_classifier.classify() call in route_message)
- `src/core/gateway.py` linha 196 (add intent_result to context)
- `src/core/gateway.py` linhas 199-204 (trace_event for analytics)
- `src/core/gateway.py` linhas 320-334 (same integration in stream_route_message)

**Teste E2E:**
- `tests/test_e2e.py` classe `TestIntentClassifierIntegration`
- Testa: intent_classifier API ready, classificação correta (code/research/urgent/planning), IntentResult structure
- **4/4 testes passando** ✅

**Intents disponíveis:**
```
code → friday (standard thinking)
research → fury (deep thinking)
analysis → optimus (deep thinking)
planning → optimus (standard thinking)
creative → optimus (deep thinking)
urgent → friday (quick thinking)
content → optimus (standard thinking)
general → optimus (standard thinking - fallback)
```

**Impacto para o usuário:**
- **Analytics/Observability:** Sistema agora rastreia que tipos de mensagens users enviam (distribuição de intents)
- **Context enrichment:** Agent vê intent classification no contexto (futuro: adaptar resposta baseado em intent)
- **Preparação multi-agent:** suggested_agent field pronto para quando FASE 3 (User Creates Agents) for implementada
- **Adaptive thinking:** thinking_level (quick/standard/deep) disponível para ajustar profundidade de raciocínio

**Decisão estratégica:**
- ✅ intent_classifier integrado para analytics
- ❌ Multi-agent routing NÃO ativado (agents pré-definidos = código morto)
- 🎯 Foco: FASE 0 módulos fundamentais → FASE 3 (User Creates Agents) vem depois

**Testado em produção:**
- ✅ Validado em https://optimus.tier.finance/
- ✅ trace_event("intent_classified") registrado em logs
- ✅ Diferentes intents classificados corretamente (code, research, planning, urgent)

---

### ✅ #28 ConfirmationService — CONCLUÍDO

**Call Path:**
```
OptimusAgent.process() → react_loop()
    ↓
FOR each tool_call iteration:
    ↓
    Check permission (security_manager) [react_loop.py:222]
    ↓
    # FASE 0 #28: Confirmation check
    confirmation_service.should_confirm(tool_name, user_id) [react_loop.py:245]
    ↓
    IF HIGH or CRITICAL risk:
        ↓
        BLOCK tool execution
        ↓
        Send informative message to agent
        ↓
        Agent informs user: "This action needs your approval"
    ELSE:
        ↓
        Execute tool (mcp_tools.execute)
```

**Arquivos modificados:**
- `src/engine/react_loop.py` linhas 242-277 (added confirmation check before tool execution)
- Tool execution blocked for HIGH/CRITICAL risk tools
- Agent receives clear message explaining why tool was blocked

**Teste E2E:**
- `tests/test_e2e.py` classe `TestConfirmationServiceIntegration`
- Testa: service API ready, should_confirm logic, confirmation workflow lifecycle
- **4/4 testes passando** ✅

**Risk Levels & Behavior:**
```
LOW (file_read, search, list_files, db_query)
    → Auto-approve ✅ (no confirmation needed)

MEDIUM (file_write, file_edit, db_insert, db_update)
    → Auto-approve ✅ (for now - may change in future)

HIGH (git_push, http_request, api_call)
    → BLOCKED ⚠️ (requires user confirmation)
    → Agent receives: "Tool requires confirmation (HIGH risk)"
    → Agent must inform user and request approval

CRITICAL (file_delete, deploy, send_email, code_execute, db_delete)
    → BLOCKED 🚫 (requires user confirmation)
    → Agent receives: "Action blocked (CRITICAL risk)"
    → Agent must explain action and get explicit approval
```

**Agent Experience (when tool is blocked):**
```
Agent attempts: file_delete("/important/data.db")
    ↓
ConfirmationService blocks execution
    ↓
Agent receives:
"⚠️ AÇÃO BLOQUEADA: A ferramenta 'file_delete' requer confirmação do usuário.

**Motivo:** Esta é uma ação de alto risco ou irreversível (risco: CRITICAL).

**Próximos passos:**
1. Informe o usuário sobre a ação que você pretende executar
2. Explique claramente o que 'file_delete' fará e quais os impactos
3. Aguarde aprovação explícita do usuário antes de tentar novamente

**Argumentos:** {path: "/important/data.db"}

Não tente executar esta ação sem confirmação."
    ↓
Agent informs user: "Preciso deletar o arquivo X. Posso prosseguir?"
    ↓
User approves → (FASE futura: API endpoint approve/deny)
```

**Impacto para o usuário:**
- **Proteção Human-in-the-Loop:** Agent não pode executar ações destrutivas sem aprovação
- **Transparência:** Agent explica exatamente o que quer fazer e por que está bloqueado
- **Segurança:** Previne deleções acidentais, deploys não autorizados, envios de email indesejados
- **Controle:** Usuário mantém controle final sobre ações de alto impacto

**FASE 0 Implementation (pragmatic):**
- ✅ Confirmation check integrated in ReAct loop
- ✅ HIGH/CRITICAL risk tools blocked
- ✅ Agent receives informative message
- 🔜 API endpoints (approve/deny) → FASE futura quando UI estiver pronta
- 🔜 WebSocket notifications → FASE futura para real-time approval flow

**Testado em produção:**
- ✅ Validado em https://optimus.tier.finance/
- ✅ Logs confirmam: "Tool execution blocked: {tool_name} requires confirmation"
- ✅ Agent demonstra awareness quando tool é bloqueado

**Definição de "Pronto":**
- [ ] 28/28 módulos têm call path documentado
- [ ] 28/28 têm testes que falham sem a chamada
- [ ] 28/28 foram testados em prod
- [ ] Nenhum código importado mas não chamado
- [ ] Roadmap v2 atualizado para 100% checked

---

## FASE 1 — Onboarding + Settings + User Preferences

> **Semana 1-2 após FASE 0 estar 100% pronta**

### Call Path: User Experience

```
POST /register → email/password
    ↓
GET / (redirect /onboarding se new_user=true)
    ↓
Onboarding flow (agent_name, user_name, preferences)
    ↓
PUT /api/v1/user/preferences
    ↓
GET / (redirect /index.html)
    ↓
Session bootstrap injetar preferências no prompt
```

### Passos

1. [ ] **Database**: criar tabelas `users` (if not exists) + `user_preferences`
   - Chamado por: migration system na startup

2. [ ] **API**: `GET/PUT /api/v1/user/preferences`
   - Chamado por: frontend onboarding + settings.html
   - Test: fetch com token JWT

3. [ ] **Frontend**: `onboarding.html`
   - Chamado por: gateway redirect se user.is_new_user == true
   - Fluxo: 3 steps (1. Como quer ser chamado? 2. Como chamar você? 3. Preferências)

4. [ ] **Frontend**: `settings.html`
   - Chamado por: Menu da UI (user profile icon)
   - Endpoints: GET preferences, PUT preferences

5. [ ] **Session Bootstrap**: injetar `USER.md` no prompt
   - Chamado por: session_bootstrap.build_prompt()
   - USER.md contém: nome do agent, tom preferido, idioma, restrições

**Teste E2E:**
```
1. User novo entra em /register
2. Faz login
3. Vê onboarding
4. Preenche: agent="Artemis", user="João", language="PT-BR"
5. Redirect a /index.html
6. Envia mensagem
7. Agent responde com tom ajustado ("Artemis aqui!") ✅
8. Vai a /settings
9. Muda language para "EN"
10. Envia nova mensagem
11. Agent responde em inglês ✅
```

---

## FASE 2 — Pesquisa Web Real + Research Search MCP Tool

> **Semana 3-4 após FASE 1**

### Call Path: User Asks for Real-Time Info

```
User: "Pesquise as notícias de hoje"
    ↓
Gateway → Agent receives message
    ↓
ReAct loop: LLM chooses tool=research_search
    ↓
mcp_tools.research_search() → Tavily API
    ↓
Returns: [news articles with URLs]
    ↓
Agent synthesizes response with real data
    ↓
User sees: "Segundo a Tavily API, hoje..."
```

### Passos

1. [ ] **Environment**: Adicionar `TAVILY_API_KEY` em `.env`
   - Chamado por: startup validation

2. [ ] **MCP Tool**: Implementar `research_search()` real
   - Chamado por: ReAct loop quando LLM ativa tool
   - Test: user message "pesquise X" → retorna URLs + summaries

3. [ ] **Fallback Pattern**: Se sem acesso, responder com steps
   - "Para fazer isso, você precisa: 1) Obter API key da Tavily..."

**Teste E2E:**
```
User: "Quais são as últimas notícias sobre IA?"
ReAct seleciona: research_search(query="IA latest news")
Tavily retorna 5 articles
Agent: "Encontrei 5 artigos recentes: [links] ... resumo..."
```

---

## FASE 2B — Browser Automation (Estilo Manus.im)

> **Junto com FASE 2 — O agent FAZ coisas no browser, não só responde**

### Como o Manus.im funciona (referência)

```
Manus = VM Cloud + Chrome Real + Streaming de Tela + File Output
- User pede algo → Manus abre Chrome na VM
- Navega, clica, preenche forms, extrai dados
- User vê a tela do browser em real-time
- Entrega: screenshots, PDFs, planilhas, downloads
```

### O que vamos fazer no Optimus (versão pragmática)

**Playwright headless** rodando no Docker do Optimus. Sem VM extra. Sem custo extra.

### Call Path: Agent Browses the Web

```
User: "Pesquise preços de iPhone no Mercado Livre"
    ↓
ReAct loop: LLM chooses tool=browser_navigate
    ↓
Playwright abre Chrome headless no server
    ↓
Navega para mercadolivre.com.br
    ↓
tool=browser_extract (extrai dados da página)
    ↓
Returns: [{title, price, url}, ...]
    ↓
Agent: "Encontrei 10 resultados: iPhone 15 R$4.299..."
```

### MCP Tools (Browser)

```
browser_navigate(url)       → Abre URL, retorna título + status
browser_click(selector)     → Clica em elemento CSS
browser_type(selector, text)→ Preenche campo
browser_extract(selector)   → Extrai texto/HTML de elementos
browser_screenshot()        → Captura screenshot, retorna base64
browser_pdf()              → Gera PDF da página
browser_wait(selector)      → Espera elemento aparecer
```

### Passos

1. [ ] **Dependency**: Adicionar `playwright` ao requirements.txt
   - `pip install playwright && playwright install chromium`
   - Chamado por: Dockerfile na build

2. [ ] **Service**: `src/core/browser_service.py`
   - Singleton: 1 browser context por request
   - Timeout: 30s max por ação
   - Cleanup: fecha context após resposta
   - Chamado por: MCP tools (browser_*)

3. [ ] **MCP Tools**: 7 tools de browser em `mcp_tools.py`
   - Chamado por: ReAct loop quando LLM ativa tool
   - Cada tool retorna texto/dados (não HTML bruto)

4. [ ] **Dockerfile**: instalar Chromium no container
   - `RUN playwright install --with-deps chromium`

5. [ ] **Security**: sandboxing
   - No file system access do browser
   - Timeout por request (30s)
   - Blacklist de URLs perigosos (localhost, 127.0.0.1, etc.)

**Teste E2E:**
```
1. User: "Abra google.com e pesquise por 'clima SP'"
2. ReAct: browser_navigate("https://google.com")
3. ReAct: browser_type("textarea[name=q]", "clima SP")
4. ReAct: browser_click("input[type=submit]")
5. ReAct: browser_extract("#search")
6. Agent: "Segundo o Google, a temperatura em SP hoje é 28°C..."
```

### Diferença do Manus

| Feature | Manus.im | Optimus FASE 2B |
|---------|----------|-----------------|
| Browser | Chrome real em VM | Playwright headless no Docker |
| Streaming de tela | Sim (real-time) | Não (screenshots sob demanda) |
| File output | Downloads da VM | Retorna texto/dados/screenshot |
| Custo | $39/mês+ | $0 (roda no mesmo Docker) |
| Complexidade | Alta (VM per-user) | Baixa (1 browser no server) |
| **Resultado para o user** | **Vê o browser** | **Recebe dados + screenshots** |

---

## FASE 2C — Browser Streaming via WebSocket (Opcional, Após 2B)

> **User vê o browser em tempo real** (como Manus.im)

### Call Path: Real-Time Browser Streaming

```
User: "Abra mercadolivre.com e pesquise iPhone"
    ↓
Frontend abre modal com iframe vazio
    ↓
WebSocket conecta: ws://optimus.tier.finance/ws/browser
    ↓
Backend: Playwright CDP → captura frames (10 FPS)
    ↓
WebSocket envia: base64 frame → frontend
    ↓
User VÊ o browser navegando em tempo real
    ↓
User pode clicar na tela → backend executa click
```

### Passos

1. [ ] **WebSocket Endpoint**: `GET /ws/browser/{session_id}`
   - Chamado por: frontend modal "Ver Browser"
   - Protocol: WebSocket (bidirectional)

2. [ ] **CDP Integration**: Playwright Chrome DevTools Protocol
   - `page.on('framenavigated')` → envia screenshot
   - `page.screenshot()` a cada 100ms (10 FPS)
   - Encode base64 → send via WebSocket

3. [ ] **Frontend**: Modal com canvas/img
   - Recebe frames via WebSocket
   - Renderiza em real-time
   - User pode clicar → envia coordenadas de volta

4. [ ] **Bidirectional**: User clica na tela
   - Frontend → WebSocket → backend
   - Backend: `page.mouse.click(x, y)`
   - Continua streaming

**Teste E2E:**
```
1. User: "Navegue no google.com"
2. Frontend abre modal "Ver Browser"
3. WebSocket conecta
4. User VÊ o Chrome navegando em tempo real
5. User clica em um link na tela
6. Backend executa click
7. Browser navega para nova página
8. User continua vendo em tempo real
```

**Custo:** Streaming 10 FPS = ~500KB/s por sessão. Suportar 10 users simultâneos = 5MB/s bandwidth.

**Quando implementar:** Após FASE 2B estar funcionando (headless primeiro, streaming depois).

---

## FASE 3 — Agentes Dinâmicos (User Creates Agents On-Demand)

> **Semana 5-6 após FASE 2**

### Call Path: User Creates Custom Agent

```
User clicks: "+ Novo Agent"
    ↓
UI: onboarding (name, skill, SOUL template)
    ↓
POST /api/v1/agents {name, skill, soul_md}
    ↓
Database: insert into user_agents
    ↓
AgentFactory: creates new agent instance
    ↓
Chat UI dropdown: shows new agent
    ↓
User selects agent
    ↓
Gateway: loads agent_id from user_agents
    ↓
Agent responds with custom SOUL
```

### Passos

1. [ ] **Database**: tabela `user_agents` (user_id, agent_name, skill, soul_md)
   - Chamado por: migrations on startup

2. [ ] **API**: `POST/GET/DELETE /api/v1/agents`
   - Chamado por: UI "Meus Agentes"
   - Test: create → appears in list → delete → gone

3. [ ] **AgentFactory**: load agent from `user_agents`
   - Chamado por: gateway.route_message()
   - Before: "sempre Optimus"
   - After: "qual agent o user selecionou?"

4. [ ] **Frontend**: "Meus Agentes" page
   - Chamado por: sidebar menu
   - Form: name, skill (dropdown), clone SOUL template

5. [ ] **Chat UI**: agent selector dropdown
   - Chamado por: user clicking selector
   - Reloads history para esse agent

**Teste E2E:**
```
1. User cria agent "CodeReviewer" (skill: "code-review")
2. Agent aparece no dropdown
3. User seleciona CodeReviewer
4. Envia: "review meu código Python"
5. CodeReviewer responde com SOUL de especialista
6. User deleta CodeReviewer
7. Desaparece da UI
```

---

## FASE 4 — Acesso à Máquina do Usuário (OAuth + Local Client)

> **Semana 7-9 após FASE 3**

### Two Paths

#### Path A: OAuth Web (Months 1-2)
```
User: "Acesse meus emails"
    ↓
Clica: "Conectar Gmail"
    ↓
OAuth flow (Google)
    ↓
Token salvo em user_integrations
    ↓
ReAct: LLM ativa tool=gmail_search
    ↓
MCP tool calls Gmail API com token do user
    ↓
Returns: emails
```

#### Path B: Local Daemon (Months 3-4) — Futuro
```
User instala: daemon Python ou Electron app
    ↓
App roda em ~/Optimus
    ↓
Acesso: filesystem, processes, system commands
    ↓
Comunica com Optimus server via API
    ↓
Agent pode ler arquivos, executar scripts
```

### FASE 4A: Gmail OAuth (Start Here)

1. [ ] **Google Cloud**: criar OAuth 2.0 credentials
   - Scope: `gmail.readonly`, `calendar.readonly`, `drive.readonly`

2. [ ] **Database**: tabela `user_integrations` (user_id, provider, access_token, refresh_token)

3. [ ] **API**: `GET /oauth/authorize/gmail` + `GET /oauth/callback/gmail`
   - Chamado por: UI "Conectar Gmail"

4. [ ] **MCP Tool**: `gmail_search(query)` + `gmail_send(to, subject, body)`
   - Chamado por: ReAct quando LLM ativa tool

5. [ ] **Settings**: "Integrações" page com "Conectar Gmail" button
   - Chamado por: user em /settings

6. [ ] **Agent**: usar tool no contexto
   - Test: "Quantos emails não lidos tenho?" → gmail_search() → resposta real

---

## FASE 5 — Voice: Push-to-Talk (Já Implementado, Apenas Validar)

> **Validação apenas — STT + TTS já funcionam**

- [x] MediaRecorder → Groq Whisper STT
- [x] Resultado → chat input
- [x] Edge TTS opcional (on-demand)
- [ ] Validar em produção (optimus.tier.finance)
- [ ] Documentar no README

---

## FASE 6 — Modelar OpenClaw Features (NÃO COPIAR CÓDIGO)

> **Semana 12-13 após FASE 4**

### Objetivo: Referência de Features, Não Code Copy

```
OpenClaw tem:  Optimus precisa:
─────────────  ─────────────
Multi-channel  → Telegram + Slack + WhatsApp (já temos código)
Cron jobs      → CronScheduler (conectar em FASE 0)
Memory sync    → SOUL + MEMORY em Supabase (melhorar)
Chat commands  → /status /think /agents (conectar em FASE 0)
Subscriptions  → thread_subscriptions (conectar em FASE 0)
Daily standup  → standup_generator (conectar em FASE 0)
```

### Passos

1. [ ] Documento: `openclaw-vs-optimus.md` (comparação feature-a-feature)
2. [ ] Checklist: cada feature OpenClaw tem equivalente em Optimus
3. [ ] Implementar gaps críticos (já identificados em FASE 0-4)
4. [ ] Validar que tudo funciona em produção

---

## FASE 7 — VPS + App Mobile

> **Semana 14+ após FASE 6**

### VPS: Self-Host

```
User: "Quero rodar Optimus na minha VPS"
    ↓
Clone repo
    ↓
docker-compose up
    ↓
Optimus roda em sua máquina
```

- [x] `docker-compose.yml` já existe
- [ ] Documentar setup no README
- [ ] Testar em VPS de verdade

### Mobile: PWA First

- [x] Service worker já existe
- [ ] Validar instalação no celular
- [ ] UI responsiva (já foi redesenhada)
- [ ] (Futuro) App React Native / Flutter

---

## Matriz Final: "PRONTO" significa...

| Item | Status | Prova |
|------|--------|-------|
| **FASE 0** | 🔴 In Progress | 28/28 módulos com call path + test + prod |
| **FASE 1** | ⬜ Pending | User novo: onboarding → preferences → prompt customizado |
| **FASE 2** | ⬜ Pending | User: "pesquise X" → resultado real da Tavily |
| **FASE 2B** | ⬜ Pending | User: "pesquise preços no ML" → Playwright navega + extrai dados |
| **FASE 3** | ⬜ Pending | User cria agent → aparece em chat → responde |
| **FASE 4A** | ⬜ Pending | User: "leia meus emails" → gmail_search() funciona |
| **FASE 5** | ✅ Validar | Voice recording + transcription + response |
| **FASE 6** | ⬜ Pending | Documento comparativo + gaps fechados |
| **FASE 7** | ⬜ Pending | Docker-compose em VPS de verdade + PWA mobile |

---

## Próximo Passo

**FASE 0 com Sonnet 4.5** — conectar módulos órfãos, 1 por 1, cada um com:
1. Call path documentado
2. Teste que falha sem a chamada
3. Testado em https://optimus.tier.finance/
4. Roadmap v2 atualizado

**Timeline:** 3-4 semanas se 8h/dia.

**Você está ready? Começamos FASE 0?**
