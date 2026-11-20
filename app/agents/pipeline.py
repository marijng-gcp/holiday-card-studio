"""ADK App, Runner, SessionService, Compaction, and Async Memory consolidation."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from google.adk.agents import SequentialAgent
from google.adk.apps.app import App, EventsCompactionConfig, ResumabilityConfig
from google.adk.memory import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types

from app.agents.art_director import build_art_director_agent
from app.agents.copywriter import build_copy_loop_agent
from app.agents.plugins import HolidayPolicyGuardrailPlugin
from app.agents.schemas import (
    CardCopyOutput,
    CardGenerationResponse,
    CardRequestInput,
    ConfirmCardInput,
    RemixRequestInput,
)
from app.agents.tools.image_tools import _build_fallback_svg_base64
from app.config import Settings, apply_vertex_env, get_settings, load_theme_config
from app.observability.logging import get_logger
from app.observability.pii_redactor import PIIRedactor

APP_NAME = "holiday_card_studio"
DEFAULT_USER_ID = "party_guest"


class HolidayCardPipeline:
    """Orchestrates ADK Runner, persistent sessions, compaction, and async memory."""

    def __init__(self, settings: Settings, redactor: PIIRedactor) -> None:
        self._settings = settings
        self._redactor = redactor
        self._logger = get_logger("agent.pipeline")
        self._background_tasks: set[asyncio.Task[Any]] = set()

        if settings.session_db_url.startswith("sqlite") and ":///" in settings.session_db_url:
            db_file = settings.session_db_url.split(":///", 1)[1]
            if db_file and db_file != ":memory:":
                Path(db_file).parent.mkdir(parents=True, exist_ok=True)

        self.session_service = DatabaseSessionService(db_url=settings.session_db_url)
        self.memory_service = InMemoryMemoryService()
        self.guardrail_plugin = HolidayPolicyGuardrailPlugin(redactor=redactor)

        copy_loop = build_copy_loop_agent(fast_model=settings.fast_model)
        art_director = build_art_director_agent(pro_model=settings.pro_model)
        self.root_agent = SequentialAgent(
            name="HolidayCardPipelineAgent",
            sub_agents=[copy_loop, art_director],
        )

        self.adk_app = App(
            name=APP_NAME,
            root_agent=self.root_agent,
            plugins=[self.guardrail_plugin],
            events_compaction_config=EventsCompactionConfig(
                compaction_interval=4,
                overlap_size=1,
            ),
            resumability_config=ResumabilityConfig(is_resumable=True),
        )

        self.runner = Runner(
            app=self.adk_app,
            session_service=self.session_service,
            memory_service=self.memory_service,
            auto_create_session=True,
        )

    def _schedule_async_memory_consolidation(self, session_id: str) -> None:
        """Run memory consolidation asynchronously without blocking the HTTP response."""

        async def _consolidate() -> None:
            try:
                session = await self.session_service.get_session(
                    app_name=APP_NAME,
                    user_id=DEFAULT_USER_ID,
                    session_id=session_id,
                )
                if session is not None:
                    # Scrub PII from state before consolidating into long-term memory
                    session.state = self._redactor.redact_dict(dict(session.state))
                    await self.memory_service.add_session_to_memory(session)
                    self._logger.info("async_memory_consolidated", session_id=session_id)
            except Exception as exc:
                self._logger.warning(
                    "async_memory_consolidation_failed",
                    session_id=session_id,
                    error=str(exc),
                )

        task = asyncio.create_task(_consolidate())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def generate_card(
        self, req: CardRequestInput, session_id: str, trace_id: str | None = None
    ) -> CardGenerationResponse:
        """Run the full multi-agent pipeline for a new holiday card."""
        theme_cfg = load_theme_config(self._settings)

        session = await self.session_service.get_session(
            app_name=APP_NAME,
            user_id=DEFAULT_USER_ID,
            session_id=session_id,
        )
        initial_state = {
            "first_name": req.first_name,
            "highlight_2026": req.highlight_2026,
            "wish_2027": req.wish_2027,
            "vibe": req.vibe.value,
            "style": req.style.value,
            "require_copy_confirmation": (
                req.require_confirmation or self._settings.require_copy_confirmation
            ),
        }
        if session is None:
            await self.session_service.create_session(
                app_name=APP_NAME,
                user_id=DEFAULT_USER_ID,
                session_id=session_id,
                state=initial_state,
            )

        prompt = (
            f"Create a holiday card for {req.first_name}.\n"
            f"- 2026 Highlight: {req.highlight_2026}\n"
            f"- 2027 Wish: {req.wish_2027}\n"
            f"- Festive Vibe: {req.vibe.value}\n"
            f"- Card Style: {req.style.value}\n"
        )
        user_msg = types.Content(role="user", parts=[types.Part(text=prompt)])

        return await self._execute_runner(
            session_id=session_id,
            new_message=user_msg,
            req_style=req.style,
            event_title=theme_cfg.event_title,
            event_footer=theme_cfg.event_footer,
            trace_id=trace_id,
        )

    async def remix_card(
        self, req: RemixRequestInput, trace_id: str | None = None
    ) -> CardGenerationResponse:
        """Run a multi-turn remix inside an existing persistent session."""
        theme_cfg = load_theme_config(self._settings)
        session = await self.session_service.get_session(
            app_name=APP_NAME,
            user_id=DEFAULT_USER_ID,
            session_id=req.session_id,
        )
        style_value = (
            req.style.value
            if req.style
            else (session.state.get("style", "cozy_gourmet") if session else "cozy_gourmet")
        )
        prompt = (
            f"Remix the current holiday card in this session.\n"
            f"- Guest instruction: {req.instruction}\n"
            f"- Card Style: {style_value}\n"
        )
        user_msg = types.Content(role="user", parts=[types.Part(text=prompt)])

        from app.agents.schemas import CardStyle

        return await self._execute_runner(
            session_id=req.session_id,
            new_message=user_msg,
            req_style=CardStyle(style_value),
            event_title=theme_cfg.event_title,
            event_footer=theme_cfg.event_footer,
            trace_id=trace_id,
        )

    async def confirm_card(
        self, req: ConfirmCardInput, trace_id: str | None = None
    ) -> CardGenerationResponse:
        """Resume a paused HITL invocation after guest confirmation."""
        theme_cfg = load_theme_config(self._settings)
        session = await self.session_service.get_session(
            app_name=APP_NAME,
            user_id=DEFAULT_USER_ID,
            session_id=req.session_id,
        )
        from app.agents.schemas import CardStyle

        style_val = session.state.get("style", "cozy_gourmet") if session else "cozy_gourmet"
        confirmation_payload = types.FunctionResponse(
            name="adk_request_confirmation",
            response={
                "confirmed": req.confirmed,
                "edited_greeting": req.edited_greeting,
            },
        )
        msg = types.Content(
            role="user",
            parts=[types.Part(function_response=confirmation_payload)],
        )
        return await self._execute_runner(
            session_id=req.session_id,
            new_message=msg,
            req_style=CardStyle(style_val),
            event_title=theme_cfg.event_title,
            event_footer=theme_cfg.event_footer,
            trace_id=trace_id,
            invocation_id=req.invocation_id,
        )

    async def _execute_runner(
        self,
        *,
        session_id: str,
        new_message: types.Content,
        req_style: Any,
        event_title: str,
        event_footer: str,
        trace_id: str | None,
        invocation_id: str | None = None,
    ) -> CardGenerationResponse:
        awaiting_invocation_id: str | None = None
        confirmation_reason: str | None = None

        run_kwargs: dict[str, Any] = {
            "user_id": DEFAULT_USER_ID,
            "session_id": session_id,
            "new_message": new_message,
        }
        if invocation_id:
            run_kwargs["invocation_id"] = invocation_id

        async for event in self.runner.run_async(**run_kwargs):
            for call in event.get_function_calls() if hasattr(event, "get_function_calls") else []:
                if call.name == "adk_request_confirmation":
                    awaiting_invocation_id = event.invocation_id
                    confirmation_reason = (call.args or {}).get(
                        "hint", "Please confirm your card copy."
                    )

        session = await self.session_service.get_session(
            app_name=APP_NAME,
            user_id=DEFAULT_USER_ID,
            session_id=session_id,
        )
        state = dict(session.state) if session else {}

        raw_copy = state.get("card_copy")
        card_copy: CardCopyOutput | None = None
        if isinstance(raw_copy, dict):
            card_copy = CardCopyOutput.model_validate(raw_copy)
        elif isinstance(raw_copy, str):
            card_copy = CardCopyOutput.model_validate(json.loads(raw_copy))

        if awaiting_invocation_id:
            return CardGenerationResponse(
                session_id=session_id,
                status="awaiting_confirmation",
                invocation_id=awaiting_invocation_id,
                card_copy=card_copy,
                event_title=event_title,
                event_footer=event_footer,
                trace_id=trace_id,
                confirmation_reason=confirmation_reason,
            )

        bg_b64 = state.get("background_image_base64")
        bg_mime = state.get("background_mime_type", "image/svg+xml")
        used_fallback = bool(state.get("used_fallback_image", False))
        if not bg_b64:
            bg_b64 = _build_fallback_svg_base64(req_style)
            bg_mime = "image/svg+xml"
            used_fallback = True

        self._schedule_async_memory_consolidation(session_id)

        return CardGenerationResponse(
            session_id=session_id,
            status="completed",
            card_copy=card_copy,
            background_image_base64=bg_b64,
            background_mime_type=bg_mime,
            used_fallback_image=used_fallback,
            event_title=event_title,
            event_footer=event_footer,
            trace_id=trace_id,
        )


def build_default_pipeline() -> HolidayCardPipeline:
    """Factory used by FastAPI startup and CLI tools."""
    from app.observability.logging import configure_logging

    settings = get_settings()
    apply_vertex_env(settings)
    redactor = configure_logging(
        log_level=settings.log_level,
        project_id=settings.google_cloud_project,
        enable_cloud_dlp=settings.enable_cloud_dlp,
    )
    return HolidayCardPipeline(settings=settings, redactor=redactor)
