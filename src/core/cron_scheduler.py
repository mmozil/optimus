"""
Agent Optimus — Cron Scheduler (Fase 10: Proactive Intelligence).
Persistent scheduler for recurring and one-shot jobs.
Jobs survive restarts (JSON persistence). Agents can self-schedule via MCP tools.
"""

import asyncio
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from src.core.events import Event, EventType, event_bus

logger = logging.getLogger(__name__)

CRON_DIR = Path(__file__).parent.parent.parent / "workspace" / "cron"
JOBS_FILE = CRON_DIR / "jobs.json"


@dataclass
class CronJob:
    """A scheduled job definition."""

    id: str = field(default_factory=lambda: str(uuid4())[:8])
    name: str = ""
    schedule_type: str = "at"  # "at" (one-shot), "every" (interval), "cron" (expression)
    schedule_value: str = ""  # ISO datetime / "30m" / "0 7 * * *"
    payload: str = ""  # Message or command to execute
    session_target: str = "main"  # "main" or "isolated"
    channel: str = ""  # Target channel (telegram, slack, etc.)
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_run: str = ""
    next_run: str = ""
    delete_after_run: bool = False
    run_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CronJob":
        # Filter only known fields
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)


class CronScheduler:
    """
    Persistent job scheduler.

    Features:
    - Jobs persist in JSON (survive restarts)
    - Supports: one-shot (at), recurring (every), cron expressions
    - Background loop checks every 60s for due jobs
    - Emits CRON_TRIGGERED events on the EventBus
    """

    def __init__(self):
        self._jobs: dict[str, CronJob] = {}
        self._task: asyncio.Task | None = None
        self._running = False
        CRON_DIR.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self) -> None:
        """Load jobs from persistent storage."""
        if JOBS_FILE.exists():
            try:
                data = json.loads(JOBS_FILE.read_text(encoding="utf-8"))
                for job_data in data:
                    job = CronJob.from_dict(job_data)
                    self._jobs[job.id] = job
                logger.info(f"Cron: loaded {len(self._jobs)} jobs from {JOBS_FILE}")
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Cron: failed to load jobs: {e}")

    def _save(self) -> None:
        """Persist jobs to JSON file."""
        data = [job.to_dict() for job in self._jobs.values()]
        JOBS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.debug(f"Cron: saved {len(data)} jobs")

    def add(self, job: CronJob) -> str:
        """
        Add a new scheduled job.

        Returns the job ID.
        """
        # Calculate next_run based on schedule
        job.next_run = self._calculate_next_run(job)
        self._jobs[job.id] = job
        self._save()
        logger.info(f"Cron: job '{job.name}' ({job.id}) added, next_run={job.next_run}")
        return job.id

    def remove(self, job_id: str) -> bool:
        """Remove a job by ID."""
        if job_id in self._jobs:
            name = self._jobs[job_id].name
            del self._jobs[job_id]
            self._save()
            logger.info(f"Cron: job '{name}' ({job_id}) removed")
            return True
        logger.warning(f"Cron: job {job_id} not found")
        return False

    def list_jobs(self, enabled_only: bool = False) -> list[CronJob]:
        """List all scheduled jobs."""
        jobs = list(self._jobs.values())
        if enabled_only:
            jobs = [j for j in jobs if j.enabled]
        return sorted(jobs, key=lambda j: j.next_run or "")

    def get(self, job_id: str) -> CronJob | None:
        """Get a job by ID."""
        return self._jobs.get(job_id)

    async def run_now(self, job_id: str) -> bool:
        """Execute a job immediately (regardless of schedule)."""
        job = self._jobs.get(job_id)
        if not job:
            logger.warning(f"Cron: job {job_id} not found for run_now")
            return False
        await self._execute_job(job)
        return True

    def _calculate_next_run(self, job: CronJob) -> str:
        """Calculate the next run time for a job."""
        now = datetime.now(timezone.utc)

        if job.schedule_type == "at":
            # One-shot: run at specified time
            return job.schedule_value

        elif job.schedule_type == "every":
            # Interval: parse "30m", "1h", "24h"
            interval = self._parse_interval(job.schedule_value)
            if interval:
                next_time = now + interval
                return next_time.isoformat()

        elif job.schedule_type == "cron":
            # Simplified cron — for MVP, just use interval as fallback
            # Full cron parsing would require croniter library
            return (now + timedelta(hours=1)).isoformat()

        return now.isoformat()

    def _parse_interval(self, value: str) -> timedelta | None:
        """Parse interval strings like '30m', '1h', '24h', '7d'."""
        if not value:
            return None

        value = value.strip().lower()
        try:
            if value.endswith("m"):
                return timedelta(minutes=int(value[:-1]))
            elif value.endswith("h"):
                return timedelta(hours=int(value[:-1]))
            elif value.endswith("d"):
                return timedelta(days=int(value[:-1]))
            elif value.endswith("s"):
                return timedelta(seconds=int(value[:-1]))
        except ValueError:
            pass

        logger.warning(f"Cron: invalid interval '{value}'")
        return None

    def _is_due(self, job: CronJob) -> bool:
        """Check if a job is due to run."""
        if not job.enabled or not job.next_run:
            return False

        try:
            next_run = datetime.fromisoformat(job.next_run)
            # Handle naive datetimes by assuming UTC
            if next_run.tzinfo is None:
                next_run = next_run.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) >= next_run
        except (ValueError, TypeError):
            return False

    async def _execute_job(self, job: CronJob) -> None:
        """Execute a single job and emit event."""
        logger.info(f"Cron: executing job '{job.name}' ({job.id})")

        # Update job state
        job.last_run = datetime.now(timezone.utc).isoformat()
        job.run_count += 1

        # Emit event
        await event_bus.emit(Event(
            type=EventType.CRON_TRIGGERED,
            source="cron_scheduler",
            data={
                "job_id": job.id,
                "job_name": job.name,
                "payload": job.payload,
                "session_target": job.session_target,
                "channel": job.channel,
                "run_count": job.run_count,
            },
        ))

        # Handle post-execution
        if job.delete_after_run:
            del self._jobs[job.id]
            logger.info(f"Cron: one-shot job '{job.name}' completed and removed")
        elif job.schedule_type == "every":
            # Reschedule recurring jobs
            job.next_run = self._calculate_next_run(job)
            logger.debug(f"Cron: job '{job.name}' rescheduled for {job.next_run}")

        self._save()

    async def start(self) -> None:
        """Start the background scheduler loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("Cron scheduler started")

    async def stop(self) -> None:
        """Stop the background scheduler loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Cron scheduler stopped")

    async def _scheduler_loop(self) -> None:
        """Background loop — checks for due jobs every 60 seconds."""
        while self._running:
            try:
                due_jobs = [j for j in self._jobs.values() if self._is_due(j)]
                for job in due_jobs:
                    await self._execute_job(job)

                if due_jobs:
                    logger.debug(f"Cron: executed {len(due_jobs)} due jobs")

            except Exception as e:
                logger.error(f"Cron scheduler error: {e}")

            await asyncio.sleep(60)


# Singleton
cron_scheduler = CronScheduler()
