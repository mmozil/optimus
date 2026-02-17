"""
Agent Optimus — Optimus (Lead Orchestrator).
The head of the squad. Classifies intent, delegates to specialists, synthesizes results.
"""

import logging

from src.agents.base import AgentConfig, BaseAgent
from src.identity.personas import PersonaSelector

# Phase 10 & 11 Integrations
from src.memory.session_bootstrap import session_bootstrap
from src.memory.auto_journal import auto_journal
from src.core.context_awareness import context_awareness

logger = logging.getLogger(__name__)


class OptimusAgent(BaseAgent):
    """
    Lead Orchestrator agent.
    Enhanced with intent classification, delegation, and proactive capabilities.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.persona_selector = PersonaSelector()

    async def process(self, message: str, context: dict | None = None) -> dict:
        """Process with context enrichment (Memory + Time + Persona + Sentiment)."""
        # 1. Base Context (Memory + Ambient)
        # Bootstrapped context (SOUL + MEMORY) - loaded in Gateway, retrieved from cache
        boot_ctx = await session_bootstrap.load_context(self.name)
        bootstrap_prompt = boot_ctx.build_prompt()

        # Ambient context (Time, Day, Business Hours)
        ctx = context_awareness.build_context()
        ctx = await context_awareness.enrich_with_activity(ctx, self.name)
        ambient_prompt = context_awareness.build_context_prompt(ctx)

        # 2. Tone Instruction (from Gateway emotional analysis)
        tone_instruction = context.get("tone_instruction", "") if context else ""

        # 3. Classify intent and adapt persona
        persona = self.persona_selector.get_persona_for_message(message)
        persona_prompt = self.persona_selector.get_persona_prompt(message)

        # 4. Add persona to context
        enriched_context = dict(context) if context else {}
        enriched_context["persona"] = persona

        # 5. Temporarily adapt temperature based on persona
        original_temp = self.config.temperature
        self.config.temperature = persona.get("temperature", original_temp)

        # 6. Compose Dynamic System Prompt
        # Order: Original System -> Bootstrap (Memory) -> Ambient (Time) -> Tone -> Persona
        original_system = self._system_prompt

        dynamic_sys_prompt = [
            original_system,
            bootstrap_prompt,
            ambient_prompt,
            f"## Current Tone Instruction\n{tone_instruction}" if tone_instruction else "",
            persona_prompt
        ]

        # Filter empty strings and join
        self._system_prompt = "\n\n".join([p for p in dynamic_sys_prompt if p])

        try:
            # 7. Execute Process
            result = await super().process(message, enriched_context)

            # 8. Post-Process: Auto-Journaling (Proactive Learning)
            response_text = result.get("content", "")
            if response_text:
                # Check if auto-journaling is appropriate (could use filters here)
                await auto_journal.process_interaction(message, response_text)

            # Enrich result metadata
            result["persona"] = persona["name"]
            result["intent"] = persona.get("intent", "default")

            if "metadata" not in result:
                result["metadata"] = {}

            result["metadata"]["tone_applied"] = tone_instruction
            result["metadata"]["ambient_context"] = f"{ctx.day_of_week}, {ctx.local_time}"

            return result

        finally:
            # Restore original values to avoid pollution between requests
            self.config.temperature = original_temp
            self._system_prompt = original_system

    async def classify_and_delegate(self, message: str) -> dict:
        """
        Classify the message intent and suggest which agent should handle it.
        Returns routing info (for future orchestration).
        """
        intent = self.persona_selector.classify_intent(message)

        # Routing map based on intent
        routing = {
            "debug": "friday",
            "planning": "optimus",
            "analysis": "optimus",
            "creative": "optimus",
            "education": "fury",
            "alert": "friday",
            "default": "optimus",
        }

        target_agent = routing.get(intent, "optimus")

        return {
            "intent": intent,
            "target_agent": target_agent,
            "message": message,
            "confidence": 0.7,
        }
