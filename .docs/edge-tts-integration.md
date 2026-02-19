# FASE 0 #18 — Edge TTS Integration + Voice Endpoint Migration

## ✅ Implementado (Commit 9de3c54)

### 1. **Edge TTS Provider** — Alternativa Gratuita para TTS

**Arquivo:** `src/channels/voice_interface.py`

#### O que foi adicionado:
- ✅ `VoiceProviderType.EDGE = "edge"` (enum line 28)
- ✅ `EdgeTTSProvider` class (lines 177-225)
  - **FREE** — sem necessidade de API key
  - **400+ vozes** em 100+ idiomas
  - **Voz padrão:** `pt-BR-AntonioNeural` (português brasileiro masculino)
  - **Fallback gracioso:** se `edge-tts` não instalado, usa stub
  - **TTS apenas:** STT usa stub (Edge TTS não faz transcrição)

#### Como usar:
```bash
# Via API REST
curl -X PUT https://optimus.tier.finance/api/v1/voice/config \
  -H "Content-Type: application/json" \
  -d '{"tts_provider": "edge"}'

# Variável de ambiente (opcional, customizar voz)
EDGE_TTS_VOICE=pt-BR-FranciscaNeural  # voz feminina
```

#### Vozes disponíveis (Edge TTS):
- `pt-BR-AntonioNeural` — Masculino (padrão)
- `pt-BR-FranciscaNeural` — Feminino
- `pt-BR-BrendaNeural` — Feminino jovem
- `en-US-AriaNeural` — Inglês feminino
- [400+ outras vozes...](https://speech.microsoft.com/portal/voicegallery)

---

### 2. **Frontend Voice Endpoint Migration**

**Arquivo:** `src/static/index.html` (lines 849-908)

#### ❌ ANTES (endpoint antigo):
```javascript
// OLD: /api/v1/audio/stt (apenas STT)
const formData = new FormData();
formData.append('file', blob, 'audio.webm');
const resp = await fetch('/api/v1/audio/stt', {
  method: 'POST',
  body: formData  // multipart/form-data
});
const data = await resp.json();
transcript = data.text;  // apenas texto
```

#### ✅ DEPOIS (endpoint novo):
```javascript
// NEW: /api/v1/voice/command (pipeline completo)
const reader = new FileReader();
const base64 = await new Promise(resolve => {
  reader.onloadend = () => resolve(reader.result.split(',')[1]);
  reader.readAsDataURL(blob);
});

const resp = await fetch('/api/v1/voice/command', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    audio_base64: base64,
    user_id: 'web-user',
    session_id: 'web-session'
  })
});

const data = await resp.json();
transcript = data.transcribed_text;

// Wake word detection
if (data.wake_word_detected) {
  console.log('Wake word detected! Command:', data.command);
}
```

#### Benefícios da migração:
- ✅ **Pipeline completo:** audio → STT → wake word → agent → TTS
- ✅ **Wake word detection:** detecta "Optimus" ou "Hey Optimus"
- ✅ **Base64 transport:** funciona com qualquer formato de áudio
- ✅ **Response completo:** texto + comando + resposta + áudio

---

### 3. **Wake Word Detection** — Como Alexa/Siri

**Wake words configuradas:**
- `"optimus"`
- `"hey optimus"`

**Fluxo:**
1. Usuário diz: **"Hey Optimus, what time is it?"**
2. STT transcreve: `"Hey Optimus, what time is it?"`
3. `detect_wake_word()` → `True` ✅
4. `strip_wake_word()` → `"what time is it?"` (remove wake word)
5. Gateway roteia comando para agente
6. Agente responde: "It's 3:45 PM"
7. TTS converte resposta para áudio
8. Frontend recebe: `{transcribed_text, wake_word_detected, command, response, response_audio_base64}`

**Console log:**
```javascript
Wake word detected! Command: what time is it?
```

---

### 4. **Testes**

#### E2E Test:
**Arquivo:** `tests/test_e2e.py` (class `TestVoiceInterfaceIntegration`)

Novo teste adicionado:
```python
async def test_edge_tts_provider(self):
    """Test Edge TTS provider configuration (free alternative)."""
    # Verify Edge TTS enum exists
    assert VoiceProviderType.EDGE == "edge"

    # Create VoiceInterface with Edge TTS
    config = VoiceConfig(tts_provider=VoiceProviderType.EDGE)
    vi = VoiceInterface(config)

    # Test synthesis (falls back to stub if edge-tts not installed)
    result = await vi.speak("Test Edge TTS")
    assert len(result) > 0
```

#### Production Test Script:
**Arquivo:** `tests/test_wake_word.sh`

```bash
#!/bin/bash
# Test wake word detection in production

# 1. Update config to Edge TTS
curl -X PUT https://optimus.tier.finance/api/v1/voice/config \
  -H "Content-Type: application/json" \
  -d '{"tts_provider": "edge"}'

# 2. Get config (verify)
curl https://optimus.tier.finance/api/v1/voice/config

# 3. Test voice command (stub mode)
curl -X POST https://optimus.tier.finance/api/v1/voice/command \
  -H "Content-Type: application/json" \
  -d '{
    "audio_base64": "ZmFrZSBhdWRpbyBkYXRh",
    "user_id": "test-user"
  }'
```

---

## 🧪 Como Testar em Produção

### Teste 1: Atualizar config para Edge TTS
```bash
curl -X PUT https://optimus.tier.finance/api/v1/voice/config \
  -H "Content-Type: application/json" \
  -d '{"tts_provider": "edge"}'
```

**Resposta esperada:**
```json
{
  "success": true,
  "updated_fields": ["tts_provider"],
  "message": "Voice configuration updated successfully"
}
```

### Teste 2: Verificar config
```bash
curl https://optimus.tier.finance/api/v1/voice/config
```

**Resposta esperada:**
```json
{
  "stt_provider": "stub",
  "tts_provider": "edge",
  "language": "pt-BR",
  "wake_words": ["optimus", "hey optimus"],
  "voice_name": "optimus"
}
```

### Teste 3: Frontend (Wake Word)
1. Acessar https://optimus.tier.finance/
2. Clicar no botão do microfone 🎤
3. Falar: **"Hey Optimus, what time is it?"**
4. Abrir console do navegador (F12)
5. Verificar log:
   ```
   Wake word detected! Command: what time is it?
   ```

---

## 📊 Call Path Completo

```
┌─────────────────────────────────────────────────────────────────┐
│ FRONTEND (index.html)                                           │
└─────────────────────────────────────────────────────────────────┘
  1. User clicks mic → MediaRecorder.start()
  2. User speaks → audio chunks recorded
  3. User stops → Blob created from chunks
  4. FileReader → convert Blob to base64
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│ API REQUEST                                                      │
└─────────────────────────────────────────────────────────────────┘
  POST /api/v1/voice/command
  {
    "audio_base64": "UklGRi...",
    "user_id": "web-user",
    "session_id": "web-session"
  }
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│ VOICE API (src/api/voice.py)                                    │
└─────────────────────────────────────────────────────────────────┘
  1. voice_command(request)
  2. base64.b64decode(audio_base64) → audio_bytes
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│ VOICE INTERFACE (src/channels/voice_interface.py)               │
└─────────────────────────────────────────────────────────────────┘
  3. voice_interface.listen(audio_bytes)
     → STT provider (Whisper/Stub) → "Hey Optimus, what time is it?"
  4. detect_wake_word(text)
     → regex check for "optimus"/"hey optimus" → True ✅
  5. strip_wake_word(text)
     → remove wake word → "what time is it?"
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│ GATEWAY (src/core/gateway.py)                                   │
└─────────────────────────────────────────────────────────────────┘
  6. gateway.route_message(command="what time is it?", context={})
     → selects agent → agent.process()
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│ AGENT (src/core/agent_factory.py)                               │
└─────────────────────────────────────────────────────────────────┘
  7. agent.process("what time is it?")
     → LLM call → response: "It's 3:45 PM"
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│ VOICE INTERFACE (TTS)                                           │
└─────────────────────────────────────────────────────────────────┘
  8. voice_interface.speak("It's 3:45 PM")
     → EdgeTTSProvider.synthesize()
       → edge_tts.Communicate(text, "pt-BR-AntonioNeural")
         → save to temp file → read bytes → MP3 audio
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│ API RESPONSE                                                     │
└─────────────────────────────────────────────────────────────────┘
  {
    "transcribed_text": "Hey Optimus, what time is it?",
    "wake_word_detected": true,
    "command": "what time is it?",
    "response": "It's 3:45 PM",
    "response_audio_base64": "UklGRi..."  // MP3 audio
  }
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│ FRONTEND (Response Handling)                                    │
└─────────────────────────────────────────────────────────────────┘
  9. Extract transcribed_text → put in chatInput
  10. Log wake_word_detected to console
  11. (Future) Play response_audio_base64 via <audio> element
```

---

## 🎯 Diferenças: OLD vs NEW Endpoint

| Feature | `/audio/stt` (OLD) | `/voice/command` (NEW) |
|---------|-------------------|----------------------|
| **Method** | POST multipart/form-data | POST application/json |
| **Input** | FormData with file | `{audio_base64, user_id}` |
| **STT** | ✅ Yes | ✅ Yes |
| **Wake Word** | ❌ No | ✅ Yes |
| **Agent Routing** | ❌ No | ✅ Yes |
| **TTS Response** | ❌ No | ✅ Yes |
| **Response** | `{text}` | `{transcribed_text, wake_word_detected, command, response, response_audio_base64}` |
| **Use Case** | Apenas transcrição | Pipeline completo de voz |

---

## 📦 Arquivos Modificados

| Arquivo | Linhas | Descrição |
|---------|--------|-----------|
| `src/channels/voice_interface.py` | +52 | EdgeTTSProvider class + enum |
| `src/static/index.html` | +25/-10 | Migration to `/voice/command` |
| `tests/test_e2e.py` | +28 | Edge TTS provider test |
| `tests/test_wake_word.sh` | +55 | Production test script (NEW) |

**Total:** 4 arquivos, +160 linhas, -10 linhas

---

## 🚀 Deploy

**Commit:** `9de3c54` — feat: add Edge TTS provider + update frontend to new voice endpoints
**Push:** `origin/main` → GitHub
**Coolify:** Auto-deploy triggered via webhook
**Production:** https://optimus.tier.finance/

**Status:** ✅ Deployed and ready to test

---

## 📝 Next Steps (Opcional)

1. **Testar Edge TTS em produção:**
   - Rodar `tests/test_wake_word.sh`
   - Verificar logs no Coolify

2. **Frontend: Auto-play audio response:**
   ```javascript
   // Adicionar em index.html após linha 908
   if (data.response_audio_base64) {
     const audio = new Audio('data:audio/mp3;base64,' + data.response_audio_base64);
     audio.play();
   }
   ```

3. **Documentar no roadmap:**
   - Marcar #18 Voice Interface como `[x]` concluído
   - Adicionar seção "✅ #18 Voice Interface — CONCLUÍDO"

---

## ✅ Checklist REGRA DE OURO

- [x] **#1 Call Path:** Documentado acima (completo)
- [x] **#2 Tests:** `test_edge_tts_provider()` + `test_wake_word.sh`
- [x] **#3 Integration:** Edge TTS provider + frontend migration
- [ ] **#4 Production Test:** Pendente (você vai testar no Swagger/frontend)
- [ ] **#5 Roadmap:** Pendente (marcar #18 como concluído)

---

**Resumo:** Edge TTS integrado como provider gratuito, frontend migrado para `/voice/command` com wake word detection. Pronto para testar em produção! 🎉
