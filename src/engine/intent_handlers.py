"""
Agent Optimus — IntentPredictor CRON Handlers.
FASE 0 #4: Connects CronScheduler weekly job to IntentPredictor.

Call Path:
  CronScheduler._execute_job("pattern_learning")
    → EventBus.emit(CRON_TRIGGERED, {job_name: "pattern_learning"})
      → on_pattern_learning_triggered(event)
        → intent_predictor.learn_patterns(agent_name="optimus", days=30)
          → daily_notes.get_date() → collect last 30 days
          → _extract_actions() → detect actions via keywords
          → Analyze weekdays + time_slots for each action
          → Calculate confidence based on frequency
        → intent_predictor.save_patterns(agent_name, patterns)
          → workspace/patterns/optimus.json
"""

import logging

from src.core.events import Event, EventType, event_bus

logger = logging.getLogger(__name__)


async def on_pattern_learning_triggered(event: Event) -> None:
    """Learn behavioral patterns when the pattern_learning cron job fires."""
    data = event.data
    job_name = data.get("job_name", "")

    if job_name != "pattern_learning":
        return  # Not our job — ignore

    logger.info("FASE 0 #4: Pattern learning cron triggered — analyzing last 30 days")

    from src.engine.intent_predictor import intent_predictor

    try:
        # Learn patterns from last 30 days of interactions
        patterns = await intent_predictor.learn_patterns(
            agent_name="optimus",
            days=30,
        )

        logger.info(
            f"FASE 0 #4: Pattern learning complete — "
            f"{len(patterns)} patterns detected"
        )

        # Save patterns to workspace
        patterns_path = await intent_predictor.save_patterns("optimus", patterns)

        logger.info(f"FASE 0 #4: Patterns saved to {patterns_path}")

        # Log top 3 patterns for debugging
        if patterns:
            top_patterns = patterns[:3]
            for p in top_patterns:
                logger.info(
                    f"FASE 0 #4: Top pattern — {p.action}: "
                    f"frequency={p.frequency}, confidence={p.confidence}, "
                    f"weekdays={p.weekdays}, time_slots={p.time_slots}"
                )

    except Exception as e:
        logger.error(f"FASE 0 #4: Pattern learning failed: {e}", exc_info=True)


def register_intent_handlers() -> None:
    """
    Register pattern learning cron handler on EventBus.
    Called from main.py lifespan startup (FASE 0 #4).
    """
    event_bus.on(EventType.CRON_TRIGGERED.value, on_pattern_learning_triggered)
    logger.info("FASE 0 #4: Pattern learning handler registered on EventBus")
