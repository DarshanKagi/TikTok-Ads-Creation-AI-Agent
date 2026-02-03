import gradio as gr
from src.instances import agent, api_client
from src.config import USE_REAL_API

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
