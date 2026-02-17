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
| 3 | `intent_classifier` | Gateway ou Agent routing | [ ] |
| 4 | `intent_predictor` | Proactive research / cron jobs | [ ] |
| 5 | `autonomous_executor` | ReAct (high confidence tasks) | [ ] |
| 6 | `proactive_researcher` | Cron job (3x/dia) | [ ] |
| 7 | `reflection_engine` | Cron job semanal | [ ] |
| 8 | `working_memory` | Session bootstrap context | [ ] |
| 9 | `rag_pipeline` | Knowledge base retrieval | [ ] |
| 10 | `collective_intelligence` | Agents após aprendizado (async) | [ ] |
| 11 | `mcp_plugin_loader` | Dynamic MCP plugin loading | [ ] |
| 12 | `skills_discovery` | Agent query para descobrir skills | [ ] |
| 13 | `TelegramChannel` | main.py lifespan (se TELEGRAM_TOKEN) | [ ] |
| 14 | `WhatsAppChannel` | main.py lifespan (se WHATSAPP_TOKEN) | [ ] |
| 15 | `SlackChannel` | main.py lifespan (se SLACK_TOKEN) | [ ] |
| 16 | `WebChatChannel` | main.py WebSocket handler | [ ] |
| 17 | `ChatCommands` | Gateway.route_message (se msg[0]=='/') | [ ] |
| 18 | `VoiceInterface` | Web UI wake word listener | [ ] |
| 19 | `ThreadManager` | Task/message comment system | [ ] |
| 20 | `NotificationService` | Task lifecycle events | [ ] |
| 21 | `TaskManager` | Chat commands + UI task CRUD | [ ] |
| 22 | `ActivityFeed` | Event bus subscribers | [ ] |
| 23 | `StandupGenerator` | Cron job diário 09:00 BRT | [ ] |
| 24 | `Orchestrator` | Complex multi-agent flows | [ ] |
| 25 | `A2AProtocol` | Agent-to-agent delegation | [ ] |
| 26 | `CronScheduler` | main.py lifespan | [ ] |
| 27 | `ContextAwareness` | Session bootstrap + greeting | [ ] |
| 28 | `ConfirmationService` | ReAct human-in-the-loop | [ ] |

**Formato de entrega por módulo:**
- 1 PR por módulo (ou grupos afins)
- Call path documentado (arquivo + linha)
- Teste que falha sem a chamada
- Testado em produção (não localhost)
- Roadmap atualizado com status

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

> **Futuro**: Adicionar streaming via WebSocket para user ver browser em tempo real (como Manus). Mas primeiro: funcionar headless.

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
