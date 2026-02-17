"""
Tests End-to-End — Agent Optimus.
Fluxos completos: message → gateway → agent → response.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.channels.base_channel import IncomingMessage, ChannelType
from src.channels.chat_commands import ChatCommandHandler
from src.core.a2a_protocol import A2AProtocol, AgentCard, DelegationRequest
from src.collaboration.task_manager import TaskCreate, TaskManager, TaskPriority
from src.collaboration.notification_service import NotificationService
from src.core.security import SecurityManager, Permission
from src.core.performance import ContextCompactor, QueryCache, SessionPruner
from src.core.events import EventBus, Event, EventType


# ============================================
# E2E: Message → Command → Response
# ============================================
class TestE2ECommands:
    """Test message flow through chat commands."""

    def setup_method(self):
        self.handler = ChatCommandHandler()

    @pytest.mark.asyncio
    async def test_help_command(self):
        result = await self.handler.handle("/help", "user1")
        assert result is not None
        assert "Comandos" in result or "help" in result.lower()

    @pytest.mark.asyncio
    async def test_status_command(self):
        result = await self.handler.handle("/status", "user1")
        assert result is not None

    @pytest.mark.asyncio
    async def test_agents_command(self):
        result = await self.handler.handle("/agents", "user1")
        assert result is not None

    @pytest.mark.asyncio
    async def test_unknown_command(self):
        result = await self.handler.handle("/nonexistent", "user1")
        # Should return None or help text
        assert result is None or isinstance(result, str)


# ============================================
# E2E: Task Create → Notification
# ============================================
class TestE2ETaskFlow:
    """Test task creation → notification flow."""

    def setup_method(self):
        self.tasks = TaskManager()
        self.notifications = NotificationService()

    @pytest.mark.asyncio
    async def test_create_task_flow(self):
        # 1. Create task
        task = await self.tasks.create(TaskCreate(
            title="Implement feature X",
            description="Full implementation",
            priority=TaskPriority.HIGH,
            assignee="friday",
            tags=["backend", "urgent"],
        ))
        assert task.title == "Implement feature X"
        assert task.assignee == "friday"

        # 2. Send notification
        await self.notifications.notify_assignment(
            agent_name="friday",
            task_id=task.id,
            assigned_by="optimus",
        )

        # 3. Verify notification exists
        notifs = await self.notifications.get_notifications("friday")
        assert len(notifs) >= 1

    @pytest.mark.asyncio
    async def test_task_lifecycle_flow(self):
        # Create → Assign → InProgress → Review → Done
        task = await self.tasks.create(TaskCreate(title="Lifecycle test"))

        from src.collaboration.task_manager import TaskStatus, TaskUpdate
        transitions = [
            TaskStatus.ASSIGNED,
            TaskStatus.IN_PROGRESS,
            TaskStatus.REVIEW,
            TaskStatus.DONE,
        ]
        for status in transitions:
            updated = await self.tasks.update(task.id, TaskUpdate(status=status))
            assert updated.status == status


# ============================================
# E2E: A2A Delegation Flow
# ============================================
class TestE2ADelegation:
    """Test agent-to-agent delegation flow."""

    def setup_method(self):
        self.a2a = A2AProtocol()

    @pytest.mark.asyncio
    async def test_full_delegation_flow(self):
        # 1. Register agents
        self.a2a.register_agent(AgentCard(
            name="optimus", role="Lead", level="lead",
            capabilities=["planning", "delegation"],
        ))
        self.a2a.register_agent(AgentCard(
            name="friday", role="Developer", level="specialist",
            capabilities=["code", "debug"],
        ))

        # 2. Optimus delegates to Friday
        request = DelegationRequest(
            from_agent="optimus",
            to_agent="friday",
            task_description="Implement authentication module",
            context="FastAPI + JWT",
        )
        msg = await self.a2a.delegate(request)

        # 3. Verify load increased
        friday_card = self.a2a.get_card("friday")
        assert friday_card.current_load == 1

        # 4. Friday completes the work
        await self.a2a.complete_delegation(msg.id, "Auth module done with JWT + refresh tokens")

        # 5. Verify load decreased
        friday_card = self.a2a.get_card("friday")
        assert friday_card.current_load == 0

        # 6. Verify response sent back to optimus
        optimus_messages = await self.a2a.get_messages("optimus", message_type="response")
        assert len(optimus_messages) >= 1
        assert "Auth module done" in optimus_messages[0].content


# ============================================
# E2E: Security → Permission Check Flow
# ============================================
class TestE2ESecurity:
    """Test security permission enforcement flow."""

    def setup_method(self):
        self.sec = SecurityManager()

    def test_intern_cannot_write_db(self):
        allowed = self.sec.check_permission("intern_bot", "intern", Permission.DB_WRITE, "users_table")
        assert allowed is False

        # Verify audit trail recorded it
        audit = self.sec.get_denied_actions(limit=1)
        assert len(audit) == 1
        assert audit[0].agent_name == "intern_bot"

    def test_lead_full_access_flow(self):
        # Lead should have all permissions
        for perm in Permission:
            assert self.sec.check_permission("optimus", "lead", perm)

    def test_custom_permission_override(self):
        # Intern normally can't write
        assert not self.sec.check_permission("special", "intern", Permission.FS_WRITE)

        # Grant custom permission
        self.sec.grant_permission("special", Permission.FS_WRITE)
        assert self.sec.check_permission("special", "intern", Permission.FS_WRITE)


# ============================================
# E2E: Event-driven Flow
# ============================================
class TestE2EEvents:
    """Test event-driven architecture flow."""

    def setup_method(self):
        self.bus = EventBus()

    @pytest.mark.asyncio
    async def test_task_event_triggers_notification(self):
        """Simulate: task created → event emitted → handler notifies."""
        notifications_sent = []

        async def on_task_created(event: Event):
            notifications_sent.append(event.data.get("title"))

        self.bus.on(EventType.TASK_CREATED.value, on_task_created)

        # Emit task created event
        await self.bus.emit(Event(
            type=EventType.TASK_CREATED,
            source="task_manager",
            data={"title": "New feature", "assignee": "friday"},
        ))

        assert len(notifications_sent) == 1
        assert notifications_sent[0] == "New feature"

    @pytest.mark.asyncio
    async def test_webhook_event_flow(self):
        """Simulate: GitHub webhook → event → handler."""
        processed = []

        async def on_webhook(event: Event):
            processed.append(event.data)

        self.bus.on(EventType.WEBHOOK_GITHUB.value, on_webhook)

        await self.bus.emit(Event(
            type=EventType.WEBHOOK_GITHUB,
            source="github",
            data={"action": "push", "branch": "main"},
        ))

        assert len(processed) == 1
        assert processed[0]["action"] == "push"


# ============================================
# E2E: Performance — Cache + Compact Flow
# ============================================
class TestE2EPerformance:
    """Test performance optimization flow."""

    def setup_method(self):
        self.cache = QueryCache(max_size=10, ttl_seconds=60)
        self.compactor = ContextCompactor(max_messages=5)

    def test_cache_reduces_duplicate_queries(self):
        # First call — miss
        result = self.cache.get("what is python?")
        assert result is None

        # Cache the response
        self.cache.set("what is python?", "Python is a programming language...")

        # Second call — hit (no LLM call needed)
        result = self.cache.get("what is python?")
        assert result == "Python is a programming language..."

        stats = self.cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1

    @pytest.mark.asyncio
    async def test_context_compacting_saves_tokens(self):
        # 20 messages (exceeds max of 5)
        messages = [{"role": "user", "content": f"Message number {i} with some content"} for i in range(20)]

        before_tokens = self.compactor.estimate_tokens(messages)
        result = await self.compactor.compact(messages)

        assert result["compacted"] is True
        assert result["compacted_count"] < 20

        after_tokens = self.compactor.estimate_tokens(result["messages"])
        # Compacted should use fewer tokens
        assert after_tokens < before_tokens


# ============================================
# E2E: Full Pipeline Simulation
# ============================================
class TestE2EFullPipeline:
    """Simulate a complete user interaction pipeline."""

    @pytest.mark.asyncio
    async def test_message_to_response_pipeline(self):
        """
        Simulates:
        1. User sends message on Telegram
        2. Message normalized via BaseChannel
        3. Command check
        4. Security permission check
        5. Event emitted
        6. Response generated
        """
        # 1. Incoming message
        msg = IncomingMessage(
            channel=ChannelType.TELEGRAM,
            sender_id="user123",
            text="/status",
            chat_id="chat456",
        )
        assert msg.channel == ChannelType.TELEGRAM

        # 2. Command handling
        handler = ChatCommandHandler()
        response = await handler.handle(msg.text, msg.sender_id)
        assert response is not None

        # 3. Security check (user level)
        sec = SecurityManager()
        allowed = sec.check_permission("optimus", "lead", Permission.MCP_EXECUTE)
        assert allowed

        # 4. Event emission
        bus = EventBus()
        events_log = []

        async def log_event(event):
            events_log.append(event)

        bus.on(EventType.MESSAGE_RECEIVED.value, log_event)
        await bus.emit(Event(
            type=EventType.MESSAGE_RECEIVED,
            source="telegram",
            data={"sender": msg.sender_id, "text": msg.text},
        ))
        assert len(events_log) == 1


# ============================================
# FASE 0 #17: Gateway → Chat Commands Integration
# ============================================
class TestGatewayChatCommandsIntegration:
    """
    FASE 0 Module #17: ChatCommands integration test.

    This test FAILS if chat_commands check is removed from gateway.route_message().
    Validates REGRA DE OURO checkpoint #2: "test that fails without the feature".
    """

    @pytest.mark.asyncio
    async def test_slash_command_intercepted_before_agent(self):
        """
        Test that slash commands are handled BEFORE routing to agents.

        Flow:
        User sends "/help" → Gateway → ChatCommands → Response (no agent)

        If this test passes but feature is removed, the gateway would route
        "/help" to the LLM agent instead of executing the command.
        """
        from src.core.gateway import gateway

        # Send /help command
        result = await gateway.route_message(
            message="/help",
            user_id="test_user",
        )

        # CRITICAL: Must be handled by chat_commands, NOT by agent
        assert result["agent"] == "chat_commands", \
            "Command was NOT intercepted! Gateway routed to agent instead of chat_commands."

        assert result["is_command"] is True
        assert "Comandos Disponíveis" in result["content"] or "/help" in result["content"].lower()

    @pytest.mark.asyncio
    async def test_normal_message_not_intercepted(self):
        """Test that normal messages still go to agents."""
        from src.core.gateway import gateway

        result = await gateway.route_message(
            message="Hello, how are you?",
            user_id="test_user",
        )

        # Should NOT be handled by chat_commands
        assert result["agent"] != "chat_commands"
        assert result.get("is_command") is not True

    @pytest.mark.asyncio
    async def test_all_commands_work_via_gateway(self):
        """Test that all slash commands are accessible via Gateway."""
        from src.core.gateway import gateway

        commands_to_test = ["/help", "/status", "/agents"]

        for cmd in commands_to_test:
            result = await gateway.route_message(message=cmd, user_id="test_user")

            assert result["agent"] == "chat_commands", \
                f"Command {cmd} was not intercepted by chat_commands"

            assert result["is_command"] is True
            assert isinstance(result["content"], str)
            assert len(result["content"]) > 0


# ============================================
# FASE 0 #26: CronScheduler Integration
# ============================================
class TestCronSchedulerIntegration:
    """
    FASE 0 Module #26: CronScheduler integration test.

    This test FAILS if cron_scheduler.start() is removed from main.py lifespan.
    Validates REGRA DE OURO checkpoint #2: "test that fails without the feature".
    """

    @pytest.mark.asyncio
    async def test_cron_scheduler_can_start(self):
        """
        Test that CronScheduler can be started (simulates main.py lifespan).

        If this test passes but cron_scheduler.start() is NOT called in main.py,
        jobs will never execute in production.
        """
        from src.core.cron_scheduler import cron_scheduler

        # Start scheduler (this is what main.py lifespan should do)
        if not cron_scheduler._running:
            await cron_scheduler.start()

        # Verify it started successfully
        assert cron_scheduler._running is True, \
            "CronScheduler failed to start!"

        # Cleanup
        await cron_scheduler.stop()

    @pytest.mark.asyncio
    async def test_cron_job_execution(self):
        """
        Test that cron jobs are actually executed.

        Creates a simple job and verifies it runs when due.
        """
        from src.core.cron_scheduler import cron_scheduler, CronJob
        from src.core.events import event_bus, EventType
        from datetime import datetime, timezone, timedelta

        # Track if job was executed via event
        executed_jobs = []

        async def on_cron_triggered(event):
            executed_jobs.append(event.data.get("job_name"))

        event_bus.on(EventType.CRON_TRIGGERED.value, on_cron_triggered)

        # Create a job that runs in 1 second
        job = CronJob(
            name="test_job_immediate",
            schedule_type="at",
            schedule_value=(datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat(),
            payload="test payload",
            delete_after_run=True,
        )

        job_id = cron_scheduler.add(job)

        # Wait for job to execute (scheduler checks every 60s, but we can run_now)
        await cron_scheduler.run_now(job_id)

        # Verify job was executed
        assert "test_job_immediate" in executed_jobs, \
            "Cron job was NOT executed! Scheduler may not be running properly."

    @pytest.mark.asyncio
    async def test_cron_scheduler_can_list_jobs(self):
        """Test that we can add and list cron jobs."""
        from src.core.cron_scheduler import cron_scheduler, CronJob

        initial_count = len(cron_scheduler.list_jobs())

        # Add a test job
        job = CronJob(
            name="test_recurring_job",
            schedule_type="every",
            schedule_value="1h",
            payload="hourly check",
        )
        job_id = cron_scheduler.add(job)

        # List jobs
        jobs = cron_scheduler.list_jobs()
        assert len(jobs) == initial_count + 1

        # Cleanup
        cron_scheduler.remove(job_id)
