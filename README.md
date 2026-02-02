# TikTok Ads AI Agent

A production-grade, conversational AI agent that helps users create and submit TikTok Ads.
Built with Python, Gradio, and Gemini Pro.

## Features

-   **Conversational Interface**: Natural language ad creation.
-   **End-to-End OAuth**: Automatic Authorization Code flow with local callback server.
-   **Robust Logic**:
    -   **Strict State Enforcement**: Validates inputs (Campaign Name > 3 chars, Objective rules).
    -   **Music Logic**: Enforces "Conversions = Music Required" rule.
    -   **Mock & Real Modes**: Toggleable backend for easy demonstration.
-   **Production Reliability**:
    -   **Token Persistence**: Saves/Refreshes tokens automatically.
    -   **Schema Validation**: strict JSON schema for LLM outputs.
    -   **Auto-Retry**: Handles transient API errors.

## Setup & Configuration

### Prerequisites
-   Python 3.10+
-   TikTok for Business Developer Account (for Real Mode)
-   Google Gemini API Key

### Installation
```bash
pip install -r requirements.txt
```

### Environment Variables
Set these in your terminal or `.env` file:

**Required:**
```bash
export GOOGLE_API_KEY="AIza..."
```

**For Real TikTok API (Optional):**
```bash
export USE_REAL_TIKTOK_API="True"
export TIKTOK_APP_ID="your_app_id"
export TIKTOK_SECRET="your_app_secret"
export TIKTOK_REDIRECT_URI="http://localhost:8000/callback"
export TIKTOK_ADVERTISER_ID="your_act_id"
```

## OAuth Setup (Real Mode)

1.  Create an App in the [TikTok Developer Portal](https://ads.tiktok.com/marketing_api/).
2.  In "Redirect URI", whitelist `http://localhost:8000/callback`.
3.  Select "Ads Management" and "Creative Management" scopes.
4.  Copy App ID and Secret to env vars.

## Architecture

```mermaid
graph TD
    User([User]) <--> UI[Gradio UI]
    UI <--> Agent[AdAgent]
    
    subgraph "Core Logic"
        Agent -- "Prompts" --> LLM[Gemini 1.5 Pro]
        LLM -- "JSON Command" --> Agent
        Agent -- "Actions" --> API{TikTokAPI Interface}
    end
    
    subgraph "Backend"
        API <|-- Real[RealTikTokAPI]
        API <|-- Mock[MockTikTokAPI]
        Real <--> TikTok[TikTok Ads API]
        Real -- "Read/Write" --> TokenStore[(tiktok_token.json)]
    end

    subgraph "OAuth Flow"
        Browser[User Browser] -- "Redirect" --> Server[FastAPI Server :8000]
        Server -- "Exchange Code" --> Real
    end
    
    User -- "Connect" --> Browser
```

### Prompt Design
The agent uses a **Structured Chain-of-Thought** prompt. It is instructed to output strictly valid JSON with the following fields:
-   `thought`: Internal reasoning step.
-   `message_to_user`: The response shown in the UI.
-   `action`: A deterministic command (`VALIDATE_MUSIC`, `SUBMIT_AD`, etc.).
-   `updated_ad_state`: key-value pairs to update the internal state machine.

This separation ensures logic (Action) is distinct from conversation (Message), preventing "hallucinated" API calls.

### Token Storage & Security
> **Note**: For this assignment/demo, tokens are stored in `tiktok_token.json` in plaintext.
> **Production Recommendation**: In a real deployment, use a secure secret store (e.g., AWS Secrets Manager, HashiCorp Vault) or OS-level Keyring to store refresh tokens.

## Demo Walkthrough (5-Minute Script)

**1. Setup**
-   Run `python main.py`.
-   Open `http://127.0.0.1:7860`.

**2. OAuth Flow**
-   Click **Connect**.
-   Authorize the app.
-   Verify the "Connected!" success page on localhost:8000.

**3. Case A: Existing Music**
-   User: "Create a Traffic campaign called 'Summer Sale'."
-   Agent asks for Music.
-   User: "Use Music ID 123."
-   Agent: Validates ID 123 (Valid) -> Updates State.

**4. Case B: Upload Music**
-   User: "Actually, I want to upload a file."
-   Agent: Simulates upload -> Returns new Music ID -> Updates State.

**5. Case C: Business Rule Enforcement**
-   User: "Switch objective to Conversions and remove the music."
-   Agent: "Conversions objective REQUIRE music. Please provide music." (Blocks submission).

**6. API Failure & Retry**
-   (Mock Mode: Check "Simulate Geo Fail" checkbox)
-   User: "Okay, use music 123 and submit."
-   Agent: Calls API -> Returns 403 Geo Error -> Explains error to user.

## File Structure
-   `main.py`: Single-file implementation containing Agent, Mock/Real API, Server, and UI.
-   `tiktok_token.json`: Local token store (created at runtime).
