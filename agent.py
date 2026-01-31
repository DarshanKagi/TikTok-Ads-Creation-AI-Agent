"""
Main conversational agent for TikTok Ads creation.
Handles conversation flow, validation, and API orchestration.

This file contains:
- Data models with Pydantic validation
- Prompt templates for LLM
- LLM client with structured output
- Conversation manager
"""

import json
import os
from typing import Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field, validator
from openai import OpenAI
from mock_api import MockTikTokAPI, ErrorInterpreter


# ============================================================================
# DATA MODELS & VALIDATION
# ============================================================================

class AdConfig(BaseModel):
    """
    Ad configuration with business rule validation.
    
    This Pydantic model enforces all business rules:
    - Campaign name: minimum 3 characters
    - Objective: must be "Traffic" or "Conversions"
    - Ad text: maximum 100 characters
    - CTA: required
    - Music logic: Conversions requires music, Traffic is optional
    """
    
    campaign_name: str = Field(..., min_length=3, description="Campaign name (min 3 chars)")
    objective: str = Field(..., description="Traffic or Conversions")
    ad_text: str = Field(..., max_length=100, description="Ad text (max 100 chars)")
    cta: str = Field(..., description="Call-to-action")
    music_id: Optional[str] = Field(None, description="Music ID (optional for Traffic)")
    
    @validator('campaign_name')
    def validate_campaign_name(cls, v):
        """Ensure campaign name is at least 3 characters after trimming"""
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Campaign name must be at least 3 characters")
        return v
    
    @validator('objective')
    def validate_objective(cls, v):
        """Ensure objective is either Traffic or Conversions"""
        if v not in ["Traffic", "Conversions"]:
            raise ValueError("Objective must be 'Traffic' or 'Conversions'")
        return v
    
    @validator('ad_text')
    def validate_ad_text(cls, v):
        """Ensure ad text doesn't exceed 100 characters"""
        if len(v) > 100:
            raise ValueError(f"Ad text cannot exceed 100 characters (current: {len(v)})")
        return v
    
    @validator('music_id')
    def validate_music_logic(cls, v, values):
        """
        CRITICAL: Enforce music logic based on objective.
        
        Business rules:
        - If objective = "Conversions", music MUST be provided
        - If objective = "Traffic", music is optional
        """
        objective = values.get('objective')
        
        # Rule: Conversions REQUIRES music
        if objective == "Conversions" and not v:
            raise ValueError(
                "Music is REQUIRED when objective is 'Conversions'. "
                "Please provide a music ID or upload custom music."
            )
        
        # Rule: If music is provided, it must be non-empty
        if v is not None and len(v.strip()) == 0:
            raise ValueError("Music ID cannot be empty")
        
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "campaign_name": "Summer Sale 2026",
                "objective": "Traffic",
                "ad_text": "Get 50% off on all products! Limited time offer.",
                "cta": "Shop Now",
                "music_id": "12345"
            }
        }


# ============================================================================
# PROMPT TEMPLATES
# ============================================================================

SYSTEM_PROMPT = """You are an expert TikTok Ads assistant helping users create successful ad campaigns.

Your mission is to guide users through creating a TikTok ad campaign by collecting all required information conversationally while enforcing business rules.

BUSINESS RULES (CRITICAL - MUST ENFORCE):
1. Campaign name: minimum 3 characters, required
2. Objective: must be either "Traffic" or "Conversions" (case-sensitive)
3. Ad text: maximum 100 characters, required
4. CTA (Call-to-Action): required field
5. Music logic (MOST IMPORTANT):
   - If objective = "Conversions" → Music is REQUIRED (must provide music ID or upload)
   - If objective = "Traffic" → Music is OPTIONAL (user can skip)
   - All music IDs must be validated via API before submission

CONVERSATION WORKFLOW:
1. Greet the user warmly
2. Ask for campaign name (min 3 chars)
3. Ask for campaign objective (Traffic or Conversions)
4. Based on objective, explain music requirements clearly
5. Collect music information (ID, upload, or skip if Traffic)
6. Ask for ad text (max 100 chars)
7. Ask for CTA
8. Confirm all details with user
9. Submit to TikTok Ads API

OUTPUT FORMAT - YOU MUST ALWAYS RESPOND WITH THIS JSON STRUCTURE:
{
  "message": "Your friendly, conversational response to the user",
  "reasoning": "Your internal thought process (for debugging)",
  "state": {
    "campaign_name": "value or null",
    "objective": "value or null", 
    "ad_text": "value or null",
    "cta": "value or null",
    "music_id": "value or null"
  },
  "action": "collect|validate_music|upload_music|submit",
  "errors": []
}

CRITICAL EXAMPLES - MUSIC LOGIC:

Example 1: User says "No music" when objective is "Conversions"
{
  "message": "I'm sorry, but music is REQUIRED when your campaign objective is 'Conversions'. TikTok requires engaging audio for conversion campaigns. Would you like to provide a music ID from TikTok's library, or would you prefer to upload your own track?",
  "reasoning": "User wants no music but objective is Conversions - this violates business rule. Must reject and offer alternatives.",
  "state": {"objective": "Conversions", "music_id": null},
  "action": "collect",
  "errors": ["Music is required for Conversions objective"]
}

Example 2: User says "No music" when objective is "Traffic"
{
  "message": "No problem! Music is optional for Traffic campaigns. Your ad will work great without it. Now, let's move on to your ad text. What message would you like to convey? (Maximum 100 characters)",
  "reasoning": "Traffic objective allows no music. This is valid. Proceeding to next field.",
  "state": {"objective": "Traffic", "music_id": null},
  "action": "collect",
  "errors": []
}

Example 3: User provides music ID "12345"
{
  "message": "Great! Let me validate music ID 12345 with TikTok's library...",
  "reasoning": "User provided music ID. Need to call API to validate it exists and is usable.",
  "state": {"music_id": "12345"},
  "action": "validate_music",
  "errors": []
}

Example 4: User wants to upload music
{
  "message": "Perfect! Please provide the file path to your music track, and I'll upload it to TikTok for you.",
  "reasoning": "User wants to upload custom music. Will simulate upload process.",
  "state": {},
  "action": "upload_music",
  "errors": []
}

TONE & STYLE:
- Be friendly, encouraging, and professional
- Use emojis sparingly (✅, ❌, 🎵, 🎯)
- Keep responses concise but informative
- Always explain WHY a rule exists when rejecting input
- Offer clear alternatives when something isn't allowed

Remember: Your job is to make ad creation easy and enjoyable while ensuring all campaign data meets TikTok's requirements!
"""


# ============================================================================
# LLM CLIENT
# ============================================================================

class LLMClient:
    """
    Handles LLM interactions with structured output using function calling.
    
    This ensures reliable, parseable responses from the LLM by enforcing
    a JSON schema via OpenAI's function calling feature.
    """
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """
        Initialize LLM client.
        
        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4o-mini for cost efficiency)
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
    
    def get_response(self, messages: List[Dict], context: Dict) -> Dict:
        """
        Get structured response from LLM.
        
        Args:
            messages: Conversation history
            context: Current ad configuration state
            
        Returns:
            Structured dict with message, reasoning, state, action, errors
        """
        # Prepare messages with system prompt and context
        full_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *messages,
            {"role": "system", "content": f"Current ad configuration state: {json.dumps(context)}"}
        ]
        
        # Define function schema for structured output
        function_schema = {
            "name": "respond",
            "description": "Generate structured agent response",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Conversational response to user"
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Internal thought process"
                    },
                    "state": {
                        "type": "object",
                        "description": "Current ad configuration state",
                        "properties": {
                            "campaign_name": {"type": ["string", "null"]},
                            "objective": {"type": ["string", "null"]},
                            "ad_text": {"type": ["string", "null"]},
                            "cta": {"type": ["string", "null"]},
                            "music_id": {"type": ["string", "null"]}
                        }
                    },
                    "action": {
                        "type": "string",
                        "enum": ["collect", "validate_music", "upload_music", "submit"],
                        "description": "Next action to perform"
                    },
                    "errors": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Validation errors if any"
                    }
                },
                "required": ["message", "action"]
            }
        }
        
        try:
            # Call LLM with function calling
            response = self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                functions=[function_schema],
                function_call={"name": "respond"},
                temperature=0.7
            )
            
            # Parse function call arguments
            result = json.loads(response.choices[0].message.function_call.arguments)
            
            # Ensure all required fields exist
            if "reasoning" not in result:
                result["reasoning"] = "No reasoning provided"
            if "state" not in result:
                result["state"] = {}
            if "errors" not in result:
                result["errors"] = []
            
            return result
            
        except Exception as e:
            # Fallback response if LLM fails
            return {
                "message": f"I apologize, but I encountered an error: {str(e)}. Let's try again.",
                "reasoning": f"LLM error: {str(e)}",
                "state": context,
                "action": "collect",
                "errors": [str(e)]
            }


# ============================================================================
# CONVERSATION MANAGER
# ============================================================================

class ConversationManager:
    """
    Manages conversation flow and state throughout the ad creation process.
    
    This is the main orchestrator that:
    - Maintains conversation history
    - Tracks ad configuration state
    - Calls LLM for responses
    - Executes actions (validate, upload, submit)
    - Handles errors gracefully
    """
    
    def __init__(self, llm_client: LLMClient, api_client):
        """
        Initialize conversation manager.
        
        Args:
            llm_client: LLM client for generating responses
            api_client: API client (MockTikTokAPI or real client)
        """
        self.llm = llm_client
        self.api = api_client  # MOCK API in development
        self.messages = []
        self.ad_config = {}
        self.conversation_started = False
    
    def process_message(self, user_msg: str) -> str:
        """
        Process user message and return agent response.
        
        This is the main entry point for handling user input.
        
        Args:
            user_msg: User's message
            
        Returns:
            Agent's response message
        """
        # Add user message to history
        self.messages.append({"role": "user", "content": user_msg})
        
        try:
            # Get LLM response with current context
            response = self.llm.get_response(self.messages, self.ad_config)
            
            # Log reasoning for debugging
            print(f"\n[AGENT REASONING] {response.get('reasoning', 'N/A')}")
            
            # Extract components
            agent_msg = response["message"]
            action = response.get("action", "collect")
            
            # Update state if provided
            if "state" in response and response["state"]:
                # Only update non-null values
                for key, value in response["state"].items():
                    if value is not None:
                        self.ad_config[key] = value
            
            # Execute action
            if action == "validate_music":
                agent_msg = self._validate_music()
            elif action == "upload_music":
                agent_msg = self._upload_music(user_msg)
            elif action == "submit":
                agent_msg = self._submit_ad()
            
            # Add agent response to history
            self.messages.append({"role": "assistant", "content": agent_msg})
            
            return agent_msg
            
        except Exception as e:
            error_msg = f"I apologize, but I encountered an error: {str(e)}. Could you please try again?"
            self.messages.append({"role": "assistant", "content": error_msg})
            return error_msg
    
    def _validate_music(self) -> str:
        """
        Validate music ID via API.
        
        Returns:
            Success or error message
        """
        music_id = self.ad_config.get("music_id")
        
        if not music_id:
            return "⚠️ Please provide a music ID to validate."
        
        print(f"[ACTION] Validating music ID: {music_id}")
        
        # MOCK API CALL
        result = self.api.validate_music_id(music_id, "mock_access_token")
        
        if result["success"]:
            data = result["data"]
            return (
                f"✅ Music validated successfully!\n\n"
                f"🎵 **Track**: {data['title']}\n"
                f"🎤 **Artist**: {data['artist']}\n"
                f"⏱️ **Duration**: {data['duration']}s\n\n"
                f"Great choice! Now, what would you like your ad text to say? (Max 100 characters)"
            )
        else:
            # Interpret error
            error = ErrorInterpreter.interpret(result["error_code"])
            return (
                f"❌ **{error['explanation']}**\n\n"
                f"💡 {error['action']}"
            )
    
    def _upload_music(self, file_path: str) -> str:
        """
        Upload music file via API.
        
        Args:
            file_path: Path provided by user
            
        Returns:
            Success or error message
        """
        print(f"[ACTION] Uploading music: {file_path}")
        
        # MOCK API CALL
        result = self.api.upload_music(file_path, "mock_access_token")
        
        if result["success"]:
            # Store the generated music ID
            self.ad_config["music_id"] = result["data"]["music_id"]
            
            return (
                f"✅ Music uploaded successfully!\n\n"
                f"🎵 **Music ID**: {result['data']['music_id']}\n"
                f"📁 **File**: {result['data']['title']}\n"
                f"✨ **Status**: {result['data']['status']}\n\n"
                f"Excellent! Now let's create your ad text. What message would you like to convey? (Max 100 characters)"
            )
        else:
            # Interpret error
            error = ErrorInterpreter.interpret(result["error_code"])
            return (
                f"❌ **{error['explanation']}**\n\n"
                f"💡 {error['action']}"
            )
    
    def _submit_ad(self) -> str:
        """
        Submit ad to TikTok API after validation.
        
        Returns:
            Success message with ad details or error message
        """
        try:
            # Validate with Pydantic before submission
            validated_config = AdConfig(**self.ad_config)
            
            print(f"[ACTION] Submitting ad: {validated_config.dict()}")
            
            # MOCK API CALL
            result = self.api.create_ad(validated_config.dict(), "mock_access_token")
            
            if result["success"]:
                data = result["data"]
                return (
                    f"🎉 **SUCCESS! Your TikTok ad has been created!**\n\n"
                    f"📊 **Ad ID**: {data['ad_id']}\n"
                    f"📊 **Campaign ID**: {data['campaign_id']}\n"
                    f"📊 **Status**: {data['status']}\n"
                    f"📅 **Created**: {data['created_at']}\n\n"
                    f"**Campaign Details:**\n"
                    f"- Name: {data['campaign_name']}\n"
                    f"- Objective: {data['objective']}\n\n"
                    f"Your ad is now pending review by TikTok. You'll be notified once it's approved!\n\n"
                    f"Would you like to create another ad? Just say 'yes' or 'new campaign'!"
                )
            else:
                # Interpret error
                error = ErrorInterpreter.interpret(result["error_code"])
                retry_msg = "\n\nWould you like me to retry the submission?" if error["retryable"] else ""
                
                return (
                    f"❌ **Submission Failed**\n\n"
                    f"**Issue**: {error['explanation']}\n\n"
                    f"💡 **What to do**: {error['action']}{retry_msg}"
                )
                
        except ValueError as e:
            # Pydantic validation error
            return (
                f"❌ **Validation Failed**\n\n"
                f"**Issue**: {str(e)}\n\n"
                f"Please provide the correct information and I'll help you fix this."
            )
        except Exception as e:
            return f"❌ An unexpected error occurred: {str(e)}\n\nPlease try again."
    
    def get_config_summary(self) -> str:
        """
        Get current ad configuration summary for display.
        
        Returns:
            Formatted markdown summary
        """
        if not self.ad_config:
            return "📝 **No configuration yet**\n\nStart chatting to create your ad!"
        
        return f"""
### 📊 Current Ad Configuration

**Campaign Name**: {self.ad_config.get('campaign_name', '❌ Not set')}  
**Objective**: {self.ad_config.get('objective', '❌ Not set')}  
**Ad Text**: {self.ad_config.get('ad_text', '❌ Not set')}  
**CTA**: {self.ad_config.get('cta', '❌ Not set')}  
**Music ID**: {self.ad_config.get('music_id', '❌ Not set')}  

---
**Completion**: {sum(1 for v in self.ad_config.values() if v)}/5 fields
"""
    
    def reset(self):
        """Reset conversation and ad configuration."""
        self.messages = []
        self.ad_config = {}
        self.conversation_started = False
        print("[RESET] Conversation and state cleared")
