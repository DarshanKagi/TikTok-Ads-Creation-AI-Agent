import secrets
from typing import Dict
from src.api_interface import TikTokAPI

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
