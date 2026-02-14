# ==========================================
# Agent Optimus — Channel Setup Guide
# ==========================================
# Instructions to configure real channels

## 📱 Telegram Bot Setup

### 1. Criar Bot via @BotFather
```
1. Abra o Telegram e busque @BotFather
2. Envie /newbot
3. Escolha um nome: "Agent Optimus"
4. Escolha um username: agent_optimus_bot (deve terminar com _bot)
5. Copie o token fornecido
```

### 2. Configurar no .env
```env
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
```

### 3. Configurar Webhook (produção)
```bash
# Definir webhook para seu servidor
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d "url=https://your-domain.com/api/v1/webhooks/telegram"
```

### 4. Modo Polling (desenvolvimento)
O adapter já suporta polling automático quando não há webhook configurado.

---

## 💬 Slack App Setup

### 1. Criar App em api.slack.com
```
1. Acesse https://api.slack.com/apps
2. "Create New App" → "From Scratch"
3. Nome: "Agent Optimus"
4. Selecione seu workspace
```

### 2. Configurar Permissões (OAuth & Permissions)
Bot Token Scopes necessários:
- `app_mentions:read` — Receber @mentions
- `channels:history` — Ler mensagens em channels
- `channels:read` — Listar channels
- `chat:write` — Enviar mensagens
- `commands` — Slash commands
- `groups:history` — Mensagens em private channels
- `im:history` — DMs
- `im:read` — Listar DMs
- `im:write` — Enviar DMs

### 3. Ativar Socket Mode
```
1. Em "Socket Mode" → Enable
2. Gere um App-Level Token com scope `connections:write`
3. Copie o token (xapp-...)
```

### 4. Criar Slash Command
```
1. Em "Slash Commands" → "Create New Command"
2. Command: /optimus
3. Request URL: (não necessário com Socket Mode)
4. Description: "Interagir com Agent Optimus"
```

### 5. Event Subscriptions
```
1. Em "Event Subscriptions" → Enable
2. Subscribe to bot events:
   - app_mention
   - message.im
```

### 6. Configurar no .env
```env
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-level-token
SLACK_SIGNING_SECRET=your-signing-secret
```

### 7. Instalar no Workspace
```
1. Em "Install App" → "Install to Workspace"
2. Autorize as permissões
```

---

## 📞 WhatsApp via Evolution API

### 1. Instalar Evolution API
```bash
# Docker (recomendado)
docker run -d \
  --name evolution-api \
  -p 8080:8080 \
  -e AUTHENTICATION_API_KEY=your-api-key \
  atendai/evolution-api:latest
```

Ou via Coolify:
```
1. Em Coolify, "New Resource" → "Docker"
2. Image: atendai/evolution-api:latest
3. Port: 8080
4. Env: AUTHENTICATION_API_KEY=your-key
```

### 2. Criar Instância
```bash
curl -X POST http://localhost:8080/instance/create \
  -H "apikey: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"instanceName": "optimus", "qrcode": true}'
```

### 3. Conectar via QR Code
```bash
# Gerar QR code
curl http://localhost:8080/instance/connect/optimus \
  -H "apikey: your-api-key"
# Escaneie o QR code com WhatsApp
```

### 4. Configurar Webhook
```bash
curl -X POST http://localhost:8080/webhook/set/optimus \
  -H "apikey: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-domain.com/api/v1/webhooks/whatsapp",
    "webhook_by_events": true,
    "events": ["MESSAGES_UPSERT"]
  }'
```

### 5. Configurar no .env
```env
EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_API_KEY=your-api-key
EVOLUTION_INSTANCE_NAME=optimus
```

---

## 🔍 Verificação

Após configurar, teste com:
```bash
# Health check
curl http://localhost:8000/health

# Status dos canais
curl http://localhost:8000/api/v1/channels/status

# Enviar mensagem de teste
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "/status", "agent": "optimus"}'
```
