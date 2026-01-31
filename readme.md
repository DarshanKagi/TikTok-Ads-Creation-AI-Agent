# TikTok Ads Creation AI Agent 🤖🎵

A conversational AI agent that helps users create TikTok ad campaigns through natural language. The agent collects campaign details step-by-step, enforces TikTok business rules (especially music requirements), validates inputs, and submits ads via a mock TikTok Ads API with OAuth support.

---

## 🚀 Features

- **Conversational Ad Creation** – Create TikTok ad campaigns via chat
- **Business Rule Enforcement**
  - Conversions → Music **required**
  - Traffic → Music **optional**
- **Smart Music Handling**
  - Validate existing music IDs
  - Upload custom music
  - Reject invalid music IDs
- **OAuth 2.0 Integration (Simulated)**
- **Mock TikTok Ads API** for safe testing
- **Error Recovery & User Guidance**
- **Structured Outputs** using Pydantic models
- **Gradio Web UI**
- **Test Suite** with pytest

---

## 🧠 Architecture Overview

```
├── app.py            # Gradio UI (main entry point)
├── agent.py          # AI agent logic & prompt orchestration
├── mock_api.py       # Mock TikTok Ads API + music validation
├── oauth_server.py   # OAuth 2.0 authorization server (simulated)
├── test.py           # Pytest test cases
├── README.md         # Project documentation
```

---

## 🛠️ Tech Stack

- **Python 3.10+**
- **Gradio** – Web UI
- **OpenAI API** – LLM interaction
- **Pydantic** – Input validation & schemas
- **Flask** – OAuth server
- **Pytest** – Testing
- **python-dotenv** – Environment variables

---

## ⚙️ Setup Instructions

### 1️⃣ Clone the repository
```bash
git clone <your-repo-url>
cd tiktok-ads-ai-agent
```

### 2️⃣ Create virtual environment
```bash
python -m venv .venv
source .venv/bin/activate    # Linux / Mac
.venv\Scripts\activate       # Windows
```

### 3️⃣ Install dependencies
```bash
pip install -r requirements.txt
```

---

## 🔐 Environment Variables

Create a `.env` file:

```env
OPENAI_API_KEY=your_openai_api_key
TIKTOK_CLIENT_ID=dummy_client_id
TIKTOK_CLIENT_SECRET=dummy_client_secret
REDIRECT_URI=http://localhost:8000/callback
```

> ⚠️ TikTok credentials are mocked — real credentials are **not required**.

---

## ▶️ Running the Application

### Start the Gradio UI
```bash
python app.py
```

Then open your browser at:
```
http://127.0.0.1:7860
```

---

## 🔑 OAuth Server (Optional)

To simulate TikTok OAuth:

```bash
python oauth_server.py
```

This starts a local OAuth authorization flow for demonstration purposes.

---

## 🎵 Mock Music IDs for Testing

Use these predefined music IDs:

| Music ID | Description |
|--------|------------|
| `12345` | Sample Track 12345 |
| `67890` | Sample Track 67890 |
| `11111` | Sample Track 11111 |
| `22222` | Sample Track 22222 |
| `33333` | Sample Track 33333 |

### Music Rules
- **Conversions** → Music **required**
- **Traffic** → Music optional
- Custom music uploads return IDs like: `UPLOAD_xxxxx`

---

## 💬 Example Chat Messages

### Valid Conversion Campaign
```
Create a Conversions campaign named "CandleBoost".
Budget: 50 USD/day.
Target: India, age 18–45.
Ad text: Handmade candles with natural scents. Shop now!
CTA: Shop Now.
Music ID: 12345.
Landing page: https://example.com
```

### Invalid (Conversions without music)
```
Create a Conversions campaign named "NoMusic".
Budget: 20 USD/day.
No music.
```
➡️ Agent will reject and explain why.

---

## 🧪 Running Tests

```bash
pytest test.py -v
```

Tests cover:
- Campaign validation rules
- Music ID validation
- Music upload flow
- Mock API failures
- Agent error handling

---

## 🧩 Prompt Design

- **System Prompt** strictly enforces:
  - Required fields
  - Business rules
  - JSON-only structured output
- Agent always returns:

```json
{
  "message": "...",
  "reasoning": "...",
  "state": {...},
  "action": "collect | validate | submit",
  "errors": []
}
```

This ensures predictable orchestration and safe automation.

---

## 🎥 Demo Expectations (Assignment)

In the demo video:
- Show a **Conversions campaign with music**
- Show rejection of **Conversions without music**
- Show **Traffic campaign without music**
- Show **custom music upload**
- Run `pytest` and show passing tests

---

## 🔮 Future Improvements

- Real TikTok Ads API integration
- Persistent session storage
- Multi-ad group campaigns
- Budget optimization suggestions
- Internationalization (multi-language support)

---

## ✅ Submission Status

✔ All assignment requirements implemented  
✔ Mock API + OAuth included  
✔ Business rules enforced  
✔ Tests provided  
✔ UI ready for demo

---

If you want, I can also:
- Generate a `requirements.txt`
- Create a `.env.example`
- Review your demo script
- Tighten the prompt for even more deterministic outputs
- Add a short `CHANGELOG.md`

Just tell me 👍

