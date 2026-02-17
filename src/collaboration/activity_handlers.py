"""
Agent Optimus — Activity Feed Event Handlers.
FASE 0 #22: Connects EventBus events to ActivityFeed.record().

Without this, activity_feed is always empty and /standup has no real data.

Call Path:
  TaskManager.create()
    → EventBus.emit("task.created")
      → on_task_created(event)
        → activity_feed.record("task_created", ...)

  Gateway.route_message()
    → EventBus.emit("message.received")
      → on_message_received(event)
        → activity_feed.record("message_sent", ...)
"""

import logging
from src.core.events import Event, EventType, event_bus
from src.collaboration.activity_feed import activity_feed, ActivityType

logger = logging.getLogger(__name__)


async def on_task_created(event: Event):
    """Record task creation in ActivityFeed."""
    data = event.data
    title = data.get("title", "")
    created_by = data.get("created_by", "system")
    priority = data.get("priority", "medium")

    await activity_feed.record(
        activity_type=ActivityType.TASK_CREATED,
        message=f"Task criada: '{title}' (prioridade: {priority})",
        agent_name=created_by,
        metadata={"task_id": data.get("task_id"), "priority": priority},
    )


async def on_task_updated(event: Event):
    """Record task status changes in ActivityFeed."""
    data = event.data
    title = data.get("title", "")
    old_status = data.get("old_status", "")
    new_status = data.get("new_status", "")
    agent = data.get("agent", "system")

    await activity_feed.record(
        activity_type=ActivityType.TASK_STATUS_CHANGED,
        message=f"Task '{title}': {old_status} → {new_status}",
        agent_name=agent,
        metadata={
            "task_id": data.get("task_id"),
            "old_status": old_status,
            "new_status": new_status,
        },
    )


async def on_task_completed(event: Event):
    """Record task completion in ActivityFeed."""
    data = event.data
    title = data.get("title", "")
    created_by = data.get("created_by", "system")

    await activity_feed.record(
        activity_type=ActivityType.TASK_STATUS_CHANGED,
        message=f"Task concluída: '{title}'",
        agent_name=created_by,
        metadata={"task_id": data.get("task_id"), "new_status": "done"},
    )


async def on_message_received(event: Event):
    """Record user messages in ActivityFeed."""
    data = event.data
    user_id = data.get("user_id", "user")
    agent_name = data.get("agent_name", "optimus")
    preview = data.get("message_preview", "")

    await activity_feed.record(
        activity_type=ActivityType.MESSAGE_SENT,
        message=f"Mensagem para {agent_name}: {preview[:120]}",
        agent_name=agent_name,
        metadata={"user_id": user_id},
    )


async def on_cron_triggered(event: Event):
    """Record cron job executions in ActivityFeed."""
    data = event.data
    job_id = data.get("job_id", "")
    job_name = data.get("job_name", "")

    await activity_feed.record(
        activity_type="cron_triggered",
        message=f"Cron job executado: {job_name or job_id}",
        agent_name="cron_scheduler",
        metadata=data,
    )


def register_activity_handlers():
    """
    Register all activity event handlers with EventBus.
    Called from main.py lifespan startup (FASE 0 #22).
    """
    event_bus.on(EventType.TASK_CREATED.value, on_task_created)
    event_bus.on(EventType.TASK_UPDATED.value, on_task_updated)
    event_bus.on(EventType.TASK_COMPLETED.value, on_task_completed)
    event_bus.on(EventType.MESSAGE_RECEIVED.value, on_message_received)
    event_bus.on(EventType.CRON_TRIGGERED.value, on_cron_triggered)

    logger.info("FASE 0 #22: Activity handlers registered on EventBus")
