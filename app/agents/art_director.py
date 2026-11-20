"""ArtDirectorAgent using Pro model routing for visual planning and image generation."""

from __future__ import annotations

from google.adk.agents import LlmAgent

from app.agents.prompts import ART_DIRECTOR_CONSTITUTION
from app.agents.tools.image_tools import generate_festive_background_image
from app.agents.tools.memory_tools import record_anonymized_vibe_metric
from app.agents.tools.theme_tools import load_event_theme_config


def build_art_director_agent(pro_model: str) -> LlmAgent:
    """Build the ArtDirectorAgent routed to the Pro reasoning model.

    Args:
        pro_model: Model ID for nuanced visual prompt planning and error recovery.

    Returns:
        Configured ADK LlmAgent.
    """
    return LlmAgent(
        name="ArtDirectorAgent",
        model=pro_model,
        description=(
            "Crafts text-free festive scene prompts, invokes image generation "
            "with HITL support, and records anonymized vibe metrics."
        ),
        instruction=ART_DIRECTOR_CONSTITUTION,
        tools=[
            load_event_theme_config,
            generate_festive_background_image,
            record_anonymized_vibe_metric,
        ],
    )
