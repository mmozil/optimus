"""
Agent Optimus — Prometheus Metrics.
Application metrics for monitoring: tokens, latency, errors, sessions.
Optional dependency: prometheus_client.
"""

import logging
import time
from functools import wraps

try:
    from prometheus_client import (
        Counter,
        Gauge,
        Histogram,
        Info,
        generate_latest,
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Mock classes if prometheus_client is not installed
    class MockMetric:
        def __init__(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self
        def inc(self, *args, **kwargs): pass
        def dec(self, *args, **kwargs): pass
        def set(self, *args, **kwargs): pass
        def observe(self, *args, **kwargs): pass
        def info(self, *args, **kwargs): pass

    Counter = Gauge = Histogram = Info = MockMetric
    def generate_latest(): return b""

logger = logging.getLogger(__name__)

if not PROMETHEUS_AVAILABLE:
    logger.warning("prometheus_client not installed, metrics will be disabled")

# ============================================
# Application Info
# ============================================
APP_INFO = Info("optimus", "Agent Optimus platform info")
APP_INFO.info({
    "version": "0.1.0",
    "framework": "agno",
    "orchestration": "google_adk",
})

# ============================================
# Request Metrics
# ============================================
REQUEST_COUNT = Counter(
    "optimus_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "optimus_request_duration_seconds",
    "Request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

# ============================================
# Agent Metrics
# ============================================
AGENT_REQUESTS = Counter(
    "optimus_agent_requests_total",
    "Total agent processing requests",
    ["agent_name", "agent_level"],
)

AGENT_ERRORS = Counter(
    "optimus_agent_errors_total",
    "Total agent processing errors",
    ["agent_name", "error_type"],
)

AGENT_LATENCY = Histogram(
    "optimus_agent_processing_seconds",
    "Agent processing latency in seconds",
    ["agent_name"],
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 15.0, 30.0, 60.0],
)

ACTIVE_AGENTS = Gauge(
    "optimus_active_agents",
    "Currently active agents",
)

# ============================================
# Token Metrics
# ============================================
TOKENS_USED = Counter(
    "optimus_tokens_total",
    "Total tokens consumed",
    ["agent_name", "model", "type"],  # type: input/output
)

TOKEN_COST = Counter(
    "optimus_token_cost_usd",
    "Estimated token cost in USD",
    ["agent_name", "model"],
)

# ============================================
# Channel Metrics
# ============================================
CHANNEL_MESSAGES = Counter(
    "optimus_channel_messages_total",
    "Total messages received per channel",
    ["channel"],  # telegram, whatsapp, slack, webchat
)

CHANNEL_ERRORS = Counter(
    "optimus_channel_errors_total",
    "Total channel errors",
    ["channel", "error_type"],
)

# ============================================
# Memory & Cache Metrics
# ============================================
CACHE_HITS = Counter("optimus_cache_hits_total", "Total cache hits")
CACHE_MISSES = Counter("optimus_cache_misses_total", "Total cache misses")

ACTIVE_SESSIONS = Gauge(
    "optimus_active_sessions",
    "Currently active sessions",
)

MEMORY_OPERATIONS = Counter(
    "optimus_memory_operations_total",
    "Total memory operations",
    ["operation", "memory_type"],  # operation: read/write, type: working/daily/longterm
)

# ============================================
# Task Metrics
# ============================================
TASKS_CREATED = Counter("optimus_tasks_created_total", "Total tasks created")
TASKS_COMPLETED = Counter("optimus_tasks_completed_total", "Total tasks completed")
TASKS_ACTIVE = Gauge("optimus_tasks_active", "Currently active tasks")

# ============================================
# MCP Tool Metrics
# ============================================
MCP_TOOL_CALLS = Counter(
    "optimus_mcp_tool_calls_total",
    "Total MCP tool executions",
    ["tool_name", "category"],
)

MCP_TOOL_ERRORS = Counter(
    "optimus_mcp_tool_errors_total",
    "Total MCP tool errors",
    ["tool_name"],
)

MCP_TOOL_LATENCY = Histogram(
    "optimus_mcp_tool_duration_seconds",
    "MCP tool execution latency",
    ["tool_name"],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0],
)


# ============================================
# Helper Decorators
# ============================================

def track_agent_request(agent_name: str, agent_level: str = "specialist"):
    """Decorator to track agent request metrics."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if PROMETHEUS_AVAILABLE:
                AGENT_REQUESTS.labels(agent_name=agent_name, agent_level=agent_level).inc()
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                if PROMETHEUS_AVAILABLE:
                    duration = time.time() - start
                    AGENT_LATENCY.labels(agent_name=agent_name).observe(duration)
                return result
            except Exception as e:
                if PROMETHEUS_AVAILABLE:
                    AGENT_ERRORS.labels(agent_name=agent_name, error_type=type(e).__name__).inc()
                raise
        return wrapper
    return decorator


def track_mcp_tool(tool_name: str, category: str = "custom"):
    """Decorator to track MCP tool execution metrics."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if PROMETHEUS_AVAILABLE:
                MCP_TOOL_CALLS.labels(tool_name=tool_name, category=category).inc()
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                if PROMETHEUS_AVAILABLE:
                    duration = time.time() - start
                    MCP_TOOL_LATENCY.labels(tool_name=tool_name).observe(duration)
                return result
            except Exception as e:
                if PROMETHEUS_AVAILABLE:
                    MCP_TOOL_ERRORS.labels(tool_name=tool_name).inc()
                raise
        return wrapper
    return decorator


def get_metrics() -> bytes:
    """Generate Prometheus metrics output."""
    return generate_latest()
