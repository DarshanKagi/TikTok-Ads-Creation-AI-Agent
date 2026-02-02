
# TikTok Ads AI Agent

**Repository:** AI agent that helps a user create and submit TikTok Ads via conversation.  
**Language:** Python  
**Interface:** CLI / minimal web UI (Gradio) + FastAPI callback for OAuth  
**LLM:** Google Generative AI (Gemini) via `google.generativeai` SDK

> This README describes how OAuth is handled, the prompt & schema design, API assumptions and mocks, and how to run the agent (mock mode or real TikTok mode). The 5-minute demo is intentionally omitted as requested.

---

## Table of contents
- [What this does](#what-this-does)
- [High-level design](#high-level-design)
- [OAuth (Authorization Code) flow](#oauth-authorization-code-flow)
- [Prompt & structured output design](#prompt--structured-output-design)
- [Music logic (cases A/B/C)](#music-logic-cases-abc)
- [API assumptions & mocks](#api-assumptions--mocks)
- [Security & token storage](#security--token-storage)
- [Requirements & install](#requirements--install)
- [Environment variables](#environment-variables)
- [Running the agent (mock mode)](#running-the-agent-mock-mode)
- [Running the agent (real TikTok API)](#running-the-agent-real-tiktok-api)
- [Testing / example flows to try (with mock mode)](#testing--example-flows-to-try-with-mock-mode)
- [Troubleshooting](#troubleshooting)
- [Notes & limitations](#notes--limitations)
- [License](#license)

---

## What this does

This project implements an AI agent that:
- Performs TikTok OAuth Authorization Code flow (callback endpoint included).
- Collects ad inputs conversationally via an LLM-guided flow (Gradio chat).
- Uses a schema-enforced structured output from the model.
- Enforces business rules deterministically (campaign name min length, objective allowed values, ad text presence and max length, CTA required, music rules).
- Handles music in three supported ways:
  - Validate an existing music ID.
  - Simulate music upload (mock) and validate.
  - Allow no music only for `Traffic` objective; **block** if `Conversions` objective and no music present.
- Attempts to submit the ad to TikTok and handles common API failures (401 token problems, 403 geo/permission, 5xx server errors) with remediation logic.
- Supports mock mode (no TikTok credentials necessary) and an optional real-TikTok mode (requires TikTok developer account & app).

---

## High-level design

- `main.py` contains:
  - `RealTikTokAPI` — real API client (access token exchange, refresh, validate_music, submit_ad).  
  - `MockTikTokAPI` — deterministic mock for dev/grading.
  - `AdAgent` — conversational agent that queries the LLM and expects structured JSON responses (schema enforced).
  - FastAPI callback endpoint (`/callback`) running on **port 8000** to receive OAuth `code`.
  - Gradio UI for chat (launches the browser UI for conversation).
- Tokens are saved to `tiktok_token.json`. OAuth `state` used & persisted in `oauth_state.json`.

---

## OAuth (Authorization Code) flow

1. Agent generates an authorization URL via `RealTikTokAPI.get_auth_url()`:
   - Includes `client_key` (app id), `redirect_uri`, `scope=ads_management,creative_management`, and a random `state`.
   - Saves `state` to `oauth_state.json`.
2. User visits the URL and authorizes the app on TikTok. TikTok redirects back to the configured redirect URI (by default `http://localhost:8000/callback`) with `code` and `state`.
3. FastAPI callback validates `state` (CSRF protection) and calls `get_access_token(code)`.
4. `get_access_token` exchanges the code for access + refresh tokens, checks required scopes, and stores tokens with expiry.
5. `ensure_token()` validates token freshness before API calls and attempts refresh if needed (`refresh_access_token`).

> **Important:** `TIKTOK_REDIRECT_URI` configured for your TikTok App must exactly match the `TIKTOK_REDIRECT_URI` environment variable (default `http://localhost:8000/callback`). Configure this in your TikTok developer console.

---

## Prompt & structured output design

The agent uses a system prompt and expects the LLM to return a JSON with this structure (enforced by `AGENT_OUTPUT_SCHEMA`):

```json
{
  "thought": "string (internal reasoning)",
  "message_to_user": "string (what the bot should display)",
  "action": "NONE | VALIDATE_MUSIC | SUBMIT_AD | UPLOAD_MUSIC",
  "action_params": { "music_id": "..." },
  "updated_ad_state": {
    "campaign_name": "...",
    "objective": "Traffic|Conversions",
    "creative_details": {
      "text": "...",
      "cta": "...",
      "music_id": "..."
    }
  }
}
```

- The agent programmatically **validates** the LLM output via `jsonschema`. If validation fails it asks the model to retry (one automatic retry).
- **Separation of concerns**: the agent uses `thought` for internal chain-of-thought / reasoning (not shown to the user), `message_to_user` for user-facing messages, and `updated_ad_state` as canonical structured state to be merged into the running ad payload.

---

## Music logic (cases A/B/C)

The agent implements and enforces the three required music cases:

- **Case A: Existing Music ID**
  - Agent asks for `music_id`.
  - Calls `validate_music_id(music_id)` (mock or real).
  - If valid → proceeds.
  - If rejected → explains why and asks user for next step.

- **Case B: Uploaded / Custom Music**
  - Agent asks if user wants to upload custom music.
  - In **mock mode** `upload_music("test.mp3")` simulates and returns a `mock_up_<hex>` ID which is inserted into the agent's state.
  - Agent validates the returned music id via `validate_music_id`.
  - If rejected → explains and suggests next steps.

- **Case C: No Music**
  - Allowed **only** if `objective == "Traffic"`.
  - If `objective == "Conversions"` and no `music_id`, the agent **blocks submission** and asks the user to provide/upload a music track before submitting.

These rules are enforced *programmatically before submission*, not entrusted solely to the LLM.

---

## API assumptions & mocks

- **Mock Mode (`USE_REAL_TIKTOK_API=false`)**
  - No TikTok credentials required.
  - `MockTikTokAPI` implements:
    - `get_auth_url()` returns a mock URL.
    - `get_access_token()` always succeeds.
    - `validate_music_id()` uses an internal map: `"123" -> valid`, `"456" -> copyright error`, `mock_up_*` IDs are valid.
    - `upload_music()` returns a `mock_up_<hex>` ID.
    - `submit_ad()` returns success or a simulated `403 Geo Restricted` if `mock_failures["geo"] == True`.
  - Good for automated testing and grading reproducible flows.

- **Real Mode (`USE_REAL_TIKTOK_API=true`)**
  - Requires TikTok Developer app credentials:
    - `TIKTOK_APP_ID` (client key)
    - `TIKTOK_SECRET` (client secret)
    - `TIKTOK_REDIRECT_URI` (must match your app config)
    - `TIKTOK_ADVERTISER_ID` (advertiser ID used in payloads)
  - `RealTikTokAPI.upload_music()` is **not implemented** in this demo (returns error). If you need real uploads, implement multipart/form-data upload to TikTok's file endpoints per TikTok docs.
  - The real client:
    - Exchanges `code` → tokens and persists them in `tiktok_token.json`
    - Refreshes tokens automatically when near expiry
    - Validates `music_id` through the API
    - Submits ads to TikTok’s `open_api/v1.3/ad/create/` endpoint

---

## Security & token storage

- **Demo behavior:** tokens are saved to `tiktok_token.json` in plaintext for convenience.  
- **Production note:** do not store secrets in plaintext. Use OS keyring, environment-only secrets, or an encrypted secrets store. Rotate your API keys / secrets if accidentally committed.
- The OAuth `state` value is saved to `oauth_state.json` and verified in the callback (CSRF protection).

---

## Requirements & install

Recommended: use a virtual environment.

```bash
python -m venv .venv
source .venv/bin/activate      # Mac / Linux
.venv\Scripts\activate         # Windows
pip install --upgrade pip
pip install gradio google-generativeai requests fastapi uvicorn[standard] jsonschema
```

> The code imports `google.generativeai` and expects `GOOGLE_API_KEY` (for Gemini model). Install the official package matching your environment.

---

## Environment variables

Create a `.env` file or export these variables in your shell. Minimal variables for **mock** run:

```bash
export GOOGLE_API_KEY="your_google_api_key_for_gemini"   # required
export USE_REAL_TIKTOK_API="False"
```

For **real TikTok** run:

```bash
export GOOGLE_API_KEY="your_google_api_key"
export USE_REAL_TIKTOK_API="True"
export TIKTOK_APP_ID="your_tiktok_app_id"
export TIKTOK_SECRET="your_tiktok_secret"
export TIKTOK_REDIRECT_URI="http://localhost:8000/callback"  # must match app settings
export TIKTOK_ADVERTISER_ID="your_advertiser_id"
```

> If `GOOGLE_API_KEY` is missing, the agent will raise an error on startup because the LLM is required for the conversational agent.

---

## Running the agent (mock mode)

1. Ensure env vars (see above). For mock:

```bash
export GOOGLE_API_KEY="YOUR_GOOGLE_KEY"
export USE_REAL_TIKTOK_API="False"
python main.py
```

2. The script launches:
   - A FastAPI callback server on port `8000` (used only in real OAuth flow).
   - A Gradio UI in your browser (the chat interface).

3. In the UI:
   - Click **Connect** — it will show a mock auth URL.
   - Chat with the agent to create campaign, objective, ad text, CTA, and music choices.
   - Use the **Simulate Geo Fail** checkbox to trigger a mocked `403 Geo Restricted` during submit to test error reasoning.

---

## Running the agent (real TikTok API)

> **Set up TikTok Developer app first** and configure redirect URL to `http://localhost:8000/callback`.

1. Set environment variables as shown in [Environment variables](#environment-variables).

2. Run:

```bash
python main.py
```

3. Click **Connect** in the Gradio UI — copy the authorization URL into a browser, authenticate with TikTok, and allow the app to access the requested scopes. TikTok will redirect back to `http://localhost:8000/callback` and the server will exchange the `code` for tokens and persist them.

4. Continue conversationally to collect ad details and submit.

**Notes:**
- The app checks that `ads_management` and `creative_management` scopes are returned during token exchange; if missing, it will show an error instructing reauthorization with required scopes.
- `upload_music` on the real client is not implemented in this demo — use an existing `music_id` or extend `RealTikTokAPI.upload_music()` to call TikTok's file upload endpoint.

---

## Testing / example flows to try (mock mode)

- **Music Case A (Existing Music ID):**
  1. Tell the agent you have an existing music id `123` — mock recognizes `123` as valid.
  2. Agent validates and proceeds.

- **Music Case A (Invalid ID):**
  1. Tell agent `456` — mock returns `"Copyright Error"`.
  2. Agent explains error and asks next step.

- **Music Case B (Upload / Custom):**
  1. Tell the agent you want to upload custom music.
  2. Mock `upload_music` returns a `mock_up_<hex>` ID which gets validated and inserted into state.

- **Music Case C (No Music):**
  - If you select `Traffic` objective: Agent allows no music.
  - If you select `Conversions` objective: Agent blocks submission and asks for music before submitting.

- **Geo failure simulation:**
  - In UI, check `Simulate Geo Fail` and attempt to submit — `MockTikTokAPI` returns `403` and the agent will explain remediation.

---

## Troubleshooting

- **`RuntimeError: GOOGLE_API_KEY missing`** — set `GOOGLE_API_KEY` before launching.
- **Callback not receiving code** — ensure `TIKTOK_REDIRECT_URI` matches the redirect URI configured in your TikTok app and that your server (localhost:8000) is reachable.
- **Missing advertiser id on real mode** — set `TIKTOK_ADVERTISER_ID` env var.
- **Model JSON parse / schema failures** — the agent retries once automatically. If the LLM still emits invalid JSON, check model logs printed to console; run in dev mode and copy the RAW_MODEL_RESPONSE for debugging.
- **Upload in real mode returns not implemented** — real `upload_music` is intentionally a placeholder; implement real multipart upload if needed.

---

## Notes & limitations

- This code is a **demo / prototype** focusing on agent design, prompt engineering, structured output, and robust API reasoning — not a production deployment.
- Tokens are stored in plaintext JSON for convenience. Do **not** use this storage strategy in production.
- Real TikTok music upload is **not** implemented in the demo (placeholder). If you need that functionality, implement per TikTok's file upload spec (authenticated multipart upload endpoints).
- The LLM used is Google Gemini via `google.generativeai`. Make sure you have access or swap with another LLM SDK if needed.

---

## License

MIT License — feel free to reuse and adapt for educational purposes.

---

If you want, I can:
- generate a short `demo_script.md` with step-by-step interactions to record or run through (useful for graders), or
- create a small `test_flow.py` script that programmatically drives the mock API through Music A/B/C so graders can reproduce quickly.
Which would you prefer next?
