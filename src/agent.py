import json
import google.generativeai as genai
from jsonschema import validate, ValidationError
from src.schemas import AGENT_OUTPUT_SCHEMA
from src.api_interface import TikTokAPI

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
