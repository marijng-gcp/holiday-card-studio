"""Golden dataset validation tests (offline schema check + live ADK eval hook)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

EVAL_SET_PATH = Path(__file__).parent / "golden_cards.evalset.json"
EVAL_CONFIG_PATH = Path(__file__).parent / "eval_config.json"


def test_golden_evalset_structure() -> None:
    """Verify golden dataset and eval config are valid JSON with required ADK fields."""
    eval_set = json.loads(EVAL_SET_PATH.read_text(encoding="utf-8"))
    eval_cfg = json.loads(EVAL_CONFIG_PATH.read_text(encoding="utf-8"))

    assert eval_set["eval_set_id"] == "holiday_card_studio_golden"
    assert len(eval_set["eval_cases"]) >= 1
    assert "criteria" in eval_cfg


@pytest.mark.skipif(
    not os.getenv("RUN_LIVE_ADK_EVALS"),
    reason="Set RUN_LIVE_ADK_EVALS=1 in Cloud Shell with Vertex AI ADC to run live ADK evals.",
)
@pytest.mark.asyncio
async def test_live_adk_golden_eval() -> None:
    """Run ADK AgentEvaluator against the golden dataset when Vertex AI is available."""
    from google.adk.evaluation.agent_evaluator import AgentEvaluator

    from app.config import apply_vertex_env

    apply_vertex_env()
    await AgentEvaluator.evaluate(
        agent_module="app.agents",
        eval_dataset_file_path_or_dir=str(EVAL_SET_PATH),
    )
