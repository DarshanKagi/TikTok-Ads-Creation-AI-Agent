import gradio as gr
import google.generativeai as genai
import json
import time
import os
import secrets
import requests
import urllib.parse
import threading
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from jsonschema import validate, ValidationError

# --- Configuration & Security ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TIKTOK_APP_ID = os.getenv("TIKTOK_APP_ID")
TIKTOK_SECRET = os.getenv("TIKTOK_SECRET")
# Callback URI must match your TikTok App settings exactly
TIKTOK_REDIRECT_URI = os.getenv("TIKTOK_REDIRECT_URI", "http://localhost:8000/callback")
USE_REAL_API = os.getenv("USE_REAL_TIKTOK_API", "False").lower() == "true"
TOKEN_FILE = "tiktok_token.json"

if not GOOGLE_API_KEY:
    raise RuntimeError("CRITICAL: GOOGLE_API_KEY environment variable is not set. Please set it to run the agent.")
else:
    genai.configure(api_key=GOOGLE_API_KEY)

# --- Schemas ---
AGENT_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["thought", "message_to_user", "action", "updated_ad_state"],
    "properties": {
        "thought": {"type": "string"},
        "message_to_user": {"type": "string"},
        "action": {"type": "string", "enum": ["NONE", "VALIDATE_MUSIC", "SUBMIT_AD", "UPLOAD_MUSIC"]},
        "action_params": {"type": "object"},
        "updated_ad_state": {
            "type": "object",
            "properties": {
                "campaign_name": {"type": "string"},
                "objective": {"type": "string"},
                "creative_details": {"type": "object"}
            }
        }
    }
}

# --- TikTok API Interface ---
class TikTokAPI(ABC):
    @abstractmethod
    def get_auth_url(self) -> str: pass
    @abstractmethod
    def get_access_token(self, code: str) -> Dict: pass
    @abstractmethod
    def refresh_access_token(self) -> bool: pass
    @abstractmethod
    def validate_music_id(self, music_id: str) -> Dict: pass
    @abstractmethod
    def submit_ad(self, payload: Dict) -> Dict: pass
    @abstractmethod
    def upload_music(self, file_name: str) -> Dict: pass
    @abstractmethod
    def ensure_token(self) -> Dict: pass

# --- Real TikTok API ---
class RealTikTokAPI(TikTokAPI):
    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self.expires_at = 0
        self.advertiser_id = os.getenv("TIKTOK_ADVERTISER_ID")
        self.state_file = "oauth_state.json"
        self.load_token()

    def _save_state(self, state):
        try:
            with open(self.state_file, "w") as f: json.dump({"state": state}, f)
        except: pass

    def verify_state(self, received_state):
        if not received_state: return False
        try:
            if os.path.exists(self.state_file):
                saved = json.load(open(self.state_file)).get("state")
                return saved == received_state
        except: pass
        return False

    def load_token(self):
        # NOTE: Tokens are saved in plaintext. Use encryption/keyring for production.
        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, "r") as f:
                    data = json.load(f)
                    self.access_token = data.get("access_token")
                    self.refresh_token = data.get("refresh_token")
                    self.expires_at = data.get("expires_at", 0)
            except Exception as e:
                print(f"Failed to load token: {e}")

    def save_token(self, access_token, refresh_token, scope, expires_in):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_at = time.time() + expires_in
        try:
            with open(TOKEN_FILE, "w") as f:
                json.dump({
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "scope": scope,
                    "expires_at": self.expires_at
                }, f)
        except Exception as e:
            print(f"Failed to save token: {e}")

    def get_auth_url(self) -> str:
        base = "https://www.tiktok.com/v2/auth/authorize/"
        state = secrets.token_hex(8)
        self._save_state(state)
        params = {
            "client_key": TIKTOK_APP_ID,
            "response_type": "code",
            "scope": "ads_management,creative_management",
            "redirect_uri": TIKTOK_REDIRECT_URI,
            "state": state
        }
        return f"{base}?{urllib.parse.urlencode(params)}"

    def get_access_token(self, code: str) -> Dict:
        url = "https://business-api.tiktok.com/open_api/v1.3/oauth2/access_token/"
        params = {"app_id": TIKTOK_APP_ID, "secret": TIKTOK_SECRET, "auth_code": code}
        try:
            resp = requests.post(url, json=params)
            data = resp.json()
            if data.get("code") == 0:
                d = data["data"]
                # Scope Parsing
                scope_raw = d.get("scope", [])
                if isinstance(scope_raw, str):
                    scopes = [s.strip() for s in scope_raw.split(",") if s.strip()]
                else:
                    scopes = scope_raw
                
                # Check Scopes
                required = {"ads_management", "creative_management"}
                if not required.issubset(set(scopes)):
                    return {"status": "error", "message": f"Missing Scopes. Got: {scopes}"}

                self.save_token(d["access_token"], d.get("refresh_token"), scopes, d.get("expires_in", 86400))
                return {"status": "success"}
            return {"status": "error", "message": data.get("message")}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def refresh_access_token(self) -> bool:
        if not self.refresh_token: return False
        url = "https://business-api.tiktok.com/open_api/v1.3/oauth2/refresh_token/"
        params = {
            "app_id": TIKTOK_APP_ID,
            "secret": TIKTOK_SECRET,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token"
        }
        try:
            resp = requests.post(url, json=params)
            data = resp.json()
            if data.get("code") == 0:
                d = data["data"]
                self.save_token(d["access_token"], d.get("refresh_token"), d.get("scope"), d.get("expires_in", 86400))
                return True
        except Exception:
            pass
        return False

    def ensure_token(self) -> Dict:
        # Buffer of 5 minutes
        if self.access_token and time.time() < (self.expires_at - 300):
            return {"status": "success"}
        
        if self.refresh_access_token():
            return {"status": "success"}
            
        return {"status": "error", "code": 401, "message": "Session expired. Please reconnect TikTok."}

    def validate_music_id(self, music_id: str) -> Dict:
        auth = self.ensure_token()
        if auth["status"] == "error": return auth
        
        url = "https://business-api.tiktok.com/open_api/v1.3/file/music/get/"
        headers = {"Access-Token": self.access_token}
        params = {"music_id": music_id, "advertiser_id": self.advertiser_id}
        try:
            resp = requests.get(url, headers=headers, params=params)
            data = resp.json()
            if data.get("code") == 0: return {"status": "success", "data": data["data"]}
            return {"status": "error", "message": data.get("message")}
        except Exception as e: return {"status": "error", "message": str(e)}

    def submit_ad(self, payload: Dict) -> Dict:
        # Auto-Retry Logic
        for attempt in range(2):
            auth = self.ensure_token()
            if auth["status"] == "error" and attempt == 0:
                 # Force refresh attempt if not already tried by ensure_token implicitly
                 if self.refresh_access_token(): continue
                 return auth
            if auth["status"] == "error": return auth
    
            url = "https://business-api.tiktok.com/open_api/v1.3/ad/create/"
            headers = {"Access-Token": self.access_token}
            payload["advertiser_id"] = self.advertiser_id
            
            try:
                resp = requests.post(url, headers=headers, json=payload)
                data = resp.json()
                if data.get("code") == 0: return {"status": "success", "ad_id": data["data"]["ad_id"]}
                
                # If 401, refresh and retry
                if data.get("code") == 401 and attempt == 0:
                    if self.refresh_access_token(): continue
                
                return {"status": "error", "code": data.get("code"), "message": data.get("message")}
            except Exception as e: 
                if attempt == 1: return {"status": "error", "message": str(e)}
        return {"status": "error", "message": "Max retries exceeded"}

    def upload_music(self, file_name: str) -> Dict:
        return {"status": "error", "message": "Real Upload Not Implemented in Demo"}


# --- Mock API ---
class MockTikTokAPI(TikTokAPI):
    def __init__(self):
        self.access_token = None
        self.music_db = {"123": True, "456": False} # ID: Valid
        self.mock_failures = {"geo": False}

    def get_auth_url(self) -> str:
        return "mock://authorize?code=mock_code"

    def get_access_token(self, code: str) -> Dict:
        self.access_token = "mock_token"
        return {"status": "success"}

    def refresh_access_token(self) -> bool:
        self.access_token = "mock_refreshed_token"
        return True

    def ensure_token(self) -> Dict:
        if not self.access_token: return {"status": "error", "message": "Not Connected"}
        return {"status": "success"}

    def validate_music_id(self, music_id: str) -> Dict:
        if music_id.startswith("mock_up"): return {"status": "success"}
        if music_id in self.music_db:
            return {"status": "success"} if self.music_db[music_id] else {"status": "error", "message": "Copyright Error"}
        return {"status": "error", "message": "Not Found"}

    def submit_ad(self, payload: Dict) -> Dict:
        if self.mock_failures["geo"]: return {"status": "error", "code": 403, "message": "Geo Restricted"}
        return {"status": "success", "ad_id": "mock_ad_id"}

    def upload_music(self, file_name: str) -> Dict:
        return {"status": "success", "music_id": f"mock_up_{secrets.token_hex(4)}"}


# --- Agent ---
class AdAgent:
    def __init__(self, api_client: TikTokAPI):
        self.api_client = api_client
        self.model = genai.GenerativeModel('gemini-1.5-pro-latest')
        self.history = []
        self.collected_data = {}
        self.system_prompt = """
You are a TikTok Ads Agent.
Rules:
1. OAuth Check: If not authenticated, ask user to Connect.
2. Collect: Campaign Name (min 3), Objective (Traffic/Conversions), Text (<100), Music.
3. Music Logic: Conversions REQUIRES Music. Traffic OPTIONAL.
4. Validation: Validate Music ID if provided.
Output JSON: { "thought": "...", "message_to_user": "...", "action": "NONE|VALIDATE_MUSIC|SUBMIT_AD|UPLOAD_MUSIC", "action_params": {}, "updated_ad_state": {} }
"""

    def process_message(self, user_input, system_context=None, retry=False):
        # Build Context
        context = f"Auth status: {'OK' if self.api_client.access_token else 'None'}"
        if system_context: context += f" | System Msg: {system_context}"
        
        msgs = [{"role": "user", "parts": [self.system_prompt]}, {"role": "model", "parts": ["OK"]}]
        for t in self.history:
            msgs.append({"role": "user", "parts": [t["user"]]})
            msgs.append({"role": "model", "parts": [json.dumps(t["agent"])]})
        msgs.append({"role": "user", "parts": [f"Ctx: {context}\nUser: {user_input}"]})

        try:
            res = self.model.generate_content(msgs)
            
            # Robust Text Extraction
            text = None
            if hasattr(res, "text"):
                text = res.text
            elif hasattr(res, "output_text"):
                text = res.output_text
            elif hasattr(res, "candidates") and res.candidates:
                cand = res.candidates[0]
                text = getattr(cand, "content", None) or getattr(cand, "output", None)
            
            if not text:
                raise RuntimeError(f"Model returned no usable text. Raw: {repr(res)}")

            # Clean markdown
            if "```json" in text: text = text.split("```json")[1].split("```")[0]
            elif "```" in text: text = text.split("```")[1].split("```")[0]
            
            data = json.loads(text.strip())
            
            # Schema Validation
            validate(instance=data, schema=AGENT_OUTPUT_SCHEMA)
            
            # Merge State
            new_state = data.get("updated_ad_state", {})
            for k, v in new_state.items(): self.collected_data[k] = v 
            
            self.history.append({"user": user_input, "agent": data})
            return data

        except ValidationError as e:
            if not retry:
                return self.process_message(user_input, f"JSON Schema Error: {str(e)}. Retry with valid JSON.", retry=True)
            return {"thought": "Fail", "message_to_user": "System Error: Output Validation Failed.", "action": "NONE"}
        except Exception as e:
            print("RAW MODEL ERROR:", str(e))
            # If we have a response object but parsing failed, print it
            if 'res' in locals():
                print("RAW MODEL RESPONSE:", repr(res))
            return {"thought": "Fail", "message_to_user": f"System Error: {str(e)}", "action": "NONE"}


# --- Callback Server ---
app = FastAPI()
api_client = RealTikTokAPI() if USE_REAL_API else MockTikTokAPI()
agent = AdAgent(api_client)

@app.get("/callback")
@app.get("/callback")
async def callback(code: Optional[str] = None, state: Optional[str] = None):
    if not code:
        return HTMLResponse("<h1>Error: No code provided.</h1>")
    
    if USE_REAL_API:
        if not api_client.verify_state(state):
             return HTMLResponse("<h1>Error: Invalid State (CSRF Warning).</h1>")

    res = api_client.get_access_token(code)
    if res["status"] == "success":
        return HTMLResponse("<h1>Connected! You can close this tab and return to the Agent.</h1>")
    return HTMLResponse(f"<h1>Error: {res.get('message')}</h1>")

def run_server():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="error")

# Start Server Thread
server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()


# --- UI ---
def chat_interface(user_input, history):
    if not user_input: return history
    
    resp = agent.process_message(user_input)
    msg = resp["message_to_user"]
    action = resp.get("action")
    state = agent.collected_data # Use accumulated state
    
    if action == "VALIDATE_MUSIC":
        mid = resp.get("action_params", {}).get("music_id")
        if mid:
            r = api_client.validate_music_id(mid)
            if r["status"] == "error":
                resp = agent.process_message("Validation Error: " + r["message"], system_context=r)
                msg = resp["message_to_user"]

    elif action == "UPLOAD_MUSIC":
        r = api_client.upload_music("test.mp3")
        if r["status"] == "success":
            mid = r["music_id"]
            if "creative_details" not in agent.collected_data: agent.collected_data["creative_details"] = {}
            agent.collected_data["creative_details"]["music_id"] = mid
            msg += f"\n(System: Uploaded ID {mid})"
    
    elif action == "SUBMIT_AD":
        # Strict Pre-Check
        errors = []
        if state.get("objective") == "Conversions" and not state.get("creative_details", {}).get("music_id"):
            errors.append("Conversions require Music.")
        
        # Strict Music Check
        mid = state.get("creative_details", {}).get("music_id")
        if mid:
            mr = api_client.validate_music_id(mid)
            if mr["status"] == "error": errors.append(f"Music Invalid: {mr['message']}")
            
        if errors:
            resp = agent.process_message("Submit Blocked: " + ";".join(errors))
            msg = resp["message_to_user"]
        else:
            # Payload
            payload = {
                "campaign": {"name": state.get("campaign_name"), "objective": state.get("objective")},
                "creative": state.get("creative_details", {})
            }
            
            if not payload["campaign"]["name"] or not payload["campaign"]["objective"]:
                 resp = agent.process_message("System Error: Payload incomplete (Missing Name/Objective).")
                 msg = resp["message_to_user"]
            else:
                r = api_client.submit_ad(payload)
                if r["status"] == "error":
                    code = r.get("code")
                    msg_api = r.get("message", "")
                    
                    if code == 401:
                        advice = "Session expired or invalid token. Please reconnect via the Connect button (will refresh tokens) or reauthorize."
                    elif code == 403:
                        advice = "Permission or geo restriction. Check TikTok developer console and your campaign targeting."
                    elif code and 500 <= code < 600:
                        advice = "Server error at TikTok. Will retry shortly. If repeated, try again later."
                    else:
                        advice = "Check payload and music. " + msg_api
                    
                    resp = agent.process_message(f"API Error {code}: {msg_api}. Advice: {advice}")
                    msg = resp["message_to_user"]
                else:
                    msg += f"\n\nSUCCESS! Ad ID: {r.get('ad_id')}"

    history.append((user_input, msg))
    return history

def connect():
    return f"Please authorize here (Callback will auto-handle): {api_client.get_auth_url()}"

with gr.Blocks(title="TikTok Agent") as demo:
    gr.Markdown("# Production TikTok Agent")
    gr.Markdown("Auto-Callback running on localhost:8000")
    
    with gr.Row():
        auth_url_box = gr.Textbox(label="Auth URL")
        connect_btn = gr.Button("Connect")
        connect_btn.click(connect, inputs=None, outputs=auth_url_box)
        
        if not USE_REAL_API:
             geo_cb = gr.Checkbox(label="Simulate Geo Fail", value=False)
             # Explicit wiring
             def set_geo(x):
                 api_client.mock_failures["geo"] = bool(x)
                 return ""
             geo_cb.change(set_geo, inputs=[geo_cb], outputs=[auth_url_box])
            
    chatbot = gr.Chatbot(height=500)
    txt = gr.Textbox()
    txt.submit(chat_interface, [txt, chatbot], [chatbot]).then(lambda: "", None, txt)

if __name__ == "__main__":
    demo.launch()
