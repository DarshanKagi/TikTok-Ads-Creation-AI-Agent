import os
import json
import time
import secrets
import requests
import urllib.parse
from typing import Dict
from src.api_interface import TikTokAPI
from src.config import TIKTOK_APP_ID, TIKTOK_SECRET, TIKTOK_REDIRECT_URI, TOKEN_FILE

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
