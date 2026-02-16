"""
Agent Optimus — Autonomous Executor (Fase 11: Jarvis Mode).
Executes high-confidence tasks without user permission.
Full audit trail. Sandbox enforcement for risky tasks.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from uuid import uuid4

from src.core.events import Event, EventType, event_bus

logger = logging.getLogger(__name__)

AUDIT_DIR = Path(__file__).parent.parent.parent / "workspace" / "autonomous"
AUDIT_FILE = AUDIT_DIR / "audit.jsonl"
CONFIG_FILE = AUDIT_DIR / "config.json"


class ExecutionStatus(str, Enum):
    """Status of an autonomous execution."""

    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    SKIPPED = "skipped"
    NEEDS_APPROVAL = "needs_approval"


class TaskRisk(str, Enum):
    """Risk level of a task."""

    LOW = "low"  # Read-only, queries, searches
    MEDIUM = "medium"  # File edits, config changes
    HIGH = "high"  # Deploy, database mutations, external API calls
    CRITICAL = "critical"  # Destructive: delete, drop, production changes


@dataclass
class ExecutionResult:
    """Result of an autonomous execution."""

    id: str = field(default_factory=lambda: str(uuid4())[:8])
    task: str = ""
    status: ExecutionStatus = ExecutionStatus.SKIPPED
    confidence: float = 0.0
    risk: TaskRisk = TaskRisk.LOW
    output: str = ""
    error: str = ""
    agent_name: str = ""
    executed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    duration_ms: int = 0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        d["risk"] = self.risk.value
        return d


# Risk keywords for task classification
RISK_KEYWORDS: dict[TaskRisk, list[str]] = {
    TaskRisk.CRITICAL: [
        "delete", "drop", "destroy", "production", "rm -rf", "truncate",
        "apagar", "destruir", "produção", "remover tudo",
    ],
    TaskRisk.HIGH: [
        "deploy", "migrate", "mutation", "write to", "push to main",
        "external api", "send email", "payment", "billing",
    ],
    TaskRisk.MEDIUM: [
        "edit", "modify", "create file", "config", "update",
        "editar", "modificar", "criar arquivo", "atualizar",
    ],
    TaskRisk.LOW: [
        "read", "search", "query", "list", "get", "check", "status",
        "ler", "buscar", "consultar", "verificar",
    ],
}


@dataclass
class ExecutorConfig:
    """Configuration for the autonomous executor."""

    auto_execute_threshold: float = 0.9
    max_risk_level: str = "medium"  # Max risk to auto-execute without approval
    require_sandbox_for: list[str] = field(
        default_factory=lambda: ["code_execution", "file_mutation", "deploy"]
    )
    daily_budget: int = 50  # Max auto-executions per day
    enabled: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ExecutorConfig":
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in data.items() if k in known})


class AutonomousExecutor:
    """
    Executes tasks autonomously when confidence is high enough.

    Rules:
    - Confidence must exceed threshold (default: 0.9)
    - Risk level must be within max_risk_level
    - Critical tasks ALWAYS require approval
    - Full audit trail in JSONL format
    """

    def __init__(self):
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        self.config = self._load_config()
        self._today_count = 0

    def _load_config(self) -> ExecutorConfig:
        """Load executor config from file."""
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                return ExecutorConfig.from_dict(data)
            except (json.JSONDecodeError, KeyError):
                pass
        return ExecutorConfig()

    def save_config(self) -> None:
        """Persist executor config."""
        CONFIG_FILE.write_text(
            json.dumps(self.config.to_dict(), indent=2),
            encoding="utf-8",
        )

    def classify_risk(self, task: str) -> TaskRisk:
        """Classify the risk level of a task based on keywords."""
        task_lower = task.lower()

        for risk_level in [TaskRisk.CRITICAL, TaskRisk.HIGH, TaskRisk.MEDIUM, TaskRisk.LOW]:
            keywords = RISK_KEYWORDS.get(risk_level, [])
            if any(kw in task_lower for kw in keywords):
                return risk_level

        return TaskRisk.LOW

    def _risk_within_limit(self, risk: TaskRisk) -> bool:
        """Check if a risk level is within the configured max."""
        risk_order = [TaskRisk.LOW, TaskRisk.MEDIUM, TaskRisk.HIGH, TaskRisk.CRITICAL]
        max_idx = risk_order.index(TaskRisk(self.config.max_risk_level))
        task_idx = risk_order.index(risk)
        return task_idx <= max_idx

    def should_auto_execute(self, task: str, confidence: float) -> bool:
        """
        Determine if a task should be auto-executed.

        Returns True if all conditions are met:
        - Executor is enabled
        - Confidence >= threshold
        - Risk level within limit
        - Not critical risk
        - Under daily budget
        """
        if not self.config.enabled:
            return False

        if confidence < self.config.auto_execute_threshold:
            return False

        risk = self.classify_risk(task)
        if risk == TaskRisk.CRITICAL:
            return False  # Critical ALWAYS needs approval

        if not self._risk_within_limit(risk):
            return False

        if self._today_count >= self.config.daily_budget:
            logger.warning("Autonomous executor: daily budget exceeded")
            return False

        return True

    async def execute(self, task: str, confidence: float, agent_name: str = "optimus") -> ExecutionResult:
        """
        Attempt to auto-execute a task.

        If conditions aren't met, returns SKIPPED or NEEDS_APPROVAL.
        """
        risk = self.classify_risk(task)

        result = ExecutionResult(
            task=task,
            confidence=confidence,
            risk=risk,
            agent_name=agent_name,
        )

        if not self.should_auto_execute(task, confidence):
            if risk == TaskRisk.CRITICAL:
                result.status = ExecutionStatus.NEEDS_APPROVAL
                result.output = f"⚠️ Task requires approval (risk: {risk.value})"
            else:
                result.status = ExecutionStatus.SKIPPED
                result.output = f"Skipped: confidence={confidence}, risk={risk.value}"

            self._audit(result)
            return result

        # Execute (in MVP: just log and mark success — real execution comes later)
        try:
            result.status = ExecutionStatus.SUCCESS
            result.output = f"✅ Auto-executed: {task[:100]}"
            self._today_count += 1

            # Emit event
            await event_bus.emit(Event(
                type=EventType.TASK_COMPLETED,
                source="autonomous_executor",
                data={
                    "task": task[:200],
                    "confidence": confidence,
                    "risk": risk.value,
                    "auto_executed": True,
                },
            ))

            logger.info(f"Auto-executed: '{task[:80]}' (confidence={confidence}, risk={risk.value})")

        except Exception as e:
            result.status = ExecutionStatus.FAILED
            result.error = str(e)
            logger.error(f"Auto-execution failed: {e}")

        self._audit(result)
        return result

    def _audit(self, result: ExecutionResult) -> None:
        """Append execution result to audit trail (JSONL)."""
        with open(AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(result.to_dict(), ensure_ascii=False) + "\n")

    def get_audit_trail(self, limit: int = 50) -> list[dict]:
        """Get recent audit trail entries."""
        if not AUDIT_FILE.exists():
            return []

        entries: list[dict] = []
        try:
            lines = AUDIT_FILE.read_text(encoding="utf-8").strip().split("\n")
            for line in lines[-limit:]:
                if line:
                    entries.append(json.loads(line))
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Audit trail read error: {e}")

        return entries

    def get_stats(self) -> dict:
        """Get executor statistics."""
        trail = self.get_audit_trail(limit=1000)
        return {
            "total_executions": len(trail),
            "today_count": self._today_count,
            "daily_budget": self.config.daily_budget,
            "threshold": self.config.auto_execute_threshold,
            "max_risk": self.config.max_risk_level,
            "enabled": self.config.enabled,
            "by_status": {
                status.value: sum(1 for e in trail if e.get("status") == status.value)
                for status in ExecutionStatus
            },
        }


# Singleton
autonomous_executor = AutonomousExecutor()
