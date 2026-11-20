# Holiday Card Studio

Mobile-first, multi-agent AI holiday greeting card application built with **Google Agent Development Kit (ADK)**, **FastAPI**, **Vertex AI**, and **HTML5 Canvas**.

## Architecture Highlights

1. **Multi-Agent ADK Orchestration (`SequentialAgent` + `LoopAgent`)**
   - `CopywriterAgent` (`FAST_MODEL`) drafts a `holiday_title`, `superpower_2027`, and 2-sentence `greeting_text`.
   - `ToneSafetyCriticAgent` (`FAST_MODEL`) reviews for inclusivity, PG tone, and safety, approving via `approve_card_copy` or requesting a rewrite.
   - `ArtDirectorAgent` (`PRO_MODEL`) crafts a text-free illustration prompt and calls `generate_festive_background_image` with guided error recovery and pre-bundled SVG fallback.
2. **Privacy-First Client-Side Compositing**
   - Guest selfies never leave the browser. HTML5 Canvas composites the AI background, framed selfie/emoji, and typography into a downloadable `1080x1440` PNG.
3. **Context, Memory & Guardrails**
   - Persistent `DatabaseSessionService` + `EventsCompactionConfig` for multi-turn card remixes.
   - Non-blocking `asyncio.create_task` memory consolidation with PII scrubbing (`PIIRedactor`).
   - `HolidayPolicyGuardrailPlugin` for prompt-injection checks, Intent vs. Outcome structured JSON logging (`structlog`), and OpenTelemetry tracing.
   - Explicit Human-in-the-Loop (`ToolContext.request_confirmation`) gate before background rendering when enabled or flagged.

## Quickstart (Local / Cloud Shell)

1. Install dependencies with `uv`:
   ```bash
   uv sync --extra dev
   ```
2. Copy `.env.example` to `.env` and set your GCP project (`GOOGLE_CLOUD_PROJECT=l200dy5-sandbox-68969`).
   - Note: Override `FAST_MODEL` / `PRO_MODEL` in `.env` if your project uses a different Gemini model version.
3. Enable required APIs in your GCP project:
   ```bash
   gcloud services enable \
     aiplatform.googleapis.com \
     run.googleapis.com \
     cloudbuild.googleapis.com \
     artifactregistry.googleapis.com \
     secretmanager.googleapis.com \
     dlp.googleapis.com \
     cloudtrace.googleapis.com \
     --project=l200dy5-sandbox-68969
   ```
4. Run locally (or in Cloud Shell on port 8080 for Web Preview):
   ```bash
   uv run uvicorn app.main:app --host 0.0.0.0 --port 8080
   ```
5. Run tests & linter:
   ```bash
   uv run ruff check app tests
   uv run pytest
   ```
6. Run ADK golden dataset evaluation (requires Vertex AI credentials in Cloud Shell):
   ```bash
   uv run adk eval app/agents tests/evals/golden_cards.evalset.json --config_file_path=tests/evals/eval_config.json
   ```

## Deploy-Time Branding Customization

The public repository uses generic seasonal defaults. To inject event-specific branding at deploy time without committing it to Git:
1. Create a gitignored `theme_config.json` locally, or
2. Store the JSON payload in Google Cloud Secret Manager under `holiday-card-theme-config` and set `ENABLE_SECRET_MANAGER=true`.
