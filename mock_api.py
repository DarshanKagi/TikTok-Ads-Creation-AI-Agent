"""
MOCK API: Simulates TikTok Ads API responses for development.
Replace with real API calls in production.

All methods are marked with # MOCK API comments for easy identification.
"""

import random
from typing import Dict, Any


class MockTikTokAPI:
    """
    MOCK API: Simulates TikTok Ads API endpoints.
    
    This class provides mock implementations of TikTok Ads API endpoints
    for development and testing purposes. It simulates various success
    and failure scenarios to test error handling.
    """
    
    def __init__(self, simulate_failures: bool = True, failure_rate: float = 0.1):
        """
        Initialize Mock API.
        
        Args:
            simulate_failures: Whether to randomly simulate API failures
            failure_rate: Probability of failure (0.0 to 1.0)
        """
        # MOCK DATA: Valid music IDs in the simulated database
        self.valid_music_ids = ["12345", "67890", "11111", "22222", "33333"]
        
        # MOCK DATA: Uploaded music storage
        self.uploaded_music = {}
        
        # MOCK CONFIG: Failure simulation settings
        self.simulate_failures = simulate_failures
        self.failure_rate = failure_rate
    
    def validate_music_id(self, music_id: str, access_token: str) -> Dict[str, Any]:
        """
        MOCK API: Validates music ID.
        Real endpoint: GET /api/v1.3/music/search/
        
        Args:
            music_id: Music ID to validate
            access_token: OAuth access token
            
        Returns:
            Response dict with success status and data or error
        """
        # MOCK: Simulate occasional token errors
        if self.simulate_failures and random.random() < self.failure_rate:
            return {
                "success": False,
                "error_code": "INVALID_TOKEN",
                "message": "Access token has expired"
            }
        
        # MOCK: Check if music ID exists in simulated database
        if music_id in self.valid_music_ids or music_id.startswith("UPLOAD_"):
            return {
                "success": True,
                "data": {
                    "music_id": music_id,
                    "title": f"Sample Track {music_id}",
                    "artist": "Mock Artist",
                    "duration": 30,
                    "genre": "Pop"
                }
            }
        
        # MOCK: Music not found
        return {
            "success": False,
            "error_code": "MUSIC_NOT_FOUND",
            "message": f"Music ID '{music_id}' does not exist or has been removed"
        }
    
    def upload_music(self, file_path: str, access_token: str) -> Dict[str, Any]:
        """
        MOCK API: Simulates music upload.
        Real endpoint: POST /api/v1.3/music/upload/
        
        Args:
            file_path: Path to music file
            access_token: OAuth access token
            
        Returns:
            Response dict with success status and uploaded music data
        """
        # MOCK: Simulate geo-restriction occasionally
        if self.simulate_failures and random.random() < self.failure_rate:
            return {
                "success": False,
                "error_code": "GEO_RESTRICTED",
                "message": "Music upload is not available in your region"
            }
        
        # MOCK: Generate new music ID for uploaded file
        new_music_id = f"UPLOAD_{random.randint(10000, 99999)}"
        
        # MOCK: Store upload metadata
        self.uploaded_music[new_music_id] = {
            "file_path": file_path,
            "uploaded_at": "2026-01-31T12:00:00Z"
        }
        
        # MOCK: Add to valid IDs list
        self.valid_music_ids.append(new_music_id)
        
        return {
            "success": True,
            "data": {
                "music_id": new_music_id,
                "title": file_path.split("/")[-1].split("\\")[-1],
                "status": "ready",
                "duration": 30
            }
        }
    
    def create_ad(self, payload: dict, access_token: str) -> Dict[str, Any]:
        """
        MOCK API: Simulates ad creation.
        Real endpoint: POST /api/v1.3/ad/create/
        
        Args:
            payload: Ad configuration payload
            access_token: OAuth access token
            
        Returns:
            Response dict with created ad data or error
        """
        # MOCK: Simulate various failure scenarios
        if self.simulate_failures:
            rand = random.random()
            
            if rand < 0.05:  # 5% token expiry
                return {
                    "success": False,
                    "error_code": "INVALID_TOKEN",
                    "message": "Access token has expired"
                }
            elif rand < 0.08:  # 3% permission error
                return {
                    "success": False,
                    "error_code": "INSUFFICIENT_PERMISSIONS",
                    "message": "Missing ads management permission"
                }
            elif rand < 0.10:  # 2% invalid music
                return {
                    "success": False,
                    "error_code": "INVALID_MUSIC_ID",
                    "message": "Music cannot be used for ads due to licensing"
                }
        
        # MOCK: Success - generate ad and campaign IDs
        return {
            "success": True,
            "data": {
                "ad_id": f"AD_{random.randint(100000, 999999)}",
                "campaign_id": f"CAMP_{random.randint(100000, 999999)}",
                "status": "pending_review",
                "created_at": "2026-01-31T12:00:00Z",
                "campaign_name": payload.get("campaign_name"),
                "objective": payload.get("objective")
            }
        }


class ErrorInterpreter:
    """
    Converts API error codes into user-friendly messages.
    Provides explanations and suggested corrective actions.
    """
    
    # Error code mappings with explanations and actions
    ERRORS = {
        "INVALID_TOKEN": {
            "explanation": "Your TikTok access token has expired or is invalid.",
            "action": "I'll attempt to refresh your token automatically. If this fails, you'll need to re-authenticate with TikTok.",
            "retryable": True,
            "severity": "medium"
        },
        "INSUFFICIENT_PERMISSIONS": {
            "explanation": "Your TikTok app doesn't have the required permissions to create ads.",
            "action": "Please go to TikTok Developer Portal → Your App → Permissions and enable 'Ads Management' scope, then re-authenticate.",
            "retryable": False,
            "severity": "high"
        },
        "MUSIC_NOT_FOUND": {
            "explanation": "The music ID you provided doesn't exist in TikTok's library or has been removed.",
            "action": "Would you like to: 1) Try a different music ID, 2) Upload your own music, or 3) Proceed without music (if your objective allows)?",
            "retryable": False,
            "severity": "low"
        },
        "INVALID_MUSIC_ID": {
            "explanation": "This music track cannot be used for TikTok ads, possibly due to licensing restrictions.",
            "action": "Please choose a different music track from TikTok's library or upload your own music with proper licensing.",
            "retryable": False,
            "severity": "medium"
        },
        "GEO_RESTRICTED": {
            "explanation": "This feature is not available in your geographical region.",
            "action": "Unfortunately, TikTok Ads API has regional restrictions. You may need to use a different account or contact TikTok Business support.",
            "retryable": False,
            "severity": "high"
        }
    }
    
    @classmethod
    def interpret(cls, error_code: str) -> Dict[str, str]:
        """
        Interpret an error code and return user-friendly message.
        
        Args:
            error_code: API error code to interpret
            
        Returns:
            Dict with explanation, action, retryable flag, and severity
        """
        return cls.ERRORS.get(error_code, {
            "explanation": f"An unexpected error occurred: {error_code}",
            "action": "Please try again. If the issue persists, contact support.",
            "retryable": True,
            "severity": "medium"
        })
