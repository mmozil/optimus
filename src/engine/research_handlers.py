"""
Agent Optimus — ProactiveResearcher CRON Handlers.
FASE 0 #6: Connects CronScheduler 3x/day job to ProactiveResearcher.

Call Path:
  CronScheduler._execute_job("proactive_research")
    → EventBus.emit(CRON_TRIGGERED, {job_name: "proactive_research"})
      → on_research_cron_triggered(event)
        → proactive_researcher.run_check_cycle()
          → check_source() → fetch_rss | fetch_github | fetch_url
          → generate_briefing(findings)
          → save_briefing() → workspace/research/findings/optimus-<date>.md
"""

import logging
from pathlib import Path

from src.core.events import Event, EventType, event_bus

logger = logging.getLogger(__name__)

FINDINGS_DIR = Path(__file__).parent.parent.parent / "workspace" / "research" / "findings"


async def on_research_cron_triggered(event: Event) -> None:
    """Run proactive research when the proactive_research cron job fires."""
    data = event.data
    job_name = data.get("job_name", "")

    if job_name != "proactive_research":
        return  # Not our job — ignore

    logger.info("FASE 0 #6: Proactive research cron triggered — checking sources")

    from src.engine.proactive_researcher import proactive_researcher

    try:
        # Run full check cycle (finds due sources, fetches, generates briefing)
        findings = await proactive_researcher.run_check_cycle()

        logger.info(f"FASE 0 #6: Found {len(findings)} new items from research sources")

        # Generate briefing from findings (even if empty — shows "No new findings")
        briefing = proactive_researcher.generate_briefing(findings)

        # Save briefing to workspace/research/findings/
        FINDINGS_DIR.mkdir(parents=True, exist_ok=True)
        briefing_path = await proactive_researcher.save_briefing(briefing, agent_name="optimus")

        logger.info(f"FASE 0 #6: Research briefing saved to {briefing_path}")

    except Exception as e:
        logger.error(f"FASE 0 #6: Proactive research failed: {e}", exc_info=True)


def register_research_handlers() -> None:
    """
    Register proactive research cron handler on EventBus.
    Called from main.py lifespan startup (FASE 0 #6).
    """
    event_bus.on(EventType.CRON_TRIGGERED.value, on_research_cron_triggered)
    logger.info("FASE 0 #6: Proactive research handler registered on EventBus")
