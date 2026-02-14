"""
Agent Optimus — Security Manager.
Permission matrix, audit trail, and sandbox levels for agents.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

logger = logging.getLogger(__name__)


class SandboxLevel(str, Enum):
    FULL_ACCESS = "full_access"    # lead agents
    RESTRICTED = "restricted"      # specialist agents
    ISOLATED = "isolated"         # intern agents — no external access


class Permission(str, Enum):
    DB_READ = "db_read"
    DB_WRITE = "db_write"
    FS_READ = "fs_read"
    FS_WRITE = "fs_write"
    NETWORK = "network"
    MCP_EXECUTE = "mcp_execute"
    AGENT_DELEGATE = "agent_delegate"
    SYSTEM_CONFIG = "system_config"


# Permission matrix by agent level
PERMISSION_MATRIX: dict[str, set[Permission]] = {
    "lead": {
        Permission.DB_READ, Permission.DB_WRITE,
        Permission.FS_READ, Permission.FS_WRITE,
        Permission.NETWORK, Permission.MCP_EXECUTE,
        Permission.AGENT_DELEGATE, Permission.SYSTEM_CONFIG,
    },
    "specialist": {
        Permission.DB_READ, Permission.DB_WRITE,
        Permission.FS_READ, Permission.FS_WRITE,
        Permission.NETWORK, Permission.MCP_EXECUTE,
        Permission.AGENT_DELEGATE,
    },
    "intern": {
        Permission.DB_READ,
        Permission.FS_READ,
        Permission.MCP_EXECUTE,
    },
}

SANDBOX_BY_LEVEL: dict[str, SandboxLevel] = {
    "lead": SandboxLevel.FULL_ACCESS,
    "specialist": SandboxLevel.RESTRICTED,
    "intern": SandboxLevel.ISOLATED,
}


@dataclass
class AuditEntry:
    """Single audit trail entry."""
    id: str = field(default_factory=lambda: str(uuid4()))
    agent_name: str = ""
    action: str = ""  # What was attempted
    resource: str = ""  # What resource was accessed
    permission: str = ""
    allowed: bool = True
    reason: str = ""  # Why denied, if applicable
    metadata: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SecurityManager:
    """
    Manages agent permissions, sandbox levels, and audit trail.
    Enforces the principle of least privilege.
    """

    def __init__(self):
        self._audit_log: list[AuditEntry] = []
        self._custom_permissions: dict[str, set[Permission]] = {}  # agent-specific overrides
        self._max_audit_size = 50_000

    # ============================================
    # Permission Checks
    # ============================================

    def check_permission(
        self,
        agent_name: str,
        agent_level: str,
        permission: Permission,
        resource: str = "",
    ) -> bool:
        """Check if an agent has a specific permission."""
        # Check custom permissions first
        if agent_name in self._custom_permissions:
            allowed = permission in self._custom_permissions[agent_name]
        else:
            level_perms = PERMISSION_MATRIX.get(agent_level, set())
            allowed = permission in level_perms

        # Audit the check
        self._audit(AuditEntry(
            agent_name=agent_name,
            action="permission_check",
            resource=resource,
            permission=permission.value,
            allowed=allowed,
            reason="" if allowed else f"Level '{agent_level}' lacks '{permission.value}'",
        ))

        if not allowed:
            logger.warning(f"Permission denied: {agent_name} ({agent_level}) → {permission.value}", extra={
                "props": {"agent": agent_name, "permission": permission.value, "resource": resource}
            })

        return allowed

    def get_sandbox_level(self, agent_level: str) -> SandboxLevel:
        """Get the sandbox level for an agent level."""
        return SANDBOX_BY_LEVEL.get(agent_level, SandboxLevel.ISOLATED)

    def get_permissions(self, agent_name: str, agent_level: str) -> set[Permission]:
        """Get all permissions for an agent."""
        if agent_name in self._custom_permissions:
            return self._custom_permissions[agent_name]
        return PERMISSION_MATRIX.get(agent_level, set())

    def grant_permission(self, agent_name: str, permission: Permission):
        """Grant a custom permission to a specific agent."""
        if agent_name not in self._custom_permissions:
            self._custom_permissions[agent_name] = set()
        self._custom_permissions[agent_name].add(permission)

        self._audit(AuditEntry(
            action="permission_granted",
            agent_name=agent_name,
            permission=permission.value,
        ))

    def revoke_permission(self, agent_name: str, permission: Permission):
        """Revoke a custom permission from a specific agent."""
        if agent_name in self._custom_permissions:
            self._custom_permissions[agent_name].discard(permission)

        self._audit(AuditEntry(
            action="permission_revoked",
            agent_name=agent_name,
            permission=permission.value,
        ))

    # ============================================
    # Audit Trail
    # ============================================

    def _audit(self, entry: AuditEntry):
        """Record an audit entry."""
        self._audit_log.append(entry)
        if len(self._audit_log) > self._max_audit_size:
            self._audit_log = self._audit_log[-self._max_audit_size:]

    def audit_action(
        self,
        agent_name: str,
        action: str,
        resource: str = "",
        metadata: dict | None = None,
    ):
        """Record a general action in the audit trail."""
        self._audit(AuditEntry(
            agent_name=agent_name,
            action=action,
            resource=resource,
            metadata=metadata or {},
        ))

    def get_audit_log(
        self,
        agent_name: str | None = None,
        action: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """Query the audit trail."""
        entries = self._audit_log

        if agent_name:
            entries = [e for e in entries if e.agent_name == agent_name]
        if action:
            entries = [e for e in entries if e.action == action]
        if since:
            entries = [e for e in entries if e.timestamp > since]

        return sorted(entries, key=lambda e: e.timestamp, reverse=True)[:limit]

    def get_denied_actions(self, limit: int = 50) -> list[AuditEntry]:
        """Get recently denied permission checks."""
        denied = [e for e in self._audit_log if not e.allowed]
        return sorted(denied, key=lambda e: e.timestamp, reverse=True)[:limit]

    def get_audit_stats(self) -> dict:
        """Get audit statistics."""
        total = len(self._audit_log)
        denied = sum(1 for e in self._audit_log if not e.allowed)
        by_agent: dict[str, int] = {}
        for e in self._audit_log:
            if e.agent_name:
                by_agent[e.agent_name] = by_agent.get(e.agent_name, 0) + 1

        return {
            "total_entries": total,
            "denied_count": denied,
            "by_agent": by_agent,
        }


# Singleton
security_manager = SecurityManager()
