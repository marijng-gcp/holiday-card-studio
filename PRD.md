# PRD: Holiday Card Studio (AI Christmas Greeting Card App)

**Owner:** Marijn Goemans (`marijng@google.com`)  
**Target Event Date:** December 15, 2026 (Informal Christmas Get-Together)  
**Dual Purpose:** L200 Final Project (published to GitHub, scored against the 95-point AgentOps Code Review Matrix) & Live Mobile Party Experience  
**Language:** English  

---

## 1. Executive Summary & Goals

**Holiday Card Studio** is a mobile-first, multi-agent AI web application built with Google ADK. Event guests scan a QR code, answer two quick prompts, snap a selfie (or pick an emoji), and receive a personalized, shareable Christmas "trading card" in ~15 seconds, with optional one-tap follow-up remixes (e.g., *"Make it funnier"*).

### Primary Goals
1. **Zero-Friction Party Fun:** Guests complete the entire flow on their phone in under 30 seconds with no login or app install.
2. **High Shareability:** Every guest receives a crisp, downloadable `1080x1440` PNG greeting card featuring a custom AI-generated festive scene, their framed selfie/emoji, a playful **Holiday Title**, a **2027 Superpower** stat, and a 2-sentence greeting.
3. **Privacy-First (GDPR-Safe):** Guest selfies never leave their device or get stored in any database. Photo compositing happens 100% client-side via HTML5 Canvas, and server-side logs/memory scrub PII before persistence.
4. **95/95 AgentOps & GitHub Ready:** Designed to satisfy every criterion of the L200 AgentOps Code Review Matrix while keeping the public GitHub repository completely free of customer-specific or sensitive data via deploy-time configuration.

---

## 2. Target Audience & Constraints

1. **Audience:** Mixed group of digital/tech colleagues and business stakeholders attending an informal evening Christmas get-together.
2. **Device:** Mobile browsers (iOS Safari, Android Chrome) accessed via a printed or projected QR code.
3. **Privacy & State Boundary:**
   1. **Zero Photo Persistence:** Selfies are never uploaded to the backend.
   2. **Anonymous Ephemeral Session State:** Each browser tab generates an anonymous `session_id` (no login, no PII) backed by ADK's persistent `DatabaseSessionService` so guests can iterate/remix their card across turns.
4. **Deployment Constraint:** L200 sandbox projects block public Cloud Run ingress (`--ingress=all`). Terraform IaC parameterizes `ingress` (`INGRESS_TRAFFIC_ALL` vs. `INGRESS_TRAFFIC_INTERNAL_ONLY`) so the exact same codebase deploys cleanly to both the L200 sandbox and a public-capable GCP project before December 15.

---

## 3. User Experience & Flow

### Step 1: Quick Inputs (Mobile Form)
1. **First Name** (short text input, optional/first-name only)
2. **2026 Highlight** (short text input, e.g., *"Launched our new AI assistant"* or *"Survived Q4"*)
3. **2027 Wish or Goal** (short text input, e.g., *"More sleep and a marathon"*)
4. **1-Tap Festive Vibe Pill** (select 1): `Cozy`, `Party Mode`, `Adventurous`, `Tech & Coffee`
5. **Card Style Selector** (select 1 of 3 styles; see Section 4)

### Step 2: Selfie or Emoji
1. **Take / Upload Selfie:** Opens mobile camera or photo library (`<input type="file" accept="image/*" capture="user">`).
2. **Or Pick an Emoji:** Quick tap selector (`🎅`, `🦌`, `⛄`, `🥂`, `🎄`, `🎁`).
3. **Privacy Notice:** *"Your photo stays on your device and is never uploaded or stored."*

### Step 3: Generation, Optional HITL Confirm & Card Result (~10-15s)
1. **Festive Progress State:** Shows live agent progress (e.g., *"Drafting your holiday title..."*, *"Reviewing tone..."*, *"Painting your winter scene..."*).
2. **Human-in-the-Loop (HITL) Copy Approval / Remix:**
   1. Guests can optionally preview and confirm the generated `holiday_title`, `superpower_2027`, and `greeting_text` before triggering image generation (implemented via ADK `ToolConfirmation` / `request_confirmation` on the high-cost image rendering tool), or enable "Auto-Confirm" for 1-tap party speed.
   2. If the `ToneSafetyCriticAgent` flags a borderline input, the pipeline pauses and requests explicit user confirmation/edit before proceeding.
3. **Trading-Card Output (PNG):** Rendered client-side via HTML5 Canvas (`1080x1440` portrait):
   1. **AI-Generated Scene Background** (tailored to Card Style + 2026/2027 prompts)
   2. **Framed Selfie / Emoji** (circular ornament or festive polaroid frame)
   3. **Holiday Title** (e.g., *"Chief Glühwein Architect"*)
   4. **2027 Superpower Stat** (e.g., *"2027 Superpower: Instant Inbox Zero +99"*)
   5. **Personalized 2-Sentence Greeting**
   6. **Configurable Event Footer** (injected at deploy time)
4. **Actions:**
   1. **Share / Save Card** (Mobile Web Share API or direct PNG download)
   2. **Remix Card** (multi-turn follow-up in the same ADK session, e.g., *"Make it funnier"* or *"Switch to Party Mode"*)
   3. **Create Another** (starts a fresh session)

---

## 4. Card Styles & Configurable Branding

| Style ID | Guest-Facing Label | Visual & Prompt Theme | Deploy-Time Customization (Gitignored Config) |
| :--- | :--- | :--- | :--- |
| `cozy_gourmet` | **Cozy Gourmet** | Warm candlelit Christmas market table, festive treats, mulled wine, rich seasonal ingredients | Optional festive market/food theme cues injected via deploy config |
| `diy_workshop` | **DIY Workshop** | Cozy holiday woodshop, twinkling fairy lights, handmade ornaments, crafting tools | Optional workshop/crafting theme cues injected via deploy config |
| `winter_escape` | **Winter Escape** | Snowy alpine lodge, northern lights, ski/travel vibes, warm cocoa by the window | Optional winter travel theme cues injected via deploy config |

> **GitHub Data Hygiene:** The public GitHub repository uses generic seasonal descriptions by default. Event-specific co-branding (event title, footer text, optional style cues) is injected at deployment time via **Google Cloud Secret Manager** / environment variables or a gitignored `theme_config.json`.

---

## 5. AgentOps Architecture (Aligned to 95-Point Review Matrix)

### 5.1 Orchestration & Logic (Category 3)
The backend exposes FastAPI endpoints (`/api/generate-card`, `/api/confirm-card`, `/api/remix-card`) backed by a Google ADK multi-agent workflow:

1. **Multi-Agent Pattern (`SequentialAgent` + `LoopAgent`):**
   1. **`CopyLoopAgent` (`LoopAgent`, `max_iterations=2`):**
      1. **`CopywriterAgent` (`LlmAgent`):** Generates structured `CardCopyOutput` (`holiday_title`, `superpower_2027`, `greeting_text`).
      2. **`ToneSafetyCriticAgent` (`LlmAgent`):** Evaluates the draft for inclusivity, PG-rating, jargon balance, and prompt-injection safety. Calls `approve_card_copy` (exiting the loop) or returns `SafetyCritiqueOutput` with actionable rewrite feedback.
   2. **`ArtDirectorAgent` (`LlmAgent` + Tools):** Translates the approved copy, style, and guest inputs into a **text-free** illustration prompt and invokes `generate_festive_background_image`.
2. **Strategic Model Routing:**
   1. **`gemini-2.5-flash`:** Used for `CopywriterAgent` and `ToneSafetyCriticAgent` (low-latency drafting, critique, and session compaction).
   2. **`gemini-2.5-pro`:** Used for `ArtDirectorAgent` (nuanced visual composition planning and error-recovery reasoning).
   3. **`gemini-2.5-flash-image` / `imagen-3.0-generate-002`:** Invoked inside the image generation tool.
3. **Guardrails & Policy Plugins:**
   1. Custom ADK `BasePlugin` (`HolidayPolicyGuardrailPlugin`) implementing `before_model_callback` and `before_tool_callback` to enforce input length bounds, block prompt-injection patterns, validate Pydantic schemas, and run deterministic self-eval checks.
4. **Human-in-the-Loop (HITL) Hooks:**
   1. Explicit ADK `ToolConfirmation` (`tool_context.request_confirmation(...)`) inside `generate_festive_background_image` (when `require_copy_confirmation=True` or when `ToneSafetyCriticAgent` flags a borderline input), pausing execution until the guest confirms or edits the copy via `/api/confirm-card`.

### 5.2 Tool & Interface Design (Category 1)
All agent tools live in `app/agents/tools/` and follow strict interface contracts:

1. **Descriptive Naming:**
   1. `load_event_theme_config` (loads deploy-time style cues and footer metadata)
   2. `approve_card_copy` (signals loop exit when `ToneSafetyCriticAgent` passes a draft)
   3. `generate_festive_background_image` (calls Vertex AI image generation with text-free constraints)
   4. `record_anonymized_vibe_metric` (updates non-PII party style/vibe counters)
2. **Comprehensive Tool Docstrings:** Every tool includes a Google-style docstring specifying purpose, when the LLM should call it, every parameter's meaning/constraints, and return structure.
3. **Explicit JSON Schemas:** All tool inputs/outputs and agent `output_schema` definitions use strict **Pydantic v2 `BaseModel`** classes with `Field` descriptions, enums (`CardStyle`, `FestiveVibe`), and length/value validators.
4. **Guided Error Handling:** Tools never crash with raw tracebacks to the model. Exceptions (timeouts, quota limits, image safety blocks) return a structured `ToolErrorResult` containing `error_code`, `reason`, and `recovery_instruction` (e.g., *"Safety filter triggered; remove brand/person references, soften scene description, and retry once, or set use_bundled_fallback=True"*).

### 5.3 Context & Memory (Category 2)
1. **Robust System Instructions:** Each agent has a dedicated "constitution" in `app/agents/prompts.py` defining persona, domain rules, style guidelines, strict PG/inclusivity constraints, and output formatting rules.
2. **Persistent Session State:** Uses ADK `DatabaseSessionService` (`sqlite+aiosqlite:///./data/sessions.db` locally; Cloud SQL / Firestore or Vertex AI Agent Engine Sessions in prod) keyed by anonymous `session_id` to persist multi-turn remix history and `state` (`current_card_copy`, `chosen_style`, `remix_count`).
3. **History Compaction:** Configures ADK `EventsCompactionConfig` (`compaction_interval=4`, `overlap_size=1` with `gemini-2.5-flash` summarizer) to prevent context bloat during multi-turn card remixes.
4. **Async Memory Operations:** After returning the card response, a non-blocking background task (`asyncio.create_task`) consolidates anonymized session insights (popular vibes, style choices, latency stats) into ADK `MemoryService` / Vertex AI Memory Bank without blocking the mobile UI.

### 5.4 Observability & Tracing (Category 4)
1. **Structured JSON Logging:** Uses `structlog` configured for JSON output (`trace_id`, `span_id`, `session_id`, `agent_name`, `model`, `latency_ms`), with zero bare `print()` calls.
2. **Intent vs. Outcome Capture:** ADK plugin callbacks (`before_tool_callback` / `after_tool_callback` and `before_agent_callback` / `after_agent_callback`) explicitly log an `agent_intent` / `tool_intent` event before execution and an `agent_outcome` / `tool_outcome` event (status, duration, fallback flag) after execution.
3. **Distributed Tracing:** Instruments FastAPI, ADK `Runner`, and outbound Vertex AI calls with **OpenTelemetry** (`opentelemetry-sdk`, `CloudTraceSpanExporter` in GCP / console or OTLP exporter locally) so every request is traceable end-to-end.
4. **PII Redaction:** A dedicated `PIIRedactor` utility scrubs emails, phone numbers, and free-text personal identifiers from logs and async memory payloads before storage, using **Google Cloud DLP (Sensitive Data Protection)** when enabled in GCP and a deterministic regex scrubber as an offline/test fallback.

### 5.5 Infrastructure & CI/CD (Category 5)
1. **Automated Evaluation Suites:**
   1. `tests/unit/`: `pytest` tests for Pydantic schemas, guided error recovery, PII redaction, and guardrail plugin callbacks.
   2. `tests/evals/`: ADK `AgentEvaluator` (`adk eval`) suite with a golden dataset (`golden_cards.evalset.json`) measuring tool trajectories, safety critic catch rates, and copy quality regressions.
   3. `.github/workflows/ci.yml`: Runs linting (`ruff`), unit tests, and ADK evals on every PR.
2. **Infrastructure as Code & CLI:**
   1. `deployment/terraform/`: Terraform configs (aligned with `GoogleCloudPlatform/agent-starter-pack` patterns) provisioning Cloud Run (or Vertex AI Agent Engine), Artifact Registry, Service Accounts, IAM, Secret Manager, and Cloud Trace/Logging permissions, with parameterized `ingress`.
   2. Deployment scripts supporting `adk deploy cloud_run` / `adk deploy agent_engine`.
3. **Secure Secret Management:** Zero hardcoded API keys or credentials. Production secrets and deploy-time event configs are stored in **Google Cloud Secret Manager** and injected into Cloud Run / Agent Engine via IAM-bound secret references.

---

## 6. Tech Stack & Repository Structure

1. **Backend:** Python 3.12+, `google-adk`, `fastapi`, `uvicorn`, `pydantic>=2`, `structlog`, `opentelemetry-sdk`, `google-cloud-dlp`, `google-cloud-secret-manager`, `aiosqlite`, managed with `uv`.
2. **Frontend:** Vanilla HTML5 + Tailwind CSS + HTML5 Canvas API + Web Share API (zero build-step complexity).
3. **Proposed Repo Layout (GitHub-ready):**
   ```text
   holiday-card-studio/
   ├── .github/
   │   └── workflows/
   │       └── ci.yml                 # Ruff + pytest + ADK golden evals
   ├── app/
   │   ├── main.py                    # FastAPI app + OTel middleware + API routes
   │   ├── config.py                  # Settings + Secret Manager / theme_config loader
   │   ├── observability/
   │   │   ├── logging.py             # structlog JSON logger
   │   │   ├── tracing.py             # OpenTelemetry + Cloud Trace setup
   │   │   └── pii_redactor.py        # Cloud DLP + regex fallback scrubber
   │   └── agents/
   │       ├── prompts.py             # Agent constitutions (system instructions)
   │       ├── schemas.py             # Strict Pydantic v2 input/output models
   │       ├── plugins.py             # Guardrails + Intent/Outcome logging plugin
   │       ├── pipeline.py            # Runner, SessionService, Compaction, Memory
   │       ├── copywriter.py          # Copywriter + ToneSafetyCritic (Flash)
   │       ├── art_director.py        # ArtDirector (Pro) + HITL hook
   │       └── tools/
   │           ├── theme_tools.py     # load_event_theme_config
   │           ├── image_tools.py     # generate_festive_background_image + recovery
   │           └── memory_tools.py    # approve_card_copy, record_anonymized_vibe_metric
   ├── static/
   │   ├── index.html                 # Mobile-first UI + Remix/Confirm controls
   │   ├── canvas_card.js             # Client-side selfie framing & 1080x1440 PNG
   │   └── assets/                    # Bundled fallback festive backgrounds
   ├── deployment/
   │   └── terraform/                 # IaC (Cloud Run/Agent Engine, Secret Manager, IAM)
   ├── tests/
   │   ├── unit/                      # Schema, guardrail, error-handling, PII tests
   │   └── evals/                     # ADK golden dataset & regression evals
   ├── Dockerfile
   ├── pyproject.toml
   ├── .env.example                   # Generic non-sensitive placeholders only
   └── README.md
   ```
