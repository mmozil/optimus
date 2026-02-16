"""
Agent Optimus — Native Cron Jobs (Fase 10: Proactive Intelligence).
Predefined cron jobs for common use cases: morning briefing, monitoring,
scheduled research, and reminders.
"""

import logging
from datetime import datetime, timedelta, timezone

import httpx

from src.core.cron_scheduler import CronJob, cron_scheduler
from src.core.events import Event, event_bus

logger = logging.getLogger(__name__)

# ============================================
# Job Identifiers (prevent duplicates)
# ============================================
MORNING_BRIEFING_NAME = "morning_briefing"
MONITORING_ALERTS_NAME = "monitoring_alerts"
SCHEDULED_RESEARCH_NAME = "scheduled_research"


# ============================================
# Morning Briefing
# ============================================
def setup_morning_briefing(
    channel: str = "telegram",
    interval: str = "24h",
) -> str:
    """
    Create a recurring job that generates a daily briefing.

    The briefing includes: yesterday's standup summary, pending tasks,
    and today's scheduled events.

    Returns the job ID.
    """
    # Remove existing if any
    _remove_existing_by_name(MORNING_BRIEFING_NAME)

    job = CronJob(
        name=MORNING_BRIEFING_NAME,
        schedule_type="every",
        schedule_value=interval,
        payload="morning_briefing",
        session_target="main",
        channel=channel,
    )
    job_id = cron_scheduler.add(job)
    logger.info(f"Native cron: morning_briefing registered (every {interval}, channel={channel})")
    return job_id


# ============================================
# Monitoring Alerts
# ============================================
DEFAULT_MONITORING_URLS: list[str] = []


def setup_monitoring_alerts(
    urls: list[str] | None = None,
    channel: str = "telegram",
    interval: str = "30m",
) -> str:
    """
    Create a recurring job that checks health of configured URLs.

    If any URL returns non-200 status, an alert event is emitted.

    Returns the job ID.
    """
    _remove_existing_by_name(MONITORING_ALERTS_NAME)

    monitored_urls = urls or DEFAULT_MONITORING_URLS
    # Encode URLs in the payload as comma-separated
    payload = f"monitoring_alerts|{','.join(monitored_urls)}"

    job = CronJob(
        name=MONITORING_ALERTS_NAME,
        schedule_type="every",
        schedule_value=interval,
        payload=payload,
        session_target="isolated",
        channel=channel,
    )
    job_id = cron_scheduler.add(job)
    logger.info(f"Native cron: monitoring_alerts registered ({len(monitored_urls)} URLs, every {interval})")
    return job_id


async def check_monitoring_urls(urls: list[str], timeout: float = 10.0) -> list[dict]:
    """
    Check health of URLs and return results.

    Returns a list of dicts with url, status, ok, and error fields.
    """
    results: list[dict] = []

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for url in urls:
            try:
                response = await client.get(url)
                results.append({
                    "url": url,
                    "status": response.status_code,
                    "ok": 200 <= response.status_code < 400,
                    "error": "",
                })
            except httpx.HTTPError as e:
                results.append({
                    "url": url,
                    "status": 0,
                    "ok": False,
                    "error": str(e),
                })

    # Emit alert for failures
    failures = [r for r in results if not r["ok"]]
    if failures:
        await event_bus.emit(Event(
            type="system.alert",
            source="monitoring_alerts",
            data={
                "alert_type": "health_check_failed",
                "failures": failures,
                "total_checked": len(urls),
                "total_failed": len(failures),
            },
        ))
        logger.warning(f"Monitoring: {len(failures)}/{len(urls)} URLs unhealthy")

    return results


# ============================================
# Scheduled Research
# ============================================
def setup_scheduled_research(
    channel: str = "telegram",
    interval: str = "6h",
) -> str:
    """
    Create a recurring job that triggers proactive research checks.

    Integrates with ProactiveResearcher to check due sources and
    generate briefings.

    Returns the job ID.
    """
    _remove_existing_by_name(SCHEDULED_RESEARCH_NAME)

    job = CronJob(
        name=SCHEDULED_RESEARCH_NAME,
        schedule_type="every",
        schedule_value=interval,
        payload="scheduled_research",
        session_target="isolated",
        channel=channel,
    )
    job_id = cron_scheduler.add(job)
    logger.info(f"Native cron: scheduled_research registered (every {interval})")
    return job_id


# ============================================
# Reminder System
# ============================================
def create_reminder(
    message: str,
    when: datetime | str,
    channel: str = "telegram",
) -> str:
    """
    Create a one-shot reminder that fires at the specified time.

    Args:
        message: Reminder text to deliver.
        when: ISO datetime string or datetime object for when to fire.
        channel: Channel to deliver the reminder on.

    Returns the job ID.
    """
    if isinstance(when, datetime):
        when_iso = when.isoformat()
    else:
        when_iso = when

    job = CronJob(
        name=f"reminder_{datetime.now(timezone.utc).strftime('%H%M%S')}",
        schedule_type="at",
        schedule_value=when_iso,
        payload=f"reminder|{message}",
        session_target="main",
        channel=channel,
        delete_after_run=True,
    )
    job_id = cron_scheduler.add(job)
    logger.info(f"Native cron: reminder created for {when_iso}: {message[:50]}")
    return job_id


# ============================================
# Register All Native Jobs
# ============================================
def register_all_native_jobs(
    channel: str = "telegram",
    monitoring_urls: list[str] | None = None,
) -> dict[str, str]:
    """
    Register all predefined native cron jobs at boot time.

    Returns a dict of {job_name: job_id}.
    """
    ids: dict[str, str] = {}

    ids[MORNING_BRIEFING_NAME] = setup_morning_briefing(channel=channel)
    ids[MONITORING_ALERTS_NAME] = setup_monitoring_alerts(
        urls=monitoring_urls,
        channel=channel,
    )
    ids[SCHEDULED_RESEARCH_NAME] = setup_scheduled_research(channel=channel)

    logger.info(f"Native cron: {len(ids)} jobs registered at boot")
    return ids


# ============================================
# Helpers
# ============================================
def _remove_existing_by_name(name: str) -> None:
    """Remove any existing job with the given name to prevent duplicates."""
    for job in cron_scheduler.list_jobs():
        if job.name == name:
            cron_scheduler.remove(job.id)
            break
