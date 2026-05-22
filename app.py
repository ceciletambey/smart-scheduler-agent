"""
Smart Scheduler Web App.
Premium consulting-style interface for the multi-user scheduling agent.
Supports finding common availability AND booking meetings with Google Meet.
"""

import os
from datetime import datetime, timedelta, timezone
import pytz
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv

from calendar_client import (
    authenticate_user,
    get_freebusy,
    list_authenticated_users,
    create_event,
    _token_path,
)
from scheduler import parse_busy_slots, find_common_free_slots


load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

LOCAL_TZ = pytz.timezone("Europe/Madrid")


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

html, body, [class*="css"], .stApp, .main {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background-color: #000000 !important;
    color: #ffffff !important;
}

.stApp { background: linear-gradient(180deg, #000000 0%, #0a0a0a 100%); }

[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"],
[data-testid="stHeader"],
.main .block-container { background-color: transparent !important; }

#MainMenu, footer, header,
[data-testid="stHeader"],
[data-testid="stToolbar"],
.stDeployButton,
button[kind="header"] { display: none !important; }

h1 {
    font-size: 3.5rem !important;
    font-weight: 800 !important;
    color: #ffffff !important;
    letter-spacing: -0.04em !important;
    line-height: 1 !important;
    margin: 0 !important;
}

h2, h3, h4 { color: #ffffff !important; font-weight: 700 !important; letter-spacing: -0.02em !important; }
p, span, div, label { color: #e5e5e5 !important; }

.main .block-container { padding: 3rem 4rem !important; max-width: 1400px !important; }

section[data-testid="stSidebar"] {
    background-color: #050505 !important;
    border-right: 1px solid #1f1f1f !important;
}
section[data-testid="stSidebar"] > div { padding: 1.5rem !important; }

.brand-line {
    height: 3px; width: 48px;
    background: linear-gradient(90deg, #ff0055 0%, #ff3377 100%);
    margin-bottom: 1.5rem; border-radius: 2px;
}
.brand-line-small {
    height: 2px; width: 32px; background: #ff0055;
    margin-bottom: 1rem; border-radius: 1px;
}

.section-label {
    color: #ff0055 !important; font-size: 0.7rem !important;
    text-transform: uppercase !important; letter-spacing: 0.2em !important;
    font-weight: 700 !important; margin-bottom: 1rem !important;
    font-family: 'JetBrains Mono', monospace !important;
}

.tagline {
    color: #a0a0a0 !important; font-size: 1.125rem !important;
    font-weight: 400 !important; line-height: 1.6 !important;
    margin: 1.5rem 0 0 0 !important; max-width: 720px !important;
}

.participant-card {
    background: linear-gradient(135deg, #141414 0%, #0f0f0f 100%);
    border: 1px solid #2a2a2a; border-left: 3px solid #ff0055;
    padding: 14px 18px; margin-bottom: 10px; border-radius: 6px;
    font-size: 0.875rem; color: #ffffff !important; font-weight: 500;
    font-family: 'JetBrains Mono', monospace; word-break: break-all;
    transition: all 0.2s ease;
}
.participant-card:hover { border-color: #ff0055; }

.participant-card-empty {
    background-color: #0a0a0a; border: 1px dashed #2a2a2a;
    padding: 24px; border-radius: 6px; color: #666666 !important;
    font-size: 0.875rem; text-align: center;
}

.stButton > button {
    background: linear-gradient(135deg, #ff0055 0%, #ff3377 100%) !important;
    color: #ffffff !important; border: none !important; border-radius: 6px !important;
    font-weight: 600 !important; font-size: 0.875rem !important;
    letter-spacing: 0.02em !important; padding: 0.75rem 1.25rem !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 2px 12px rgba(255, 0, 85, 0.25) !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 20px rgba(255, 0, 85, 0.4) !important;
}

button[kind="secondary"] {
    background: transparent !important; color: #666666 !important;
    border: 1px solid #2a2a2a !important; box-shadow: none !important;
}
button[kind="secondary"]:hover {
    border-color: #ff0055 !important; color: #ff0055 !important;
    background: rgba(255, 0, 85, 0.08) !important;
}

.stTextInput > div > div > input {
    background-color: #0f0f0f !important; color: #ffffff !important;
    border: 1px solid #2a2a2a !important; border-radius: 6px !important;
    padding: 0.75rem 1rem !important;
    font-family: 'JetBrains Mono', monospace !important; font-size: 0.875rem !important;
}
.stTextInput > div > div > input:focus {
    border-color: #ff0055 !important;
    box-shadow: 0 0 0 3px rgba(255, 0, 85, 0.1) !important;
}
.stTextInput > div > div > input::placeholder { color: #444444 !important; }

[data-testid="stBottomBlockContainer"],
[data-testid="stBottom"],
.stBottom,
section[data-testid="stChatInputContainer"] {
    background-color: #000000 !important; border-top: 1px solid #1f1f1f !important;
}
[data-testid="stChatInput"], .stChatInput {
    background-color: #000000 !important; padding: 1rem 0 !important;
}
[data-testid="stChatInput"] > div, .stChatInput > div {
    background-color: #0f0f0f !important; border: 1px solid #2a2a2a !important;
    border-radius: 8px !important;
}
[data-testid="stChatInput"] textarea, .stChatInput textarea {
    background-color: #0f0f0f !important; color: #ffffff !important;
    border: none !important; font-family: 'Inter', sans-serif !important;
    font-size: 0.95rem !important; padding: 0.875rem 1rem !important;
}
[data-testid="stChatInput"] textarea:focus { outline: none !important; box-shadow: none !important; }
[data-testid="stChatInput"] textarea::placeholder { color: #555555 !important; }
div[data-baseweb="textarea"] { background-color: #0f0f0f !important; border-radius: 8px !important; }
[data-testid="stChatInput"] button {
    background: linear-gradient(135deg, #ff0055 0%, #ff3377 100%) !important;
    border-radius: 6px !important; margin-right: 0.5rem !important;
}
[data-testid="stChatInput"] button svg { fill: #ffffff !important; }

[data-testid="stChatMessage"] {
    background-color: #0a0a0a !important; border: 1px solid #1f1f1f !important;
    border-radius: 8px !important; padding: 1.25rem 1.5rem !important;
    margin-bottom: 1rem !important;
}
[data-testid="stChatMessage"] p, [data-testid="stChatMessage"] li {
    color: #f0f0f0 !important; line-height: 1.7 !important;
}
[data-testid="stChatMessage"] strong { color: #ff3377 !important; font-weight: 600 !important; }
[data-testid="stChatMessage"] a { color: #ff3377 !important; }

.stAlert {
    background-color: #0f0f0f !important; border: 1px solid #2a2a2a !important;
    border-left: 3px solid #ff0055 !important; border-radius: 6px !important;
    color: #ffffff !important;
}
.stAlert p { color: #ffffff !important; }

hr { border-color: #1f1f1f !important; margin: 2.5rem 0 !important; }
section[data-testid="stSidebar"] hr { margin: 1.5rem 0 !important; }

.privacy-note {
    background: linear-gradient(135deg, #0a0a0a 0%, #050505 100%);
    border: 1px solid #1f1f1f; padding: 1.25rem; border-radius: 8px;
    color: #888888 !important; font-size: 0.8rem; line-height: 1.7; margin-top: 1rem;
}
.privacy-note-title {
    color: #ff0055 !important; text-transform: uppercase; letter-spacing: 0.15em;
    font-size: 0.7rem; font-weight: 700; display: block; margin-bottom: 0.75rem;
    font-family: 'JetBrains Mono', monospace;
}

.empty-state {
    text-align: center; padding: 6rem 2rem; color: #666666;
    border: 1px dashed #1f1f1f; border-radius: 12px; background: #050505; margin-top: 2rem;
}
.empty-state-icon {
    width: 64px; height: 64px; margin: 0 auto 1.5rem auto;
    border: 2px solid #2a2a2a; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    color: #ff0055; font-size: 1.5rem; font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
}
.empty-state-title {
    color: #ffffff !important; font-size: 1.5rem !important;
    font-weight: 700 !important; margin-bottom: 0.75rem !important;
}
.empty-state-text {
    color: #888888 !important; font-size: 1rem !important;
    max-width: 480px; margin: 0 auto; line-height: 1.6 !important;
}

.status-badge {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 6px 14px; background: rgba(255, 0, 85, 0.1);
    border: 1px solid rgba(255, 0, 85, 0.3); border-radius: 100px;
    color: #ff3377 !important; font-size: 0.75rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.1em;
    font-family: 'JetBrains Mono', monospace; margin-bottom: 1.5rem;
}
.status-dot {
    width: 6px; height: 6px; background: #ff0055; border-radius: 50%;
    animation: pulse 2s infinite;
}
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }

.stSpinner > div { border-top-color: #ff0055 !important; }

::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: #050505; }
::-webkit-scrollbar-thumb { background: #2a2a2a; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #ff0055; }

code {
    background-color: #1a1a1a !important; color: #ff3377 !important;
    padding: 0.2rem 0.4rem !important; border-radius: 4px !important;
    font-family: 'JetBrains Mono', monospace !important; font-size: 0.875rem !important;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ============================================================
# TOOLS
# ============================================================

def find_meeting_slots(
    attendee_emails: list[str],
    duration_minutes: int = 60,
    days_ahead: int = 7,
    working_hours_start: int = 9,
    working_hours_end: int = 18,
    include_weekends: bool = False,
) -> dict:
    """
    Find common free time slots where all attendees are available.
    Privacy-preserving: only uses free/busy data, never event details.

    Args:
        attendee_emails: list of participant emails
        duration_minutes: desired meeting duration (default 60)
        days_ahead: how many days ahead to search (default 7)
        working_hours_start: start hour in local time (default 9)
        working_hours_end: end hour in local time (default 18)
        include_weekends: include Saturday/Sunday (default False)
    """
# Round up to the next clean 15-minute mark so slots align to :00/:15/:30/:45
    now = datetime.now(timezone.utc)
    minutes_to_add = (15 - now.minute % 15) % 15
    start = now.replace(second=0, microsecond=0) + timedelta(minutes=minutes_to_add)
    if minutes_to_add == 0 and now.second > 0:
        start += timedelta(minutes=15)
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
            timezone_name="Europe/Madrid",
        )
        formatted = [
            {
                "day": s.astimezone(LOCAL_TZ).strftime("%A %d %B %Y"),
                "start_time": s.astimezone(LOCAL_TZ).strftime("%H:%M"),
                "end_time": e.astimezone(LOCAL_TZ).strftime("%H:%M"),
                "iso_start": s.astimezone(LOCAL_TZ).strftime("%Y-%m-%dT%H:%M:%S"),
                "duration_hours": round((e - s).total_seconds() / 3600, 1),
            }
            for s, e in common_slots[:10]
        ]
        return {
            "success": True,
            "attendees": attendee_emails,
            "available_slots": formatted,
            "total_slots_found": len(common_slots),
            "timezone": "Europe/Madrid (CET)",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def schedule_meeting(
    organizer_email: str,
    attendee_emails: list[str],
    title: str,
    start_iso: str,
    duration_minutes: int = 60,
) -> dict:
    """
    Create and schedule a meeting in the organizer's calendar, inviting all
    attendees and automatically adding a Google Meet video link.

    Use this AFTER find_meeting_slots, once the user confirms which slot they want.

    Args:
        organizer_email: email of the meeting organizer (usually first participant)
        attendee_emails: all participant emails to invite
        title: the meeting title
        start_iso: exact start time in ISO format, e.g. "2026-05-26T14:00:00"
        duration_minutes: meeting length in minutes (default 60)
    """
    return create_event(
        organizer_email=organizer_email,
        attendee_emails=attendee_emails,
        title=title,
        start_iso=start_iso,
        duration_minutes=duration_minutes,
        add_google_meet=True,
    )


SYSTEM_PROMPT = """You are an executive scheduling assistant.

You have two tools:
1. find_meeting_slots — finds common free time between participants (privacy-preserving, free/busy only)
2. schedule_meeting — creates a calendar event, invites attendees, and adds a Google Meet link

WORKFLOW:
- When the user wants to find availability, use find_meeting_slots
- When the user confirms a specific slot and wants to book it, use schedule_meeting
- Before scheduling, make sure you have: a chosen time slot, a title, and the participants
- If the title is missing, suggest a sensible default or ask
- The organizer_email is the first authenticated participant unless told otherwise
- For schedule_meeting, use the iso_start value from the slot the user selected

TIME CONSTRAINTS for find_meeting_slots:
- "tomorrow" -> days_ahead=1
- "this week" -> days_ahead=7
- "next week" -> days_ahead=14
- "this month" -> days_ahead=30
- "morning" -> working_hours_start=9, working_hours_end=12
- "afternoon" -> working_hours_start=13, working_hours_end=18
- "evening" -> working_hours_start=16, working_hours_end=20
- "weekend" -> include_weekends=True

After creating an event, always share the Google Meet link and confirm who was invited.

Be concise, professional, executive-tone. All times are Central European Time (Europe/Madrid).
Format slots as a clean bulleted list with day and time range in bold.
"""


def build_chat():
    """Create a fresh Gemini chat session with both tools."""
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=SYSTEM_PROMPT,
        tools=[find_meeting_slots, schedule_meeting],
    )
    return model.start_chat(enable_automatic_function_calling=True)


# ============================================================
# Session state
# ============================================================

if "chat" not in st.session_state:
    st.session_state.chat = build_chat()
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
            st.session_state.chat = build_chat()
            st.session_state.messages = []
            st.rerun()

    st.markdown("---")
    st.markdown(
        """
        <div class="privacy-note">
            <span class="privacy-note-title">Privacy by Design</span>
            Availability is read via Google Calendar's freebusy endpoint, 
            which exposes only busy/free ranges — never event titles, 
            attendees, or descriptions. Event creation uses scoped permissions 
            limited to the meetings this app books.
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
    'availability across multiple calendars and books meetings with video links — '
    'without exposing personal schedule details.</div>',
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
                Try: "Find 1 hour this week between everyone", then 
                "Book the Monday slot at 2pm, title Project Sync"
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
            with st.spinner("Analyzing..."):
                try:
                    response = st.session_state.chat.send_message(full_prompt)
                    answer = response.text
                except Exception as e:
                    answer = f"Error: {e}"
            st.markdown(answer)

        st.session_state.messages.append({"role": "assistant", "content": answer})