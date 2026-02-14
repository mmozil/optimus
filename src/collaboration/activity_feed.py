"""
Agent Optimus — Activity Feed.
Stream of system events: task changes, messages, agent actions.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ActivityType(str):
    TASK_CREATED = "task_created"
    TASK_STATUS_CHANGED = "task_status_changed"
    TASK_ASSIGNED = "task_assigned"
    MESSAGE_SENT = "message_sent"
    AGENT_WAKEUP = "agent_wakeup"
    AGENT_HEARTBEAT = "agent_heartbeat"
    LLM_CALL = "llm_call"
    RAG_QUERY = "rag_query"
    LEARNING_ADDED = "learning_added"
    ERROR = "error"


class Activity(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    type: str
    agent_name: str = ""
    task_id: UUID | None = None
    message: str
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ActivityFeed:
    """
    Records and queries system-wide activity events.
    In-memory for now; production stores in Supabase 'activities' table.
    """

    def __init__(self, max_size: int = 10_000):
        self._activities: list[Activity] = []
        self._max_size = max_size

    async def record(
        self,
        activity_type: str,
        message: str,
        agent_name: str = "",
        task_id: UUID | None = None,
        metadata: dict | None = None,
    ) -> Activity:
        """Record a new activity event."""
        activity = Activity(
            type=activity_type,
            agent_name=agent_name,
            task_id=task_id,
            message=message,
            metadata=metadata or {},
        )

        self._activities.append(activity)

        # Trim if over max size (FIFO)
        if len(self._activities) > self._max_size:
            self._activities = self._activities[-self._max_size:]

        logger.debug(f"Activity recorded: {activity_type}", extra={"props": {
            "type": activity_type, "agent": agent_name, "message_preview": message[:100],
        }})

        return activity

    async def get_recent(self, limit: int = 50) -> list[Activity]:
        """Get most recent activities."""
        return sorted(self._activities, key=lambda a: a.created_at, reverse=True)[:limit]

    async def get_by_agent(self, agent_name: str, limit: int = 50) -> list[Activity]:
        """Get activities for a specific agent."""
        agent_activities = [a for a in self._activities if a.agent_name == agent_name]
        return sorted(agent_activities, key=lambda a: a.created_at, reverse=True)[:limit]

    async def get_by_task(self, task_id: UUID, limit: int = 50) -> list[Activity]:
        """Get activities for a specific task."""
        task_activities = [a for a in self._activities if a.task_id == task_id]
        return sorted(task_activities, key=lambda a: a.created_at, reverse=True)[:limit]

    async def get_by_type(self, activity_type: str, limit: int = 50) -> list[Activity]:
        """Get activities of a specific type."""
        typed = [a for a in self._activities if a.type == activity_type]
        return sorted(typed, key=lambda a: a.created_at, reverse=True)[:limit]

    async def get_daily_summary(self, date: str | None = None) -> dict:
        """Get summary of activities for a date (YYYY-MM-DD)."""
        target_date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        day_activities = [
            a for a in self._activities
            if a.created_at.strftime("%Y-%m-%d") == target_date
        ]

        # Count by type
        by_type: dict[str, int] = {}
        for a in day_activities:
            by_type[a.type] = by_type.get(a.type, 0) + 1

        # Count by agent
        by_agent: dict[str, int] = {}
        for a in day_activities:
            if a.agent_name:
                by_agent[a.agent_name] = by_agent.get(a.agent_name, 0) + 1

        return {
            "date": target_date,
            "total_activities": len(day_activities),
            "by_type": by_type,
            "by_agent": by_agent,
            "active_agents": list(by_agent.keys()),
        }


# Singleton
activity_feed = ActivityFeed()
