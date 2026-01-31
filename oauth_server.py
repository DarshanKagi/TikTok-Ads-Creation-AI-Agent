"""
OAuth 2.0 flow for TikTok Ads API.
Runs a Flask server to handle authorization callback.

This is optional for development (using mock API).
For production, you'll need real TikTok Developer credentials.
"""

from flask import Flask, request, redirect, session, jsonify
import requests
import secrets
import os
from dotenv import load_dotenv

load_dotenv()

# OAuth Configuration
CLIENT_ID = os.getenv("TIKTOK_CLIENT_ID", "your_client_id_here")
CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET", "your_client_secret_here")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:5000/callback")

# TikTok OAuth endpoints
AUTH_URL = "https://business-api.tiktok.com/portal/auth"
TOKEN_URL = "https://business-api.tiktok.com/open_api/v1.3/oauth2/access_token/"

# Create Flask app
app = Flask(__name__)
app.secret_key = secrets.token_urlsafe(32)

# Store token in memory (use database in production)
ACCESS_TOKEN = None
REFRESH_TOKEN = None
TOKEN_EXPIRY = None


@app.route("/")
def index():
    """Landing page with authorization link and token status."""
    token_status = "✅ Active" if ACCESS_TOKEN else "❌ Not authorized"
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>TikTok Ads AI Agent - OAuth</title>
        <style>
            body {{
                font-family: 'Segoe UI', Arial, sans-serif;
                max-width: 600px;
                margin: 50px auto;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }}
            .card {{
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 15px;
                padding: 30px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
            }}
            h1 {{ margin-top: 0; }}
            .button {{
                display: inline-block;
                background: #ff0050;
                color: white;
                padding: 12px 30px;
                text-decoration: none;
                border-radius: 25px;
                font-weight: bold;
                margin: 10px 0;
                transition: transform 0.2s;
            }}
            .button:hover {{
                transform: scale(1.05);
            }}
            .status {{
                background: rgba(255, 255, 255, 0.2);
                padding: 10px;
                border-radius: 8px;
                margin: 15px 0;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>🎵 TikTok Ads AI Agent</h1>
            <h2>OAuth Authentication</h2>
            
            <div class="status">
                <strong>Token Status:</strong> {token_status}
            </div>
            
            {'<p><strong>Access Token:</strong> ' + ACCESS_TOKEN[:30] + '...</p>' if ACCESS_TOKEN else ''}
            
            <p>Click the button below to authorize this app with your TikTok Ads account:</p>
            
            <a href="/authorize" class="button">🔐 Authorize with TikTok</a>
            
            <hr style="border-color: rgba(255,255,255,0.2); margin: 30px 0;">
            
            <h3>📝 Setup Instructions:</h3>
            <ol>
                <li>Create a TikTok Developer account at <a href="https://ads.tiktok.com/marketing_api/homepage" style="color: #ffd700;">TikTok for Business</a></li>
                <li>Create a new app in the Developer Portal</li>
                <li>Add required scopes: <code>ad.management</code>, <code>ad.creative</code></li>
                <li>Set redirect URI to: <code>http://localhost:5000/callback</code></li>
                <li>Update your <code>.env</code> file with Client ID and Secret</li>
            </ol>
        </div>
    </body>
    </html>
    """


@app.route("/authorize")
def authorize():
    """Redirect user to TikTok authorization page."""
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state
    
    # Build authorization URL
    auth_params = {
        "app_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "state": state,
        "scope": "ad.management,ad.creative"
    }
    
    query_string = "&".join([f"{k}={v}" for k, v in auth_params.items()])
    authorization_url = f"{AUTH_URL}?{query_string}"
    
    print(f"[OAuth] Redirecting to: {authorization_url}")
    
    return redirect(authorization_url)


@app.route("/callback")
def callback():
    """Handle OAuth callback from TikTok."""
    global ACCESS_TOKEN, REFRESH_TOKEN, TOKEN_EXPIRY
    
    # Verify state to prevent CSRF
    state = request.args.get("state")
    if state != session.get("oauth_state"):
        return """
        <h1>❌ OAuth Error</h1>
        <p>Invalid state parameter. This might be a CSRF attack.</p>
        <a href="/">Go back</a>
        """, 400
    
    # Get authorization code
    auth_code = request.args.get("auth_code")
    if not auth_code:
        return """
        <h1>❌ OAuth Error</h1>
        <p>No authorization code received from TikTok.</p>
        <a href="/">Go back</a>
        """, 400
    
    print(f"[OAuth] Received authorization code: {auth_code[:20]}...")
    
    # Exchange code for access token
    try:
        response = requests.post(
            TOKEN_URL,
            json={
                "app_id": CLIENT_ID,
                "secret": CLIENT_SECRET,
                "auth_code": auth_code
            },
            headers={"Content-Type": "application/json"}
        )
        
        data = response.json()
        print(f"[OAuth] Token response: {data}")
        
        # Check if successful (TikTok returns code=0 on success)
        if data.get("code") == 0:
            token_data = data["data"]
            ACCESS_TOKEN = token_data["access_token"]
            REFRESH_TOKEN = token_data.get("refresh_token")
            TOKEN_EXPIRY = token_data.get("expires_in", 86400)  # Default 24h
            
            print(f"[OAuth] Successfully obtained access token")
            
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Authorization Successful</title>
                <style>
                    body {{
                        font-family: 'Segoe UI', Arial, sans-serif;
                        max-width: 600px;
                        margin: 50px auto;
                        padding: 20px;
                        background: linear-gradient(135deg, #56ab2f 0%, #a8e063 100%);
                        color: white;
                    }}
                    .card {{
                        background: rgba(255, 255, 255, 0.15);
                        backdrop-filter: blur(10px);
                        border-radius: 15px;
                        padding: 30px;
                        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
                    }}
                    code {{
                        background: rgba(0, 0, 0, 0.3);
                        padding: 2px 8px;
                        border-radius: 4px;
                        font-family: 'Courier New', monospace;
                    }}
                </style>
            </head>
            <body>
                <div class="card">
                    <h1>✅ Authorization Successful!</h1>
                    
                    <p>Your TikTok Ads account has been successfully connected.</p>
                    
                    <h3>📊 Token Details:</h3>
                    <p><strong>Access Token:</strong> <code>{ACCESS_TOKEN[:30]}...</code></p>
                    <p><strong>Expires in:</strong> {TOKEN_EXPIRY} seconds (~{TOKEN_EXPIRY//3600} hours)</p>
                    
                    <hr style="border-color: rgba(255,255,255,0.3);">
                    
                    <p>✨ You can now close this window and return to the Gradio app!</p>
                    <p>The token will be used automatically for API calls.</p>
                    
                    <a href="/" style="color: #ffd700;">← Back to home</a>
                </div>
            </body>
            </html>
            """
        else:
            # OAuth error
            error_msg = interpret_oauth_error(data)
            return f"""
            <h1>❌ OAuth Error</h1>
            <p><strong>Error:</strong> {error_msg}</p>
            <p><strong>Details:</strong> {data.get('message', 'Unknown error')}</p>
            <a href="/">← Go back</a>
            """, 400
            
    except Exception as e:
        print(f"[OAuth] Exception: {str(e)}")
        return f"""
        <h1>❌ Error</h1>
        <p>Failed to exchange authorization code for token.</p>
        <p><strong>Details:</strong> {str(e)}</p>
        <a href="/">← Go back</a>
        """, 500


def interpret_oauth_error(error_data: dict) -> str:
    """
    Interpret OAuth error codes from TikTok.
    
    Args:
        error_data: Error response from TikTok
        
    Returns:
        User-friendly error message
    """
    code = error_data.get("code")
    
    error_messages = {
        40002: "Invalid client credentials. Please check your App ID and Secret in the .env file.",
        40003: "Invalid authorization code. Please try authorizing again.",
        40004: "Invalid redirect URI. Make sure it matches the one in your TikTok app settings.",
        40100: "Missing required permission scope. Enable 'Ads Management' in your TikTok app settings.",
        40101: "Geo-restriction: TikTok Ads API is not available in your region.",
        40102: "App not approved. Your TikTok app may still be pending approval."
    }
    
    return error_messages.get(
        code, 
        f"Unknown OAuth error (code: {code}). Check TikTok Developer documentation."
    )


def get_access_token():
    """
    Get current access token.
    
    Returns:
        Access token string or None if not authenticated
    """
    return ACCESS_TOKEN


def is_authenticated():
    """
    Check if user is authenticated.
    
    Returns:
        True if access token exists, False otherwise
    """
    return ACCESS_TOKEN is not None


if __name__ == "__main__":
    print("=" * 60)
    print("🔐 TikTok Ads AI Agent - OAuth Server")
    print("=" * 60)
    print("\n📝 Configuration:")
    print(f"   Client ID: {CLIENT_ID[:20]}..." if len(CLIENT_ID) > 20 else f"   Client ID: {CLIENT_ID}")
    print(f"   Redirect URI: {REDIRECT_URI}")
    print("\n🌐 Server starting...")
    print("   → Visit http://localhost:5000 to authorize")
    print("=" * 60)
    print("\n⚠️  NOTE: This is for production use only.")
    print("   For development, the main app uses MOCK API (no OAuth needed).\n")
    
    app.run(host="0.0.0.0", port=5000, debug=True)
