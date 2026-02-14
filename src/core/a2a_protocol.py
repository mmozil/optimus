"""
Agent Optimus — A2A Protocol.
Agent-to-Agent communication protocol for inter-agent discovery & messaging.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


@dataclass
class AgentCard:
    """Agent discovery card — exposes capabilities and status."""
    name: str
    role: str
    level: str  # lead | specialist | intern
    capabilities: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    status: str = "available"  # available | busy | offline
    max_concurrent: int = 5
    current_load: int = 0


@dataclass
class A2AMessage:
    """Message between agents."""
    id: UUID = field(default_factory=uuid4)
    from_agent: str = ""
    to_agent: str = ""
    message_type: str = "request"  # request | response | broadcast | delegation
    content: str = ""
    task_id: UUID | None = None
    reply_to: UUID | None = None
    priority: str = "normal"  # low | normal | high | urgent
    metadata: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DelegationRequest:
    """Request to delegate a task to another agent."""
    from_agent: str
    to_agent: str
    task_description: str
    context: str = ""
    thinking_level: str = "standard"
    timeout: float = 120.0
    callback_id: str | None = None  # For async delegation


class A2AProtocol:
    """
    Agent-to-Agent communication protocol.
    Handles agent discovery, messaging, delegation, and broadcasts.
    """

    def __init__(self):
        self._agents: dict[str, AgentCard] = {}
        self._message_log: list[A2AMessage] = []
        self._pending_delegations: dict[UUID, DelegationRequest] = {}

    # ============================================
    # Agent Discovery
    # ============================================

    def register_agent(self, card: AgentCard):
        """Register an agent in the discovery service."""
        self._agents[card.name] = card
        logger.info(f"A2A: Agent registered: {card.name} ({card.role})")

    def unregister_agent(self, agent_name: str):
        """Remove an agent from discovery."""
        self._agents.pop(agent_name, None)

    def discover(
        self,
        capability: str | None = None,
        level: str | None = None,
        available_only: bool = True,
    ) -> list[AgentCard]:
        """Discover agents matching criteria."""
        agents = list(self._agents.values())

        if available_only:
            agents = [a for a in agents if a.status == "available"]
        if capability:
            agents = [a for a in agents if capability in a.capabilities]
        if level:
            agents = [a for a in agents if a.level == level]

        return agents

    def find_best_agent(self, capability: str) -> AgentCard | None:
        """Find the best available agent for a capability."""
        candidates = self.discover(capability=capability)
        if not candidates:
            return None

        # Prefer agents with lower load
        candidates.sort(key=lambda a: a.current_load)
        return candidates[0]

    def get_card(self, agent_name: str) -> AgentCard | None:
        return self._agents.get(agent_name)

    def update_status(self, agent_name: str, status: str):
        """Update an agent's availability status."""
        if agent_name in self._agents:
            self._agents[agent_name].status = status

    def update_load(self, agent_name: str, delta: int):
        """Increment/decrement agent load counter."""
        if agent_name in self._agents:
            self._agents[agent_name].current_load = max(
                0, self._agents[agent_name].current_load + delta
            )

    # ============================================
    # Messaging
    # ============================================

    async def send(self, message: A2AMessage) -> bool:
        """Send a message between agents."""
        if message.to_agent not in self._agents:
            logger.warning(f"A2A: Target agent '{message.to_agent}' not found")
            return False

        self._message_log.append(message)

        logger.info(f"A2A message sent", extra={"props": {
            "from": message.from_agent, "to": message.to_agent,
            "type": message.message_type, "priority": message.priority,
        }})

        return True

    async def broadcast(self, from_agent: str, content: str, exclude: list[str] | None = None):
        """Send a message to all registered agents."""
        exclude = exclude or [from_agent]

        for agent_name in self._agents:
            if agent_name not in exclude:
                msg = A2AMessage(
                    from_agent=from_agent,
                    to_agent=agent_name,
                    message_type="broadcast",
                    content=content,
                )
                await self.send(msg)

    async def get_messages(
        self,
        agent_name: str,
        since: datetime | None = None,
        message_type: str | None = None,
    ) -> list[A2AMessage]:
        """Get messages for an agent."""
        messages = [m for m in self._message_log if m.to_agent == agent_name]

        if since:
            messages = [m for m in messages if m.timestamp > since]
        if message_type:
            messages = [m for m in messages if m.message_type == message_type]

        return sorted(messages, key=lambda m: m.timestamp, reverse=True)

    # ============================================
    # Delegation
    # ============================================

    async def delegate(self, request: DelegationRequest) -> A2AMessage:
        """Delegate a task from one agent to another."""
        # Update load
        self.update_load(request.to_agent, 1)

        message = A2AMessage(
            from_agent=request.from_agent,
            to_agent=request.to_agent,
            message_type="delegation",
            content=request.task_description,
            metadata={
                "context": request.context,
                "thinking_level": request.thinking_level,
                "callback_id": request.callback_id,
            },
        )

        self._pending_delegations[message.id] = request
        await self.send(message)

        logger.info(f"A2A delegation: {request.from_agent} → {request.to_agent}")
        return message

    async def complete_delegation(self, delegation_id: UUID, result: str):
        """Mark a delegation as complete and return result."""
        request = self._pending_delegations.pop(delegation_id, None)
        if not request:
            return

        self.update_load(request.to_agent, -1)

        response = A2AMessage(
            from_agent=request.to_agent,
            to_agent=request.from_agent,
            message_type="response",
            content=result,
            reply_to=delegation_id,
        )
        await self.send(response)

    def get_pending_delegations(self, agent_name: str) -> list[DelegationRequest]:
        """Get pending delegations for an agent."""
        return [
            req for req in self._pending_delegations.values()
            if req.to_agent == agent_name
        ]

    # ============================================
    # Stats
    # ============================================

    def get_stats(self) -> dict:
        """Get A2A protocol statistics."""
        return {
            "registered_agents": len(self._agents),
            "total_messages": len(self._message_log),
            "pending_delegations": len(self._pending_delegations),
            "agents": {
                name: {
                    "status": card.status,
                    "load": card.current_load,
                    "capabilities": card.capabilities,
                }
                for name, card in self._agents.items()
            },
        }


# Singleton
a2a_protocol = A2AProtocol()
