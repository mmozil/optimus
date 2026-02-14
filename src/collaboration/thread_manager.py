"""
Agent Optimus — Thread Manager.
Comments on tasks + thread subscriptions + @mentions parsing.
"""

import logging
import re
from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Message(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    from_agent: str  # agent name
    content: str
    mentions: list[str] = Field(default_factory=list)  # agent names mentioned
    confidence_score: float | None = None
    thinking_mode: str | None = None  # standard | tot | compact
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ThreadSubscription(BaseModel):
    agent_name: str
    task_id: UUID
    subscribed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ThreadManager:
    """
    Manages comments/messages on tasks and thread subscriptions.
    Auto-subscribes agents when they interact with a task.
    """

    def __init__(self):
        self._messages: dict[UUID, list[Message]] = {}  # task_id → messages
        self._subscriptions: dict[UUID, set[str]] = {}  # task_id → agent names

    # ============================================
    # Messages
    # ============================================

    async def post_message(
        self,
        task_id: UUID,
        from_agent: str,
        content: str,
        confidence_score: float | None = None,
        thinking_mode: str | None = None,
    ) -> Message:
        """Post a message/comment on a task thread."""
        # Parse @mentions
        mentions = self._parse_mentions(content)

        message = Message(
            task_id=task_id,
            from_agent=from_agent,
            content=content,
            mentions=mentions,
            confidence_score=confidence_score,
            thinking_mode=thinking_mode,
        )

        if task_id not in self._messages:
            self._messages[task_id] = []
        self._messages[task_id].append(message)

        # Auto-subscribe the agent who posted
        await self.subscribe(from_agent, task_id)

        # Auto-subscribe mentioned agents
        for mentioned in mentions:
            await self.subscribe(mentioned, task_id)

        logger.info(f"Message posted on task", extra={"props": {
            "task_id": str(task_id), "from": from_agent,
            "mentions": mentions, "length": len(content),
        }})

        return message

    async def get_messages(self, task_id: UUID, limit: int = 50) -> list[Message]:
        """Get messages for a task, most recent first."""
        messages = self._messages.get(task_id, [])
        return sorted(messages, key=lambda m: m.created_at, reverse=True)[:limit]

    async def get_thread_summary(self, task_id: UUID) -> dict:
        """Get a summary of a thread."""
        messages = self._messages.get(task_id, [])
        if not messages:
            return {"task_id": str(task_id), "message_count": 0, "participants": []}

        participants = list({m.from_agent for m in messages})
        return {
            "task_id": str(task_id),
            "message_count": len(messages),
            "participants": participants,
            "last_message_at": max(m.created_at for m in messages).isoformat(),
            "first_message_at": min(m.created_at for m in messages).isoformat(),
        }

    # ============================================
    # Subscriptions
    # ============================================

    async def subscribe(self, agent_name: str, task_id: UUID):
        """Subscribe an agent to a task thread."""
        if task_id not in self._subscriptions:
            self._subscriptions[task_id] = set()

        if agent_name not in self._subscriptions[task_id]:
            self._subscriptions[task_id].add(agent_name)
            logger.debug(f"Agent '{agent_name}' subscribed to task {task_id}")

    async def unsubscribe(self, agent_name: str, task_id: UUID):
        """Unsubscribe an agent from a task thread."""
        if task_id in self._subscriptions:
            self._subscriptions[task_id].discard(agent_name)

    async def get_subscribers(self, task_id: UUID) -> list[str]:
        """Get all agents subscribed to a task."""
        return list(self._subscriptions.get(task_id, set()))

    async def get_agent_subscriptions(self, agent_name: str) -> list[UUID]:
        """Get all tasks an agent is subscribed to."""
        return [
            task_id for task_id, agents in self._subscriptions.items()
            if agent_name in agents
        ]

    # ============================================
    # @Mentions
    # ============================================

    def _parse_mentions(self, content: str) -> list[str]:
        """Extract @mentions from message content."""
        return re.findall(r'@(\w+)', content)

    async def get_unread_mentions(self, agent_name: str, since: datetime | None = None) -> list[Message]:
        """Get messages that mention a specific agent."""
        mentioned_messages = []
        cutoff = since or datetime.min.replace(tzinfo=timezone.utc)

        for messages in self._messages.values():
            for msg in messages:
                if agent_name in msg.mentions and msg.created_at > cutoff:
                    mentioned_messages.append(msg)

        return sorted(mentioned_messages, key=lambda m: m.created_at, reverse=True)


# Singleton
thread_manager = ThreadManager()
