"""
Agent Optimus — ReflectionEngine CRON Handlers.
FASE 0 #7: Connects CronScheduler weekly job to ReflectionEngine.

Call Path:
  CronScheduler._execute_job("weekly_reflection")
    → EventBus.emit(CRON_TRIGGERED, {job_name: "weekly_reflection"})
      → on_reflection_cron_triggered(event)
        → reflection_engine.analyze_recent(agent_name="optimus", days=7)
          → daily_notes.get_date() → collect last 7 days of notes
          → _analyze_topics() → count topic mentions
          → _detect_gaps() → detect knowledge gaps via failure indicators
          → _generate_suggestions() → actionable suggestions
        → report.to_markdown()
        → reflection_engine.save_report(report)
          → workspace/memory/reflections/optimus/<year-W<week>>.md
"""

import logging

from src.core.events import Event, EventType, event_bus

logger = logging.getLogger(__name__)


async def on_reflection_cron_triggered(event: Event) -> None:
    """Generate weekly reflection report when the weekly_reflection cron job fires."""
    data = event.data
    job_name = data.get("job_name", "")

    if job_name != "weekly_reflection":
        return  # Not our job — ignore

    logger.info("FASE 0 #7: Weekly reflection cron triggered — analyzing last 7 days")

    from src.engine.reflection_engine import reflection_engine

    try:
        # Analyze last 7 days of interactions
        report = await reflection_engine.analyze_recent(
            agent_name="optimus",
            days=7,
        )

        logger.info(
            f"FASE 0 #7: Reflection analysis complete — "
            f"{report.total_interactions} interactions, {len(report.topics)} topics, "
            f"{len(report.gaps)} gaps detected"
        )

        # Save report to workspace
        report_path = await reflection_engine.save_report(report)

        logger.info(f"FASE 0 #7: Reflection report saved to {report_path}")

    except Exception as e:
        logger.error(f"FASE 0 #7: Weekly reflection failed: {e}", exc_info=True)


def register_reflection_handlers() -> None:
    """
    Register weekly reflection cron handler on EventBus.
    Called from main.py lifespan startup (FASE 0 #7).
    """
    event_bus.on(EventType.CRON_TRIGGERED.value, on_reflection_cron_triggered)
    logger.info("FASE 0 #7: Weekly reflection handler registered on EventBus")
