"""
Agent Optimus — Reminder Delivery.
Stores pending reminder messages to be delivered on the user's next chat request.

Flow:
  CronScheduler._execute_job(job{name="Lembrete:..."})
    → EventBus.emit(CRON_TRIGGERED, {job_name="Lembrete:...", payload="message"})
      → on_reminder_cron_triggered(event)
        → pending_reminders.store(payload)
          → (next user message arrives)
            → gateway.route_message()
              → context["pending_reminders"] = pending_reminders.get_and_clear()
                → OptimusAgent sees reminder in system prompt → delivers to user
"""

import logging

logger = logging.getLogger(__name__)


class PendingReminders:
    """
    Thread-safe in-process queue of pending reminder messages.
    Reminders are stored when a cron job fires, cleared after delivery.
    """

    def __init__(self):
        self._queue: list[str] = []

    def store(self, message: str) -> None:
        """Add a reminder to the pending queue."""
        self._queue.append(message)
        logger.info(f"PendingReminders: stored reminder — '{message[:80]}'")

    def get_and_clear(self) -> list[str]:
        """Return all pending reminders and clear the queue."""
        reminders = list(self._queue)
        self._queue.clear()
        return reminders

    def has_reminders(self) -> bool:
        return len(self._queue) > 0


# Singleton shared across all requests in this process
pending_reminders = PendingReminders()
