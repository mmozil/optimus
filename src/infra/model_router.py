"""
Agent Optimus — Multi-Model Router (Phase 12).
Async routing via LiteLLM with native Google Generative AI fallback.
Dynamic configuration via .env (MODEL_MAPPINGS and MODEL_FALLBACKS).
"""

import json
import logging
import os
import time
from typing import Any

# Optional dependencies - Exposed at module level for mocking/testing
class DummyModule:
    def __getattr__(self, name):
        return None
    async def acompletion(self, *args, **kwargs):
        raise ImportError("LiteLLM not installed")
    async def generate_content_async(self, *args, **kwargs):
        raise ImportError("Google Generative AI not installed")

litellm = DummyModule()
genai = DummyModule()

LITELLM_AVAILABLE = False
GOOGLE_GENAI_AVAILABLE = False

try:
    import litellm as _litellm
    litellm = _litellm
    LITELLM_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    pass

try:
    from google import genai as _genai
    genai = _genai
    GOOGLE_GENAI_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    pass

_GENAI_CLIENT = None  # initialized in _configure_api_keys

from src.core.config import settings

logger = logging.getLogger(__name__)

# Suppress litellm's verbose logging unless DEBUG
if LITELLM_AVAILABLE:
    litellm.suppress_debug_info = not settings.DEBUG
    if not settings.DEBUG:
        import logging as _logging
        _logging.getLogger("LiteLLM").setLevel(_logging.ERROR)
        _logging.getLogger("litellm").setLevel(_logging.ERROR)

# ============================================
# Default Model Configuration (Fallbacks)
# ============================================

DEFAULT_MODEL_MAP: dict[str, str] = {
    "gemini-2.5-pro": "gemini/gemini-2.5-pro",
    "gemini-2.5-flash": "gemini/gemini-2.5-flash",
    "gemini-2.0-flash": "gemini/gemini-2.0-flash",
    "gpt-4o": "gpt-4o",
    "gpt-4o-mini": "gpt-4o-mini",
    "claude-sonnet": "anthropic/claude-sonnet-4-5-20250929",
    "groq-llama": "groq/llama-3.3-70b-versatile",
}

DEFAULT_FALLBACK_CHAINS: dict[str, list[str]] = {
    "default": ["gemini-2.5-flash", "gpt-4o-mini", "groq-llama"],
    "complex": ["gemini-2.5-flash", "gemini-2.5-pro", "gpt-4o"],
    "economy": ["groq-llama", "gemini-2.0-flash"],
    "heartbeat": ["gemini-2.0-flash"],
}

# Compatibility aliases for tests and other modules
MODEL_NAME_MAP = DEFAULT_MODEL_MAP
FALLBACK_CHAINS = DEFAULT_FALLBACK_CHAINS


def _configure_api_keys() -> None:
    """Set API keys in environment for LiteLLM to discover."""
    global _GENAI_CLIENT
    if settings.GOOGLE_API_KEY:
        os.environ.setdefault("GEMINI_API_KEY", settings.GOOGLE_API_KEY)
        if GOOGLE_GENAI_AVAILABLE:
            _GENAI_CLIENT = genai.Client(api_key=settings.GOOGLE_API_KEY)
    if settings.OPENAI_API_KEY:
        os.environ.setdefault("OPENAI_API_KEY", settings.OPENAI_API_KEY)
    if settings.ANTHROPIC_API_KEY:
        os.environ.setdefault("ANTHROPIC_API_KEY", settings.ANTHROPIC_API_KEY)
    if settings.GROQ_API_KEY:
        os.environ.setdefault("GROQ_API_KEY", settings.GROQ_API_KEY)


class ModelRouter:
    """Routes LLM calls with automatic failover between models."""

    def __init__(self) -> None:
        _configure_api_keys()
        self._load_dynamic_config()
        if not LITELLM_AVAILABLE:
            logger.warning("LiteLLM not available, will use native Google Generative AI for Gemini models")
        if not GOOGLE_GENAI_AVAILABLE and not LITELLM_AVAILABLE:
            logger.error("No LLM clients available (LiteLLM and Google GenAI missing)")

    def _load_dynamic_config(self) -> None:
        """Load model mappings and fallbacks from settings."""
        self.model_map = DEFAULT_MODEL_MAP.copy()
        self.fallback_chains = DEFAULT_FALLBACK_CHAINS.copy()

        # Override with dynamic mappings
        if settings.MODEL_MAPPINGS and settings.MODEL_MAPPINGS != "{}":
            try:
                dynamic_map = json.loads(settings.MODEL_MAPPINGS)
                self.model_map.update(dynamic_map)
            except json.JSONDecodeError:
                pass

        # Override with dynamic fallbacks
        if settings.MODEL_FALLBACKS and settings.MODEL_FALLBACKS != "{}":
            try:
                dynamic_fallbacks = json.loads(settings.MODEL_FALLBACKS)
                self.fallback_chains.update(dynamic_fallbacks)
            except json.JSONDecodeError:
                pass

    def _resolve_model(self, short_name: str) -> str:
        """Resolve a short model name to LiteLLM format."""
        return self.model_map.get(short_name, short_name)

    async def generate_with_history(
        self,
        messages: list[dict],
        chain: str = "default",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict] | None = None,
        stream: bool = False,
    ) -> Any:
        """Generate response from history (for ReAct loop)."""
        if stream:
            return self.stream_generate(messages, chain, temperature, max_tokens, tools)
            
        return await self._call_with_fallback(
            messages=messages,
            chain=chain,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            include_raw=True,
        )

    async def generate(self, prompt: str, **kwargs) -> Any:
        """Simple generation for backward compatibility."""
        messages = [{"role": "user", "content": prompt}]
        if kwargs.get("stream"):
            return self.stream_generate(messages, **kwargs)
        return await self._call_with_fallback(messages=messages, **kwargs)

    async def stream_generate(
        self,
        messages: list[dict],
        chain: str = "default",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict] | None = None,
    ):
        """Yield tokens and tool calls in real-time."""
        models = self.fallback_chains.get(chain, self.fallback_chains.get("default", []))
        last_error = None

        for short_name in models:
            try:
                # 1. Try LiteLLM Streaming
                if LITELLM_AVAILABLE:
                    async for chunk in self._lite_llm_stream(
                        short_name, messages, temperature, max_tokens, tools
                    ):
                        yield chunk
                    return

                # 2. Try Native Gemini Streaming
                elif GOOGLE_GENAI_AVAILABLE and "gemini" in short_name:
                    async for chunk in self._native_gemini_stream(
                        short_name, messages, temperature, max_tokens, tools
                    ):
                        yield chunk
                    return

            except Exception as e:
                last_error = e
                logger.warning(f"Streaming model {short_name} failed: {e}")
                continue

        raise RuntimeError(f"All models in chain {chain} failed for streaming. Last: {last_error}")

    async def _call_with_fallback(
        self,
        messages: list[dict],
        chain: str = "default",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict] | None = None,
        include_raw: bool = False,
    ) -> dict:
        """Core: try models in chain until success."""
        models = self.fallback_chains.get(chain, self.fallback_chains.get("default", []))
        last_error = None

        for short_name in models:
            try:
                # 1. Try LiteLLM if available OR if we are in a test (LITELLM_AVAILABLE will be false but litellm is patched)
                # To support tests, we try litellm call first and catch ImportError later if it really fails
                return await self._lite_llm_call(
                    short_name, messages, temperature, max_tokens, tools, include_raw
                )
            except (ImportError, Exception) as e:
                # If it's a Gemini model, try native fallback
                if GOOGLE_GENAI_AVAILABLE and "gemini" in short_name:
                    try:
                        return await self._native_gemini_call(
                            short_name, messages, temperature, max_tokens, tools, include_raw
                        )
                    except Exception as ge:
                        last_error = ge
                        continue
                
                last_error = e
                logger.warning(f"Model {short_name} failed: {e}")
                continue

        raise RuntimeError(f"All models in chain {chain} failed. Last: {last_error}")

    async def _lite_llm_call(self, short_name, messages, temp, tokens, tools, include_raw):
        """Standard LiteLLM call."""
        litellm_model = self._resolve_model(short_name)
        kwargs = {
            "model": litellm_model,
            "messages": messages,
            "temperature": temp,
            "max_tokens": tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        start = time.monotonic()
        response = await litellm.acompletion(**kwargs)
        duration_ms = (time.monotonic() - start) * 1000

        choice = response.choices[0]
        message = choice.message
        
        # Tool extraction
        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                args = tc.function.arguments
                if isinstance(args, str):
                    args = json.loads(args)
                tool_calls.append({
                    "id": tc.id, "name": tc.function.name, "arguments": args
                })

        logger.info(f"LLM Succeeded ({short_name}) in {duration_ms:.0f}ms")

        result = {
            "content": message.content or "",
            "model": short_name,
            "usage": {
                "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                "completion_tokens": getattr(response.usage, "completion_tokens", 0),
            },
            "tool_calls": tool_calls,
            "finish_reason": choice.finish_reason or "stop",
        }
        if include_raw:
            result["raw_message"] = message
        return result

    async def _download_image(self, url: str) -> dict | None:
        """Download image from URL and return as Gemini-compatible part."""
        import httpx
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=10.0)
                resp.raise_for_status()
                
                content_type = resp.headers.get("content-type", "image/jpeg")
                return {
                    "mime_type": content_type,
                    "data": resp.content
                }
        except Exception as e:
            logger.error(f"Failed to download image from {url}: {e}")
            return None

    async def _prepare_native_messages(self, messages: list[dict]) -> tuple[list[dict], str | None]:
        """Convert standard messages to native Gemini format with image handling."""
        native_messages = []
        system_instr = None
        
        # Extract system instruction
        system_msg = next((m for m in messages if m["role"] == "system"), None)
        if system_msg:
            system_instr = system_msg["content"]

        for m in messages:
            if m["role"] == "system":
                continue
            
            parts = []
            content = m.get("content", "")
            
            # Handle multimodal list
            if isinstance(content, list):
                for p in content:
                    if p.get("type") == "text":
                        parts.append({"text": p.get("text", "")})
                    elif p.get("type") == "image_url":
                        url = p["image_url"]["url"]
                        image_data = await self._download_image(url)
                        if image_data:
                            import base64
                            data = image_data["data"]
                            parts.append({"inline_data": {
                                "mime_type": image_data["mime_type"],
                                "data": base64.b64encode(data).decode() if isinstance(data, bytes) else data,
                            }})
            else:
                parts.append({"text": content})
                
            native_messages.append({
                "role": "user" if m["role"] == "user" else "model", 
                "parts": parts
            })
            
        return native_messages, system_instr

    async def _native_gemini_call(self, short_name, messages, temp, tokens, tools, include_raw):
        """Fallback to native Gemini SDK (google-genai)."""
        if "2.5-pro" in short_name: model_id = "gemini-1.5-pro"
        else: model_id = "gemini-1.5-flash"

        native_messages, system_instr = await self._prepare_native_messages(messages)

        config_kwargs = {"temperature": temp, "max_output_tokens": tokens}
        if system_instr:
            config_kwargs["system_instruction"] = system_instr
        config = genai.types.GenerateContentConfig(**config_kwargs)

        start = time.monotonic()
        response = await _GENAI_CLIENT.aio.models.generate_content(
            model=model_id,
            contents=native_messages,
            config=config,
        )
        duration_ms = (time.monotonic() - start) * 1000

        logger.info(f"Native Gemini Succeeded ({model_id}) in {duration_ms:.0f}ms")

        usage = {"prompt_tokens": 0, "completion_tokens": 0}
        if response.usage_metadata:
            usage["prompt_tokens"] = response.usage_metadata.prompt_token_count or 0
            usage["completion_tokens"] = response.usage_metadata.candidates_token_count or 0

        result = {
            "content": response.text,
            "model": f"native/{model_id}",
            "usage": usage,
            "tool_calls": [],
            "finish_reason": "stop",
        }
        if include_raw:
            from types import SimpleNamespace
            result["raw_message"] = SimpleNamespace(content=response.text, tool_calls=[])
        return result

    async def _lite_llm_stream(self, short_name, messages, temp, tokens, tools):
        """Yield tokens from LiteLLM."""
        litellm_model = self._resolve_model(short_name)
        kwargs = {
            "model": litellm_model,
            "messages": messages,
            "temperature": temp,
            "max_tokens": tokens,
            "stream": True
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = await litellm.acompletion(**kwargs)
        async for chunk in response:
            delta = chunk.choices[0].delta
            # Yield token
            if delta.content:
                yield {"type": "token", "content": delta.content}
            
            # Yield tool calls if any (LiteLLM handles partials)
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    yield {"type": "tool_call", "tool_call": tc}

    async def _native_gemini_stream(self, short_name, messages, temp, tokens, tools):
        """Yield tokens from native Gemini (google-genai)."""
        model_id = self._resolve_model(short_name).replace("gemini/", "")

        native_messages, system_instr = await self._prepare_native_messages(messages)

        config_kwargs = {"temperature": temp, "max_output_tokens": tokens}
        if system_instr:
            config_kwargs["system_instruction"] = system_instr
        config = genai.types.GenerateContentConfig(**config_kwargs)

        async for chunk in await _GENAI_CLIENT.aio.models.generate_content_stream(
            model=model_id,
            contents=native_messages,
            config=config,
        ):
            if chunk.text:
                yield {
                    "type": "token",
                    "content": chunk.text,
                    "model": f"native/{model_id}"
                }

    async def embed_text(self, text: str, model: str = "text-embedding-004") -> list[float]:
        """
        Generate embeddings for text.
        Tries LiteLLM first, falls back to native Google GenAI.
        """
        # 1. Try LiteLLM
        if LITELLM_AVAILABLE:
            try:
                response = await litellm.aembedding(
                    model=f"gemini/{model}",
                    input=[text]
                )
                return response.data[0].embedding
            except Exception as e:
                logger.warning(f"LiteLLM embedding failed: {e}")

        # 2. Try Native Gemini
        if GOOGLE_GENAI_AVAILABLE and _GENAI_CLIENT:
            try:
                result = await _GENAI_CLIENT.aio.models.embed_content(
                    model=model,
                    contents=text,
                )
                return result.embeddings[0].values
            except Exception as e:
                logger.error(f"Native embedding failed: {e}")
                raise

        raise RuntimeError("No embedding provider available")


# Singleton
model_router = ModelRouter()
