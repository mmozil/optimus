"""
Agent Optimus — Event System.
Event-driven architecture with Supabase Real-time preparation,
heartbeats, and webhook receiver.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine
from uuid import uuid4

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    # Agent events
    AGENT_WAKEUP = "agent.wakeup"
    AGENT_HEARTBEAT = "agent.heartbeat"
    AGENT_ERROR = "agent.error"
    # Task events
    TASK_CREATED = "task.created"
    TASK_UPDATED = "task.updated"
    TASK_COMPLETED = "task.completed"
    # Message events
    MESSAGE_RECEIVED = "message.received"
    MESSAGE_SENT = "message.sent"
    # System events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    # External events
    WEBHOOK_RECEIVED = "webhook.received"
    WEBHOOK_GITHUB = "webhook.github"
    CRON_TRIGGERED = "cron.triggered"


@dataclass
class Event:
    """System event."""
    id: str = field(default_factory=lambda: str(uuid4()))
    type: EventType | str = ""
    source: str = ""  # Who emitted
    data: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# Type alias for event handlers
EventHandler = Callable[[Event], Coroutine[Any, Any, None]]


class EventBus:
    """
    Pub/sub event bus for internal event-driven communication.
    Prepared for Supabase Real-time integration in production.
    """

    def __init__(self):
        self._handlers: dict[str, list[EventHandler]] = {}
        self._event_log: list[Event] = []
        self._max_log_size = 10_000

    def on(self, event_type: str, handler: EventHandler):
        """Subscribe a handler to an event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug(f"EventBus: handler registered for '{event_type}'")

    def off(self, event_type: str, handler: EventHandler):
        """Unsubscribe a handler."""
        if event_type in self._handlers:
            self._handlers[event_type] = [
                h for h in self._handlers[event_type] if h != handler
            ]

    async def emit(self, event: Event):
        """Emit an event to all subscribed handlers."""
        self._event_log.append(event)
        if len(self._event_log) > self._max_log_size:
            self._event_log = self._event_log[-self._max_log_size:]

        event_type = event.type if isinstance(event.type, str) else event.type.value
        handlers = self._handlers.get(event_type, [])

        # Also notify wildcard handlers
        wildcard_handlers = self._handlers.get("*", [])
        all_handlers = handlers + wildcard_handlers

        if not all_handlers:
            return

        # Execute handlers concurrently
        tasks = [h(event) for h in all_handlers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"EventBus handler error: {result}")

    async def emit_simple(self, event_type: str, source: str = "", data: dict | None = None):
        """Convenience method to emit a simple event."""
        await self.emit(Event(type=event_type, source=source, data=data or {}))

    def get_recent_events(self, event_type: str | None = None, limit: int = 50) -> list[Event]:
        """Get recent events."""
        events = self._event_log
        if event_type:
            events = [e for e in events
                      if (e.type if isinstance(e.type, str) else e.type.value) == event_type]
        return sorted(events, key=lambda e: e.timestamp, reverse=True)[:limit]


class HeartbeatManager:
    """
    Manages agent heartbeats.
    Scheduled heartbeats at configurable intervals (default 60 min).
    Zero LLM tokens — just DB health checks + status updates.
    """

    def __init__(self, event_bus: EventBus, interval_minutes: int = 60):
        self._bus = event_bus
        self.interval_minutes = interval_minutes
        self._agents: dict[str, datetime] = {}  # agent → last heartbeat
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self):
        """Start heartbeat monitoring."""
        self._running = True
        self._task = asyncio.create_task(self._heartbeat_loop())
        logger.info(f"HeartbeatManager started (interval: {self.interval_minutes}m)")

    async def stop(self):
        """Stop heartbeat monitoring."""
        self._running = False
        if self._task:
            self._task.cancel()

    def register_agent(self, agent_name: str):
        """Register an agent for heartbeat monitoring."""
        self._agents[agent_name] = datetime.now(timezone.utc)

    async def beat(self, agent_name: str):
        """Record a heartbeat from an agent."""
        self._agents[agent_name] = datetime.now(timezone.utc)
        await self._bus.emit_simple(
            EventType.AGENT_HEARTBEAT.value,
            source=agent_name,
            data={"timestamp": datetime.now(timezone.utc).isoformat()},
        )

    def is_alive(self, agent_name: str, timeout_minutes: int | None = None) -> bool:
        """Check if an agent's heartbeat is recent."""
        last = self._agents.get(agent_name)
        if not last:
            return False
        timeout = timeout_minutes or (self.interval_minutes * 2)
        return (datetime.now(timezone.utc) - last).total_seconds() < timeout * 60

    def get_status(self) -> dict:
        """Get heartbeat status for all agents."""
        now = datetime.now(timezone.utc)
        return {
            name: {
                "last_beat": last.isoformat(),
                "alive": self.is_alive(name),
                "age_minutes": int((now - last).total_seconds() / 60),
            }
            for name, last in self._agents.items()
        }

    async def _heartbeat_loop(self):
        """Background loop for periodic heartbeats."""
        while self._running:
            try:
                await asyncio.sleep(self.interval_minutes * 60)
                for agent_name in list(self._agents.keys()):
                    if not self.is_alive(agent_name):
                        logger.warning(f"Heartbeat missed: {agent_name}")
                        await self._bus.emit_simple(
                            EventType.AGENT_ERROR.value,
                            source="heartbeat_manager",
                            data={"agent": agent_name, "error": "heartbeat_timeout"},
                        )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")


class WebhookReceiver:
    """
    Receives and processes external webhooks (GitHub, forms, etc.).
    Routes webhook events through the EventBus.
    """

    def __init__(self, event_bus: EventBus):
        self._bus = event_bus
        self._processors: dict[str, Callable] = {}

    def register_processor(self, source: str, processor: Callable):
        """Register a webhook processor for a source."""
        self._processors[source] = processor

    async def process_webhook(self, source: str, payload: dict, headers: dict | None = None) -> dict:
        """Process an incoming webhook."""
        event_type = EventType.WEBHOOK_RECEIVED.value
        if source == "github":
            event_type = EventType.WEBHOOK_GITHUB.value

        # Emit event
        await self._bus.emit(Event(
            type=event_type,
            source=source,
            data={"payload": payload, "headers": headers or {}},
        ))

        # Run custom processor if registered
        processor = self._processors.get(source)
        if processor:
            try:
                result = await processor(payload, headers or {})
                return {"status": "processed", "source": source, "result": result}
            except Exception as e:
                logger.error(f"Webhook processor error ({source}): {e}")
                return {"status": "error", "source": source, "error": str(e)}

        return {"status": "received", "source": source}


# Singletons
event_bus = EventBus()
heartbeat_manager = HeartbeatManager(event_bus)
webhook_receiver = WebhookReceiver(event_bus)
