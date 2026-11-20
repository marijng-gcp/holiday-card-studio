"""Application configuration, Secret Manager resolution, and theme loading."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class StyleTheme(BaseModel):
    """Configuration for a single holiday card visual style."""

    id: str
    label: str
    visual_cue: str
    copy_cue: str


class EventThemeConfig(BaseModel):
    """Deploy-time configurable event branding (generic defaults for public repo)."""

    event_title: str = "Holiday Card Studio 2026"
    event_footer: str = "Season's Greetings & Happy 2027!"
    styles: dict[str, StyleTheme] = Field(
        default_factory=lambda: {
            "cozy_gourmet": StyleTheme(
                id="cozy_gourmet",
                label="Cozy Gourmet",
                visual_cue=(
                    "warm candlelit winter market table, festive pastries, "
                    "mulled spice mugs, golden fairy lights"
                ),
                copy_cue="warm foodie and festive market hospitality",
            ),
            "diy_workshop": StyleTheme(
                id="diy_workshop",
                label="DIY Workshop",
                visual_cue=(
                    "cozy holiday woodshop, twinkling string lights, handmade wooden "
                    "ornaments, pine garlands, crafting bench"
                ),
                copy_cue="creative maker spirit and hands-on holiday crafting",
            ),
            "winter_escape": StyleTheme(
                id="winter_escape",
                label="Winter Escape",
                visual_cue=(
                    "snowy alpine lodge window, northern lights, pine forest, "
                    "steaming hot cocoa, cozy blanket"
                ),
                copy_cue="adventure, travel dreams, and snowy relaxation",
            ),
        }
    )


class Settings(BaseSettings):
    """Environment-driven application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    google_cloud_project: str = ""
    google_cloud_location: str = "global"
    google_genai_use_vertexai: bool = True

    fast_model: str = "gemini-3.8-flash"
    pro_model: str = "gemini-3.8-flash"
    image_model: str = "gemini-3.1-flash-image"

    session_db_url: str = "sqlite+aiosqlite:///./data/sessions.db"
    theme_config_path: str = "theme_config.json"

    enable_cloud_trace: bool = False
    enable_cloud_dlp: bool = False
    enable_secret_manager: bool = False
    log_level: str = "INFO"

    event_title: str = "Holiday Card Studio 2026"
    event_footer: str = "Season's Greetings & Happy 2027!"
    require_copy_confirmation: bool = False
    rate_limit_per_minute: int = 15


def resolve_secret(
    secret_id: str,
    project_id: str,
    enable_secret_manager: bool,
    fallback_value: str = "",
) -> str:
    """Resolve a secret from Google Cloud Secret Manager with local env fallback.

    Args:
        secret_id: Secret Manager secret name.
        project_id: GCP project ID hosting the secret.
        enable_secret_manager: Whether Secret Manager lookup is enabled.
        fallback_value: Value returned when Secret Manager is disabled or unavailable.

    Returns:
        The resolved secret string.
    """
    if not enable_secret_manager or not project_id:
        return fallback_value

    try:
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("utf-8").strip()
    except Exception:
        return fallback_value


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()


def apply_vertex_env(settings: Settings | None = None) -> None:
    """Ensure google-adk and google-genai see Vertex AI settings in os.environ."""
    cfg = settings or get_settings()
    if cfg.google_genai_use_vertexai:
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
    if cfg.google_cloud_project:
        os.environ["GOOGLE_CLOUD_PROJECT"] = cfg.google_cloud_project
    if cfg.google_cloud_location:
        os.environ["GOOGLE_CLOUD_LOCATION"] = cfg.google_cloud_location


def load_theme_config(settings: Settings | None = None) -> EventThemeConfig:
    """Load deploy-time event branding from Secret Manager, file, or defaults.

    Args:
        settings: Optional Settings instance.

    Returns:
        EventThemeConfig with generic defaults or deploy-time overrides.
    """
    cfg = settings or get_settings()
    base = EventThemeConfig(
        event_title=cfg.event_title,
        event_footer=cfg.event_footer,
    )

    secret_json = resolve_secret(
        secret_id="holiday-card-theme-config",
        project_id=cfg.google_cloud_project,
        enable_secret_manager=cfg.enable_secret_manager,
    )
    if secret_json:
        try:
            raw: dict[str, Any] = json.loads(secret_json)
            return EventThemeConfig.model_validate(raw)
        except Exception:
            pass

    theme_path = Path(cfg.theme_config_path)
    if theme_path.exists():
        raw = json.loads(theme_path.read_text(encoding="utf-8"))
        return EventThemeConfig.model_validate(raw)

    return base
