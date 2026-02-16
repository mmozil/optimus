"""
Agent Optimus — Distributed Tracing (Phase 16).
OpenTelemetry integration for end-to-end request tracing.
Each request = 1 trace, each ReAct step = 1 span.
"""

import logging
from contextlib import contextmanager

from src.core.config import settings

logger = logging.getLogger(__name__)

# ============================================
# OpenTelemetry Setup (lazy, optional)
# ============================================

_tracer = None
_OTEL_AVAILABLE = False

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        ConsoleSpanExporter,
    )
    from opentelemetry.sdk.resources import Resource
    _OTEL_AVAILABLE = True
except ImportError:
    pass


def init_tracing():
    """Initialize OpenTelemetry tracing. Call once at app startup."""
    global _tracer

    if not settings.TRACING_ENABLED:
        logger.info("Tracing disabled (TRACING_ENABLED=False)")
        return

    if not _OTEL_AVAILABLE:
        logger.warning("opentelemetry-sdk not installed. Tracing disabled.")
        return

    resource = Resource.create({
        "service.name": settings.OTEL_SERVICE_NAME,
        "service.version": settings.VERSION,
        "deployment.environment": settings.ENVIRONMENT,
    })

    provider = TracerProvider(resource=resource)

    if settings.OTEL_EXPORTER_TYPE == "otlp":
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
            exporter = OTLPSpanExporter(
                endpoint=settings.OTEL_EXPORTER_ENDPOINT,
            )
            provider.add_span_processor(BatchSpanProcessor(exporter))
            logger.info(f"OTLP exporter → {settings.OTEL_EXPORTER_ENDPOINT}")
        except ImportError:
            logger.warning("OTLP exporter not available, falling back to console")
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    else:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        logger.info("Console trace exporter active")

    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer("agent-optimus", settings.VERSION)

    logger.info("OpenTelemetry tracing initialized")


def get_tracer():
    """Get the application tracer. Returns None if tracing is disabled."""
    return _tracer


# ============================================
# Convenience Helpers
# ============================================

@contextmanager
def trace_span(name: str, attributes: dict | None = None):
    """
    Context manager for creating traced spans.
    No-ops gracefully if tracing is disabled.

    Usage:
        with trace_span("react_step", {"tool": "file_read", "iteration": 1}):
            result = await do_work()
    """
    tracer = get_tracer()
    if tracer is None:
        yield None
        return

    with tracer.start_as_current_span(name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value) if not isinstance(value, (int, float, bool)) else value)
        try:
            yield span
        except Exception as e:
            span.set_attribute("error", True)
            span.set_attribute("error.message", str(e)[:500])
            span.record_exception(e)
            raise


def trace_event(name: str, attributes: dict | None = None):
    """Add an event to the current active span."""
    tracer = get_tracer()
    if tracer is None:
        return

    span = trace.get_current_span()
    if span and span.is_recording():
        span.add_event(name, attributes=attributes or {})
