# 🎵 TikTok Ads Creation AI Agent

An intelligent conversational AI agent that helps users create TikTok ad campaigns through natural language interaction. Built for the **TikTok Ads AI Engineer Assignment** with focus on prompt design, API reasoning, business rule enforcement, and robust error handling.

## ✨ Features

- ✅ **Conversational Ad Creation** - Natural language interface via Gradio
- ✅ **Smart Music Logic** - Handles 3 music scenarios (existing ID, upload, none)
- ✅ **Business Rule Enforcement** - Pydantic validation before API calls
- ✅ **Intelligent Error Handling** - User-friendly error interpretation
- ✅ **OAuth Integration** - Complete OAuth 2.0 flow for TikTok Ads API
- ✅ **Mock API** - Development without TikTok account
- ✅ **Structured Output** - LLM function calling for reliable responses
- ✅ **Comprehensive Testing** - Unit and integration tests

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- OpenAI API key
- (Optional) TikTok Developer account for production

### Installation

1. **Clone or download the project**
   ```bash
   cd tiktok-ads-agent
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   # Copy example env file
   copy .env.example .env
   
   # Edit .env and add your OpenAI API key
   OPENAI_API_KEY=your_openai_api_key_here
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Open in browser**
   - Navigate to `http://localhost:7860`
   - Start chatting with the agent!

## 📁 Project Structure

```
tiktok-ads-agent/
├── mock_api.py         # MOCK API - Simulates TikTok Ads API (~150 lines)
├── agent.py            # LLM client, prompts, validation, conversation (~400 lines)
├── oauth_server.py     # OAuth 2.0 flow (optional for production) (~180 lines)
├── app.py              # Gradio UI and entry point (~150 lines)
├── test.py             # Comprehensive unit tests (~300 lines)
├── requirements.txt    # Python dependencies
├── .env.example        # Environment configuration template
└── README.md           # This file
```

**Total: ~1,180 lines of code across 4 main files**

### Why This Structure?

- ✅ **Simple & Flat** - No nested directories, easy to navigate
- ✅ **Clear Separation** - Each file has a single responsibility
- ✅ **Easy Imports** - No complex module paths
- ✅ **Production Ready** - Clean, maintainable code

## 🎯 How It Works

### 1. Mock API Layer (`mock_api.py`)

Simulates all TikTok Ads API endpoints:

```python
# MOCK API: All methods marked with comments
api = MockTikTokAPI()

# Validate music ID
result = api.validate_music_id("12345", token)

# Upload custom music
result = api.upload_music("/path/to/track.mp3", token)

# Create ad campaign
result = api.create_ad(payload, token)
```

**Error Simulation:**
- 10% random failure rate for testing
- Simulates: token expiry, geo-restrictions, invalid music, etc.

### 2. Conversational Agent (`agent.py`)

**Key Components:**

#### a) Pydantic Validation (Business Rules)
```python
class AdConfig(BaseModel):
    campaign_name: str = Field(min_length=3)
    objective: str  # "Traffic" or "Conversions"
    ad_text: str = Field(max_length=100)
    cta: str
    music_id: Optional[str] = None
    
    @validator('music_id')
    def validate_music_logic(cls, v, values):
        # CRITICAL: Enforce music logic
        if values['objective'] == "Conversions" and not v:
            raise ValueError("Music REQUIRED for Conversions")
        return v
```

#### b) Prompt Engineering
```python
SYSTEM_PROMPT = """You are a TikTok Ads expert...

BUSINESS RULES (CRITICAL):
- If objective = "Conversions" → Music REQUIRED
- If objective = "Traffic" → Music OPTIONAL

OUTPUT FORMAT (JSON):
{
  "message": "...",
  "reasoning": "...",
  "state": {...},
  "action": "collect|validate_music|submit"
}
"""
```

#### c) LLM Structured Output
- Uses OpenAI function calling
- Guarantees JSON schema compliance
- Separates user message from internal reasoning

#### d) Conversation Flow
1. Collect campaign name
2. Collect objective (Traffic/Conversions)
3. Explain music requirements based on objective
4. Collect music (validate or upload)
5. Collect ad text and CTA
6. Confirm and submit

### 3. OAuth Server (`oauth_server.py`)

**Optional** - Only needed for production with real TikTok API.

```bash
# Run OAuth server separately
python oauth_server.py

# Visit http://localhost:5000 to authorize
```

**Handles:**
- Authorization URL generation
- Token exchange
- Token refresh
- Error interpretation (invalid credentials, missing scopes, etc.)

### 4. Gradio UI (`app.py`)

Clean, modern chat interface with:
- Real-time conversation
- Configuration display
- Quick guide and help
- Reset functionality

## 🎵 Music Logic (Core Feature)

The agent handles **3 distinct music scenarios**:

### Case A: Existing Music ID

```
User: "I want to use music ID 12345"
Agent: "Let me validate that... ✅ Music validated!"
```

**Flow:**
1. User provides music ID
2. Agent calls `api.validate_music_id()` (MOCK API)
3. If valid → Continue
4. If invalid → Suggest alternatives

### Case B: Upload Custom Music

```
User: "I want to upload my own music"
Agent: "Please provide the file path..."
User: "/path/to/track.mp3"
Agent: "✅ Uploaded! New ID: UPLOAD_12345"
```

**Flow:**
1. User indicates upload
2. Agent calls `api.upload_music()` (MOCK API)
3. Receives new music ID
4. Stores in configuration

### Case C: No Music

```
User: "No music please"
Agent (Traffic): "✅ No problem! Music is optional for Traffic."
Agent (Conversions): "❌ Sorry, music is REQUIRED for Conversions."
```

**Flow:**
1. Check objective
2. **Traffic** → Allow, continue
3. **Conversions** → Reject, ask for music

**This is enforced at TWO levels:**
- **Pydantic validator** (before API call)
- **LLM prompt** (during conversation)

## 🧪 Testing

### Run Tests

```bash
python test.py
```

or with pytest directly:

```bash
pytest test.py -v
```

### Test Coverage

**Validation Tests:**
- ✅ Traffic without music (valid)
- ✅ Traffic with music (valid)
- ✅ Conversions with music (valid)
- ✅ Conversions without music (invalid) ← **Critical test**
- ✅ Campaign name validation
- ✅ Ad text length validation
- ✅ Objective validation

**Mock API Tests:**
- ✅ Valid music ID validation
- ✅ Invalid music ID handling
- ✅ Music upload
- ✅ Ad creation
- ✅ Failure simulation

**Error Interpreter Tests:**
- ✅ Token errors
- ✅ Permission errors
- ✅ Music errors
- ✅ Geo-restrictions

**Integration Tests:**
- ✅ Complete Traffic workflow
- ✅ Complete Conversions workflow
- ✅ Upload music workflow

## 🎨 Prompt Design Highlights

### 1. System Prompt Structure

```
Role Definition → Business Rules → Output Format → Examples
```

### 2. Separation of Concerns

```json
{
  "message": "User-facing conversational text",
  "reasoning": "Internal thought process (debugging)",
  "state": "Current ad configuration",
  "action": "Next action to execute"
}
```

### 3. Few-Shot Examples

Critical scenarios provided in prompt:
- ✅ No music + Conversions → Reject
- ✅ No music + Traffic → Allow
- ✅ Music ID provided → Validate
- ✅ Upload request → Process

### 4. Structured Output via Function Calling

- **Problem**: LLM outputs are unpredictable
- **Solution**: OpenAI function calling enforces JSON schema
- **Benefit**: Reliable parsing, no hallucination

## 🔧 Development vs Production

### Development Mode (Default)

```python
# Uses Mock API - no TikTok account needed
mock_api = MockTikTokAPI()
conversation = ConversationManager(llm_client, mock_api)
```

**Benefits:**
- No OAuth setup required
- Instant testing
- Simulated error scenarios
- Fast iteration

### Production Mode

1. **Get TikTok credentials:**
   - Create account at [TikTok for Business](https://ads.tiktok.com/)
   - Create app in Developer Portal
   - Enable scopes: `ad.management`, `ad.creative`

2. **Update `.env`:**
   ```
   TIKTOK_CLIENT_ID=your_real_id
   TIKTOK_CLIENT_SECRET=your_real_secret
   ```

3. **Run OAuth server:**
   ```bash
   python oauth_server.py
   ```

4. **Replace Mock API:**
   ```python
   # In app.py, replace:
   from tiktok_client import TikTokAPIClient
   api = TikTokAPIClient(access_token)
   ```

## 🛡️ Error Handling

### Error Interpretation Layer

All API errors are converted to user-friendly messages:

```python
error = ErrorInterpreter.interpret("INVALID_TOKEN")
# Returns:
{
  "explanation": "Your access token has expired.",
  "action": "I'll refresh it automatically...",
  "retryable": True
}
```

### Handled Error Types

| Error Code | Explanation | User Action |
|------------|-------------|-------------|
| `INVALID_TOKEN` | Token expired | Auto-refresh |
| `INSUFFICIENT_PERMISSIONS` | Missing scopes | Update app settings |
| `MUSIC_NOT_FOUND` | Invalid music ID | Try different ID |
| `INVALID_MUSIC_ID` | Licensing issue | Choose different track |
| `GEO_RESTRICTED` | Regional limit | Contact support |

### Retry Logic

- **Retryable errors** (token, network) → Ask user to retry
- **Non-retryable errors** (permissions, validation) → Provide fix instructions

## 📊 Valid Mock Music IDs

For testing, use these pre-configured IDs:

- `12345` - Sample Track 12345
- `67890` - Sample Track 67890
- `11111` - Sample Track 11111
- `22222` - Sample Track 22222
- `33333` - Sample Track 33333

Any uploaded music gets ID: `UPLOAD_xxxxx`

## 🎥 Demo Video Script

### Segment 1: Architecture (1 min)
- Show 4-file structure
- Explain each file's purpose
- Point out MOCK API comments

### Segment 2: Prompt Design (1.5 min)
- Open `agent.py` → `SYSTEM_PROMPT`
- Show business rules
- Demonstrate structured output
- Highlight music logic examples

### Segment 3: Happy Path Demo (1 min)
- Run app
- Create Traffic campaign without music
- Show successful submission

### Segment 4: Error Handling (1 min)
- Try Conversions without music → Rejection
- Provide invalid music ID → Error interpretation
- Show retry suggestion

### Segment 5: Testing (30 sec)
- Run `python test.py`
- Show passing tests
- Highlight music logic tests

## 🏆 Key Engineering Decisions

### 1. Why Mock API First?
- ✅ Develop without TikTok account
- ✅ Test error scenarios easily
- ✅ Fast iteration
- ✅ Deterministic testing

### 2. Why Pydantic for Validation?
- ✅ Enforce rules BEFORE API calls
- ✅ Clear error messages
- ✅ Type safety
- ✅ Prevent invalid submissions

### 3. Why Function Calling?
- ✅ Guaranteed JSON schema
- ✅ No parsing errors
- ✅ Reliable responses
- ✅ Easy debugging

### 4. Why 4 Files Only?
- ✅ Easy to understand
- ✅ Simple imports
- ✅ Perfect for assignment
- ✅ Still production-ready

## 🚧 Potential Improvements

Given more time, I would add:

1. **Conversation Memory**
   - Vector database for context
   - Semantic search over history

2. **Multi-Language Support**
   - Detect user language
   - Localized responses

3. **A/B Testing for Prompts**
   - Track success rates
   - Optimize prompt variations

4. **Advanced Analytics**
   - Conversation flow metrics
   - Error rate tracking
   - User satisfaction scores

5. **Batch Operations**
   - Create multiple ads at once
   - Import from CSV

6. **Real-Time Preview**
   - Show ad mockup
   - Preview before submission

## 📝 Assignment Requirements Coverage

| Requirement | Implementation | Location |
|-------------|----------------|----------|
| **OAuth Integration** | ✅ Complete flow | `oauth_server.py` |
| **Conversational Creation** | ✅ Gradio UI + LLM | `app.py`, `agent.py` |
| **Music Case A** | ✅ Validate existing ID | `agent.py:_validate_music()` |
| **Music Case B** | ✅ Upload custom | `agent.py:_upload_music()` |
| **Music Case C** | ✅ Conditional no music | `agent.py:AdConfig.validate_music()` |
| **Prompt Design** | ✅ Structured output | `agent.py:SYSTEM_PROMPT` |
| **API Failure Handling** | ✅ Error interpreter | `mock_api.py:ErrorInterpreter` |
| **Business Rules** | ✅ Pydantic validators | `agent.py:AdConfig` |

## 📧 Contact & Support

**Created by:** [Your Name]  
**Email:** [Your Email]  
**GitHub:** [Your GitHub]

**For TikTok Ads AI Engineer Assignment**

---

## 🙏 Acknowledgments

- **OpenAI** - For GPT-4 and function calling
- **Gradio** - For rapid UI development
- **Pydantic** - For robust validation
- **TikTok** - For the inspiring API design

---

**⭐ If you found this helpful, please consider starring the repository!**
