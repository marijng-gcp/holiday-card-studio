"""ADK Plugin for deterministic guardrails and Intent vs. Outcome structured logging."""

from __future__ import annotations

import re
import time
from typing import Any

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from app.observability.logging import get_logger
from app.observability.pii_redactor import PIIRedactor

_INJECTION_RE = re.compile(
    r"(?:ignore\s+previous\s+instructions|system\s+prompt|reveal\s+secrets|<script)",
    re.IGNORECASE,
)


class HolidayPolicyGuardrailPlugin(BasePlugin):
    """Enforces input safety guardrails and logs Intent vs. Outcome per step."""

    def __init__(self, redactor: PIIRedactor) -> None:
        super().__init__(name="holiday_policy_guardrail")
        self._redactor = redactor
        self._logger = get_logger("agent.plugin")
        self._tool_start_times: dict[str, float] = {}
        self._agent_start_times: dict[str, float] = {}

    async def before_agent_callback(
        self, *, agent: Any, callback_context: CallbackContext
    ) -> types.Content | None:
        """Log agent intent before execution."""
        key = f"{callback_context.invocation_id}:{agent.name}"
        self._agent_start_times[key] = time.perf_counter()
        self._logger.info(
            "agent_intent",
            agent_name=agent.name,
            invocation_id=callback_context.invocation_id,
            session_id=callback_context.session.id,
        )
        return None

    async def after_agent_callback(
        self, *, agent: Any, callback_context: CallbackContext
    ) -> types.Content | None:
        """Log agent outcome and duration after execution."""
        key = f"{callback_context.invocation_id}:{agent.name}"
        started = self._agent_start_times.pop(key, None)
        duration_ms = round((time.perf_counter() - started) * 1000, 2) if started else 0.0
        self._logger.info(
            "agent_outcome",
            agent_name=agent.name,
            invocation_id=callback_context.invocation_id,
            session_id=callback_context.session.id,
            duration_ms=duration_ms,
        )
        return None

    async def before_model_callback(
        self, *, callback_context: CallbackContext, llm_request: LlmRequest
    ) -> LlmResponse | None:
        """Block prompt-injection patterns and log model intent."""
        user_text = ""
        for content in llm_request.contents or []:
            for part in content.parts or []:
                if getattr(part, "text", None):
                    user_text += " " + part.text

        if _INJECTION_RE.search(user_text):
            self._logger.warning(
                "guardrail_blocked_prompt_injection",
                invocation_id=callback_context.invocation_id,
                session_id=callback_context.session.id,
            )
            return LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            text=(
                                '{"approved": false, "feedback": "Blocked by safety '
                                'guardrail.", "needs_human_review": true, '
                                '"flagged_reason": "Suspicious instruction pattern"}'
                            )
                        )
                    ],
                )
            )

        self._logger.info(
            "model_intent",
            model=str(llm_request.model or "default"),
            invocation_id=callback_context.invocation_id,
            session_id=callback_context.session.id,
        )
        return None

    async def before_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
    ) -> dict[str, Any] | None:
        """Log PII-redacted tool intent before execution."""
        key = f"{tool_context.invocation_id}:{tool.name}"
        self._tool_start_times[key] = time.perf_counter()
        self._logger.info(
            "tool_intent",
            tool_name=tool.name,
            tool_args=self._redactor.redact_dict(tool_args),
            invocation_id=tool_context.invocation_id,
            session_id=tool_context.session.id,
        )
        return None

    async def after_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
        result: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Log tool outcome and duration after execution."""
        key = f"{tool_context.invocation_id}:{tool.name}"
        started = self._tool_start_times.pop(key, None)
        duration_ms = round((time.perf_counter() - started) * 1000, 2) if started else 0.0
        self._logger.info(
            "tool_outcome",
            tool_name=tool.name,
            outcome_status=result.get("status", "unknown") if isinstance(result, dict) else "ok",
            used_fallback=result.get("used_fallback", False)
            if isinstance(result, dict)
            else False,
            duration_ms=duration_ms,
            invocation_id=tool_context.invocation_id,
            session_id=tool_context.session.id,
        )
        return None
