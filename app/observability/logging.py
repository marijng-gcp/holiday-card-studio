"""Structured JSON logging with trace correlation and PII redaction."""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from opentelemetry import trace

from app.observability.pii_redactor import PIIRedactor


def _add_otel_context(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    span = trace.get_current_span()
    ctx = span.get_span_context() if span else None
    if ctx and ctx.is_valid:
        event_dict["trace_id"] = format(ctx.trace_id, "032x")
        event_dict["span_id"] = format(ctx.span_id, "016x")
    return event_dict


def configure_logging(
    log_level: str = "INFO",
    project_id: str = "",
    enable_cloud_dlp: bool = False,
) -> PIIRedactor:
    """Configure structlog to emit structured, PII-redacted JSON logs.

    Args:
        log_level: Minimum log level (e.g., INFO, DEBUG).
        project_id: Optional GCP project ID for Cloud DLP redaction.
        enable_cloud_dlp: Whether to invoke Cloud DLP in addition to regex scrubbing.

    Returns:
        Configured PIIRedactor instance.
    """
    redactor = PIIRedactor(project_id=project_id, enable_cloud_dlp=enable_cloud_dlp)

    def _redact_processor(
        logger: Any, method_name: str, event_dict: dict[str, Any]
    ) -> dict[str, Any]:
        return redactor.redact_dict(event_dict)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _add_otel_context,
            _redact_processor,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    return redactor


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a structured logger bound to module name."""
    return structlog.get_logger(name)
