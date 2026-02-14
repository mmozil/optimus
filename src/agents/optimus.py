"""
Agent Optimus — Optimus (Lead Orchestrator).
The head of the squad. Classifies intent, delegates to specialists, synthesizes results.
"""

import logging

from src.agents.base import AgentConfig, BaseAgent
from src.identity.personas import PersonaSelector

logger = logging.getLogger(__name__)


class OptimusAgent(BaseAgent):
    """
    Lead Orchestrator agent.
    Enhanced with intent classification and delegation capabilities.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.persona_selector = PersonaSelector()

    async def process(self, message: str, context: dict | None = None) -> dict:
        """Process with persona adaptation based on intent."""
        # 1. Classify intent and adapt persona
        persona = self.persona_selector.get_persona_for_message(message)
        persona_prompt = self.persona_selector.get_persona_prompt(message)

        # 2. Add persona to context
        enriched_context = dict(context) if context else {}
        enriched_context["persona"] = persona

        # 3. Temporarily adapt temperature based on persona
        original_temp = self.config.temperature
        self.config.temperature = persona.get("temperature", original_temp)

        # 4. Add persona instruction to the system prompt temporarily
        original_system = self._system_prompt
        self._system_prompt = original_system + persona_prompt

        try:
            result = await super().process(message, enriched_context)
            result["persona"] = persona["name"]
            result["intent"] = persona.get("intent", "default")
            return result
        finally:
            # Restore original values
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
            "confidence": 0.7,  # Will be enhanced by UncertaintyQuantifier in Phase 2
        }
