import streamlit as st
import requests
import json
from datetime import datetime
import base64
from pathlib import Path

# Page configuration
st.set_page_config(
    page_title="Health Advice Chatbot",
    page_icon="🏥",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stTextInput > div > div > input {
        background-color: #f0f2f6;
    }
    .chat-message {
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .user-message {
        background-color: #e3f2fd;
        border-left: 5px solid #2196f3;
    }
    .bot-message {
        background-color: #f1f8e9;
        border-left: 5px solid #4caf50;
    }
    .disclaimer {
        background-color: #fff3cd;
        border: 1px solid #ffc107;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .voice-button {
        background-color: #4caf50;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        border: none;
        cursor: pointer;
        font-size: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "api_key" not in st.session_state:
    st.session_state.api_key = ""

if "voice_enabled" not in st.session_state:
    st.session_state.voice_enabled = False

# Function to call DeepSeek API with proper error handling
def get_deepseek_response(messages, api_key):
    """Call DeepSeek API to get health advice"""
    
    if not api_key or api_key.strip() == "":
        return "❌ Error: API key is empty. Please enter a valid DeepSeek API key in the sidebar."
    
    url = "https://api.deepseek.com/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key.strip()}"
    }
    
    # Add system prompt for health advice
    system_message = {
        "role": "system",
        "content": """You are a helpful health advice assistant. Provide general health information, wellness tips, and lifestyle advice. 

IMPORTANT DISCLAIMERS:
- You are NOT a replacement for professional medical advice
- Always remind users to consult healthcare professionals for diagnosis and treatment
- Do not provide specific diagnoses or prescribe medications
- Focus on general wellness, preventive care, and healthy lifestyle tips
- If someone describes serious symptoms, urge them to seek immediate medical attention

Be empathetic, informative, and always prioritize user safety. Keep responses concise and clear."""
    }
    
    full_messages = [system_message] + messages
    
    data = {
        "model": "deepseek-chat",
        "messages": full_messages,
        "temperature": 0.7,
        "max_tokens": 1000,
        "stream": False
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        
        # Check for specific error codes
        if response.status_code == 401:
            return "❌ Authentication Error: Invalid API key. Please check your DeepSeek API key and make sure it's correct."
        elif response.status_code == 429:
            return "⚠️ Rate Limit: Too many requests. Please wait a moment and try again."
        elif response.status_code == 500:
            return "❌ Server Error: DeepSeek API is experiencing issues. Please try again later."
        
        response.raise_for_status()
        result = response.json()
        
        if 'choices' in result and len(result['choices']) > 0:
            return result['choices'][0]['message']['content']
        else:
            return "❌ Error: Unexpected response format from API."
            
    except requests.exceptions.Timeout:
        return "⏱️ Timeout Error: Request took too long. Please try again."
    except requests.exceptions.ConnectionError:
        return "🌐 Connection Error: Unable to connect to DeepSeek API. Check your internet connection."
    except requests.exceptions.RequestException as e:
        return f"❌ Request Error: {str(e)}"
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        return f"❌ Parse Error: Unable to parse API response - {str(e)}"

# Function to convert text to speech using browser TTS
def text_to_speech(text):
    """Generate speech from text using JavaScript"""
    # Clean text for speech
    clean_text = text.replace('"', '\\"').replace('\n', ' ')
    
    js_code = f"""
    <script>
    function speak() {{
        const text = `{clean_text}`;
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 0.9;
        utterance.pitch = 1;
        utterance.volume = 1;
        window.speechSynthesis.speak(utterance);
    }}
    speak();
    </script>
    """
    return js_code

# Sidebar for API key and settings
with st.sidebar:
    st.title("⚙️ Settings")
    
    st.markdown("### 🔑 API Configuration")
    api_key_input = st.text_input(
        "DeepSeek API Key",
        type="password",
        value=st.session_state.api_key,
        help="Enter your DeepSeek API key",
        placeholder="sk-..."
    )
    
    if api_key_input:
        st.session_state.api_key = api_key_input.strip()
        st.success("✅ API Key saved")
    else:
        st.warning("⚠️ Please enter your API key")
    
    st.markdown("---")
    
    st.markdown("### 🔊 Voice Settings")
    st.session_state.voice_enabled = st.checkbox(
        "Enable Voice Responses",
        value=st.session_state.voice_enabled,
        help="Bot will speak responses aloud"
    )
    
    st.markdown("---")
    
    st.markdown("### 📋 Get API Key:")
    st.markdown("""
    1. Visit [platform.deepseek.com](https://platform.deepseek.com)
    2. Sign up or login
    3. Go to API Keys section
    4. Click "Create API Key"
    5. Copy the key (starts with 'sk-')
    6. Paste it above
    
    **Note:** The API key format is `sk-xxxxxxxx`
    """)
    
    st.markdown("---")
    
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    st.markdown("---")
    st.markdown("### 📊 Statistics")
    st.metric("Messages", len(st.session_state.messages))
    
    st.markdown("---")
    st.markdown("### 🧪 Test API Connection")
    if st.button("Test Connection", use_container_width=True):
        if st.session_state.api_key:
            with st.spinner("Testing..."):
                test_msg = [{"role": "user", "content": "Say 'API connection successful' in 5 words or less"}]
                response = get_deepseek_response(test_msg, st.session_state.api_key)
                if "❌" in response or "Error" in response:
                    st.error(response)
                else:
                    st.success("✅ Connection successful!")
        else:
            st.error("Please enter API key first")

# Main content
st.title("🏥 Health Advice Chatbot")
st.markdown("*Powered by DeepSeek AI with Voice Support*")

# Disclaimer
st.markdown("""
<div class="disclaimer">
    <strong>⚠️ Medical Disclaimer:</strong> This chatbot provides general health information only. 
    It is NOT a substitute for professional medical advice, diagnosis, or treatment. 
    Always consult with qualified healthcare providers for medical concerns.
</div>
""", unsafe_allow_html=True)

# Display chat messages
chat_container = st.container()
with chat_container:
    for idx, message in enumerate(st.session_state.messages):
        role = message["role"]
        content = message["content"]
        
        if role == "user":
            st.markdown(f"""
            <div class="chat-message user-message">
                <strong>👤 You:</strong><br>{content}
            </div>
            """, unsafe_allow_html=True)
        else:
            col1, col2 = st.columns([0.95, 0.05])
            with col1:
                st.markdown(f"""
                <div class="chat-message bot-message">
                    <strong>🤖 Health Assistant:</strong><br>{content}
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                # Add speak button for each bot message
                if st.button("🔊", key=f"speak_{idx}", help="Speak this response"):
                    st.components.v1.html(text_to_speech(content), height=0)

# Chat input
if st.session_state.api_key:
    user_input = st.chat_input("Ask about health, wellness, nutrition, exercise, or general medical information...")
    
    if user_input:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Get bot response
        with st.spinner("🤔 Thinking..."):
            bot_response = get_deepseek_response(
                st.session_state.messages,
                st.session_state.api_key
            )
        
        # Add bot message
        st.session_state.messages.append({"role": "assistant", "content": bot_response})
        
        # Auto-speak if voice is enabled
        if st.session_state.voice_enabled and not bot_response.startswith("❌"):
            st.components.v1.html(text_to_speech(bot_response), height=0)
        
        # Rerun to display new messages
        st.rerun()
else:
    st.info("👈 Please enter your DeepSeek API key in the sidebar to start chatting")

# Sample questions
with st.expander("💡 Sample Questions You Can Ask"):
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Nutrition & Diet:**
        - What are some healthy breakfast options?
        - How much water should I drink daily?
        - What foods boost immune system?
        
        **Exercise & Fitness:**
        - What exercises are good for back pain?
        - How to start a workout routine?
        - Benefits of walking daily?
        """)
    
    with col2:
        st.markdown("""
        **Mental Health:**
        - How can I reduce stress naturally?
        - What are the benefits of meditation?
        - Tips for better sleep quality?
        
        **General Wellness:**
        - How to maintain healthy weight?
        - Importance of regular checkups?
        - Ways to boost energy levels?
        """)

# Quick action buttons
st.markdown("### 🎯 Quick Actions")
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("💤 Sleep Tips", use_container_width=True):
        st.session_state.messages.append({"role": "user", "content": "Give me tips for better sleep"})
        st.rerun()

with col2:
    if st.button("🥗 Healthy Eating", use_container_width=True):
        st.session_state.messages.append({"role": "user", "content": "How to eat healthier?"})
        st.rerun()

with col3:
    if st.button("🏃 Exercise Guide", use_container_width=True):
        st.session_state.messages.append({"role": "user", "content": "What exercises should beginners do?"})
        st.rerun()

with col4:
    if st.button("🧘 Stress Relief", use_container_width=True):
        st.session_state.messages.append({"role": "user", "content": "How to manage stress?"})
        st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <small>Built with Streamlit 🎈 | Powered by DeepSeek AI 🤖 | Voice by Web Speech API 🔊<br>
    For educational purposes only - Always consult healthcare professionals</small>
</div>
""", unsafe_allow_html=True)
