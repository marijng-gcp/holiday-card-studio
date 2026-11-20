"""FastAPI endpoint tests with mocked ADK pipeline."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app import main as app_main
from app.agents.schemas import CardCopyOutput, CardGenerationResponse
from app.config import get_settings


def test_health_and_public_config(monkeypatch, tmp_path) -> None:
    """Verify /api/health and /api/config return generic deploy-time branding."""
    monkeypatch.setenv("SESSION_DB_URL", f"sqlite+aiosqlite:///{tmp_path}/sessions.db")
    get_settings.cache_clear()
    with TestClient(app_main.app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok"}

        cfg = client.get("/api/config")
        assert cfg.status_code == 200
        data = cfg.json()
        assert len(data["styles"]) == 3
        assert "event_footer" in data


def test_generate_card_endpoint_with_mocked_pipeline(monkeypatch, tmp_path) -> None:
    """Verify /api/generate-card validates input and returns CardGenerationResponse."""
    monkeypatch.setenv("SESSION_DB_URL", f"sqlite+aiosqlite:///{tmp_path}/sessions.db")
    get_settings.cache_clear()

    class _FakePipeline:
        async def generate_card(self, req, session_id, trace_id=None):
            return CardGenerationResponse(
                session_id=session_id,
                status="completed",
                card_copy=CardCopyOutput(
                    holiday_title="Chief Cocoa Architect",
                    superpower_2027="Inbox Zero +99",
                    greeting_text=(
                        "Congrats on launching your AI helper in 2026! "
                        "Wishing you restful nights and a joyful 2027."
                    ),
                ),
                background_image_base64="PHN2Zz48L3N2Zz4=",
                background_mime_type="image/svg+xml",
                used_fallback_image=True,
                event_title="Holiday Card Studio 2026",
                event_footer="Season's Greetings & Happy 2027!",
                trace_id=trace_id,
            )

    with TestClient(app_main.app) as client:
        monkeypatch.setattr(app_main, "_PIPELINE", _FakePipeline())
        res = client.post(
            "/api/generate-card",
            json={
                "first_name": "Alex",
                "highlight_2026": "Launched our new AI helper",
                "wish_2027": "More sleep",
                "vibe": "Cozy",
                "style": "cozy_gourmet",
            },
        )
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "completed"
        assert body["card_copy"]["holiday_title"] == "Chief Cocoa Architect"
