"""
Main application with Gradio UI.
Run this file to start the TikTok Ads AI Agent.

Usage:
    python app.py
    
Then open http://localhost:7860 in your browser.
"""

import gradio as gr
import os
from dotenv import load_dotenv
from agent import ConversationManager, LLMClient
from mock_api import MockTikTokAPI

# Load environment variables
load_dotenv()

# Initialize components
print("🚀 Initializing TikTok Ads AI Agent...")

# Get OpenAI API key
api_key = os.getenv("OPENAI_API_KEY", "")
if not api_key:
    print("⚠️  WARNING: OPENAI_API_KEY not found in .env file")
    print("   Please create a .env file with your OpenAI API key")

# Initialize LLM client
llm_client = LLMClient(api_key=api_key, model="gpt-4o-mini")

# Initialize MOCK API for development
mock_api = MockTikTokAPI(simulate_failures=True, failure_rate=0.1)
print("📝 Using MOCK API for development (10% random failure rate)")

# Initialize conversation manager
conversation = ConversationManager(llm_client, mock_api)

print("✅ Initialization complete!\n")


# ============================================================================
# GRADIO FUNCTIONS
# ============================================================================

def chat_fn(message, history):
    """
    Process chat message and return updated history.
    
    Args:
        message: User's message
        history: Current chat history
        
    Returns:
        Updated chat history
    """
    if not message or not message.strip():
        return history
    
    # Process message through agent
    response = conversation.process_message(message.strip())
    
    # Append to history
    history.append((message, response))
    
    return history


def reset_fn():
    """
    Reset conversation and state.
    
    Returns:
        Empty history and reset message
    """
    global conversation
    conversation.reset()
    conversation = ConversationManager(llm_client, mock_api)
    
    initial_greeting = (
        "👋 Hello! I'm your TikTok Ads assistant. "
        "Let's create an amazing ad campaign together!\n\n"
        "What would you like to name your campaign? "
        "(Minimum 3 characters)"
    )
    
    return [("", initial_greeting)], "Conversation reset! 🔄"


def config_fn():
    """
    Get current ad configuration.
    
    Returns:
        Formatted configuration summary
    """
    return conversation.get_config_summary()


# ============================================================================
# GRADIO UI
# ============================================================================

# Custom CSS for better styling
custom_css = """
.gradio-container {
    font-family: 'Segoe UI', Arial, sans-serif;
}

.chat-message {
    font-size: 16px;
    line-height: 1.6;
}

#config-box {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 20px;
    border-radius: 10px;
}

.info-box {
    background: rgba(102, 126, 234, 0.1);
    padding: 15px;
    border-radius: 8px;
    border-left: 4px solid #667eea;
}
"""

# Create Gradio interface
with gr.Blocks(
    title="TikTok Ads AI Agent",
    theme=gr.themes.Soft(primary_hue="purple"),
    css=custom_css
) as demo:
    
    # Header
    gr.Markdown(
        """
        # 🎵 TikTok Ads Creation AI Agent
        
        Create TikTok ad campaigns through natural conversation! I'll guide you through the process step-by-step.
        
        **Features:** ✅ OAuth Integration | ✅ Smart Music Logic | ✅ Error Recovery | ✅ Business Rule Enforcement
        """
    )
    
    # Main layout
    with gr.Row():
        # Left column - Chat interface
        with gr.Column(scale=2):
            chatbot = gr.Chatbot(
                label="💬 Conversation",
                height=500,
                elem_classes="chat-message"
            )
            
            with gr.Row():
                msg_box = gr.Textbox(
                    label="Your Message",
                    placeholder="Type your message here...",
                    scale=4,
                    lines=2
                )
                send_btn = gr.Button("📤 Send", variant="primary", scale=1)
            
            with gr.Row():
                clear_btn = gr.Button("🗑️ Clear Chat", size="sm")
                reset_btn = gr.Button("🔄 Reset Conversation", variant="stop", size="sm")
        
        # Right column - Configuration and help
        with gr.Column(scale=1):
            # Current configuration
            config_box = gr.Markdown(
                conversation.get_config_summary(),
                elem_id="config-box"
            )
            refresh_btn = gr.Button("🔄 Refresh Config", variant="secondary")
            
            gr.Markdown("---")
            
            # Quick guide
            gr.Markdown(
                """
                ### 💡 Quick Guide
                
                **Music Rules:**
                - **Conversions**: Music is REQUIRED
                - **Traffic**: Music is OPTIONAL
                
                **Music Options:**
                1. Provide a music ID (e.g., "12345")
                2. Say "upload music [filepath]"
                3. Say "no music" (Traffic only)
                
                ### 🎯 Valid Mock Music IDs
                
                For testing, you can use these IDs:
                - `12345` - Sample Track 12345
                - `67890` - Sample Track 67890
                - `11111` - Sample Track 11111
                - `22222` - Sample Track 22222
                - `33333` - Sample Track 33333
                
                ### ✅ Business Rules
                
                - **Campaign name**: Min 3 characters
                - **Objective**: "Traffic" or "Conversions"
                - **Ad text**: Max 100 characters
                - **CTA**: Required
                - **Music**: Conditional on objective
                
                ### 🔧 Development Mode
                
                Currently using **MOCK API** for development.
                All API calls are simulated with 10% random failures
                to test error handling.
                """,
                elem_classes="info-box"
            )
    
    # Footer
    gr.Markdown(
        """
        ---
        
        ### 📝 Notes
        
        - This is a development version using **Mock API** (no real TikTok account needed)
        - For production, configure OAuth in `oauth_server.py` and update `.env`
        - All conversation reasoning is logged to console for debugging
        
        **Created for TikTok Ads AI Engineer Assignment** | Powered by OpenAI GPT-4 & Gradio
        """
    )
    
    # Event handlers
    msg_box.submit(
        chat_fn,
        inputs=[msg_box, chatbot],
        outputs=[chatbot]
    ).then(
        lambda: "",  # Clear input box
        outputs=[msg_box]
    )
    
    send_btn.click(
        chat_fn,
        inputs=[msg_box, chatbot],
        outputs=[chatbot]
    ).then(
        lambda: "",  # Clear input box
        outputs=[msg_box]
    )
    
    clear_btn.click(
        lambda: [],
        outputs=[chatbot]
    )
    
    reset_btn.click(
        reset_fn,
        outputs=[chatbot, config_box]
    )
    
    refresh_btn.click(
        config_fn,
        outputs=[config_box]
    )


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🎵 TikTok Ads AI Agent - Starting Gradio Interface")
    print("=" * 60)
    print("\n📌 Configuration:")
    print(f"   OpenAI Model: {llm_client.model}")
    print(f"   API Mode: MOCK (Development)")
    print(f"   Mock API Failure Rate: 10%")
    print("\n🌐 Launching Gradio...")
    print("   → Local URL: http://localhost:7860")
    print("   → Press Ctrl+C to stop")
    print("=" * 60 + "\n")
    
    # Launch Gradio app
    demo.launch(
        server_name="0.0.0.0",  # Allow external access
        server_port=7860,
        share=False  # Set to True for public URL
    )
