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

# Clean, minimal CSS
st.markdown("""
<style>
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Main container */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    
    /* Simple header */
    .main-header {
        background: #1a1a1a;
        color: #ffffff;
        padding: 1.5rem;
        margin-bottom: 1rem;
        text-align: center;
        border-bottom: 2px solid #333;
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
    
    /* Feature cards - minimal */
    .feature-card {
        background: #1a1a1a;
        color: #ffffff;
        padding: 1rem;
        margin: 0.5rem 0;
        border: 1px solid #333;
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
    
    /* Chat messages - clean */
    .chat-message {
        padding: 0.8rem 1rem;
        margin: 0.5rem 0;
        border-radius: 4px;
    }
    
    .user-message {
        background: #2d3748;
        color: #ffffff;
        margin-left: 1rem;
        border-left: 3px solid #4299e1;
    }
    
    .ai-message {
        background: #2d3748;
        color: #ffffff;
        margin-right: 1rem;
        border-left: 3px solid #48bb78;
    }
    
    .tool-message {
        background: #1a202c;
        color: #a0aec0;
        margin: 0.3rem 0;
        padding: 0.5rem 0.8rem;
        font-family: monospace;
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
    .stTextInput > div > div > input {
        background: #1a1a1a;
        color: #ffffff;
        border: 1px solid #333;
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
        
        model = ChatOpenAI(api_key=SecretStr(OPENAI_API_KEY), model=AGENT_MODEL_NAME, temperature=0)
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
    st.subheader("💬 Conversation History")
    
    for i, message in enumerate(st.session_state.conversation_history):
        if isinstance(message, HumanMessage):
            st.markdown(f"""
            <div class="chat-message user-message">
                <strong>👤 You:</strong> {message.content}
            </div>
            """, unsafe_allow_html=True)
        elif isinstance(message, ToolMessage):
            st.markdown(f"""
            <div class="tool-message">
                <strong>🔧 Tool:</strong> {message.content}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="chat-message ai-message">
                <strong>🤖 AI:</strong> {message.content}
            </div>
            """, unsafe_allow_html=True)

def display_booking_summary():
    """Display booking summary if appointment is booked"""
    if st.session_state.appointment_booked and st.session_state.booking_summary:
        st.markdown("""
        <div class="success-message">
            <h3>🎉 Appointment Successfully Booked!</h3>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            <div class="feature-card">
                <h4>📅 Appointment Details</h4>
                <p><strong>Patient:</strong> {}</p>
                <p><strong>Doctor:</strong> {}</p>
                <p><strong>Date:</strong> {}</p>
                <p><strong>Time:</strong> {}</p>
            </div>
            """.format(
                st.session_state.booking_summary.get('patient_name', 'N/A'),
                st.session_state.booking_summary.get('doctor_name', 'N/A'),
                st.session_state.booking_summary.get('appointment_date', 'N/A'),
                st.session_state.booking_summary.get('appointment_time', 'N/A')
            ), unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="feature-card">
                <h4>📧 What Happens Next?</h4>
                <ul>
                    <li>✅ Intake forms sent to your email</li>
                    <li>✅ Calendar invite created</li>
                    <li>✅ 3 automated reminders scheduled</li>
                    <li>✅ Insurance information collected</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

def main():
    """Main Streamlit application"""
    
    # Initialize session state
    initialize_session_state()
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🏥 AI Medical Scheduling Agent</h1>
        <p>Intelligent appointment booking with automated reminders and form distribution</p>
    </div>
    """, unsafe_allow_html=True)
    
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
        
        # Reset button
        if st.button("Reset", type="secondary"):
            st.session_state.conversation_history = []
            st.session_state.patient_details = {}
            st.session_state.appointment_booked = False
            st.session_state.booking_summary = {}
            st.rerun()
    
    # Main content area
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Chat interface
        st.markdown("### Chat")
        
        # Display conversation
        if st.session_state.conversation_history:
            display_conversation()
        else:
            st.markdown("Hi! I'm your AI medical scheduling assistant. How can I help you today?")
        
        # User input with form
        with st.form("chat_form", clear_on_submit=True):
            user_input = st.text_input("Message:", placeholder="Type your message here...")
            
            col_send, col_clear = st.columns([1, 1])
            
            with col_send:
                submitted = st.form_submit_button("Send", type="primary")
                if submitted:
                    if user_input.strip():
                        with st.spinner("Processing..."):
                            response = get_ai_response(user_input)
                            st.rerun()
                    else:
                        st.warning("Please enter a message.")
            
            with col_clear:
                if st.form_submit_button("Clear"):
                    st.session_state.conversation_history = []
                    st.rerun()
    
    with col2:
        # Booking summary
        if st.session_state.appointment_booked:
            display_booking_summary()
        else:
            st.markdown("### Quick Start")
            st.markdown("Try: 'I'd like to book an appointment'")
    
    # Minimal footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 0.5rem; font-size: 0.8rem;">
        <p>Medical Scheduling Agent</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
