"""
Agent Optimus — Multi-Model Router with failover.
Gemini 2.5 Pro → Gemini 2.5 Flash → Gemini 2.0 Flash → Error
"""

import logging
from typing import Any

import google.generativeai as genai

from src.core.config import settings

logger = logging.getLogger(__name__)


# Model tiers for different use cases
MODEL_TIERS = {
    "pro": "gemini-2.5-pro",
    "flash": "gemini-2.5-flash",
    "economy": "gemini-2.0-flash",
}

# Fallback chains by use case
FALLBACK_CHAINS = {
    "default": ["gemini-2.5-flash", "gemini-2.0-flash"],
    "complex": ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"],
    "economy": ["gemini-2.0-flash"],
    "heartbeat": ["gemini-2.0-flash"],
}


class ModelRouter:
    """Routes LLM calls with automatic failover between models."""

    def __init__(self):
        if settings.GOOGLE_API_KEY:
            genai.configure(api_key=settings.GOOGLE_API_KEY)
        self._models: dict[str, Any] = {}

    def _get_model(self, model_name: str) -> genai.GenerativeModel:
        """Lazy-load and cache model instances."""
        if model_name not in self._models:
            self._models[model_name] = genai.GenerativeModel(model_name)
        return self._models[model_name]

    async def generate(
        self,
        prompt: str,
        chain: str = "default",
        system_instruction: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> dict:
        """Generate response with automatic failover through model chain."""
        models = FALLBACK_CHAINS.get(chain, FALLBACK_CHAINS["default"])
        last_error = None

        for model_name in models:
            try:
                model = self._get_model(model_name)
                config = genai.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )

                response = model.generate_content(
                    prompt,
                    generation_config=config,
                )

                logger.info(
                    "LLM call succeeded",
                    extra={"props": {
                        "model": model_name,
                        "chain": chain,
                        "prompt_length": len(prompt),
                    }},
                )

                return {
                    "content": response.text,
                    "model": model_name,
                    "usage": {
                        "prompt_tokens": getattr(response.usage_metadata, "prompt_token_count", 0),
                        "completion_tokens": getattr(response.usage_metadata, "candidates_token_count", 0),
                    },
                }

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Model {model_name} failed, trying next in chain",
                    extra={"props": {"model": model_name, "error": str(e)}},
                )
                continue

        raise RuntimeError(f"All models in chain '{chain}' failed. Last error: {last_error}")


# Singleton
model_router = ModelRouter()
