"""
Agent Optimus — Decay Event Handlers (FASE 14).
Connects CronScheduler → decay_service.archive_stale().

Call Path:
    cron_scheduler (every 168h) → CRON_TRIGGERED("decay_archiving")
      → EventBus → on_decay_archiving_triggered()
        → decay_service.archive_stale(threshold=ARCHIVE_THRESHOLD)
"""

import logging

from src.core.events import Event, EventType, event_bus

logger = logging.getLogger(__name__)


async def on_decay_archiving_triggered(event: Event) -> None:
    """Handle CRON_TRIGGERED for 'decay_archiving' job."""
    payload = event.data if hasattr(event, "data") else {}
    job_name = payload.get("job_name", "")
    if job_name != "decay_archiving":
        return

    logger.info("FASE 14: Running weekly decay archiving cron...")
    try:
        from src.core.decay_service import ARCHIVE_THRESHOLD, decay_service
        summary = await decay_service.archive_stale(threshold=ARCHIVE_THRESHOLD)
        logger.info(f"FASE 14: Archiving complete — {summary}")
    except Exception as e:
        logger.error(f"FASE 14: Decay archiving handler failed: {e}")


def register_decay_handlers() -> None:
    """Register CRON_TRIGGERED handler for 'decay_archiving' job."""
    event_bus.on(EventType.CRON_TRIGGERED.value, on_decay_archiving_triggered)
    logger.info("FASE 14: Decay archiving handler registered")
