"""
Agent Optimus — Threads API (FASE 0 #19: Thread Manager).
REST endpoints for task comments, subscriptions, and @mentions.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.collaboration.thread_manager import Message, thread_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/threads", tags=["threads"])


# ============================================
# Request/Response Models
# ============================================


class PostMessageRequest(BaseModel):
    """Request to post a message on a task thread."""

    from_agent: str = Field(..., description="Agent posting the message")
    content: str = Field(..., description="Message content")
    confidence_score: float | None = Field(None, description="Optional confidence score")
    thinking_mode: str | None = Field(None, description="Thinking mode used")


class MessageResponse(BaseModel):
    """Response containing a message."""

    id: str
    task_id: str
    from_agent: str
    content: str
    mentions: list[str]
    confidence_score: float | None
    thinking_mode: str | None
    created_at: str

    @classmethod
    def from_message(cls, msg: Message) -> "MessageResponse":
        return cls(
            id=str(msg.id),
            task_id=str(msg.task_id),
            from_agent=msg.from_agent,
            content=msg.content,
            mentions=msg.mentions,
            confidence_score=msg.confidence_score,
            thinking_mode=msg.thinking_mode,
            created_at=msg.created_at.isoformat(),
        )


class ThreadSummaryResponse(BaseModel):
    """Response containing thread summary."""

    task_id: str
    message_count: int
    participants: list[str]
    last_message_at: str | None = None
    first_message_at: str | None = None


class SubscribeRequest(BaseModel):
    """Request to subscribe an agent to a thread."""

    agent_name: str = Field(..., description="Agent to subscribe")


# ============================================
# API Endpoints
# ============================================


@router.post("/{task_id}/messages", response_model=MessageResponse)
async def post_message(task_id: UUID, request: PostMessageRequest) -> MessageResponse:
    """
    Post a message/comment on a task thread.

    Automatically subscribes the posting agent and any @mentioned agents.
    Parses @mentions from content.
    """
    try:
        message = await thread_manager.post_message(
            task_id=task_id,
            from_agent=request.from_agent,
            content=request.content,
            confidence_score=request.confidence_score,
            thinking_mode=request.thinking_mode,
        )

        logger.info(
            f"Message posted on task {task_id} by {request.from_agent}, mentions: {message.mentions}"
        )

        return MessageResponse.from_message(message)

    except Exception as e:
        logger.error(f"Post message failed: {e}")
        raise HTTPException(status_code=500, detail=f"Post message failed: {e}")


@router.get("/{task_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    task_id: UUID,
    limit: int = Query(50, description="Maximum messages to return", ge=1, le=100),
) -> list[MessageResponse]:
    """
    Get messages for a task thread.

    Returns messages in reverse chronological order (most recent first).
    """
    try:
        messages = await thread_manager.get_messages(task_id, limit=limit)

        logger.info(f"Retrieved {len(messages)} messages for task {task_id}")

        return [MessageResponse.from_message(m) for m in messages]

    except Exception as e:
        logger.error(f"Get messages failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get messages failed: {e}")


@router.get("/{task_id}/summary", response_model=ThreadSummaryResponse)
async def get_thread_summary(task_id: UUID) -> ThreadSummaryResponse:
    """
    Get thread summary for a task.

    Returns message count, participants, and first/last message timestamps.
    """
    try:
        summary = await thread_manager.get_thread_summary(task_id)

        logger.info(f"Thread summary for task {task_id}: {summary['message_count']} messages")

        return ThreadSummaryResponse(**summary)

    except Exception as e:
        logger.error(f"Get thread summary failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get thread summary failed: {e}")


@router.post("/{task_id}/subscribe")
async def subscribe_to_thread(task_id: UUID, request: SubscribeRequest) -> dict[str, Any]:
    """
    Subscribe an agent to a task thread.

    Subscribed agents receive notifications about new messages.
    """
    try:
        await thread_manager.subscribe(request.agent_name, task_id)

        logger.info(f"Agent {request.agent_name} subscribed to task {task_id}")

        return {
            "success": True,
            "agent_name": request.agent_name,
            "task_id": str(task_id),
            "subscribed": True,
        }

    except Exception as e:
        logger.error(f"Subscribe failed: {e}")
        raise HTTPException(status_code=500, detail=f"Subscribe failed: {e}")


@router.delete("/{task_id}/subscribe/{agent_name}")
async def unsubscribe_from_thread(task_id: UUID, agent_name: str) -> dict[str, Any]:
    """
    Unsubscribe an agent from a task thread.

    Agent will no longer receive notifications about new messages.
    """
    try:
        await thread_manager.unsubscribe(agent_name, task_id)

        logger.info(f"Agent {agent_name} unsubscribed from task {task_id}")

        return {
            "success": True,
            "agent_name": agent_name,
            "task_id": str(task_id),
            "subscribed": False,
        }

    except Exception as e:
        logger.error(f"Unsubscribe failed: {e}")
        raise HTTPException(status_code=500, detail=f"Unsubscribe failed: {e}")


@router.get("/{task_id}/subscribers", response_model=list[str])
async def get_thread_subscribers(task_id: UUID) -> list[str]:
    """
    Get all agents subscribed to a task thread.

    Returns list of agent names.
    """
    try:
        subscribers = await thread_manager.get_subscribers(task_id)

        logger.info(f"Task {task_id} has {len(subscribers)} subscribers")

        return subscribers

    except Exception as e:
        logger.error(f"Get subscribers failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get subscribers failed: {e}")


@router.get("/subscriptions/{agent_name}", response_model=list[str])
async def get_agent_subscriptions(agent_name: str) -> list[str]:
    """
    Get all task threads an agent is subscribed to.

    Returns list of task IDs (as strings).
    """
    try:
        task_ids = await thread_manager.get_agent_subscriptions(agent_name)

        logger.info(f"Agent {agent_name} subscribed to {len(task_ids)} tasks")

        return [str(tid) for tid in task_ids]

    except Exception as e:
        logger.error(f"Get agent subscriptions failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get agent subscriptions failed: {e}")


@router.get("/mentions/{agent_name}", response_model=list[MessageResponse])
async def get_agent_mentions(
    agent_name: str,
    since: str | None = Query(None, description="ISO timestamp to filter mentions after"),
) -> list[MessageResponse]:
    """
    Get messages that mention a specific agent.

    Useful for building notification/inbox features.
    """
    try:
        # Parse since timestamp if provided
        since_dt = None
        if since:
            try:
                since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
            except ValueError as e:
                raise HTTPException(
                    status_code=400, detail=f"Invalid timestamp format: {e}"
                )

        mentions = await thread_manager.get_unread_mentions(agent_name, since=since_dt)

        logger.info(f"Agent {agent_name} has {len(mentions)} mentions")

        return [MessageResponse.from_message(m) for m in mentions]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get mentions failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get mentions failed: {e}")
