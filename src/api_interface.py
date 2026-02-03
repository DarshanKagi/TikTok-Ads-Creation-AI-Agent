from abc import ABC, abstractmethod
from typing import Dict

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
