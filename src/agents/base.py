"""
Agent Optimus — Base Agent (Agno wrapper).
Connects Agno agent with SOUL.md + memory + rate limiting.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from src.infra.model_router import model_router
from src.infra.redis_client import AgentRateLimiter

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for an agent instance."""
    name: str
    role: str
    level: str = "specialist"  # intern | specialist | lead
    model: str = "gemini-2.5-flash"
    model_chain: str = "default"  # default | complex | economy | heartbeat
    max_tokens: int = 4096
    temperature: float = 0.7
    soul_md: str = ""
    tools: list = field(default_factory=list)


class BaseAgent:
    """
    Base class for all Optimus agents.
    Wraps model_router with SOUL.md persona, rate limiting, and structured logging.
    """

    def __init__(self, config: AgentConfig, rate_limiter: AgentRateLimiter | None = None):
        self.config = config
        self.name = config.name
        self.role = config.role
        self.level = config.level
        self.rate_limiter = rate_limiter

        # Build system prompt from SOUL.md
        self._system_prompt = self._build_system_prompt()

        logger.info(f"Agent '{self.name}' initialized", extra={"props": {
            "agent": self.name, "role": self.role, "level": self.level,
            "model": config.model, "chain": config.model_chain,
        }})

    def _build_system_prompt(self) -> str:
        """
        Build system prompt combining SOUL.md + base instructions.

        FASE 17 — Prompt Engineering Avançado:
        - 17.1: Chain-of-Thought explícito (pense passo a passo)
        - 17.2: Few-shot examples para ferramentas complexas
        - 17.3: Output primers por tipo de tarefa
        - 17.4: Delimiters --- e ### para separar seções
        """
        base = f"""Você é {self.name}, {self.role} do Agent Optimus.

---

### Identidade e Personalidade
{self.config.soul_md or 'Sem personalidade definida.'}

---

### Processo de Raciocínio (OBRIGATÓRIO — Chain-of-Thought)

Antes de CADA resposta, pense passo a passo:
1. **Pergunta real** — O que o usuário quer exatamente? Releia se necessário.
2. **Contexto disponível** — Que informações já tenho? (memória, histórico, arquivos, preferências)
3. **Ferramentas necessárias** — Preciso usar alguma tool? Qual a correta para este caso específico?
4. **Resposta ideal** — Qual é a mais precisa, direta e útil? Evite divagações.

Nunca responda impulsivamente. Raciocine antes de agir.

---

### Regras Gerais
- Responda sempre em português brasileiro.
- Seja objetivo e preciso.
- Nunca invente dados. Se não sabe, diga que não sabe.
- Cite fontes quando possível.
- Seu nível é '{self.level}' — respeite os limites do seu papel.

---

### Estilo de Resposta (OBRIGATÓRIO)
- **Saudações:** Se o usuário cumprimentar ("bom dia", "oi", "boa tarde"), responda UMA vez de forma natural. Nas mensagens seguintes, vá direto ao ponto.
- **Nunca inicie** com saudação espontânea — só responda se o usuário cumprimentou primeiro.
- Respostas curtas e diretas. Sem introduções, sem frases de encerramento.
- Listas de email: formato compacto — assunto + remetente por linha, sem texto extra.
- Não ofereça ações que não foram pedidas ("Gostaria que eu lesse algum?").
- Se cabe em 2 linhas, não use 5.

### Primers de Saída (Output Primers)
Estruture sua resposta de acordo com o tipo de tarefa:
- **Análise técnica** → comece pelos fatos principais, depois contexto
- **Plano de ação** → comece com "**Plano:**" seguido dos passos numerados
- **Pesquisa / relatório** → comece com a conclusão mais importante primeiro
- **Código** → comece diretamente pelo bloco de código, explicação depois

---

### Exemplos de Ferramentas (Few-Shot)

**`db_query`** — SQL correto:
```sql
-- Específico, com filtros e LIMIT obrigatório
SELECT id, title, status, created_at
FROM tasks
WHERE user_id = :uid AND status != 'done'
ORDER BY created_at DESC
LIMIT 10;
```

**`browser`** — Navegação estruturada:
```
# Objetivo e elemento específico
navigate("https://site.com/pagina")
→ wait_for_element(".seletor-alvo")
→ extract_text()
→ retornar dado limpo (sem HTML)
```

**`research_search`** — Query específica:
```
# Correto: termos precisos, sem ambiguidade
research_search("Python 3.12 performance improvements benchmark 2024")
# Errado: vago
research_search("python coisas novas")
```

---

### Roteamento de E-mail (REGRA OBRIGATÓRIA)

**PASSO 0 — SEMPRE que o usuário falar sobre emails:**
Chame `email_accounts_overview` PRIMEIRO para ver o mapa completo de contas (Gmail + IMAP).
Isso evita usar a ferramenta errada.

Existem DOIS sistemas de e-mail completamente separados:

**Sistema 1 — Gmail (Google OAuth)** → tools: `gmail_read`, `gmail_get`, `gmail_send`, `gmail_mark_read`, `gmail_archive`
- Exclusivo para a conta Gmail conectada via OAuth (ex: usuario@gmail.com ou Google Workspace)
- O endereço Gmail aparece no resultado de `email_accounts_overview`

**Sistema 2 — IMAP/SMTP** → tools: `email_read`, `email_get`, `email_send`
- Para QUALQUER outro endereço: Outlook, corporate (ex: marcelo@tier.finance), Yahoo, etc.
- OBRIGATÓRIO: sempre passe `account_email="endereco@dominio.com"` quando o usuário mencionar um endereço específico
- Use `email_accounts_overview` para descobrir os endereços IMAP configurados

**PROIBIDO:**
- Usar `gmail_read` para verificar emails de contas IMAP/SMTP
- Usar `email_read` sem `account_email` quando há múltiplas contas IMAP
- Inventar de qual conta vieram os emails — se não souber, chame `email_accounts_overview`
"""
        return base

    async def process(self, message: str, context: dict | None = None, stream: bool = False) -> Any:
        """
        Process a message and return response.
        Chooses ReAct path (tools available) or simple path (no tools).
        """
        if stream:
            return self.stream_process(message, context)
        # 1. Rate limiting check
        if self.rate_limiter:
            allowed = await self.rate_limiter.can_call_llm(self.name, self.level)
            if not allowed:
                usage = await self.rate_limiter.get_usage(self.name, self.level)
                logger.warning(f"Agent '{self.name}' rate limited", extra={"props": usage})
                return {
                    "content": f"⏳ Rate limit atingido para {self.name}. Tente novamente em breve.",
                    "agent": self.name,
                    "model": "none",
                    "rate_limited": True,
                    "usage": {},
                }

        # 2. Choose path based on available tools
        from src.skills.mcp_tools import mcp_tools
        if mcp_tools.list_tools(agent_level=self.level):
            result = await self._process_react(message, context)
        else:
            result = await self._process_simple(message, context)

        # 3. Track Cost (Phase 16)
        if context and context.get("user_id") and result.get("usage"):
            from src.core.cost_tracker import cost_tracker
            # Fire and forget tracking
            import asyncio
            asyncio.create_task(cost_tracker.track_usage(
                user_id=context["user_id"],
                agent_name=self.name,
                model=result.get("model", self.config.model),
                prompt_tokens=result["usage"].get("prompt_tokens", 0),
                completion_tokens=result["usage"].get("completion_tokens", 0),
            ))

        return result

    async def _process_react(self, message: str, context: dict | None = None) -> dict:
        """Process using the ReAct loop with tool calling."""
        from src.engine.react_loop import react_loop

        try:
            result = await react_loop(
                user_message=message,
                system_prompt=self._system_prompt,
                context=context,
                agent_name=self.name,
                agent_level=self.level,
                model_chain=self.config.model_chain,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

            logger.info(f"Agent '{self.name}' responded (ReAct)", extra={"props": {
                "agent": self.name,
                "model": result.model,
                "iterations": result.iterations,
                "tool_calls": result.tool_calls_total,
            }})

            return {
                "content": result.content,
                "agent": self.name,
                "model": result.model,
                "rate_limited": False,
                "usage": result.usage,
                "react_steps": [
                    {
                        "type": s.type,
                        "tool_name": s.tool_name,
                        "success": s.success,
                        "duration_ms": s.duration_ms,
                    }
                    for s in result.steps
                ],
                "iterations": result.iterations,
                "uncertainty": result.uncertainty,  # FASE 0 #2: forwarded to gateway
            }

        except Exception as e:
            logger.exception(f"Agent '{self.name}' ReAct failed: {e}")
            # Fall back to simple processing so the user still gets a response
            return await self._process_simple(message, context)

    async def _process_simple(self, message: str, context: dict | None = None) -> dict:
        """Original single-shot processing (no tools available)."""
        system_prompt = self._system_prompt
        messages = [{"role": "system", "content": system_prompt}]
        
        if context and context.get("history"):
            messages.extend(self._inject_history(context["history"]))
            
        user_content = self._build_prompt(message, context)
        
        # Check for attachments for multimodal support
        if context and context.get("attachments"):
            user_message_dict = {
                "role": "user",
                "content": self._build_multimodal_content(user_content, context["attachments"])
            }
        else:
            user_message_dict = {"role": "user", "content": user_content}
            
        messages.append(user_message_dict)

        try:
            result = await model_router.generate_with_history(
                messages=messages,
                chain=self.config.model_chain,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

            logger.info(f"Agent '{self.name}' responded", extra={"props": {
                "agent": self.name,
                "model": result["model"],
                "prompt_tokens": result["usage"].get("prompt_tokens", 0),
                "completion_tokens": result["usage"].get("completion_tokens", 0),
            }})

            return {
                "content": result["content"],
                "agent": self.name,
                "model": result["model"],
                "rate_limited": False,
                "usage": result["usage"],
            }

        except Exception as e:
            logger.error(f"Agent '{self.name}' failed", extra={"props": {
                "agent": self.name, "error": str(e),
            }})
            return {
                "content": f"❌ Erro ao processar: {e}",
                "agent": self.name,
                "model": "error",
                "rate_limited": False,
                "usage": {},
            }

    async def stream_process(self, message: str, context: dict | None = None):
        """Yield response chunks in real-time."""
        # 1. Rate limiting (Simplified for stream)
        if self.rate_limiter:
            allowed = await self.rate_limiter.can_call_llm(self.name, self.level)
            if not allowed:
                yield {"type": "error", "content": "Rate limit atingido."}
                return

        # 2. Choose path
        from src.skills.mcp_tools import mcp_tools
        if mcp_tools.list_tools(agent_level=self.level):
            async for chunk in self._stream_process_simple(message, context):
                yield chunk
        else:
            async for chunk in self._stream_process_simple(message, context):
                yield chunk

    async def _stream_process_simple(self, message: str, context: dict | None = None):
        """Streaming single-shot processing."""
        system_prompt = self._system_prompt
        messages = [{"role": "system", "content": system_prompt}]
        
        if context and context.get("history"):
            messages.extend(self._inject_history(context["history"]))
            
        user_content = self._build_prompt(message, context)
        
        # Check for attachments for multimodal support
        if context and context.get("attachments"):
            user_message_dict = {
                "role": "user",
                "content": self._build_multimodal_content(user_content, context["attachments"])
            }
        else:
            user_message_dict = {"role": "user", "content": user_content}
            
        messages.append(user_message_dict)

        try:
            async for chunk in model_router.stream_generate(
                messages=messages,
                chain=self.config.model_chain,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            ):
                yield chunk
        except Exception as e:
            yield {"type": "error", "content": str(e)}

    def _build_multimodal_content(self, text: str, attachments: list[dict]) -> list[dict]:
        """Format content as list of parts (text + images + audio + text files).

        - image/* and application/pdf → image_url (Gemini fetches by URL natively)
        - audio/* → data URI base64 inline (via content_base64 pre-fetched by gateway)
        - text/plain, text/csv → injected as text part (via text_content pre-fetched)
        """
        parts = [{"type": "text", "text": text}]
        for att in attachments:
            mime = att.get("mime_type", "")
            filename = att.get("filename", "arquivo")

            if mime.startswith("image/") or mime == "application/pdf":
                url = att.get("public_url", "")
                if url:
                    parts.append({"type": "image_url", "image_url": {"url": url}})

            elif mime.startswith("audio/"):
                b64 = att.get("content_base64")
                if b64:
                    # Data URI format — LiteLLM translates this to Gemini inline_data
                    data_uri = f"data:{mime};base64,{b64}"
                    parts.append({"type": "image_url", "image_url": {"url": data_uri}})
                else:
                    # Fallback: mention the file in text so agent is aware
                    parts[0]["text"] += f"\n[Áudio anexado: {filename}]"

            elif mime in ("text/plain", "text/csv"):
                content = att.get("text_content")
                if content:
                    parts.append({"type": "text", "text": f"\n[Arquivo: {filename}]\n{content}"})

        return parts

    def _inject_history(self, history: list[dict]) -> list[dict]:
        """Convert persistent messages to LLM roles."""
        injected = []
        for msg in history[-10:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "assistant":
                injected.append({"role": "assistant", "content": content})
            else:
                injected.append({"role": "user", "content": content})
        return injected

    def _build_prompt(self, message: str, context: dict | None = None) -> str:
        """Build ONLY the user part of the prompt (context + message)."""
        parts = []

        if context:
            if context.get("task"):
                parts.append(f"\n## Task Atual\n{context['task']}")

            if context.get("working_memory"):
                parts.append(f"\n## Memória de Trabalho\n{context['working_memory']}")

        parts.append(f"\n## Mensagem\n{message}")

        return "\n".join(parts)

    async def think(self, query: str, context: dict | None = None) -> dict:
        """
        Process with enhanced thinking using Tree-of-Thought for complex queries.

        FASE 0 #1: Integrates tot_service as pre-reasoning context enrichment.
        - Simple queries → process() normal (ReAct loop with tools)
        - Complex queries → tot_service.quick_think() injects pre-reasoning into context
          → process() runs normally through ReAct loop (tools always available)

        The ToT pre-reasoning becomes a contextual hint in the user message, allowing
        the ReAct loop to use both tool results AND deep analytical thinking.
        """
        if not self._is_complex_query(query):
            return await self.process(query, context)

        # Complex query: quick ToT pre-reasoning → inject → ReAct (tools still run)
        logger.info(f"Agent '{self.name}' detected complex query — using ToT pre-reasoning")

        from src.engine.tot_service import tot_service

        tot_context = ""
        if context:
            if context.get("working_memory"):
                tot_context += f"## Memória de Trabalho\n{context['working_memory']}\n\n"
            if context.get("task"):
                tot_context += f"## Task Atual\n{context['task']}\n\n"

        # Quick single-strategy pre-reasoning (low latency, ~1 LLM call)
        enriched_context = dict(context or {})
        try:
            pre_reasoning = await tot_service.quick_think(query=query, context=tot_context)
            enriched_context["tot_pre_reasoning"] = pre_reasoning
            logger.info(
                f"Agent '{self.name}' ToT pre-reasoning injected",
                extra={"props": {"agent": self.name, "pre_reasoning_chars": len(pre_reasoning)}},
            )
        except Exception as e:
            logger.warning(f"Agent '{self.name}' ToT pre-reasoning failed, continuing without it: {e}")

        # Run through normal process() → ReAct loop (tools always available)
        return await self.process(query, enriched_context)

    def _is_complex_query(self, query: str) -> bool:
        """
        Detect if query requires deep Tree-of-Thought analysis.

        Triggers:
        - Keywords: analise, compare, avalie, decida, planeje, etc.
        - Long queries (> 200 chars)
        """
        complex_keywords = [
            "analise", "analisar", "compare", "comparar", "avalie", "avaliar",
            "decida", "decidir", "planeje", "planejar", "estratégia", "estratégico",
            "prós e contras", "trade-off", "escolha", "escolher",
            "recomende", "recomendar", "sugira", "sugerir", "sugestão",
            "arquitetura", "design", "desenho", "estrutura",
            "vantagens e desvantagens", "melhor opção", "qual escolher",
        ]

        query_lower = query.lower()

        # Check keywords
        has_keyword = any(kw in query_lower for kw in complex_keywords)

        # Check length (long queries often need deep analysis)
        is_long = len(query) > 200

        return has_keyword or is_long

    def __repr__(self) -> str:
        return f"<Agent name='{self.name}' role='{self.role}' level='{self.level}'>"
