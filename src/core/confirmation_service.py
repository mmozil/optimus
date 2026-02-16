"""
Agent Optimus — Confirmation Service (Phase 15 — Human-in-the-Loop).
Pauses execution for destructive/high-risk actions and requests user confirmation.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    LOW = "low"           # Read-only, informational
    MEDIUM = "medium"     # Data modification, non-destructive writes
    HIGH = "high"         # Destructive, external, irreversible
    CRITICAL = "critical" # Deploy, delete, send email, financial


# Tool → risk level mapping
TOOL_RISK_MAP: dict[str, RiskLevel] = {
    # Low risk — informational / read-only
    "file_read": RiskLevel.LOW,
    "search": RiskLevel.LOW,
    "list_files": RiskLevel.LOW,
    "db_query": RiskLevel.LOW,

    # Medium risk — data modification
    "file_write": RiskLevel.MEDIUM,
    "file_edit": RiskLevel.MEDIUM,
    "db_insert": RiskLevel.MEDIUM,
    "db_update": RiskLevel.MEDIUM,

    # High risk — external effects
    "http_request": RiskLevel.HIGH,
    "api_call": RiskLevel.HIGH,
    "git_push": RiskLevel.HIGH,

    # Critical — irreversible / financial
    "file_delete": RiskLevel.CRITICAL,
    "db_delete": RiskLevel.CRITICAL,
    "deploy": RiskLevel.CRITICAL,
    "send_email": RiskLevel.CRITICAL,
    "code_execute": RiskLevel.CRITICAL,
}


@dataclass
class ConfirmationRequest:
    """A pending confirmation request."""
    id: str
    agent_name: str
    tool_name: str
    tool_args: dict
    risk_level: RiskLevel
    description: str
    status: str = "pending"      # pending | approved | denied | expired
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: datetime | None = None
    resolver: str = ""           # Who approved/denied


class ConfirmationService:
    """
    Manages human-in-the-loop confirmations for high-risk actions.

    Usage flow:
    1. ReAct loop calls `should_confirm(tool_name)` before executing a tool
    2. If True, `create_confirmation()` → returns ConfirmationRequest
    3. User approves/denies via API
    4. ReAct loop checks result and proceeds or skips
    """

    def __init__(self):
        self._pending: dict[str, ConfirmationRequest] = {}
        self._user_whitelists: dict[str, set[str]] = {}  # user_id → set of always-allowed tools
        self._timeout_seconds = 300  # 5 minutes default
        self._on_request_callback: Callable | None = None  # Notify user via channel

    # ============================================
    # Configuration
    # ============================================

    def set_user_whitelist(self, user_id: str, tools: set[str]):
        """Set tools that are always approved for a specific user."""
        self._user_whitelists[user_id] = tools
        logger.info(f"Whitelist updated for {user_id}: {tools}")

    def set_timeout(self, seconds: int):
        """Set confirmation timeout in seconds."""
        self._timeout_seconds = max(30, min(seconds, 1800))  # 30s to 30min

    def set_notification_callback(self, callback: Callable):
        """Set callback to notify user when confirmation is needed."""
        self._on_request_callback = callback

    # ============================================
    # Risk Assessment
    # ============================================

    def get_risk_level(self, tool_name: str) -> RiskLevel:
        """Get the risk level for a tool."""
        return TOOL_RISK_MAP.get(tool_name, RiskLevel.MEDIUM)

    def should_confirm(self, tool_name: str, user_id: str = "") -> bool:
        """
        Decide if a tool execution needs user confirmation.
        Returns False for low/medium risk or whitelisted tools.
        """
        risk = self.get_risk_level(tool_name)

        # Low risk — always auto-approve
        if risk == RiskLevel.LOW:
            return False

        # Whitelisted tools — auto-approve
        if user_id and user_id in self._user_whitelists:
            if tool_name in self._user_whitelists[user_id]:
                return False

        # High and Critical risk — require confirmation
        return risk in (RiskLevel.HIGH, RiskLevel.CRITICAL)

    # ============================================
    # Confirmation Lifecycle
    # ============================================

    async def create_confirmation(
        self,
        agent_name: str,
        tool_name: str,
        tool_args: dict,
        user_id: str = "",
    ) -> ConfirmationRequest:
        """Create a confirmation request and optionally notify the user."""
        import uuid

        request = ConfirmationRequest(
            id=str(uuid.uuid4()),
            agent_name=agent_name,
            tool_name=tool_name,
            tool_args=tool_args,
            risk_level=self.get_risk_level(tool_name),
            description=self._format_description(tool_name, tool_args),
        )

        self._pending[request.id] = request

        logger.info(
            f"Confirmation requested: {tool_name} ({request.risk_level}) by {agent_name}",
            extra={"props": {"request_id": request.id}}
        )

        # Notify user if callback is set
        if self._on_request_callback:
            try:
                await self._on_request_callback(request, user_id)
            except Exception as e:
                logger.error(f"Failed to notify user: {e}")

        return request

    async def wait_for_confirmation(self, request_id: str) -> str:
        """
        Wait for user to approve/deny. Returns 'approved', 'denied', or 'expired'.
        Non-blocking: uses asyncio polling.
        """
        elapsed = 0
        poll_interval = 1  # Check every 1 second

        while elapsed < self._timeout_seconds:
            req = self._pending.get(request_id)
            if not req:
                return "expired"

            if req.status in ("approved", "denied"):
                return req.status

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        # Timeout
        req = self._pending.get(request_id)
        if req and req.status == "pending":
            req.status = "expired"
            logger.warning(f"Confirmation expired: {request_id}")

        return "expired"

    def approve(self, request_id: str, resolver: str = "user") -> bool:
        """Approve a pending confirmation."""
        req = self._pending.get(request_id)
        if not req or req.status != "pending":
            return False

        req.status = "approved"
        req.resolved_at = datetime.now(timezone.utc)
        req.resolver = resolver
        logger.info(f"Confirmation approved: {request_id} by {resolver}")
        return True

    def deny(self, request_id: str, resolver: str = "user") -> bool:
        """Deny a pending confirmation."""
        req = self._pending.get(request_id)
        if not req or req.status != "pending":
            return False

        req.status = "denied"
        req.resolved_at = datetime.now(timezone.utc)
        req.resolver = resolver
        logger.info(f"Confirmation denied: {request_id} by {resolver}")
        return True

    def get_pending(self, user_id: str = "") -> list[ConfirmationRequest]:
        """Get all pending confirmation requests."""
        return [r for r in self._pending.values() if r.status == "pending"]

    # ============================================
    # Helpers
    # ============================================

    @staticmethod
    def _format_description(tool_name: str, tool_args: dict) -> str:
        """Format a human-readable description of the action."""
        args_preview = ", ".join(f"{k}={v}" for k, v in list(tool_args.items())[:3])
        return f"Executar '{tool_name}' com argumentos: {args_preview}"


# Singleton
confirmation_service = ConfirmationService()
