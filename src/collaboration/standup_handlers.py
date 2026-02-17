"""
Agent Optimus — Standup CRON Handlers.
FASE 0 #23: Connects CronScheduler daily job to StandupGenerator.

Call Path:
  CronScheduler._execute_job("daily_standup")
    → EventBus.emit(CRON_TRIGGERED, {job_name: "daily_standup"})
      → on_standup_cron_triggered(event)
        → standup_generator.generate_team_standup()
          → ActivityFeed.get_daily_summary() + TaskManager.list_tasks()
          → report stored in ActivityFeed (type: "standup_generated")
"""

import logging
from pathlib import Path

from src.core.events import Event, EventType, event_bus
from src.collaboration.activity_feed import activity_feed

logger = logging.getLogger(__name__)

STANDUP_DIR = Path(__file__).parent.parent.parent / "workspace" / "standups"


async def on_standup_cron_triggered(event: Event) -> None:
    """Generate team standup when the daily_standup cron job fires."""
    data = event.data
    job_name = data.get("job_name", "")

    if job_name != "daily_standup":
        return  # Not our job — ignore

    logger.info("FASE 0 #23: Daily standup cron triggered — generating report")

    from src.collaboration.standup_generator import standup_generator
    from datetime import datetime, timezone

    try:
        report = await standup_generator.generate_team_standup()

        # Store report as activity so /standup reflects it
        await activity_feed.record(
            activity_type="standup_generated",
            message="Standup diário gerado automaticamente",
            agent_name="cron_scheduler",
            metadata={"report_preview": report[:200]},
        )

        # Persist to workspace/standups/<date>.md
        STANDUP_DIR.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        report_file = STANDUP_DIR / f"{date_str}.md"
        report_file.write_text(report, encoding="utf-8")

        logger.info(f"FASE 0 #23: Standup report saved to {report_file}")

    except Exception as e:
        logger.error(f"FASE 0 #23: Standup generation failed: {e}")


def register_standup_handlers() -> None:
    """
    Register standup cron handler on EventBus.
    Called from main.py lifespan startup (FASE 0 #23).
    """
    event_bus.on(EventType.CRON_TRIGGERED.value, on_standup_cron_triggered)
    logger.info("FASE 0 #23: Standup handler registered on EventBus")
