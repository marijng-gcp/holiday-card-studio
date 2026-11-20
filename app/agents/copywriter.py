"""Copywriter and ToneSafetyCritic agents with LoopAgent orchestration."""

from __future__ import annotations

from google.adk.agents import LlmAgent, LoopAgent

from app.agents.prompts import (
    COPYWRITER_CONSTITUTION,
    TONE_SAFETY_CRITIC_CONSTITUTION,
)
from app.agents.schemas import CardCopyOutput, SafetyCritiqueOutput
from app.agents.tools.memory_tools import approve_card_copy
from app.agents.tools.theme_tools import load_event_theme_config


def build_copy_loop_agent(fast_model: str) -> LoopAgent:
    """Build the Copywriter + ToneSafetyCritic LoopAgent using the fast model.

    Args:
        fast_model: Model ID for low-latency drafting and critique (e.g., Flash).

    Returns:
        Configured ADK LoopAgent (max 2 iterations).
    """
    copywriter = LlmAgent(
        name="CopywriterAgent",
        model=fast_model,
        description="Drafts personalized holiday card title, 2027 superpower, and greeting.",
        instruction=COPYWRITER_CONSTITUTION,
        tools=[load_event_theme_config],
        output_schema=CardCopyOutput,
        output_key="card_copy",
    )

    critic = LlmAgent(
        name="ToneSafetyCriticAgent",
        model=fast_model,
        description="Reviews draft copy for warmth, inclusivity, PG tone, and safety.",
        instruction=TONE_SAFETY_CRITIC_CONSTITUTION,
        tools=[approve_card_copy],
        output_schema=SafetyCritiqueOutput,
        output_key="safety_critique",
    )

    return LoopAgent(
        name="CopyLoopAgent",
        sub_agents=[copywriter, critic],
        max_iterations=2,
    )
