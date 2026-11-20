"""OpenTelemetry distributed tracing setup for FastAPI and ADK."""

from __future__ import annotations

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor, SpanExporter

_TRACING_INITIALIZED = False


def configure_tracing(
    service_name: str = "holiday-card-studio",
    project_id: str = "",
    enable_cloud_trace: bool = False,
    custom_exporter: SpanExporter | None = None,
) -> trace.Tracer:
    """Initialize OpenTelemetry TracerProvider with Cloud Trace or custom exporter.

    Args:
        service_name: Service name attached to all spans.
        project_id: GCP project ID for Cloud Trace export.
        enable_cloud_trace: Whether to export spans to Google Cloud Trace.
        custom_exporter: Optional exporter (e.g., InMemorySpanExporter for tests).

    Returns:
        Configured OpenTelemetry Tracer.
    """
    global _TRACING_INITIALIZED
    if not _TRACING_INITIALIZED:
        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)

        if custom_exporter is not None:
            provider.add_span_processor(SimpleSpanProcessor(custom_exporter))
        elif enable_cloud_trace and project_id:
            from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter

            exporter = CloudTraceSpanExporter(project_id=project_id)
            provider.add_span_processor(BatchSpanProcessor(exporter))

        trace.set_tracer_provider(provider)
        _TRACING_INITIALIZED = True

    return trace.get_tracer(service_name)


def instrument_fastapi(app: FastAPI) -> None:
    """Attach OpenTelemetry FastAPI middleware to trace inbound HTTP requests."""
    FastAPIInstrumentor.instrument_app(app)
