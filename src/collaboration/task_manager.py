"""
Agent Optimus — Task Manager.
CRUD completo + lifecycle + subtasks + dependencies + priority.
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    INBOX = "inbox"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    BLOCKED = "blocked"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


# Valid status transitions
STATUS_TRANSITIONS = {
    TaskStatus.INBOX: [TaskStatus.ASSIGNED, TaskStatus.DONE],
    TaskStatus.ASSIGNED: [TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED, TaskStatus.INBOX],
    TaskStatus.IN_PROGRESS: [TaskStatus.REVIEW, TaskStatus.BLOCKED, TaskStatus.DONE],
    TaskStatus.REVIEW: [TaskStatus.DONE, TaskStatus.IN_PROGRESS],
    TaskStatus.BLOCKED: [TaskStatus.IN_PROGRESS, TaskStatus.ASSIGNED],
    TaskStatus.DONE: [TaskStatus.IN_PROGRESS],  # Reopen
}


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    priority: TaskPriority = TaskPriority.MEDIUM
    parent_task_id: UUID | None = None
    assignee_ids: list[UUID] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    due_date: datetime | None = None
    estimated_effort: str | None = None
    created_by: str = ""  # agent name


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: TaskPriority | None = None
    status: TaskStatus | None = None
    assignee_ids: list[UUID] | None = None
    tags: list[str] | None = None
    due_date: datetime | None = None
    estimated_effort: str | None = None


class Task(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.INBOX
    priority: TaskPriority = TaskPriority.MEDIUM
    parent_task_id: UUID | None = None
    assignee_ids: list[UUID] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    due_date: datetime | None = None
    estimated_effort: str | None = None
    created_by: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TaskManager:
    """
    Manages task lifecycle with full CRUD, status transitions, subtasks.
    In-memory store for now; DB integration in production.
    """

    def __init__(self):
        self._tasks: dict[UUID, Task] = {}

    # ============================================
    # CRUD
    # ============================================

    async def create(self, data: TaskCreate) -> Task:
        """Create a new task."""
        task = Task(
            title=data.title,
            description=data.description,
            priority=data.priority,
            parent_task_id=data.parent_task_id,
            assignee_ids=data.assignee_ids,
            tags=data.tags,
            due_date=data.due_date,
            estimated_effort=data.estimated_effort,
            created_by=data.created_by,
        )

        # Auto-assign status if assignees present
        if data.assignee_ids:
            task.status = TaskStatus.ASSIGNED

        self._tasks[task.id] = task

        logger.info(f"Task created: {task.title}", extra={"props": {
            "task_id": str(task.id), "status": task.status, "priority": task.priority,
        }})

        return task

    async def get(self, task_id: UUID) -> Task | None:
        return self._tasks.get(task_id)

    async def update(self, task_id: UUID, data: TaskUpdate) -> Task | None:
        """Update task fields (excludes status — use transition instead)."""
        task = self._tasks.get(task_id)
        if not task:
            return None

        update_data = data.model_dump(exclude_none=True, exclude={"status"})
        for key, value in update_data.items():
            setattr(task, key, value)

        task.updated_at = datetime.now(timezone.utc)

        # Handle status transition separately
        if data.status and data.status != task.status:
            await self.transition(task_id, data.status)

        return task

    async def delete(self, task_id: UUID) -> bool:
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False

    async def list_tasks(
        self,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        assignee_id: UUID | None = None,
        parent_id: UUID | None = None,
        tag: str | None = None,
    ) -> list[Task]:
        """List tasks with optional filters."""
        tasks = list(self._tasks.values())

        if status:
            tasks = [t for t in tasks if t.status == status]
        if priority:
            tasks = [t for t in tasks if t.priority == priority]
        if assignee_id:
            tasks = [t for t in tasks if assignee_id in t.assignee_ids]
        if parent_id:
            tasks = [t for t in tasks if t.parent_task_id == parent_id]
        if tag:
            tasks = [t for t in tasks if tag in t.tags]

        # Sort by priority (urgent first), then by creation date
        priority_order = {TaskPriority.URGENT: 0, TaskPriority.HIGH: 1, TaskPriority.MEDIUM: 2, TaskPriority.LOW: 3}
        tasks.sort(key=lambda t: (priority_order.get(t.priority, 9), t.created_at))

        return tasks

    # ============================================
    # Lifecycle
    # ============================================

    async def transition(self, task_id: UUID, new_status: TaskStatus, agent_name: str = "") -> Task | None:
        """Transition task to a new status (validates allowed transitions)."""
        task = self._tasks.get(task_id)
        if not task:
            return None

        allowed = STATUS_TRANSITIONS.get(task.status, [])
        if new_status not in allowed:
            logger.warning(f"Invalid transition: {task.status} → {new_status}", extra={
                "props": {"task_id": str(task_id), "allowed": [s.value for s in allowed]}
            })
            return None

        old_status = task.status
        task.status = new_status
        task.updated_at = datetime.now(timezone.utc)

        logger.info(f"Task transitioned: {old_status} → {new_status}", extra={"props": {
            "task_id": str(task_id), "title": task.title, "agent": agent_name,
        }})

        return task

    async def get_subtasks(self, parent_id: UUID) -> list[Task]:
        """Get all subtasks of a parent task."""
        return [t for t in self._tasks.values() if t.parent_task_id == parent_id]

    async def get_blocked_tasks(self) -> list[Task]:
        """Get all blocked tasks."""
        return await self.list_tasks(status=TaskStatus.BLOCKED)

    async def get_agent_tasks(self, agent_id: UUID) -> list[Task]:
        """Get tasks assigned to a specific agent."""
        return await self.list_tasks(assignee_id=agent_id)

    async def get_pending_count(self, agent_name: str = "") -> int:
        """Count tasks that are not done or blocked."""
        active_statuses = {TaskStatus.INBOX, TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS, TaskStatus.REVIEW}
        return sum(1 for t in self._tasks.values() if t.status in active_statuses)


# Singleton
task_manager = TaskManager()
