AGENT_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["thought", "message_to_user", "action", "updated_ad_state"],
    "properties": {
        "thought": {"type": "string"},
        "message_to_user": {"type": "string"},
        "action": {"type": "string", "enum": ["NONE", "VALIDATE_MUSIC", "SUBMIT_AD", "UPLOAD_MUSIC"]},
        "action_params": {"type": "object"},
        "updated_ad_state": {
            "type": "object",
            "properties": {
                "campaign_name": {"type": "string"},
                "objective": {"type": "string"},
                "creative_details": {"type": "object"}
            }
        }
    }
}
