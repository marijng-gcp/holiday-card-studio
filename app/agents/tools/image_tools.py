"""Festive background image generation tool with HITL confirmation and guided recovery."""

from __future__ import annotations

import base64
from typing import Any

from google.adk.tools.tool_context import ToolContext
from pydantic import ValidationError

from app.agents.schemas import (
    BackgroundImageInput,
    BackgroundImageOutput,
    CardStyle,
    ToolErrorResult,
)
from app.config import get_settings

_FALLBACK_SVGS: dict[CardStyle, tuple[str, str, str]] = {
    CardStyle.COZY_GOURMET: ("#3B0A18", "#9B1B30", "#F6C453"),
    CardStyle.DIY_WORKSHOP: ("#143326", "#2E5E4E", "#E8B86D"),
    CardStyle.WINTER_ESCAPE: ("#0F2038", "#2B4C7E", "#AEE1F9"),
}


def _build_fallback_svg_base64(style: CardStyle) -> str:
    c1, c2, accent = _FALLBACK_SVGS[style]
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 1440">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{c1}"/>
      <stop offset="100%" stop-color="{c2}"/>
    </linearGradient>
    <radialGradient id="glow" cx="50%" cy="28%" r="45%">
      <stop offset="0%" stop-color="{accent}" stop-opacity="0.35"/>
      <stop offset="100%" stop-color="{accent}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="1080" height="1440" fill="url(#bg)"/>
  <rect width="1080" height="1440" fill="url(#glow)"/>
  <circle cx="180" cy="180" r="6" fill="{accent}" opacity="0.7"/>
  <circle cx="890" cy="240" r="8" fill="{accent}" opacity="0.6"/>
  <circle cx="240" cy="1120" r="5" fill="{accent}" opacity="0.5"/>
  <circle cx="860" cy="1080" r="7" fill="{accent}" opacity="0.65"/>
</svg>"""
    return base64.b64encode(svg.encode("utf-8")).decode("ascii")


def _invoke_vertex_image_model(
    scene_prompt: str, project_id: str, location: str, model: str
) -> tuple[str, str]:
    from google import genai
    from google.genai import types

    client = genai.Client(vertexai=True, project=project_id, location=location)
    if model.startswith("imagen"):
        result = client.models.generate_images(
            model=model,
            prompt=scene_prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="3:4",
                safety_filter_level="BLOCK_LOW_AND_ABOVE",
            ),
        )
        image_bytes = result.generated_images[0].image.image_bytes
        return base64.b64encode(image_bytes).decode("ascii"), "image/png"

    response = client.models.generate_content(
        model=model,
        contents=scene_prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio="3:4"),
        ),
    )
    for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.data:
            mime = part.inline_data.mime_type or "image/png"
            return base64.b64encode(part.inline_data.data).decode("ascii"), mime
    raise RuntimeError("No image bytes returned by Gemini image model.")


def generate_festive_background_image(
    tool_context: ToolContext,
    style: str,
    scene_prompt: str,
    use_bundled_fallback: bool = False,
) -> dict[str, Any]:
    """Generate a text-free 3:4 festive background image for a holiday card.

    This tool supports a Human-in-the-Loop (HITL) confirmation gate when
    `require_copy_confirmation` or `needs_human_review` is set in session state.
    If Vertex AI image generation fails or is blocked, it returns a guided
    ToolErrorResult instructing the ArtDirectorAgent how to recover.

    Args:
        tool_context: ADK tool execution context for HITL confirmation and state.
        style: Card style ID ('cozy_gourmet', 'diy_workshop', or 'winter_escape').
        scene_prompt: Detailed, text-free festive scene description (10-500 chars).
        use_bundled_fallback: Set True only if image generation failed and a
            pre-bundled gradient SVG fallback should be returned instead.

    Returns:
        Dictionary matching BackgroundImageOutput on success, or ToolErrorResult
        with explicit recovery instructions on failure.
    """
    try:
        validated = BackgroundImageInput(
            style=CardStyle(style),
            scene_prompt=scene_prompt,
            use_bundled_fallback=use_bundled_fallback,
        )
    except (ValidationError, ValueError) as exc:
        return ToolErrorResult(
            error_code="INVALID_IMAGE_ARGS",
            reason=str(exc),
            recovery_instruction=(
                "Provide a valid CardStyle and a scene_prompt between 10 and 500 "
                "characters describing a text-free festive scene."
            ),
        ).model_dump()

    needs_hitl = bool(
        tool_context.state.get("require_copy_confirmation")
        or tool_context.state.get("needs_human_review")
    )
    if needs_hitl and not tool_context.tool_confirmation:
        tool_context.request_confirmation(
            hint="Confirm card copy before rendering the festive background image.",
            payload={
                "style": validated.style.value,
                "needs_human_review": bool(tool_context.state.get("needs_human_review")),
                "flagged_reason": tool_context.state.get("flagged_reason", ""),
            },
        )
        return {
            "status": "awaiting_confirmation",
            "message": "Waiting for guest confirmation before rendering background.",
        }

    if tool_context.tool_confirmation and not tool_context.tool_confirmation.confirmed:
        return ToolErrorResult(
            error_code="USER_DECLINED_RENDER",
            reason="Guest declined image rendering during confirmation.",
            recovery_instruction=(
                "Call generate_festive_background_image with use_bundled_fallback=True "
                "or ask the guest for updated copy."
            ),
        ).model_dump()

    if validated.use_bundled_fallback:
        svg_b64 = _build_fallback_svg_base64(validated.style)
        out = BackgroundImageOutput(
            status="fallback",
            mime_type="image/svg+xml",
            image_base64="",
            used_fallback=True,
            note="Pre-bundled festive SVG fallback stored in session state.",
        )
        tool_context.state["background_image_base64"] = svg_b64
        tool_context.state["background_mime_type"] = out.mime_type
        tool_context.state["used_fallback_image"] = True
        return out.model_dump(exclude={"image_base64"})

    settings = get_settings()
    if not settings.google_cloud_project:
        return ToolErrorResult(
            error_code="MISSING_GCP_PROJECT",
            reason="GOOGLE_CLOUD_PROJECT is not configured for Vertex AI image generation.",
            recovery_instruction=(
                "Retry generate_festive_background_image with use_bundled_fallback=True."
            ),
        ).model_dump()

    try:
        img_b64, img_mime = _invoke_vertex_image_model(
            scene_prompt=validated.scene_prompt,
            project_id=settings.google_cloud_project,
            location=settings.google_cloud_location,
            model=settings.image_model,
        )
        out = BackgroundImageOutput(
            status="ok",
            mime_type=img_mime,
            image_base64="",
            used_fallback=False,
            note="Festive background image generated and stored in session state.",
        )
        tool_context.state["background_image_base64"] = img_b64
        tool_context.state["background_mime_type"] = out.mime_type
        tool_context.state["used_fallback_image"] = False
        return out.model_dump(exclude={"image_base64"})
    except Exception as exc:
        return ToolErrorResult(
            error_code="IMAGE_GENERATION_FAILED",
            reason=f"Vertex AI image call failed: {exc}",
            recovery_instruction=(
                "Simplify scene_prompt to remove any brand/person references and "
                "retry once, OR call generate_festive_background_image with "
                "use_bundled_fallback=True."
            ),
        ).model_dump()
