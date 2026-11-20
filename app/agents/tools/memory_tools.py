"""Copy approval and anonymized vibe telemetry tools."""

from __future__ import annotations

from collections import Counter

from google.adk.tools.tool_context import ToolContext

from app.agents.schemas import CardStyle, FestiveVibe, ToolErrorResult

_VIBE_STATS: Counter[str] = Counter()


def approve_card_copy(tool_context: ToolContext, review_summary: str) -> dict[str, str]:
    """Approve the current holiday card copy and exit the critique loop.

    Call this tool ONLY when ToneSafetyCriticAgent verifies that the draft
    passes all tone, inclusivity, length, and safety checks.

    Args:
        tool_context: ADK tool execution context used to escalate and exit the loop.
        review_summary: Short 1-sentence confirmation explaining why the draft passed.

    Returns:
        Dictionary confirming loop approval status.
    """
    tool_context.state["copy_approved"] = True
    tool_context.state["review_summary"] = review_summary.strip()
    tool_context.actions.escalate = True
    return {"status": "approved", "review_summary": review_summary.strip()}


def record_anonymized_vibe_metric(style: str, vibe: str) -> dict[str, str | int]:
    """Record an anonymized counter for card style and festive vibe popularity.

    Never pass guest names, highlights, or personal text to this tool. Call it
    once per completed card to track aggregate party style trends.

    Args:
        style: Card style ID ('cozy_gourmet', 'diy_workshop', or 'winter_escape').
        vibe: Festive vibe pill ('Cozy', 'Party Mode', 'Adventurous', or 'Tech & Coffee').

    Returns:
        Dictionary with the updated anonymized count for the (style, vibe) pair,
        or a ToolErrorResult dict with recovery instructions if arguments are invalid.
    """
    try:
        valid_style = CardStyle(style).value
        valid_vibe = FestiveVibe(vibe).value
    except ValueError as exc:
        return ToolErrorResult(
            error_code="INVALID_METRIC_DIMENSION",
            reason=str(exc),
            recovery_instruction=(
                "Pass a valid CardStyle ('cozy_gourmet', 'diy_workshop', "
                "'winter_escape') and FestiveVibe ('Cozy', 'Party Mode', "
                "'Adventurous', 'Tech & Coffee')."
            ),
        ).model_dump()

    bucket = f"{valid_style}:{valid_vibe}"
    _VIBE_STATS[bucket] += 1
    return {"status": "ok", "bucket": bucket, "count": _VIBE_STATS[bucket]}


def get_anonymized_vibe_stats() -> dict[str, int]:
    """Return a copy of aggregate anonymized style/vibe counts."""
    return dict(_VIBE_STATS)
