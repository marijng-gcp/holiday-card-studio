"""Theme configuration lookup tool."""

from __future__ import annotations

from app.agents.schemas import CardStyle, ToolErrorResult
from app.config import load_theme_config


def load_event_theme_config(style: str) -> dict[str, str]:
    """Load deploy-time event branding and visual/copy cues for a card style.

    Use this tool before drafting card copy or generating a background image so
    the output aligns with the active card style and event footer configuration.

    Args:
        style: Card style identifier. Must be one of 'cozy_gourmet',
            'diy_workshop', or 'winter_escape'.

    Returns:
        Dictionary containing event_title, event_footer, style_label,
        visual_cue, and copy_cue. On invalid style, returns a ToolErrorResult
        dict with recovery instructions.
    """
    try:
        validated_style = CardStyle(style)
    except ValueError:
        return ToolErrorResult(
            error_code="INVALID_CARD_STYLE",
            reason=f"Unsupported style '{style}'.",
            recovery_instruction=(
                "Call load_event_theme_config again with one of: "
                "'cozy_gourmet', 'diy_workshop', or 'winter_escape'."
            ),
        ).model_dump()

    config = load_theme_config()
    theme = config.styles[validated_style.value]
    return {
        "status": "ok",
        "event_title": config.event_title,
        "event_footer": config.event_footer,
        "style_id": theme.id,
        "style_label": theme.label,
        "visual_cue": theme.visual_cue,
        "copy_cue": theme.copy_cue,
    }
