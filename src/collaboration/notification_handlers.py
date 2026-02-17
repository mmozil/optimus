"""
Agent Optimus — Notification Event Handlers.
FASE 0 #20: Connects EventBus task events to NotificationService.

Call Path:
  TaskManager.create()
    → EventBus.emit("task.created")
      → on_task_created(event)
        → notification_service.send_task_assigned(target_agent, ...)
"""

import logging
from uuid import UUID

from src.core.events import Event, EventType, event_bus
from src.collaboration.notification_service import notification_service, NotificationType

logger = logging.getLogger(__name__)


async def on_task_created(event: Event):
    """
    Handle TASK_CREATED event.
    Sends notification to assignees when a task is created and assigned.
    """
    data = event.data
    task_id_str = data.get("task_id", "")
    title = data.get("title", "")
    assignee_ids = data.get("assignee_ids", [])
    created_by = data.get("created_by", "system")

    try:
        task_id = UUID(task_id_str) if task_id_str else None
    except ValueError:
        task_id = None

    for assignee_id in assignee_ids:
        try:
            await notification_service.send_task_assigned(
                target_agent=assignee_id,
                task_title=title,
                task_id=task_id,
                source_agent=created_by,
            )
            logger.info(f"Notification sent: task assigned to {assignee_id}")
        except Exception as e:
            logger.error(f"Failed to send task notification to {assignee_id}: {e}")


async def on_task_updated(event: Event):
    """
    Handle TASK_UPDATED event.
    Logs status transitions; future use for watcher notifications.
    """
    data = event.data
    title = data.get("title", "")
    old_status = data.get("old_status", "")
    new_status = data.get("new_status", "")

    logger.debug(f"Task updated: {title} ({old_status} → {new_status})")


async def on_task_completed(event: Event):
    """
    Handle TASK_COMPLETED event.
    Sends notification to task creator when task reaches DONE status.
    """
    data = event.data
    task_id_str = data.get("task_id", "")
    title = data.get("title", "")
    created_by = data.get("created_by", "")

    try:
        task_id = UUID(task_id_str) if task_id_str else None
    except ValueError:
        task_id = None

    if created_by and created_by != "system":
        try:
            await notification_service.send(
                target_agent=created_by,
                notification_type=NotificationType.TASK_STATUS,
                content=f"Task concluída: {title}",
                source_agent="task_manager",
                task_id=task_id,
            )
            logger.info(f"Notification sent: task completed to creator {created_by}")
        except Exception as e:
            logger.error(f"Failed to send completion notification to {created_by}: {e}")


def register_notification_handlers():
    """
    Register all notification event handlers with EventBus.
    Called from main.py lifespan startup (FASE 0 #20).
    """
    event_bus.on(EventType.TASK_CREATED.value, on_task_created)
    event_bus.on(EventType.TASK_UPDATED.value, on_task_updated)
    event_bus.on(EventType.TASK_COMPLETED.value, on_task_completed)

    logger.info("FASE 0 #20: Notification handlers registered on EventBus")
