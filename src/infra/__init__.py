"""
Agent Optimus — Infrastructure module.
Logging, metrics, and observability.
"""

from src.infra.logging_config import setup_logging, add_telegram_alerts
from src.infra.metrics import (
    get_metrics,
    track_agent_request,
    track_mcp_tool,
    REQUEST_COUNT,
    REQUEST_LATENCY,
    AGENT_REQUESTS,
    TOKENS_USED,
    CHANNEL_MESSAGES,
)

__all__ = [
    "setup_logging",
    "add_telegram_alerts",
    "get_metrics",
    "track_agent_request",
    "track_mcp_tool",
    "REQUEST_COUNT",
    "REQUEST_LATENCY",
    "AGENT_REQUESTS",
    "TOKENS_USED",
    "CHANNEL_MESSAGES",
]
