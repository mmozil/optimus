"""
Agent Optimus — A2A Protocol API (FASE 0 #25: A2AProtocol).
REST endpoints for agent-to-agent discovery, messaging, and delegation.
"""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.core.a2a_protocol import (
    A2AMessage,
    AgentCard,
    DelegationRequest,
    a2a_protocol,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/a2a", tags=["a2a"])


# ============================================
# Request / Response Models
# ============================================


class RegisterAgentRequest(BaseModel):
    name: str
    role: str
    level: str = Field(..., description="lead | specialist | intern")
    capabilities: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    status: str = "available"
    max_concurrent: int = 5


class AgentCardResponse(BaseModel):
    name: str
    role: str
    level: str
    capabilities: list[str]
    tools: list[str]
    status: str
    max_concurrent: int
    current_load: int

    @classmethod
    def from_card(cls, card: AgentCard) -> "AgentCardResponse":
        return cls(
            name=card.name,
            role=card.role,
            level=card.level,
            capabilities=card.capabilities,
            tools=card.tools,
            status=card.status,
            max_concurrent=card.max_concurrent,
            current_load=card.current_load,
        )


class UpdateStatusRequest(BaseModel):
    status: str = Field(..., description="available | busy | offline")


class SendMessageRequest(BaseModel):
    from_agent: str
    to_agent: str
    message_type: str = Field("request", description="request | response | broadcast | delegation")
    content: str
    priority: str = "normal"
    metadata: dict = Field(default_factory=dict)


class MessageResponse(BaseModel):
    id: str
    from_agent: str
    to_agent: str
    message_type: str
    content: str
    priority: str
    timestamp: datetime
    metadata: dict

    @classmethod
    def from_message(cls, msg: A2AMessage) -> "MessageResponse":
        return cls(
            id=str(msg.id),
            from_agent=msg.from_agent,
            to_agent=msg.to_agent,
            message_type=msg.message_type,
            content=msg.content,
            priority=msg.priority,
            timestamp=msg.timestamp,
            metadata=msg.metadata,
        )


class BroadcastRequest(BaseModel):
    from_agent: str
    content: str
    exclude: list[str] = Field(default_factory=list)


class DelegateRequest(BaseModel):
    from_agent: str
    to_agent: str
    task_description: str
    context: str = ""
    thinking_level: str = "standard"
    timeout: float = 120.0


class DelegationResponse(BaseModel):
    delegation_id: str
    from_agent: str
    to_agent: str
    task_description: str
    message_id: str


class CompleteDelegationRequest(BaseModel):
    result: str


# ============================================
# Endpoints
# ============================================


@router.post("/agents/register", response_model=AgentCardResponse, status_code=201)
async def register_agent(request: RegisterAgentRequest) -> AgentCardResponse:
    """
    Register an agent in the A2A discovery service.

    Agents must register before they can send/receive messages.
    """
    card = AgentCard(
        name=request.name,
        role=request.role,
        level=request.level,
        capabilities=request.capabilities,
        tools=request.tools,
        status=request.status,
        max_concurrent=request.max_concurrent,
    )
    a2a_protocol.register_agent(card)
    return AgentCardResponse.from_card(card)


@router.get("/agents", response_model=list[AgentCardResponse])
async def discover_agents(
    capability: str | None = None,
    level: str | None = None,
    available_only: bool = True,
) -> list[AgentCardResponse]:
    """
    Discover registered agents, with optional filters.

    - capability: filter by capability (e.g. "code_review", "analysis")
    - level: filter by level (lead | specialist | intern)
    - available_only: only return agents with status=available
    """
    agents = a2a_protocol.discover(
        capability=capability,
        level=level,
        available_only=available_only,
    )
    return [AgentCardResponse.from_card(a) for a in agents]


@router.get("/agents/{agent_name}", response_model=AgentCardResponse)
async def get_agent(agent_name: str) -> AgentCardResponse:
    """Get a specific agent's card by name."""
    card = a2a_protocol.get_card(agent_name)
    if not card:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    return AgentCardResponse.from_card(card)


@router.put("/agents/{agent_name}/status")
async def update_agent_status(agent_name: str, request: UpdateStatusRequest) -> dict:
    """Update an agent's availability status (available | busy | offline)."""
    card = a2a_protocol.get_card(agent_name)
    if not card:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    a2a_protocol.update_status(agent_name, request.status)
    return {"agent": agent_name, "status": request.status}


@router.post("/messages", response_model=MessageResponse)
async def send_message(request: SendMessageRequest) -> MessageResponse:
    """
    Send a message from one agent to another.

    Target agent must be registered first.
    """
    message = A2AMessage(
        from_agent=request.from_agent,
        to_agent=request.to_agent,
        message_type=request.message_type,
        content=request.content,
        priority=request.priority,
        metadata=request.metadata,
    )
    success = await a2a_protocol.send(message)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Target agent '{request.to_agent}' not registered",
        )
    return MessageResponse.from_message(message)


@router.get("/messages/{agent_name}", response_model=list[MessageResponse])
async def get_messages(
    agent_name: str,
    message_type: str | None = None,
) -> list[MessageResponse]:
    """Get all messages received by an agent."""
    messages = await a2a_protocol.get_messages(
        agent_name=agent_name,
        message_type=message_type,
    )
    return [MessageResponse.from_message(m) for m in messages]


@router.post("/broadcast")
async def broadcast_message(request: BroadcastRequest) -> dict:
    """
    Broadcast a message to all registered agents.

    Automatically excludes the sender and any agents in 'exclude' list.
    """
    exclude = list(set(request.exclude + [request.from_agent]))
    await a2a_protocol.broadcast(
        from_agent=request.from_agent,
        content=request.content,
        exclude=exclude,
    )
    recipient_count = len(a2a_protocol._agents) - len(exclude)
    return {
        "from_agent": request.from_agent,
        "recipients": max(0, recipient_count),
        "content_preview": request.content[:100],
    }


@router.post("/delegate", response_model=DelegationResponse, status_code=201)
async def delegate_task(request: DelegateRequest) -> DelegationResponse:
    """
    Delegate a task from one agent to another.

    Increments the target agent's load counter.
    Use POST /delegate/{id}/complete when done.
    """
    target = a2a_protocol.get_card(request.to_agent)
    if not target:
        raise HTTPException(
            status_code=404,
            detail=f"Target agent '{request.to_agent}' not registered",
        )

    delegation = DelegationRequest(
        from_agent=request.from_agent,
        to_agent=request.to_agent,
        task_description=request.task_description,
        context=request.context,
        thinking_level=request.thinking_level,
        timeout=request.timeout,
    )
    message = await a2a_protocol.delegate(delegation)

    return DelegationResponse(
        delegation_id=str(message.id),
        from_agent=request.from_agent,
        to_agent=request.to_agent,
        task_description=request.task_description,
        message_id=str(message.id),
    )


@router.post("/delegate/{delegation_id}/complete")
async def complete_delegation(
    delegation_id: UUID, request: CompleteDelegationRequest
) -> dict:
    """
    Mark a delegation as complete and send result back to delegating agent.

    Decrements the target agent's load counter.
    """
    await a2a_protocol.complete_delegation(delegation_id, request.result)
    return {
        "delegation_id": str(delegation_id),
        "status": "completed",
        "result_preview": request.result[:100],
    }


@router.get("/stats")
async def get_stats() -> dict:
    """Get A2A protocol statistics — registered agents, messages, pending delegations."""
    return a2a_protocol.get_stats()
