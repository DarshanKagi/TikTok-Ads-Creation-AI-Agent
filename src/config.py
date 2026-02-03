import os
import google.generativeai as genai

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
