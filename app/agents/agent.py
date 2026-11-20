"""ADK CLI and AgentEvaluator entrypoint exposing `root_agent` and `app`."""

from __future__ import annotations

from app.agents.pipeline import build_default_pipeline

_pipeline = build_default_pipeline()
root_agent = _pipeline.root_agent
app = _pipeline.adk_app
