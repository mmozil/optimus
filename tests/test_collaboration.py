"""
Tests for Phase 3 — Collaboration: Tasks, Threads, Notifications, Activity, Standup.
"""

import pytest
from uuid import uuid4

from src.collaboration.task_manager import (
    TaskCreate, TaskManager, TaskPriority, TaskStatus, TaskUpdate,
)
from src.collaboration.thread_manager import ThreadManager
from src.collaboration.notification_service import NotificationService
from src.collaboration.activity_feed import ActivityFeed
from src.collaboration.standup_generator import StandupGenerator


# ============================================
# Task Manager Tests
# ============================================
class TestTaskManager:
    def setup_method(self):
        self.tm = TaskManager()

    @pytest.mark.asyncio
    async def test_create_task(self):
        data = TaskCreate(title="Test Task", description="A test", created_by="optimus")
        task = await self.tm.create(data)
        assert task.title == "Test Task"
        assert task.status == TaskStatus.INBOX

    @pytest.mark.asyncio
    async def test_create_with_assignee_auto_assigns(self):
        agent_id = uuid4()
        data = TaskCreate(title="Assigned", assignee_ids=[agent_id])
        task = await self.tm.create(data)
        assert task.status == TaskStatus.ASSIGNED

    @pytest.mark.asyncio
    async def test_get_task(self):
        data = TaskCreate(title="Findable")
        task = await self.tm.create(data)
        found = await self.tm.get(task.id)
        assert found is not None
        assert found.title == "Findable"

    @pytest.mark.asyncio
    async def test_update_task(self):
        data = TaskCreate(title="Original")
        task = await self.tm.create(data)
        updated = await self.tm.update(task.id, TaskUpdate(title="Updated"))
        assert updated.title == "Updated"

    @pytest.mark.asyncio
    async def test_delete_task(self):
        data = TaskCreate(title="Deletable")
        task = await self.tm.create(data)
        result = await self.tm.delete(task.id)
        assert result is True
        assert await self.tm.get(task.id) is None

    @pytest.mark.asyncio
    async def test_valid_transition(self):
        data = TaskCreate(title="Transition Test")
        task = await self.tm.create(data)
        result = await self.tm.transition(task.id, TaskStatus.ASSIGNED)
        assert result is not None
        assert result.status == TaskStatus.ASSIGNED

    @pytest.mark.asyncio
    async def test_invalid_transition_returns_none(self):
        data = TaskCreate(title="Invalid")
        task = await self.tm.create(data)
        # INBOX → REVIEW is not valid
        result = await self.tm.transition(task.id, TaskStatus.REVIEW)
        assert result is None

    @pytest.mark.asyncio
    async def test_list_by_priority(self):
        await self.tm.create(TaskCreate(title="Low", priority=TaskPriority.LOW))
        await self.tm.create(TaskCreate(title="Urgent", priority=TaskPriority.URGENT))
        urgent = await self.tm.list_tasks(priority=TaskPriority.URGENT)
        assert len(urgent) == 1
        assert urgent[0].title == "Urgent"

    @pytest.mark.asyncio
    async def test_list_sorted_by_priority(self):
        await self.tm.create(TaskCreate(title="Low", priority=TaskPriority.LOW))
        await self.tm.create(TaskCreate(title="Urgent", priority=TaskPriority.URGENT))
        await self.tm.create(TaskCreate(title="High", priority=TaskPriority.HIGH))
        all_tasks = await self.tm.list_tasks()
        assert all_tasks[0].title == "Urgent"
        assert all_tasks[1].title == "High"


# ============================================
# Thread Manager Tests
# ============================================
class TestThreadManager:
    def setup_method(self):
        self.thread = ThreadManager()

    @pytest.mark.asyncio
    async def test_post_message(self):
        task_id = uuid4()
        msg = await self.thread.post_message(task_id, "optimus", "Hello team")
        assert msg.from_agent == "optimus"
        assert msg.task_id == task_id

    @pytest.mark.asyncio
    async def test_auto_subscribe_on_post(self):
        task_id = uuid4()
        await self.thread.post_message(task_id, "friday", "Working on it")
        subscribers = await self.thread.get_subscribers(task_id)
        assert "friday" in subscribers

    @pytest.mark.asyncio
    async def test_mention_parsing(self):
        task_id = uuid4()
        msg = await self.thread.post_message(task_id, "optimus", "Hey @friday check this")
        assert "friday" in msg.mentions

    @pytest.mark.asyncio
    async def test_mentioned_agent_auto_subscribed(self):
        task_id = uuid4()
        await self.thread.post_message(task_id, "optimus", "Hey @fury take a look")
        subscribers = await self.thread.get_subscribers(task_id)
        assert "fury" in subscribers
        assert "optimus" in subscribers

    @pytest.mark.asyncio
    async def test_get_messages(self):
        task_id = uuid4()
        await self.thread.post_message(task_id, "optimus", "First")
        await self.thread.post_message(task_id, "friday", "Second")
        messages = await self.thread.get_messages(task_id)
        assert len(messages) == 2

    @pytest.mark.asyncio
    async def test_thread_summary(self):
        task_id = uuid4()
        await self.thread.post_message(task_id, "optimus", "Msg 1")
        await self.thread.post_message(task_id, "friday", "Msg 2")
        summary = await self.thread.get_thread_summary(task_id)
        assert summary["message_count"] == 2
        assert set(summary["participants"]) == {"optimus", "friday"}


# ============================================
# Notification Service Tests
# ============================================
class TestNotificationService:
    def setup_method(self):
        self.ns = NotificationService()

    @pytest.mark.asyncio
    async def test_send_notification(self):
        n = await self.ns.send("friday", "task_assigned", "Nova task para você")
        assert n.target_agent == "friday"
        assert not n.delivered

    @pytest.mark.asyncio
    async def test_get_pending(self):
        await self.ns.send("friday", "system", "Msg 1")
        await self.ns.send("friday", "system", "Msg 2")
        pending = await self.ns.get_pending("friday")
        assert len(pending) == 2

    @pytest.mark.asyncio
    async def test_mark_delivered(self):
        n = await self.ns.send("fury", "mention", "You were mentioned")
        await self.ns.mark_delivered(n.id, "fury")
        pending = await self.ns.get_pending("fury")
        assert len(pending) == 0

    @pytest.mark.asyncio
    async def test_mark_all_delivered(self):
        await self.ns.send("optimus", "system", "A")
        await self.ns.send("optimus", "system", "B")
        count = await self.ns.mark_all_delivered("optimus")
        assert count == 2
        assert await self.ns.get_pending_count("optimus") == 0


# ============================================
# Activity Feed Tests
# ============================================
class TestActivityFeed:
    def setup_method(self):
        self.feed = ActivityFeed(max_size=100)

    @pytest.mark.asyncio
    async def test_record_activity(self):
        a = await self.feed.record("task_created", "Task criada", agent_name="optimus")
        assert a.type == "task_created"
        assert a.agent_name == "optimus"

    @pytest.mark.asyncio
    async def test_get_recent(self):
        await self.feed.record("task_created", "T1")
        await self.feed.record("message_sent", "M1")
        recent = await self.feed.get_recent(limit=10)
        assert len(recent) == 2

    @pytest.mark.asyncio
    async def test_get_by_agent(self):
        await self.feed.record("llm_call", "Call 1", agent_name="friday")
        await self.feed.record("llm_call", "Call 2", agent_name="fury")
        friday = await self.feed.get_by_agent("friday")
        assert len(friday) == 1

    @pytest.mark.asyncio
    async def test_max_size_trim(self):
        feed = ActivityFeed(max_size=5)
        for i in range(10):
            await feed.record("test", f"Activity {i}")
        recent = await feed.get_recent(limit=100)
        assert len(recent) == 5

    @pytest.mark.asyncio
    async def test_daily_summary(self):
        await self.feed.record("task_created", "T1", agent_name="optimus")
        await self.feed.record("llm_call", "L1", agent_name="friday")
        summary = await self.feed.get_daily_summary()
        assert summary["total_activities"] == 2
        assert "optimus" in summary["active_agents"]


# ============================================
# Standup Generator Tests
# ============================================
class TestStandupGenerator:
    def setup_method(self):
        self.feed = ActivityFeed()
        self.tasks = TaskManager()
        self.standup = StandupGenerator(feed=self.feed, tasks=self.tasks)

    @pytest.mark.asyncio
    async def test_agent_standup_empty(self):
        report = await self.standup.generate_agent_standup("optimus")
        assert "Standup — optimus" in report
        assert "Sem atividades" in report

    @pytest.mark.asyncio
    async def test_team_standup(self):
        await self.feed.record("task_created", "Test", agent_name="optimus")
        report = await self.standup.generate_team_standup()
        assert "Team Standup" in report

    @pytest.mark.asyncio
    async def test_standup_includes_tasks(self):
        await self.tasks.create(TaskCreate(title="Active Task"))
        task = (await self.tasks.list_tasks())[0]
        await self.tasks.transition(task.id, TaskStatus.ASSIGNED)
        await self.tasks.transition(task.id, TaskStatus.IN_PROGRESS)
        report = await self.standup.generate_agent_standup("optimus")
        assert "Active Task" in report
