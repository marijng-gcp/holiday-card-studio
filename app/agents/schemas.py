"""Strict Pydantic v2 schemas for agent inputs, outputs, and tool contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class CardStyle(StrEnum):
    """Supported visual card themes."""

    COZY_GOURMET = "cozy_gourmet"
    DIY_WORKSHOP = "diy_workshop"
    WINTER_ESCAPE = "winter_escape"


class FestiveVibe(StrEnum):
    """Supported festive tone pills."""

    COZY = "Cozy"
    PARTY_MODE = "Party Mode"
    ADVENTUROUS = "Adventurous"
    TECH_COFFEE = "Tech & Coffee"


class CardRequestInput(BaseModel):
    """Validated user request for generating a personalized holiday card."""

    first_name: str = Field(
        ...,
        min_length=1,
        max_length=40,
        description="Guest first name or nickname shown on the card.",
    )
    highlight_2026: str = Field(
        ...,
        min_length=2,
        max_length=140,
        description="Guest highlight or proud moment from 2026.",
    )
    wish_2027: str = Field(
        ...,
        min_length=2,
        max_length=140,
        description="Guest wish or playful goal for 2027.",
    )
    vibe: FestiveVibe = Field(
        default=FestiveVibe.COZY,
        description="1-tap festive tone selector.",
    )
    style: CardStyle = Field(
        default=CardStyle.COZY_GOURMET,
        description="Selected visual card style.",
    )
    session_id: str | None = Field(
        default=None,
        max_length=64,
        description="Optional anonymous browser session ID for multi-turn remixes.",
    )
    require_confirmation: bool = Field(
        default=False,
        description="When true, pauses for human confirmation before image generation.",
    )

    @field_validator("first_name", "highlight_2026", "wish_2027")
    @classmethod
    def strip_and_reject_empty(cls, value: str) -> str:
        """Trim surrounding whitespace and reject blank values."""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field must not be blank.")
        return cleaned


class RemixRequestInput(BaseModel):
    """Validated follow-up request to remix an existing card in the same session."""

    session_id: str = Field(..., min_length=1, max_length=64)
    instruction: str = Field(
        ...,
        min_length=2,
        max_length=160,
        description="Follow-up tweak instruction (e.g., 'Make it funnier').",
    )
    style: CardStyle | None = Field(
        default=None,
        description="Optional updated card style.",
    )


class ConfirmCardInput(BaseModel):
    """Human-in-the-loop confirmation payload to resume paused image generation."""

    session_id: str = Field(..., min_length=1, max_length=64)
    invocation_id: str = Field(..., min_length=1, max_length=128)
    confirmed: bool = Field(default=True)
    edited_greeting: str | None = Field(default=None, max_length=280)


class CardCopyOutput(BaseModel):
    """Structured copywriting output produced by CopywriterAgent."""

    holiday_title: str = Field(
        ...,
        min_length=3,
        max_length=45,
        description="Playful 2 to 4 word holiday title (e.g., 'Chief Cocoa Architect').",
    )
    superpower_2027: str = Field(
        ...,
        min_length=4,
        max_length=60,
        description="Short trading-card stat under 8 words (e.g., 'Inbox Zero +99').",
    )
    greeting_text: str = Field(
        ...,
        min_length=15,
        max_length=280,
        description="Warm, witty 2-sentence English holiday greeting.",
    )


class SafetyCritiqueOutput(BaseModel):
    """Structured evaluation produced by ToneSafetyCriticAgent."""

    approved: bool = Field(..., description="True if copy passes all tone and safety checks.")
    feedback: str = Field(
        ...,
        min_length=3,
        max_length=300,
        description="Specific, constructive feedback for rewrite or approval note.",
    )
    needs_human_review: bool = Field(
        default=False,
        description="True if guest input is borderline and needs HITL confirmation.",
    )
    flagged_reason: str = Field(
        default="",
        max_length=200,
        description="Short explanation when needs_human_review is True.",
    )


class BackgroundImageInput(BaseModel):
    """Validated input schema for the festive background image tool."""

    style: CardStyle = Field(..., description="Card visual theme ID.")
    scene_prompt: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Text-free festive illustration prompt.",
    )
    use_bundled_fallback: bool = Field(
        default=False,
        description="Set True to return the pre-bundled SVG fallback background.",
    )


class BackgroundImageOutput(BaseModel):
    """Validated output schema returned by the festive background image tool."""

    status: Literal["ok", "fallback"]
    mime_type: str
    image_base64: str
    used_fallback: bool
    note: str = ""


class ToolErrorResult(BaseModel):
    """Guided error payload returned to the LLM with explicit recovery steps."""

    status: Literal["error"] = "error"
    error_code: str
    reason: str
    recovery_instruction: str


class CardGenerationResponse(BaseModel):
    """HTTP response returned to the mobile frontend."""

    session_id: str
    status: Literal["completed", "awaiting_confirmation"]
    invocation_id: str | None = None
    card_copy: CardCopyOutput | None = None
    background_image_base64: str | None = None
    background_mime_type: str = "image/svg+xml"
    used_fallback_image: bool = False
    event_title: str
    event_footer: str
    trace_id: str | None = None
    confirmation_reason: str | None = None
