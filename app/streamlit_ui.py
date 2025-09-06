import streamlit as st
import sys
import os
from dotenv import load_dotenv
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
        
        # Parse insurance details if user provides them
        import re
        # Flexible insurance parsing: look for keywords and values in any order
        carrier = member_id = group_id = None
        carrier_match = re.search(r'(?:insurance\s*carrier|carrier)[:\s]+is\s+([\w\s\-]+?)(?:,|\.|$)', user_input, re.IGNORECASE)
        member_id_match = re.search(r'(?:member\s*id|id)[:\s]+is\s+([\w\-]+?)(?:,|\.|$)', user_input, re.IGNORECASE)
        group_id_match = re.search(r'(?:group\s*id|group)[:\s]+is\s+([\w\-]+?)(?:,|\.|$)', user_input, re.IGNORECASE)
        if carrier_match:
            carrier = carrier_match.group(1).strip()
        if member_id_match:
            member_id = member_id_match.group(1).strip()
        if group_id_match:
            group_id = group_id_match.group(1).strip()
        # Only update if at least one field is found
        if carrier or member_id or group_id:
            insurance = st.session_state.patient_details.get('insurance', {})
            if carrier:
                insurance['carrier'] = carrier
            if member_id:
                insurance['member_id'] = member_id
            if group_id:
                insurance['group_id'] = group_id
            st.session_state.patient_details['insurance'] = insurance

        # Ensure insurance details are passed to save_new_patient tool
        # Find the last tool call for save_new_patient and inject insurance details if present
        if st.session_state.conversation_history:
            last_tool_call = None
            for msg in reversed(st.session_state.conversation_history):
                if isinstance(msg, ToolMessage) and 'save_new_patient' in msg.content:
                    last_tool_call = msg
                    break
            if last_tool_call and 'insurance' in st.session_state.patient_details:
                # This is a simplified patch: in a real agent, you'd update the tool_args for save_new_patient
                # Here, just log that insurance would be passed
                print(f"[DEBUG] Insurance details to be saved: {st.session_state.patient_details['insurance']}")
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
                    
                    # Inject insurance details into save_new_patient tool call
                    if tool_name == 'save_new_patient':
                        insurance = st.session_state.patient_details.get('insurance', {}) if 'insurance' in st.session_state.patient_details else {}
                        if insurance:
                            # Map to expected argument names
                            if 'carrier' in insurance:
                                tool_args['insurance_carrier'] = insurance['carrier']
                            if 'member_id' in insurance:
                                tool_args['member_id'] = insurance['member_id']
                            if 'group_id' in insurance:
                                tool_args['group_id'] = insurance['group_id']
                    # Insurance check before sending forms/reminders
                    if tool_name in ['send_intake_forms', 'schedule_enhanced_reminders']:
                        insurance = st.session_state.patient_details.get('insurance', {}) if 'insurance' in st.session_state.patient_details else {}
                        missing_fields = []
                        for field in ['carrier', 'member_id', 'group_id']:
                            if not insurance.get(field):
                                missing_fields.append(field)
                        if missing_fields:
                            tool_message = ToolMessage(
                                content=f"Missing insurance details: {', '.join(missing_fields)}. Please provide carrier, member ID, and group ID before proceeding.",
                                tool_call_id=tool_call.get('id', '')
                            )
                            tool_messages.append(tool_message)
                            continue
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

    import re
    def format_time(text):
        # Find times like HH:MM or H:MM and add AM/PM if missing
        def repl(match):
            time_str = match.group(0)
            # If already has AM/PM at the end, return as is
            if re.search(r'(am|pm)\s*$', time_str, re.IGNORECASE):
                return time_str
            # Try to parse hour
            parts = time_str.split(':')
            try:
                hour = int(parts[0])
                ampm = 'AM' if 0 <= hour < 12 else 'PM'
                return f"{time_str} {ampm}"
            except Exception:
                return time_str
        # Remove Markdown bold (**text**) and italics (*text*)
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        return re.sub(r'\b\d{1,2}:\d{2}(?:\s*[APap][Mm])?\b', repl, text)

    for i, message in enumerate(st.session_state.conversation_history):
        if isinstance(message, HumanMessage):
            st.markdown(f"""
            <div class="message-row user">
                <div class="chat-message user-message">
                    <div>{format_time(message.content)}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        elif isinstance(message, ToolMessage):
            continue
        else:
            st.markdown(f"""
            <div class="message-row ai">
                <div class="chat-message ai-message">
                    <div>{format_time(message.content)}</div>
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
        st.markdown("### System Info")
        st.markdown("""
        <div class="feature-card">
            <h4>Admin Reports</h4>
            <p>Available via CLI: python -c "from app.agent.tools import build_admin_report; print(build_admin_report.invoke({'start_date': '2025-09-01', 'end_date': '2025-09-30'}))"</p>
        </div>
        """, unsafe_allow_html=True)
    
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
