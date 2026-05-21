"""
Smart Scheduler Web App.
Premium consulting-style interface for the multi-user scheduling agent.
"""

import os
from datetime import datetime, timedelta, timezone
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv

from calendar_client import (
    authenticate_user,
    get_freebusy,
    list_authenticated_users,
)
from scheduler import parse_busy_slots, find_common_free_slots


load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


st.set_page_config(
    page_title="Smart Scheduler",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# Premium consulting-style CSS
# ============================================================

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap');

/* === GLOBAL === */
html, body, [class*="css"], .stApp, .main {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background-color: #000000 !important;
    color: #ffffff !important;
}

.stApp {
    background: linear-gradient(180deg, #000000 0%, #0a0a0a 100%);
}

/* Force all containers dark */
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"],
[data-testid="stHeader"],
.main .block-container {
    background-color: transparent !important;
}

/* === HIDE STREAMLIT BRANDING === */
#MainMenu, footer, header,
[data-testid="stHeader"],
[data-testid="stToolbar"],
.stDeployButton,
button[kind="header"] {
    display: none !important;
}

/* === TYPOGRAPHY === */
h1 {
    font-size: 3.5rem !important;
    font-weight: 800 !important;
    color: #ffffff !important;
    letter-spacing: -0.04em !important;
    line-height: 1 !important;
    margin: 0 !important;
}

h2, h3, h4 {
    color: #ffffff !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
}

p, span, div, label {
    color: #e5e5e5 !important;
}

/* === MAIN CONTAINER === */
.main .block-container {
    padding: 3rem 4rem !important;
    max-width: 1400px !important;
}

/* === SIDEBAR === */
section[data-testid="stSidebar"] {
    background-color: #050505 !important;
    border-right: 1px solid #1f1f1f !important;
    padding: 1rem 0 !important;
}

section[data-testid="stSidebar"] > div {
    padding: 1.5rem !important;
}

section[data-testid="stSidebar"] h2 {
    color: #ffffff !important;
    font-size: 1.1rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.01em !important;
    text-transform: none !important;
    margin-bottom: 0.5rem !important;
}

/* === BRAND ACCENT === */
.brand-line {
    height: 3px;
    width: 48px;
    background: linear-gradient(90deg, #ff0055 0%, #ff3377 100%);
    margin-bottom: 1.5rem;
    border-radius: 2px;
}

.brand-line-small {
    height: 2px;
    width: 32px;
    background: #ff0055;
    margin-bottom: 1rem;
    border-radius: 1px;
}

/* === SECTION LABELS === */
.section-label {
    color: #ff0055 !important;
    font-size: 0.7rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.2em !important;
    font-weight: 700 !important;
    margin-bottom: 1rem !important;
    font-family: 'JetBrains Mono', monospace !important;
}

/* === TAGLINE === */
.tagline {
    color: #a0a0a0 !important;
    font-size: 1.125rem !important;
    font-weight: 400 !important;
    line-height: 1.6 !important;
    margin: 1.5rem 0 0 0 !important;
    max-width: 720px !important;
}

/* === PARTICIPANT CARDS === */
.participant-card {
    background: linear-gradient(135deg, #141414 0%, #0f0f0f 100%);
    border: 1px solid #2a2a2a;
    border-left: 3px solid #ff0055;
    padding: 14px 18px;
    margin-bottom: 10px;
    border-radius: 6px;
    font-size: 0.875rem;
    color: #ffffff !important;
    font-weight: 500;
    font-family: 'JetBrains Mono', monospace;
    word-break: break-all;
    transition: all 0.2s ease;
}

.participant-card:hover {
    border-color: #ff0055;
    background: linear-gradient(135deg, #1a1a1a 0%, #141414 100%);
}

.participant-card-empty {
    background-color: #0a0a0a;
    border: 1px dashed #2a2a2a;
    padding: 24px;
    border-radius: 6px;
    color: #666666 !important;
    font-size: 0.875rem;
    text-align: center;
}

/* === BUTTONS === */
.stButton > button {
    background: linear-gradient(135deg, #ff0055 0%, #ff3377 100%) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    letter-spacing: 0.02em !important;
    padding: 0.75rem 1.25rem !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 2px 12px rgba(255, 0, 85, 0.25) !important;
}

.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 20px rgba(255, 0, 85, 0.4) !important;
}

.stButton > button:active {
    transform: translateY(0) !important;
}

/* Small delete buttons */
button[kind="secondary"] {
    background: transparent !important;
    color: #666666 !important;
    border: 1px solid #2a2a2a !important;
    padding: 0.4rem 0.8rem !important;
    box-shadow: none !important;
    font-size: 1rem !important;
}

button[kind="secondary"]:hover {
    border-color: #ff0055 !important;
    color: #ff0055 !important;
    background: rgba(255, 0, 85, 0.08) !important;
}

/* === INPUTS === */
.stTextInput > div > div > input {
    background-color: #0f0f0f !important;
    color: #ffffff !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 6px !important;
    padding: 0.75rem 1rem !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.875rem !important;
}

.stTextInput > div > div > input:focus {
    border-color: #ff0055 !important;
    box-shadow: 0 0 0 3px rgba(255, 0, 85, 0.1) !important;
}

.stTextInput > div > div > input::placeholder {
    color: #444444 !important;
}

/* === CHAT INPUT (BOTTOM BAR) === */
[data-testid="stBottomBlockContainer"],
[data-testid="stBottom"],
.stBottom,
section[data-testid="stChatInputContainer"] {
    background-color: #000000 !important;
    border-top: 1px solid #1f1f1f !important;
}

[data-testid="stChatInput"],
.stChatInput {
    background-color: #000000 !important;
    padding: 1rem 0 !important;
}

[data-testid="stChatInput"] > div,
.stChatInput > div {
    background-color: #0f0f0f !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 8px !important;
}

[data-testid="stChatInput"] textarea,
.stChatInput textarea {
    background-color: #0f0f0f !important;
    color: #ffffff !important;
    border: none !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.95rem !important;
    padding: 0.875rem 1rem !important;
}

[data-testid="stChatInput"] textarea:focus {
    outline: none !important;
    box-shadow: none !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: #555555 !important;
}

/* Chat input wrapper - the outer container */
div[data-baseweb="textarea"] {
    background-color: #0f0f0f !important;
    border-radius: 8px !important;
}

/* Send button in chat */
[data-testid="stChatInput"] button {
    background: linear-gradient(135deg, #ff0055 0%, #ff3377 100%) !important;
    border-radius: 6px !important;
    margin-right: 0.5rem !important;
}

[data-testid="stChatInput"] button:hover {
    transform: scale(1.05) !important;
}

[data-testid="stChatInput"] button svg {
    fill: #ffffff !important;
}

/* === CHAT MESSAGES === */
[data-testid="stChatMessage"] {
    background-color: #0a0a0a !important;
    border: 1px solid #1f1f1f !important;
    border-radius: 8px !important;
    padding: 1.25rem 1.5rem !important;
    margin-bottom: 1rem !important;
}

[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li {
    color: #f0f0f0 !important;
    line-height: 1.7 !important;
}

[data-testid="stChatMessage"] strong {
    color: #ff3377 !important;
    font-weight: 600 !important;
}

/* User messages */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background-color: #0f0f0f !important;
    border-left: 3px solid #ff0055 !important;
}

/* === ALERTS === */
.stAlert {
    background-color: #0f0f0f !important;
    border: 1px solid #2a2a2a !important;
    border-left: 3px solid #ff0055 !important;
    border-radius: 6px !important;
    color: #ffffff !important;
}

.stAlert p {
    color: #ffffff !important;
}

/* === DIVIDERS === */
hr {
    border-color: #1f1f1f !important;
    margin: 2.5rem 0 !important;
}

/* Sidebar dividers */
section[data-testid="stSidebar"] hr {
    margin: 1.5rem 0 !important;
}

/* === PRIVACY NOTE === */
.privacy-note {
    background: linear-gradient(135deg, #0a0a0a 0%, #050505 100%);
    border: 1px solid #1f1f1f;
    padding: 1.25rem;
    border-radius: 8px;
    color: #888888 !important;
    font-size: 0.8rem;
    line-height: 1.7;
    margin-top: 1rem;
}

.privacy-note-title {
    color: #ff0055 !important;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    font-size: 0.7rem;
    font-weight: 700;
    display: block;
    margin-bottom: 0.75rem;
    font-family: 'JetBrains Mono', monospace;
}

/* === EMPTY STATE === */
.empty-state {
    text-align: center;
    padding: 6rem 2rem;
    color: #666666;
    border: 1px dashed #1f1f1f;
    border-radius: 12px;
    background: #050505;
    margin-top: 2rem;
}

.empty-state-icon {
    width: 64px;
    height: 64px;
    margin: 0 auto 1.5rem auto;
    border: 2px solid #2a2a2a;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #ff0055;
    font-size: 1.5rem;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
}

.empty-state-title {
    color: #ffffff !important;
    font-size: 1.5rem !important;
    font-weight: 700 !important;
    margin-bottom: 0.75rem !important;
    letter-spacing: -0.02em !important;
}

.empty-state-text {
    color: #888888 !important;
    font-size: 1rem !important;
    max-width: 480px;
    margin: 0 auto;
    line-height: 1.6 !important;
}

/* === STATUS BADGE === */
.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 14px;
    background: rgba(255, 0, 85, 0.1);
    border: 1px solid rgba(255, 0, 85, 0.3);
    border-radius: 100px;
    color: #ff3377 !important;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-family: 'JetBrains Mono', monospace;
    margin-bottom: 1.5rem;
}

.status-dot {
    width: 6px;
    height: 6px;
    background: #ff0055;
    border-radius: 50%;
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}

/* === SPINNER === */
.stSpinner > div {
    border-top-color: #ff0055 !important;
}

/* === SCROLLBAR === */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: #050505;
}

::-webkit-scrollbar-thumb {
    background: #2a2a2a;
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: #ff0055;
}

/* === CODE BLOCKS === */
code {
    background-color: #1a1a1a !important;
    color: #ff3377 !important;
    padding: 0.2rem 0.4rem !important;
    border-radius: 4px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.875rem !important;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ============================================================
# Tool
# ============================================================

def find_meeting_slots(
    attendee_emails: list[str],
    duration_minutes: int = 60,
    days_ahead: int = 7,
    working_hours_start: int = 9,
    working_hours_end: int = 18,
    include_weekends: bool = False,
) -> dict:
    """Find common free time slots between attendees (privacy-preserving)."""
    start = datetime.now(timezone.utc)
    end = start + timedelta(days=days_ahead)

    try:
        freebusy = get_freebusy(attendee_emails, start, end)
        busy_by_person = parse_busy_slots(freebusy)
        common_slots = find_common_free_slots(
            busy_by_person,
            search_start=start,
            search_end=end,
            duration_minutes=duration_minutes,
            working_hours=(working_hours_start, working_hours_end),
            include_weekends=include_weekends,
        )
        formatted = [
            {
                "day": s.strftime("%A %d %B %Y"),
                "start_time": s.strftime("%H:%M"),
                "end_time": e.strftime("%H:%M"),
                "duration_hours": round((e - s).total_seconds() / 3600, 1),
            }
            for s, e in common_slots[:10]
        ]
        return {
            "success": True,
            "attendees": attendee_emails,
            "available_slots": formatted,
            "total_slots_found": len(common_slots),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


SYSTEM_PROMPT = """You are an executive scheduling assistant.

Your role: help the user find common free time slots between multiple people,
using the find_meeting_slots tool. You never see event details, only free/busy.

When asked to find a slot:
1. Use the list of authenticated emails provided in the user's message
2. Identify the duration (default 60 min if not specified)
3. Identify time constraints:
   - "tomorrow" -> days_ahead=1
   - "this week" -> days_ahead=7
   - "next week" -> days_ahead=14
   - "this month" -> days_ahead=30
   - "morning" -> working_hours_start=9, working_hours_end=12
   - "afternoon" -> working_hours_start=13, working_hours_end=18
   - "evening" -> working_hours_start=16, working_hours_end=20
   - "weekend" -> include_weekends=True
4. Call find_meeting_slots with the right parameters
5. Present the 3-5 best slots clearly, in a clean structured format

Be concise, professional, executive-tone. Respond in the user's language.
Format slots as a clean bulleted list with day and time range in bold.
"""


# ============================================================
# Session state
# ============================================================

if "chat" not in st.session_state:
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=SYSTEM_PROMPT,
        tools=[find_meeting_slots],
    )
    st.session_state.chat = model.start_chat(enable_automatic_function_calling=True)
    st.session_state.messages = []


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown('<div class="brand-line-small"></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-label">Participants</div>', unsafe_allow_html=True)
    
    authenticated = list_authenticated_users()

    if authenticated:
        st.markdown(
            f'<div class="status-badge"><span class="status-dot"></span>'
            f'{len(authenticated)} Connected</div>',
            unsafe_allow_html=True,
        )
        for email in authenticated:
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(
                    f'<div class="participant-card">{email}</div>',
                    unsafe_allow_html=True,
                )
            with col2:
                if st.button("×", key=f"remove_{email}", help="Disconnect"):
                    from calendar_client import _token_path
                    token_file = _token_path(email)
                    if os.path.exists(token_file):
                        os.remove(token_file)
                    st.rerun()
    else:
        st.markdown(
            '<div class="participant-card-empty">No participants connected</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown('<div class="section-label">Add Participant</div>', unsafe_allow_html=True)

    new_email = st.text_input(
        "Email",
        placeholder="name@domain.com",
        key="new_email_input",
        label_visibility="collapsed",
    )

    if st.button("Authenticate via Google", type="primary", use_container_width=True):
        if not new_email:
            st.warning("Email required")
        elif "@" not in new_email:
            st.warning("Invalid email format")
        else:
            with st.spinner("Opening browser..."):
                try:
                    authenticate_user(new_email)
                    st.success(f"Connected: {new_email}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Authentication failed: {e}")

    if authenticated:
        if st.button("Clear conversation", type="secondary", use_container_width=True):
            model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                system_instruction=SYSTEM_PROMPT,
                tools=[find_meeting_slots],
            )
            st.session_state.chat = model.start_chat(enable_automatic_function_calling=True)
            st.session_state.messages = []
            st.rerun()

    st.markdown("---")

    st.markdown(
        """
        <div class="privacy-note">
            <span class="privacy-note-title">Privacy by Design</span>
            This application uses Google Calendar's freebusy endpoint, 
            which returns only busy/free time ranges. Event titles, 
            attendees, locations, and descriptions are never exposed. 
            Privacy is enforced at the infrastructure level by Google's API.
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# MAIN
# ============================================================

st.markdown('<div class="brand-line"></div>', unsafe_allow_html=True)
st.markdown("# Smart Scheduler")
st.markdown(
    '<div class="tagline">An AI-powered scheduling agent that finds common '
    'availability across multiple calendars without exposing personal schedule details.</div>',
    unsafe_allow_html=True,
)

st.markdown("---")

if not authenticated:
    st.markdown(
        """
        <div class="empty-state">
            <div class="empty-state-icon">01</div>
            <div class="empty-state-title">No active session</div>
            <div class="empty-state-text">
                Add at least two participants in the sidebar to begin. 
                Each participant authenticates with their own Google account.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f'<div class="section-label">Active Session · {len(authenticated)} Participants</div>',
        unsafe_allow_html=True,
    )

    if not st.session_state.messages:
        st.markdown(
            """
            <div style="color: #666666; font-size: 0.9rem; padding: 1rem 0;">
                Try asking: "Find 1 hour this week between everyone" or 
                "30 minutes tomorrow morning"
            </div>
            """,
            unsafe_allow_html=True,
        )

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Describe the meeting you want to schedule..."):
        full_prompt = (
            f"Authenticated participants available: {authenticated}\n\n"
            f"User request: {prompt}"
        )

        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing availability..."):
                try:
                    response = st.session_state.chat.send_message(full_prompt)
                    answer = response.text
                except Exception as e:
                    answer = f"Error: {e}"
            st.markdown(answer)

        st.session_state.messages.append({"role": "assistant", "content": answer})