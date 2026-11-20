"""FastAPI entrypoint for Holiday Card Studio."""

from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from opentelemetry import trace

from app.agents.pipeline import HolidayCardPipeline
from app.agents.schemas import (
    CardGenerationResponse,
    CardRequestInput,
    ConfirmCardInput,
    RemixRequestInput,
)
from app.agents.tools.memory_tools import get_anonymized_vibe_stats
from app.config import apply_vertex_env, get_settings, load_theme_config
from app.observability.logging import configure_logging, get_logger
from app.observability.tracing import configure_tracing, instrument_fastapi

_RATE_BUCKETS: dict[str, deque[float]] = defaultdict(deque)
_PIPELINE: HolidayCardPipeline | None = None


def _check_rate_limit(client_ip: str, limit_per_minute: int) -> None:
    now = time.monotonic()
    bucket = _RATE_BUCKETS[client_ip]
    while bucket and now - bucket[0] > 60.0:
        bucket.popleft()
    if len(bucket) >= limit_per_minute:
        raise HTTPException(
            status_code=429,
            detail="Too many card requests right now. Please wait a few seconds and try again.",
        )
    bucket.append(now)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize logging, tracing, and ADK pipeline on startup."""
    global _PIPELINE
    settings = get_settings()
    apply_vertex_env(settings)
    redactor = configure_logging(
        log_level=settings.log_level,
        project_id=settings.google_cloud_project,
        enable_cloud_dlp=settings.enable_cloud_dlp,
    )
    configure_tracing(
        project_id=settings.google_cloud_project,
        enable_cloud_trace=settings.enable_cloud_trace,
    )
    _PIPELINE = HolidayCardPipeline(settings=settings, redactor=redactor)
    get_logger("app.main").info("startup_complete", project_id=settings.google_cloud_project)
    yield


app = FastAPI(title="Holiday Card Studio", version="0.1.0", lifespan=lifespan)
instrument_fastapi(app)

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


def _get_trace_id() -> str | None:
    ctx = trace.get_current_span().get_span_context()
    if ctx and ctx.is_valid:
        return format(ctx.trace_id, "032x")
    return None


@app.get("/")
async def index() -> FileResponse:
    """Serve the mobile-first single-page frontend."""
    return FileResponse(_STATIC_DIR / "index.html")


@app.get("/api/health")
async def health() -> dict[str, str]:
    """Health check endpoint for Cloud Run and load balancers."""
    return {"status": "ok"}


@app.get("/api/config")
async def public_config() -> dict[str, object]:
    """Return non-sensitive deploy-time event branding and style options."""
    theme = load_theme_config()
    return {
        "event_title": theme.event_title,
        "event_footer": theme.event_footer,
        "styles": [s.model_dump() for s in theme.styles.values()],
        "vibe_stats": get_anonymized_vibe_stats(),
    }


@app.post("/api/generate-card", response_model=CardGenerationResponse)
async def generate_card(req: CardRequestInput, request: Request) -> CardGenerationResponse:
    """Generate a personalized holiday card using the ADK multi-agent pipeline."""
    if _PIPELINE is None:
        raise HTTPException(status_code=503, detail="Agent pipeline is still initializing.")

    settings = get_settings()
    apply_vertex_env(settings)
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip, settings.rate_limit_per_minute)

    session_id = req.session_id or str(uuid.uuid4())
    return await _PIPELINE.generate_card(req=req, session_id=session_id, trace_id=_get_trace_id())


@app.post("/api/remix-card", response_model=CardGenerationResponse)
async def remix_card(req: RemixRequestInput, request: Request) -> CardGenerationResponse:
    """Remix an existing holiday card in the same persistent session."""
    if _PIPELINE is None:
        raise HTTPException(status_code=503, detail="Agent pipeline is still initializing.")

    settings = get_settings()
    apply_vertex_env(settings)
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip, settings.rate_limit_per_minute)

    return await _PIPELINE.remix_card(req=req, trace_id=_get_trace_id())


@app.post("/api/confirm-card", response_model=CardGenerationResponse)
async def confirm_card(req: ConfirmCardInput) -> CardGenerationResponse:
    """Resume a paused HITL card generation after guest confirmation."""
    if _PIPELINE is None:
        raise HTTPException(status_code=503, detail="Agent pipeline is still initializing.")

    return await _PIPELINE.confirm_card(req=req, trace_id=_get_trace_id())
