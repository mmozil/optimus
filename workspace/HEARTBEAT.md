# Heartbeat Checklist

## Ao Acordar (Wake-up)

1. **Verificar trabalho pendente** (query Supabase direto — ZERO tokens)
   - Tasks atribuídas com status != 'done'
   - Notifications não entregues
   - @mentions desde último heartbeat

2. **Se não há trabalho** → HEARTBEAT_OK (sem chamar LLM)

3. **Se há trabalho** → Processar tasks pendentes:
   - Ordenar por prioridade
   - Verificar rate limit antes de cada LLM call
   - Atualizar WORKING.md com progresso

## Frequência

| Mecanismo | Frequência | Custo |
|-----------|-----------|-------|
| Event-driven (Supabase Real-time) | Instantâneo | $0 |
| Heartbeat (fallback) | 60 minutos | ~$0.001 |
| Manual (/agents wake) | Sob demanda | Variável |

## Anti-429 Checklist

- [ ] Verificar rate limit antes de LLM call
- [ ] Usar modelo barato para heartbeat (gemini-2.0-flash)
- [ ] Nunca fazer mais de RPM limit por minuto
- [ ] Logar toda chamada com tokens consumidos
