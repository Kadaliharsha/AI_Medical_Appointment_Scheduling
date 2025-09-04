import streamlit as st
import sys
import os
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime, timedelta
import json

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from pydantic import SecretStr
from app.agent.tools import all_tools
from app.agent.prompts import AGENT_SYSTEM_PROMPT
from app.config import OPENAI_API_KEY, AGENT_MODEL_NAME

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="AI Medical Scheduling Agent",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Minimal CSS for a clean dark UI
st.markdown("""
<style>
    /* Hide Streamlit branding */
    /* Keep header visible so sidebar toggle is accessible */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Main container max-width like ChatGPT */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 7rem; /* Leave space for input area */
        max-width: 900px;
        margin: 0 auto;
    }
    body { background: #0d1117; }
    
    /* Simple header */
    /* Header */
    .main-header {
        position: sticky;
        top: 0;
        z-index: 10;
        background: #0d1117;
        border-bottom: 1px solid #1f2937;
        padding: 0.8rem 0.5rem;
        margin-bottom: 0.5rem;
    }
    .main-header h1 {
        color: #e6edf3;
        font-size: 1.1rem;
        margin: 0;
        font-weight: 600;
        text-align: center;
    }
    
    .main-header h1 {
        color: #ffffff;
        font-size: 1.8rem;
        font-weight: 600;
        margin: 0;
    }
    
    .main-header p {
        color: #cccccc;
        font-size: 1rem;
        margin: 0.5rem 0 0 0;
    }
    
    /* Subtle cards */
    .feature-card {
        background: #0f172a;
        color: #e2e8f0;
        padding: 1rem;
        margin: 0.5rem 0;
        border: 1px solid #1f2937;
    }
    
    .feature-card h4 {
        color: #ffffff;
        font-size: 0.9rem;
        font-weight: 600;
        margin: 0 0 0.3rem 0;
    }
    
    .feature-card p {
        color: #cccccc;
        font-size: 0.8rem;
        margin: 0;
    }
    
    /* Chat messages */
    .message-row { display: flex; width: 100%; }
    .message-row.user { justify-content: flex-end; }
    .message-row.ai { justify-content: flex-start; }
    .chat-message {
        padding: 0.6rem 0.8rem;
        margin: 0.35rem 0;
        border-radius: 12px;
        display: flex; gap: 8px; align-items: flex-start;
        max-width: 75%;
        width: fit-content;
        word-wrap: break-word;
        word-break: break-word;
        box-sizing: border-box;
    }
    
    .user-message {
        background: #161b22;
        color: #e6edf3;
        border: 1px solid #1f2937;
        margin-left: auto; /* push to right */
        justify-content: flex-end;
        text-align: right;
    }
    
    .ai-message {
        background: #0f172a;
        color: #e6edf3;
        border: 1px solid #1f2937;
        margin-right: auto; /* push to left */
    }
    
    .tool-message {
        background: #0b1020;
        color: #8b949e;
        margin: 0.3rem 0;
        padding: 0.5rem 0.8rem;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size: 0.8rem;
        border-left: 3px solid #ed8936;
    }
    
    /* Success/error messages */
    .success-message {
        background: #1a202c;
        color: #48bb78;
        padding: 0.8rem;
        border: 1px solid #2d3748;
        margin: 0.5rem 0;
    }
    
    .error-message {
        background: #1a202c;
        color: #f56565;
        padding: 0.8rem;
        border: 1px solid #2d3748;
        margin: 0.5rem 0;
    }
    
    /* Input styling */
    .stTextInput > div > div > input,
    .stTextArea textarea {
        background: #0f172a;
        color: #e2e8f0;
        border: 1px solid #243244;
    }
    
    /* Button styling */
    .stButton > button {
        background: #2d3748;
        color: #ffffff;
        border: 1px solid #4a5568;
    }
    
    .stButton > button:hover {
        background: #4a5568;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables"""
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []
    if 'patient_details' not in st.session_state:
        st.session_state.patient_details = {}
    if 'appointment_booked' not in st.session_state:
        st.session_state.appointment_booked = False
    if 'booking_summary' not in st.session_state:
        st.session_state.booking_summary = {}

def get_ai_response(user_input):
    """Get AI response using the agent"""
    try:
        if not OPENAI_API_KEY:
            return "Error: OpenAI API key not found. Please set OPENAI_API_KEY in your environment variables."
        
        model = ChatOpenAI(
            api_key=SecretStr(OPENAI_API_KEY),
            model=AGENT_MODEL_NAME,
            temperature=0
        )
        model_with_tools = model.bind_tools(all_tools)
        
        # Add user message to conversation
        st.session_state.conversation_history.append(HumanMessage(content=user_input))
        
        # Get AI response
        messages = [SystemMessage(content=AGENT_SYSTEM_PROMPT)] + st.session_state.conversation_history
        response = model_with_tools.invoke(messages)
        st.session_state.conversation_history.append(response)
        
        # Process tool calls if any
        if hasattr(response, 'additional_kwargs') and response.additional_kwargs.get('tool_calls'):
            tool_calls = response.additional_kwargs['tool_calls']
            
            # Process all tool calls and collect results
            tool_messages = []
            for tool_call in tool_calls:
                try:
                    # Handle the nested function structure
                    if 'function' in tool_call:
                        tool_name = tool_call['function'].get('name', '')
                        tool_args_str = tool_call['function'].get('arguments', '{}')
                    else:
                        tool_name = tool_call.get('name', '')
                        tool_args_str = tool_call.get('args', '{}')
                    
                    # Parse arguments
                    try:
                        tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
                    except:
                        tool_args = {}
                    
                    # Find and execute the tool
                    tool_func = None
                    for tool in all_tools:
                        if tool.name == tool_name:
                            tool_func = tool
                            break
                    
                    if tool_func:
                        result = tool_func.invoke(tool_args)
                        tool_message = ToolMessage(
                            content=str(result),
                            tool_call_id=tool_call.get('id', '')
                        )
                        tool_messages.append(tool_message)
                        
                        # Check if this is a booking confirmation
                        if tool_name == 'book_calendly_slot' and 'Success' in str(result):
                            st.session_state.appointment_booked = True
                            st.session_state.booking_summary = tool_args
                    else:
                        tool_message = ToolMessage(
                            content=f"Tool {tool_name} not found",
                            tool_call_id=tool_call.get('id', '')
                        )
                        tool_messages.append(tool_message)
                        
                except Exception as e:
                    tool_message = ToolMessage(
                        content=f"Tool call error: {str(e)}",
                        tool_call_id=tool_call.get('id', '')
                    )
                    tool_messages.append(tool_message)
            
            # Add all tool messages to conversation
            st.session_state.conversation_history.extend(tool_messages)
            
            # Get follow-up response from AI
            follow_up_messages = [SystemMessage(content=AGENT_SYSTEM_PROMPT)] + st.session_state.conversation_history
            follow_up_response = model_with_tools.invoke(follow_up_messages)
            st.session_state.conversation_history.append(follow_up_response)
            
            return follow_up_response.content
        
        return response.content
        
    except Exception as e:
        return f"Error: {str(e)}"

def display_conversation():
    """Display the conversation history"""
    # Render messages
    
    for i, message in enumerate(st.session_state.conversation_history):
        if isinstance(message, HumanMessage):
            st.markdown(f"""
            <div class="message-row user">
              <div class="chat-message user-message">
                <div>{message.content}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)
        elif isinstance(message, ToolMessage):
            st.markdown(f"""
            <div class="tool-message">
                <strong>Tool:</strong> {message.content}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="message-row ai">
              <div class="chat-message ai-message">
                <div>{message.content}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

def display_booking_summary():
    """Display booking success banner centered under the input"""
    if st.session_state.appointment_booked:
        st.markdown("""
        <div style="display:flex; justify-content:center;">
            <div class="success-message" style="width:100%; max-width: 900px; text-align:center;">
                <h3 style="margin:0;">Appointment Successfully Booked!</h3>
            </div>
        </div>
        """, unsafe_allow_html=True)

def main():
    """Main Streamlit application"""
    
    # Initialize session state
    initialize_session_state()
    
    # Header (always visible)
    st.markdown(
        """
        <div class="main-header">
            <h1>🏥 AI Medical Scheduling Agent</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Minimal sidebar
    with st.sidebar:
        st.markdown("## Status")
        
        # System status
        st.markdown("""
        <div class="feature-card">
            <h4>System</h4>
            <p>API: {'Connected' if OPENAI_API_KEY else 'Not Connected'}</p>
            <p>Tools: {len(all_tools)} Available</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Clear conversation button
        if st.button("Clear Conversation", type="secondary"):
            st.session_state.conversation_history = []
            st.session_state.patient_details = {}
            st.session_state.appointment_booked = False
            st.session_state.booking_summary = {}
            st.rerun()

        st.markdown("---")
        st.markdown("### Admin Reports")
        start = st.date_input("Start date")
        end = st.date_input("End date")
        if st.button("Generate Admin Report"):
            # Find and execute build_admin_report tool directly
            tool_func = None
            for t in all_tools:
                if t.name == 'build_admin_report':
                    tool_func = t
                    break
            if tool_func:
                res = tool_func.invoke({
                    'start_date': str(start),
                    'end_date': str(end),
                })
                st.success(str(res))
            else:
                st.error("build_admin_report tool not found")
    
    # Main content area (single column like ChatGPT)
    col1, col2 = st.columns([1, 0.0001])

    with col1:
        # Chat interface
        # Display conversation
        if st.session_state.conversation_history:
            display_conversation()
        else:
            st.markdown("Hi! I'm your AI medical scheduling assistant. How can I help you today?")
        
        # Chat input - Enter to send (Streamlit chat input)
        user_input = st.chat_input("Send a message…")
        if user_input is not None and user_input.strip():
            with st.spinner("Processing..."):
                _ = get_ai_response(user_input)
                st.rerun()

        # Success banner directly under the input
        display_booking_summary()
    
    # Minimal footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 0.5rem; font-size: 0.8rem;">
        <p>Medical Scheduling Agent</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
