"""
Agent Optimus — Notification Service.
Real-time notifications via event queue. Prepared for Supabase Real-time integration.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class NotificationType(str):
    MENTION = "mention"
    TASK_ASSIGNED = "task_assigned"
    TASK_STATUS = "task_status"
    NEW_MESSAGE = "new_message"
    SYSTEM = "system"


class Notification(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    type: str
    target_agent: str  # who should receive
    source_agent: str = ""  # who triggered
    task_id: UUID | None = None
    content: str
    delivered: bool = False
    delivered_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class NotificationService:
    """
    Manages notifications for agents.
    In-memory queue for now; production uses Supabase Real-time push.
    """

    def __init__(self):
        self._queue: dict[str, list[Notification]] = {}  # agent_name → notifications

    async def send(
        self,
        target_agent: str,
        notification_type: str,
        content: str,
        source_agent: str = "",
        task_id: UUID | None = None,
    ) -> Notification:
        """Send a notification to an agent."""
        notification = Notification(
            type=notification_type,
            target_agent=target_agent,
            source_agent=source_agent,
            task_id=task_id,
            content=content,
        )

        if target_agent not in self._queue:
            self._queue[target_agent] = []
        self._queue[target_agent].append(notification)

        logger.info(f"Notification sent", extra={"props": {
            "type": notification_type, "to": target_agent,
            "from": source_agent, "content_preview": content[:100],
        }})

        return notification

    async def send_mention(self, target_agent: str, source_agent: str, task_id: UUID, message_preview: str):
        """Convenience: send a @mention notification."""
        return await self.send(
            target_agent=target_agent,
            notification_type=NotificationType.MENTION,
            content=f"@{source_agent} te mencionou: {message_preview[:200]}",
            source_agent=source_agent,
            task_id=task_id,
        )

    async def send_task_assigned(self, target_agent: str, task_title: str, task_id: UUID, source_agent: str = ""):
        """Convenience: send a task assignment notification."""
        return await self.send(
            target_agent=target_agent,
            notification_type=NotificationType.TASK_ASSIGNED,
            content=f"Nova task atribuída: {task_title}",
            source_agent=source_agent,
            task_id=task_id,
        )

    async def send_to_subscribers(
        self,
        subscribers: list[str],
        notification_type: str,
        content: str,
        exclude_agent: str = "",
        source_agent: str = "",
        task_id: UUID | None = None,
    ):
        """Send notification to all subscribers of a thread (except the sender)."""
        for agent in subscribers:
            if agent != exclude_agent:
                await self.send(agent, notification_type, content, source_agent, task_id)

    # ============================================
    # Retrieval
    # ============================================

    async def get_pending(self, agent_name: str) -> list[Notification]:
        """Get undelivered notifications for an agent."""
        notifications = self._queue.get(agent_name, [])
        return [n for n in notifications if not n.delivered]

    async def get_all(self, agent_name: str, limit: int = 50) -> list[Notification]:
        """Get all notifications for an agent."""
        notifications = self._queue.get(agent_name, [])
        return sorted(notifications, key=lambda n: n.created_at, reverse=True)[:limit]

    async def mark_delivered(self, notification_id: UUID, agent_name: str) -> bool:
        """Mark a notification as delivered."""
        for n in self._queue.get(agent_name, []):
            if n.id == notification_id:
                n.delivered = True
                n.delivered_at = datetime.now(timezone.utc)
                return True
        return False

    async def mark_all_delivered(self, agent_name: str) -> int:
        """Mark all pending notifications as delivered."""
        count = 0
        now = datetime.now(timezone.utc)
        for n in self._queue.get(agent_name, []):
            if not n.delivered:
                n.delivered = True
                n.delivered_at = now
                count += 1
        return count

    async def get_pending_count(self, agent_name: str) -> int:
        """Count pending notifications."""
        return len(await self.get_pending(agent_name))

    async def clear(self, agent_name: str):
        """Clear all notifications for an agent."""
        self._queue[agent_name] = []


# Singleton
notification_service = NotificationService()
