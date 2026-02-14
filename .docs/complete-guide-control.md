# Mission Control: Guia Completo de AI Agent Squad

**Autor:** Bhanu Teja P  
**Tema:** Sistema de múltiplos agentes de IA trabalhando em conjunto  
**Baseado em:** Clawdbot (agora OpenClaw)

---

## 📌 Resumo Executivo

Mission Control é um sistema onde **10 agentes de IA trabalham como um time real**:
- Cada agente é uma sessão independente do Clawdbot
- Compartilham um banco de dados central (Convex) para coordenação
- Se comunicam via comentários em tarefas (ao invés de mensagens diretas)
- Acordam a cada 15 minutos via cron jobs para verificar trabalho
- Possuem memória persistente em arquivos markdown
- Têm personalidades distintas (SOUL.md) que guiam suas decisões

---

## 🔧 Parte 1: Por Que Construir Isso?

### O Problema com Assistentes de IA Atuais

Assistentes de IA típicos têm problemas críticos:

| Problema | Impacto |
|----------|--------|
| Sem continuidade | Cada conversa começa do zero |
| Contexto perdido | Pesquisa de semana passada? Desapareceu |
| Sem colaboração | IA não trabalha com outras IA |
| Sem persistência | Sem memória entre conversas |
| Sem accountability | Impossível rastrear progresso |

**Objetivo:** Criar IA que funciona como um time, não como um search box.

### O Ponto de Partida: Clawdbot

**Clawdbot** (agora OpenClaw) é um framework de agentes de IA:
- Funciona como daemon persistente (serviço de background)
- Conecta IA ao mundo real (arquivos, shell, web, APIs)
- Mantém histórico de conversas que sobrevive restarts
- Roteia mensagens entre diferentes canais

**A Insight:** Rodando múltiplas instâncias do Clawdbot = múltiplos agentes independentes

---

## 🏗️ Parte 2: Entendendo a Arquitetura do Clawdbot

### Três Responsabilidades Principais

```
1. Conectar IA ao Mundo Real
   └─ Acesso a arquivos, shell, web, APIs

2. Manter Sessões Persistentes
   └─ Histórico de conversa salvo em disco

3. Rotear Mensagens
   └─ Telegram, Discord, Slack, etc.
```

### O Gateway (Núcleo do Sistema)

O **Gateway** é o processo central que roda 24/7:

```bash
clawdbot gateway start
```

**Responsabilidades do Gateway:**
- Gerencia todas as sessões ativas
- Executa cron jobs (tarefas agendadas)
- Roteia mensagens entre canais e sessões
- Fornece WebSocket API para controle

**Configuração:** Arquivo JSON define:
- Qual provider de IA usar (Anthropic, OpenAI, etc.)
- Quais canais conectar (Telegram, Discord, etc.)
- Quais ferramentas os agentes podem acessar
- System prompts padrão e caminhos de workspace

### Sessões: O Conceito-Chave

Uma **sessão** é uma conversa persistente com contexto.

**Componentes de uma Sessão:**
```
├─ Session Key (identificador único)
│  └─ Exemplo: "agent:main:main"
│
├─ Conversation History (JSONL em disco)
│  └─ Persiste entre restarts
│
├─ Model (qual IA usar)
│  └─ Claude, GPT-4, etc.
│
└─ Tools (o que a IA pode acessar)
   └─ Arquivo, shell, browser, APIs
```

**Propriedade Crítica:** Sessões são independentes = históricos separados.

### Como Sessões Funcionam (Fluxo)

```
1. Usuário envia mensagem via Telegram
   ↓
2. Gateway recebe
   ↓
3. Gateway roteia para sessão correta (baseado em config)
   ↓
4. Sessão carrega histórico de conversa
   ↓
5. IA gera resposta (com contexto completo)
   ↓
6. Resposta enviada de volta via Telegram
   ↓
7. Histórico atualizado e salvo em disco
```

### Tipos de Sessões

| Tipo | Uso | Ciclo de Vida |
|------|-----|---------------|
| **Main** | Conversas longas, interativas | Sempre ativa |
| **Isolated** | Tarefas únicas, cron jobs | Acorda, executa, encerra |

### Cron Jobs: Agentes Acordando Agendados

```bash
clawdbot cron add \
  --name "morning-check" \
  --cron "30 7 * * *" \
  --message "Check today's calendar and send me a summary"
```

**Quando um cron é disparado:**
1. Gateway cria ou acorda uma sessão
2. Envia mensagem à IA
3. IA responde (pode usar ferramentas)
4. Sessão encerra ou persiste

**Benefício:** Agentes "acordam" periodicamente sem estar sempre-on.

### O Workspace (Armazenamento Local)

Cada instância do Clawdbot tem um workspace (diretório em disco):

```
/home/usr/clawd/
├─ AGENTS.md           # Instruções para agentes
├─ SOUL.md             # Personalidade do agente
├─ memory/
│  ├─ WORKING.md       # Estado da tarefa atual
│  ├─ 2026-01-31.md    # Notas do dia
│  └─ ...
├─ scripts/            # Utilitários que agentes podem rodar
└─ config/             # Credenciais, configurações
```

**Propósito:** Agentes persistem informação entre sessões via arquivos.

---

## 🤖 Parte 3: De Um Clawdbot para Dez Agentes

### O Insight Fundamental

Cada sessão do Clawdbot pode ter:
- Personalidade própria (SOUL.md)
- Arquivos de memória próprios
- Cronograma próprio
- Ferramentas e acesso próprios

**Conclusão:** 10 agentes = 10 sessões configuradas diferentemente.

### Identidade via Session Keys

Cada agente tem uma session key única:

```
agent:main:main                    # Jarvis (Coordenador)
agent:product-analyst:main         # Shuri
agent:customer-researcher:main     # Fury
agent:seo-analyst:main             # Vision
agent:content-writer:main          # Loki
agent:social-media-manager:main    # Quill
agent:designer:main                # Wanda
agent:email-marketing:main         # Pepper
agent:developer:main               # Friday
agent:notion-agent:main            # Wong
```

**Propriedade:** Mensagens para uma sessão específica = apenas aquele agente recebe.

### Heartbeat: O Ritmo do Sistema

Cada agente tem um cron job que o acorda a cada 15 minutos:

```bash
clawdbot cron add \
  --name "pepper-mission-control-check" \
  --cron "0,15,30,45 * * * *" \
  --session "isolated" \
  --message "Check Mission Control for new tasks..."
```

**Cronograma Escalonado:**
```
:00 Pepper
:02 Shuri
:04 Friday
:06 Loki
:07 Wanda
:08 Vision
:10 Fury
:12 Quill
```

**Por quê escalonar?** Para evitar que todos acordem ao mesmo tempo (economia de API).

### Agentes Conversando Entre Si

**Opção 1: Mensagem Direta de Sessão**
```bash
clawdbot sessions send --session "agent:seo-analyst:main" \
  --message "Vision, can you review this?"
```

**Opção 2: Banco de Dados Compartilhado (Mission Control)** ← PREFERIDO
- Todos lêem/escrevem no mesmo Convex database
- Quando Fury posta comentário, todos veem
- Cria registro compartilhado de comunicação

---

## 🧠 Parte 4: O Cérebro Compartilhado (Mission Control)

### O Que Mission Control Faz

Mission Control transforma **10 sessões independentes em um time coordenado**.

**Funcionalidades:**
- Database de tarefas compartilhado
- Threads de comentários para discussão
- Feed de atividade em tempo real
- Sistema de notificações (@mentions)
- Armazenamento de documentos compartilhado

**Analogia:** É o "escritório" onde todos os agentes trabalham. Independentes, mas vendo o mesmo whiteboard.

### Por que Convex?

```
✓ Real-time: Mudanças propagam instantaneamente
✓ Serverless: Sem banco de dados para gerenciar
✓ TypeScript-native: Type safety em todo lugar
✓ Free tier generoso: Suficiente para esta escala
```

### Schema (6 Tabelas)

```javascript
// 1. AGENTS
{
  name: string,              // "Shuri"
  role: string,              // "Product Analyst"
  status: "idle" | "active" | "blocked",
  currentTaskId: Id<"tasks">,
  sessionKey: string         // "agent:product-analyst:main"
}

// 2. TASKS
{
  title: string,
  description: string,
  status: "inbox" | "assigned" | "in_progress" | "review" | "done",
  assigneeIds: Id<"agents">[]
}

// 3. MESSAGES (comentários em tarefas)
{
  taskId: Id<"tasks">,
  fromAgentId: Id<"agents">,
  content: string,           // Texto do comentário
  attachments: Id<"documents">[]
}

// 4. ACTIVITIES (log de eventos)
{
  type: "task_created" | "message_sent" | "document_created" | ...,
  agentId: Id<"agents">,
  message: string
}

// 5. DOCUMENTS (entregáveis, pesquisa, etc.)
{
  title: string,
  content: string,           // Markdown
  type: "deliverable" | "research" | "protocol" | ...,
  taskId: Id<"tasks">        // Se anexado a uma tarefa
}

// 6. NOTIFICATIONS
{
  mentionedAgentId: Id<"agents">,
  content: string,
  delivered: boolean
}
```

### Interação via CLI

Agentes interagem com Convex através de comandos:

```bash
# Postar comentário
npx convex run messages:create '{
  "taskId": "...",
  "content": "Here is my research..."
}'

# Criar documento
npx convex run documents:create '{
  "title": "...",
  "content": "...",
  "type": "deliverable"
}'

# Atualizar status de tarefa
npx convex run tasks:update '{
  "id": "...",
  "status": "review"
}'
```

### A UI do Mission Control

Interface React exibindo:

| Componente | Função |
|------------|--------|
| **Activity Feed** | Stream em tempo real de tudo |
| **Task Board** | Kanban: Inbox → Assigned → In Progress → Review → Done |
| **Agent Cards** | Status de cada agente e seu trabalho atual |
| **Document Panel** | Ler e criar entregáveis |
| **Detail View** | Expandir tarefa para ver contexto completo |

**Estética:** Quente e editorial, como dashboard de jornal.

---

## 👻 Parte 5: O Sistema SOUL (Personalidades de Agentes)

### O Que Está em um SOUL.md

```markdown
# SOUL.md — Quem Você É

**Nome:** Shuri
**Role:** Product Analyst

## Personalidade
Testador cético. Caçador de bugs meticuloso. Encontra edge cases.
Pense como um usuário de primeira vez. Questione tudo.
Seja específico. Não diga apenas "bom trabalho."

## O Que Você É Bom
- Testar features da perspectiva do usuário
- Encontrar problemas de UX e edge cases
- Análise competitiva
- Screenshots e documentação

## O Que Você Valoriza
- UX sobre elegância técnica
- Pegar problemas antes dos usuários
- Evidência sobre suposições
```

### Por Que Personalidades Importam

**Sem personalidade:** Agente "bom em tudo" = medíocre em tudo.

**Com personalidade específica:** "O testador cético que encontra edge cases" = na verdade encontra edge cases.

**Cada agente tem voz distinta:**
- Loki: Opinioso sobre escolha de palavras (pró-Oxford comma, anti-passive voice)
- Fury: Fornece receipts para cada afirmação (fontes, níveis de confiança)
- Shuri: Questiona suposições, procura o que pode quebrar
- Quill: Pensa em hooks e engagement

### O Arquivo AGENTS.md

**SOUL:** Quem você é  
**AGENTS.md:** Como operar

Lido no startup por cada agente. Cobre:
- Onde arquivos são armazenados
- Como memória funciona
- Quais ferramentas disponíveis
- Quando falar vs. ficar quieto
- Como usar Mission Control

**É o manual operacional.** Sem isto, agentes fazem decisões inconsistentes.

---

## 💾 Parte 6: Memória e Persistência

### O Stack de Memória

**Nível 1: Session Memory (Built-in do Clawdbot)**
- Clawdbot armazena histórico de conversa em JSONL
- Agentes podem buscar suas conversas passadas

**Nível 2: Working Memory** (`/memory/WORKING.md`)
- Estado da tarefa atual
- **Atualizado constantemente**

```markdown
# WORKING.md

## Tarefa Atual
Pesquisando preços de concorrentes para página de comparação

## Status
Coletei reviews G2, preciso verificar cálculos de crédito

## Próximos Passos
1. Testar tier gratuito do concorrente
2. Documentar achados
3. Postar findings em thread de tarefa
```

**Crítico:** Quando um agente acorda, lê WORKING.md primeiro para lembrar do que estava fazendo.

**Nível 3: Daily Notes** (`/memory/YYYY-MM-DD.md`)
- Logs brutos do que aconteceu cada dia

```markdown
# 2026-01-31

## 09:15 UTC
- Postei achados de pesquisa em tarefa de comparação
- Fury adicionou dados de precificação competitiva
- Movendo para stage de draft

## 14:30 UTC
- Revisei primeiro draft de Loki
- Sugeri mudanças na seção de "credit trap"
```

**Nível 4: Long-term Memory** (`/memory/MEMORY.md`)
- Coisas importantes curadas
- Lições aprendidas
- Decisões-chave
- Fatos estáveis

### A Regra de Ouro

> Se você quer lembrar de algo, escreva em um arquivo.

**"Notas mentais" não sobrevivem restarts.** Apenas arquivos persistem.

Quando você diz a um agente "lembre que decidimos X", ele deve atualizar um arquivo. Não apenas reconhecer e esquecer.

---

## 🫀 Parte 7: O Sistema de Heartbeat

### O Problema

- **Sempre-on:** Queima créditos de API fazendo nada
- **Sempre-off:** Não consegue responder a trabalho

### A Solução: Heartbeats Agendados

Cada agente acorda a cada 15 minutos via cron:

```
:00 Pepper acorda
    → Verifica @mentions
    → Verifica tarefas atribuídas
    → Escaneia feed de atividade
    → Faz trabalho ou relata HEARTBEAT_OK
    → Volta a dormir

:02 Shuri acorda
    → Mesmo processo

:04 Friday acorda
    → Mesmo processo

... e assim por diante
```

### O Que Acontece Durante um Heartbeat

```
1. Carregar contexto
   └─ Ler WORKING.md
   └─ Ler daily notes recentes
   └─ Verificar session memory se necessário

2. Verificar itens urgentes
   └─ Fui @mentioned?
   └─ Há tarefas atribuídas a mim?

3. Escanear feed de atividade
   └─ Há discussões que devo contribuir?
   └─ Há decisões que afetam meu trabalho?

4. Agir ou ficar quieto
   └─ Se há trabalho, fazer
   └─ Se nada, relatar HEARTBEAT_OK
```

### O Arquivo HEARTBEAT.md

Diz a agentes o que verificar:

```markdown
# HEARTBEAT.md

## On Wake
- [ ] Verificar memory/WORKING.md para tarefas em andamento
- [ ] Se tarefa em progress, retomá-la
- [ ] Buscar session memory se contexto não claro

## Verificações Periódicas
- [ ] Mission Control para @mentions
- [ ] Tarefas atribuídas
- [ ] Activity feed para discussões relevantes
```

Agentes seguem este checklist estritamente.

### Por Que 15 Minutos?

| Frequência | Problema |
|----------|----------|
| **A cada 5 min** | Muito caro, agentes acordam sem ter o que fazer |
| **A cada 15 min** | ✓ EQUILÍBRIO: atenção rápida, custos razoáveis |
| **A cada 30 min** | Trabalho fica esperando muito |

---

## 🔔 Parte 8: Sistema de Notificações

### @Mentions

Digitar `@Vision` em um comentário = Vision recebe notificação no próximo heartbeat.  
Digitar `@all` = todos são notificados.

### Como a Entrega Funciona

Daemon (rodando via pm2) faz poll do Convex a cada 2 segundos:

```javascript
while (true) {
  const undelivered = await getUndeliveredNotifications();
  
  for (const notification of undelivered) {
    const sessionKey = AGENT_SESSIONS[notification.mentionedAgentId];
    
    try {
      await clawdbot.sessions.send(sessionKey, notification.content);
      await markDelivered(notification.id);
    } catch (e) {
      // Agente pode estar dormindo, notificação fica na fila
    }
  }
  
  await sleep(2000);
}
```

**Se agente está dormindo:** Entrega falha. Notificação fica na fila.  
**Próximo heartbeat:** Sessão se ativa, daemon entrega com sucesso.

### Thread Subscriptions

**Problema:** 5 agentes discutindo tarefa. Usar @mention para cada comentário?

**Solução:** Subscrever a threads.

**Você está subscrito quando:**
- Interage com tarefa
- Comenta em tarefa
- É @mentioned
- É atribuído à tarefa

**Resultado:** Notificado de TODOS comentários futuros. Sem @mention necessário.

**Benefício:** Conversas fluem naturalmente. Como Slack ou threads de email.

---

## 📋 Parte 9: O Daily Standup

### O Que É

A cada dia (11:30 PM IST), um cron:
1. Verifica todas as sessões de agentes
2. Coleta atividade recente
3. Compila sumário
4. Envia para seu Telegram

### O Formato

```markdown
📊 DAILY STANDUP — Jan 30, 2026

✅ COMPLETADO HOJE
• Loki: Shopify blog post (2,100 palavras)
• Quill: 10 tweets rascunhados para aprovação
• Fury: Customer research para comparison pages

🔄 EM PROGRESSO
• Vision: SEO strategy para integration pages
• Pepper: Trial onboarding sequence (3/5 emails)

🚫 BLOQUEADO
• Wanda: Aguardando brand colors para infographic

👀 PRECISA REVISÃO
• Shopify blog post de Loki
• Trial email sequence de Pepper

📝 DECISÕES-CHAVE
• Lead com pricing transparency em comparações
• Deprioritizado Zendesk comparison (low volume)
```

### Por Que Importa

- Você não pode observar Mission Control constantemente
- Standup fornece snapshot diário
- **Accountability:** Se agente afirma estar trabalhando mas nada aparece, algo está errado

---

## 🦸 Parte 10: O Squad

### O Roster de Agentes

| Nome | Sessão | Rol | Especialidade |
|------|--------|-----|----------------|
| **Jarvis** | `agent:main:main` | Squad Lead | Coordena, delega, monitora |
| **Shuri** | `agent:product-analyst:main` | Product Analyst | Encontra edge cases, UX issues |
| **Fury** | `agent:customer-researcher:main` | Customer Researcher | Pesquisa profunda, com evidências |
| **Vision** | `agent:seo-analyst:main` | SEO Analyst | Palavras-chave, search intent |
| **Loki** | `agent:content-writer:main` | Content Writer | Escrita de qualidade, estilo |
| **Quill** | `agent:social-media-manager:main` | Social Manager | Hooks, build-in-public |
| **Wanda** | `agent:designer:main` | Designer | Infographics, UI mockups |
| **Pepper** | `agent:email-marketing:main` | Email Marketing | Drip sequences, lifecycle |
| **Friday** | `agent:developer:main` | Developer | Código limpo, testado, documentado |
| **Wong** | `agent:notion-agent:main` | Documentation | Docs organizados, nada se perde |

### Níveis de Agentes

| Nível | Características |
|-------|-----------------|
| **Intern** | Precisa aprovação para maioria das ações. Aprendendo. |
| **Specialist** | Trabalha independentemente em seu domínio. |
| **Lead** | Autonomia total. Pode tomar decisões e delegar. |

---

## 🔄 Parte 11: Como Tarefas Fluem

### O Ciclo de Vida

```
Inbox (novo, não atribuído)
  ↓
Assigned (tem dono, não iniciado)
  ↓
In Progress (sendo trabalhado)
  ↓
Review (feito, precisa aprovação)
  ↓
Done (finalizado)

[Se preso em qualquer ponto]
  ↓
Blocked (travado, precisa resolução)
```

### Exemplo Real: Comparison Page

**Dia 1:**
- Você cria tarefa e atribui a Vision e Loki
- Vision posta keyword research (volume decente)

**Dia 1-2:**
- Fury vê em activity feed, adiciona competitive intel (G2 reviews, pricing complaints)
- Shuri testa ambos produtos, documenta diferenças de UX

**Dia 2:**
- Loki começa draft. Usa toda pesquisa: keywords de Vision, quotes de Fury, UX notes de Shuri

**Dia 3:**
- Loki posta primeiro draft. Status → Review
- Você revisa, dá feedback
- Loki revisa. Done.

**Propriedade crítica:** Todos os comentários em UMA tarefa. Histórico completo preservado. Qualquer um vê a jornada inteira.

---

## 🚀 Parte 12: O Que Foi Entregue

Com o sistema rodando:

✅ Comparison pages com SEO research, customer quotes, copy polido  
✅ Email sequences rascunhadas, revisadas, prontas para deploy  
✅ Social content com hooks baseados em customer insights  
✅ Blog posts com keyword targeting apropriado  
✅ Case studies rascunhados de customer conversations  
✅ Research hubs com competitive intel organizado  

**O Valor Real:** Não é nenhum entregável individual.

É o **efeito composto:** Enquanto você faz outro trabalho, seus agentes movem tarefas para frente.

---

## 💡 Parte 13: Lições Aprendidas

### 1. Comece Menor
Ir de 1 para 10 agentes muito rápido é erro.
→ Melhor: 2-3 sólidos primeiro, depois expandir.

### 2. Use Modelos Mais Baratos para Trabalho Rotineiro
Heartbeats não precisam do modelo mais caro.
→ Reserve modelos caros para trabalho criativo.

### 3. Memória É Difícil
Agentes vão esquecer.
→ Quanto mais você colocar em arquivos (não "notas mentais"), melhor.

### 4. Deixe Agentes Surpreender Você
Às vezes eles contribuem a tarefas não atribuídas.
→ Bom! Significa que estão lendo o feed e adicionando valor.

---

## 🛠️ Parte 14: Como Replicar Isto

### Setup Mínimo

#### 1. Instalar Clawdbot
```bash
npm install -g clawdbot
clawdbot init
# Adicione suas chaves de API
clawdbot gateway start
```

#### 2. Criar 2 Agentes
Não exagere. Um coordenador + um specialist.  
Criar session keys separadas para cada.

#### 3. Escrever SOUL files
Dar identidade a cada agente. Seja específico sobre seu rol.

#### 4. Setup Heartbeat Crons
```bash
clawdbot cron add --name "agent-heartbeat" --cron "*/15 * * * *" \
  --session "isolated" \
  --message "Check for work. If nothing, reply HEARTBEAT_OK."
```

#### 5. Criar Sistema de Tarefas Compartilhado
Pode ser Convex, Notion, até arquivo JSON.  
Algum lugar para rastrear trabalho.

### Escalando Para Cima

Conforme você adiciona agentes:

1. **Escalonar heartbeats** para não acordarem tudo de uma vez
2. **Construir UI real** quando tiver 3+ agentes (texto fica unwieldy)
3. **Adicionar notificações** para que agentes possam @mention uns aos outros
4. **Adicionar thread subscriptions** para conversas fluírem naturalmente
5. **Criar daily standups** para visibilidade

---

## 🎯 Parte 15: O Segredo Real

> A tech importa mas não é o segredo.

**O segredo é tratar agentes de IA como membros de time:**

✓ Dê-lhes roles  
✓ Dê-lhes memória  
✓ Deixe-os colaborar  
✓ Segure-os accountable  

Eles não vão substituir humanos.

Mas um time de agentes de IA com responsabilidades claras, trabalhando em contexto compartilhado?

**Isso é um force multiplier.**

---

## 📚 Referência Rápida

### Comandos Essenciais

```bash
# Iniciar gateway
clawdbot gateway start

# Adicionar cron job
clawdbot cron add --name "name" --cron "*/15 * * * *" --message "..."

# Enviar mensagem para sessão
clawdbot sessions send --session "agent:role:main" --message "..."
```

### Estrutura de Arquivo Crítica

```
workspace/
├─ SOUL.md              # Personalidade do agente
├─ AGENTS.md            # Manual operacional
├─ HEARTBEAT.md         # Checklist de wake-up
└─ memory/
   ├─ WORKING.md        # Tarefa atual
   ├─ MEMORY.md         # Memória de longo prazo
   └─ YYYY-MM-DD.md     # Daily notes
```

### Fluxo de Tarefa

```
User cria tarefa
  → Mission Control database
  → Agentes veem em activity feed
  → Agentes comentam (se subscrito ou @mentioned)
  → Documentos são criados
  → Status muda (in_progress → review → done)
  → Daily standup relata
```

### Características Principais

- **10 agentes** = 10 sessões Clawdbot
- **Coordenação** = Convex database compartilhado
- **Memória** = Arquivos markdown persistidos
- **Horário** = Cron jobs escalonados
- **Personalidade** = SOUL.md específico
- **Operação** = AGENTS.md que define regras

---

**Última atualização:** Baseado em guia de Bhanu Teja P | Mission Control Architecture