import threading
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from typing import Optional
from src.config import USE_REAL_API
from src.instances import api_client

# --- Callback Server ---
app = FastAPI()

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

def start_server_thread():
    # Start Server Thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
