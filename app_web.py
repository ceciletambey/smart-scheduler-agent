"""
Smart Scheduler - Web app with rooms + per-account room history.
Access control (Option B): you must sign in with Google before entering a room.
Each room is a team where members find common availability privately.
"""

import os
from datetime import datetime, timedelta, timezone
import pytz
import streamlit as st
import google.generativeai as genai

from oauth_web import (
    get_authorization_url,
    exchange_code_for_credentials,
    get_user_email_from_credentials,
)
from rooms import (
    create_room,
    room_exists,
    get_room_name,
    add_member,
    get_room_members,
    remove_member,
    get_rooms_for_email,
)
from calendar_client import get_freebusy, create_event
from scheduler import parse_busy_slots, find_common_free_slots


# ============================================================
# Config
# ============================================================

from dotenv import load_dotenv
load_dotenv()
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_KEY:
    try:
        GEMINI_KEY = st.secrets["GEMINI_API_KEY"]
    except Exception:
        GEMINI_KEY = None

genai.configure(api_key=GEMINI_KEY)
LOCAL_TZ = pytz.timezone("Europe/Madrid")

st.set_page_config(page_title="Smart Scheduler", layout="wide", initial_sidebar_state="expanded")


# ============================================================
# CSS
# ============================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap');
html, body, [class*="css"], .stApp, .main { font-family: 'Inter', sans-serif !important;
    background-color: #000 !important; color: #fff !important; }
.stApp { background: linear-gradient(180deg, #000 0%, #0a0a0a 100%); }
[data-testid="stAppViewContainer"], [data-testid="stMain"], .main .block-container {
    background-color: transparent !important; }

/* Hide clutter */
#MainMenu, footer, .stDeployButton, [data-testid="stToolbar"] { display: none !important; }
[data-testid="stHeader"] { background: transparent !important; }

/* Lock the sidebar always open and make it scrollable */
section[data-testid="stSidebar"] {
    transform: none !important; visibility: visible !important;
    min-width: 300px !important; width: 300px !important; margin-left: 0 !important; }
section[data-testid="stSidebar"][aria-expanded="false"] {
    transform: none !important; margin-left: 0 !important; }
section[data-testid="stSidebar"] > div {
    padding: 1.5rem !important; overflow-y: auto !important; max-height: 100vh !important; }
[data-testid="stSidebarCollapseButton"] { display: none !important; }

h1 { font-size: 3.5rem !important; font-weight: 800 !important; color: #fff !important;
    letter-spacing: -0.04em !important; line-height: 1 !important; margin: 0 !important; }
h2, h3 { color: #fff !important; font-weight: 700 !important; }
p, span, div, label { color: #e5e5e5 !important; }
.main .block-container { padding: 3rem 4rem !important; max-width: 1400px !important; }
section[data-testid="stSidebar"] { background-color: #050505 !important; border-right: 1px solid #1f1f1f !important; }
.brand-line { height: 3px; width: 48px; background: linear-gradient(90deg, #ff0055, #ff3377);
    margin-bottom: 1.5rem; border-radius: 2px; }
.brand-line-small { height: 2px; width: 32px; background: #ff0055; margin-bottom: 1rem; border-radius: 1px; }
.section-label { color: #ff0055 !important; font-size: 0.7rem !important; text-transform: uppercase !important;
    letter-spacing: 0.2em !important; font-weight: 700 !important; margin-bottom: 1rem !important;
    font-family: 'JetBrains Mono', monospace !important; }
.tagline { color: #a0a0a0 !important; font-size: 1.125rem !important; line-height: 1.6 !important;
    margin: 1.5rem 0 0 0 !important; max-width: 720px !important; }
.participant-card { background: linear-gradient(135deg, #141414, #0f0f0f); border: 1px solid #2a2a2a;
    border-left: 3px solid #ff0055; padding: 14px 18px; margin-bottom: 10px; border-radius: 6px;
    font-size: 0.875rem; color: #fff !important; font-family: 'JetBrains Mono', monospace; word-break: break-all; }
.participant-card-empty { background-color: #0a0a0a; border: 1px dashed #2a2a2a; padding: 24px;
    border-radius: 6px; color: #666 !important; text-align: center; font-size: 0.875rem; }
.room-code { font-family: 'JetBrains Mono', monospace; font-size: 1.5rem; font-weight: 700;
    color: #ff0055 !important; letter-spacing: 0.1em; background: #0f0f0f; border: 1px solid #2a2a2a;
    border-radius: 8px; padding: 1rem; text-align: center; margin: 1rem 0; }
.stButton > button { background: linear-gradient(135deg, #ff0055, #ff3377) !important; color: #fff !important;
    border: none !important; border-radius: 6px !important; font-weight: 600 !important;
    padding: 0.65rem 1rem !important; box-shadow: 0 2px 12px rgba(255,0,85,0.2) !important; }
.stButton > button:hover { transform: translateY(-1px) !important; }
.stForm { border: none !important; padding: 0 !important; }
.stTextInput > div > div > input { background-color: #0f0f0f !important; color: #fff !important;
    border: 1px solid #2a2a2a !important; border-radius: 6px !important; font-family: 'JetBrains Mono', monospace !important; }
[data-testid="stChatMessage"] { background-color: #0a0a0a !important; border: 1px solid #1f1f1f !important;
    border-radius: 8px !important; padding: 1.25rem 1.5rem !important; }
[data-testid="stChatMessage"] strong { color: #ff3377 !important; }
[data-testid="stChatMessage"] a { color: #ff3377 !important; }
.stAlert { background-color: #0f0f0f !important; border-left: 3px solid #ff0055 !important; color: #fff !important; }
hr { border-color: #1f1f1f !important; }
.connect-btn a { display: inline-block; background: linear-gradient(135deg, #ff0055, #ff3377);
    color: #fff !important; padding: 0.75rem 1.5rem; border-radius: 8px; text-decoration: none !important;
    font-weight: 600; width: 100%; text-align: center; box-sizing: border-box; }
.connect-btn-big a { display: inline-block; background: linear-gradient(135deg, #ff0055, #ff3377);
    color: #fff !important; padding: 1rem 2rem; border-radius: 10px; text-decoration: none !important;
    font-weight: 700; font-size: 1.05rem; text-align: center; box-shadow: 0 4px 20px rgba(255,0,85,0.3); }
.privacy-note { background: #0a0a0a; border: 1px solid #1f1f1f; padding: 1.25rem; border-radius: 8px;
    color: #888 !important; font-size: 0.8rem; line-height: 1.7; margin-top: 1rem; }
.privacy-note-title { color: #ff0055 !important; text-transform: uppercase; letter-spacing: 0.15em;
    font-size: 0.7rem; font-weight: 700; display: block; margin-bottom: 0.75rem; font-family: 'JetBrains Mono', monospace; }
section[data-testid="stSidebar"] > div { overflow-y: auto !important; max-height: 100vh !important; }
[data-testid="stChatMessage"] { margin-bottom: 0.75rem !important; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# Session state
# ============================================================

if "room_id" not in st.session_state:
    st.session_state.room_id = None
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_room" not in st.session_state:
    st.session_state.pending_room = None  # room the user wants to enter but must sign in first


# ============================================================
# Read room from URL (store as pending until authenticated)
# ============================================================

url_room = st.query_params.get("room")
if url_room and room_exists(url_room):
    st.session_state.pending_room = url_room


# ============================================================
# Handle OAuth redirect
# ============================================================

if "code" in st.query_params:
    code = st.query_params["code"]
    state_room = st.query_params.get("state")
    try:
        creds = exchange_code_for_credentials(code)
        email = get_user_email_from_credentials(creds)
        st.session_state.current_user = email
        if state_room and room_exists(state_room):
            add_member(state_room, email, creds)
            st.session_state.room_id = state_room
            st.session_state.pending_room = None
        st.query_params.clear()
        if state_room:
            st.query_params["room"] = state_room
        st.rerun()
    except Exception as e:
        st.error(f"Authentication error: {e}")
        st.query_params.clear()


# ============================================================
# Tools
# ============================================================

def find_meeting_slots(duration_minutes: int = 60, days_ahead: int = 7,
                       working_hours_start: int = 9, working_hours_end: int = 18,
                       include_weekends: bool = False) -> dict:
    """Find common free slots between all members of the current room."""
    room_id = st.session_state.room_id
    now = datetime.now(timezone.utc)
    minutes_to_add = (15 - now.minute % 15) % 15
    start = now.replace(second=0, microsecond=0) + timedelta(minutes=minutes_to_add)
    end = start + timedelta(days=days_ahead)
    try:
        freebusy = get_freebusy(room_id, start, end)
        busy_by_person = parse_busy_slots(freebusy)
        common = find_common_free_slots(busy_by_person, start, end, duration_minutes,
                                        (working_hours_start, working_hours_end), include_weekends, "Europe/Madrid")
        formatted = [{
            "day": s.astimezone(LOCAL_TZ).strftime("%A %d %B %Y"),
            "start_time": s.astimezone(LOCAL_TZ).strftime("%H:%M"),
            "end_time": e.astimezone(LOCAL_TZ).strftime("%H:%M"),
            "iso_start": s.astimezone(LOCAL_TZ).strftime("%Y-%m-%dT%H:%M:%S"),
        } for s, e in common[:10]]
        return {"success": True, "available_slots": formatted, "total_slots_found": len(common),
                "members": get_room_members(room_id), "timezone": "Europe/Madrid (CET)"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def schedule_meeting(organizer_email: str, attendee_emails: list[str], title: str,
                     start_iso: str, duration_minutes: int = 60) -> dict:
    """Create a meeting with a Google Meet link and invite attendees."""
    return create_event(st.session_state.room_id, organizer_email, attendee_emails,
                        title, start_iso, duration_minutes, True)


SYSTEM_PROMPT = """You are an executive scheduling assistant for a team room.

Tools:
1. find_meeting_slots - finds common free time among room members (free/busy only)
2. schedule_meeting - creates an event, invites attendees, adds Google Meet

The room members are provided in the user's message. Use them as attendees.
For schedule_meeting, organizer_email = first member unless told otherwise,
and use iso_start from the chosen slot.

TIME MAPPING: tomorrow->1, this week->7, next week->14, this month->30 days.
morning->9-12, afternoon->13-18, evening->16-20. weekend->include_weekends=True.

After booking, share the Google Meet link. Be concise, executive-tone.
Times are Central European Time. Format slots as a bulleted list with day and time in bold.
"""


def build_chat():
    model = genai.GenerativeModel(model_name="gemini-2.5-flash",
                                  system_instruction=SYSTEM_PROMPT,
                                  tools=[find_meeting_slots, schedule_meeting])
    return model.start_chat(enable_automatic_function_calling=True)


if "chat" not in st.session_state:
    st.session_state.chat = build_chat()


# ============================================================
# GATE: must be signed in to do anything (Option B)
# ============================================================

def render_landing():
    """Landing page: sign in, then create or join a room."""
    st.markdown('<div class="brand-line"></div>', unsafe_allow_html=True)
    st.markdown("# Smart Scheduler")
    st.markdown('<div class="tagline">Create a team room, invite participants, and let AI find '
                'common availability across calendars - without exposing schedule details.</div>',
                unsafe_allow_html=True)
    st.markdown("---")

    # If a room is pending (from a shared link), prompt to sign in to join it
    if st.session_state.pending_room:
        rid = st.session_state.pending_room
        st.markdown('<div class="section-label">You were invited to a room</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="room-code">{rid}</div>', unsafe_allow_html=True)
        st.caption(f"{get_room_name(rid)} - Sign in with Google to join this room.")
        auth_url = get_authorization_url(rid)
        st.markdown(f'<div class="connect-btn-big"><a href="{auth_url}" target="_self">'
                    f'Sign in with Google to join</a></div>', unsafe_allow_html=True)
        st.stop()

    # Otherwise: must sign in before creating/joining
    st.markdown('<div class="section-label">Sign in to start</div>', unsafe_allow_html=True)
    st.caption("You must sign in with your Google account to create or join a room. "
               "This is how the agent reads your availability (free/busy only).")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="section-label">Create a Room</div>', unsafe_allow_html=True)
        room_name = st.text_input("Room name", placeholder="e.g. Capstone Team", key="create_name")
        if st.button("Create Room & Sign in", use_container_width=True):
            code = create_room(room_name or "Untitled")
            # send straight into OAuth for this new room
            auth_url = get_authorization_url(code)
            st.markdown(f'<meta http-equiv="refresh" content="0;url={auth_url}">', unsafe_allow_html=True)
            st.markdown(f'<div class="connect-btn-big"><a href="{auth_url}" target="_self">'
                        f'Continue to Google sign-in</a></div>', unsafe_allow_html=True)
            st.stop()

    with col2:
        st.markdown('<div class="section-label">Join a Room</div>', unsafe_allow_html=True)
        join_code = st.text_input("Room code", placeholder="TEAM-XXXX", key="join_code")
        if st.button("Join Room & Sign in", use_container_width=True):
            jc = join_code.strip().upper()
            if room_exists(jc):
                auth_url = get_authorization_url(jc)
                st.markdown(f'<meta http-equiv="refresh" content="0;url={auth_url}">', unsafe_allow_html=True)
                st.markdown(f'<div class="connect-btn-big"><a href="{auth_url}" target="_self">'
                            f'Continue to Google sign-in</a></div>', unsafe_allow_html=True)
                st.stop()
            else:
                st.error("Room not found. Check the code.")
    st.stop()


# If the user is not signed in OR not in a room, show the landing gate
if not st.session_state.current_user or not st.session_state.room_id:
    render_landing()


# ============================================================
# INSIDE A ROOM (only reachable when signed in)
# ============================================================

room_id = st.session_state.room_id
members = get_room_members(room_id)

with st.sidebar:
    st.markdown('<div class="brand-line-small"></div>', unsafe_allow_html=True)

    st.markdown('<div class="section-label">Your Rooms</div>', unsafe_allow_html=True)
    st.caption(f"Signed in as {st.session_state.current_user}")
    my_rooms = get_rooms_for_email(st.session_state.current_user)
    for r in my_rooms:
        label = f"{r['id']} - {r.get('name') or 'Untitled'}"
        if st.button(label, key=f"switch_{r['id']}", use_container_width=True):
            st.session_state.room_id = r["id"]
            st.session_state.messages = []
            st.query_params["room"] = r["id"]
            st.rerun()
    st.markdown("---")

    st.markdown('<div class="section-label">Current Room</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="room-code">{room_id}</div>', unsafe_allow_html=True)
    st.caption(f"{get_room_name(room_id)} - Share this code to invite others")

    st.markdown('<div class="section-label">Members</div>', unsafe_allow_html=True)
    if members:
        for email in members:
            c1, c2 = st.columns([5, 1])
            with c1:
                st.markdown(f'<div class="participant-card">{email}</div>', unsafe_allow_html=True)
            with c2:
                if st.button("x", key=f"rm_{email}"):
                    remove_member(room_id, email)
                    st.rerun()
    else:
        st.markdown('<div class="participant-card-empty">No members yet</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="section-label">Invite Others</div>', unsafe_allow_html=True)
    auth_url = get_authorization_url(room_id)
    st.markdown(f'<div class="connect-btn"><a href="{auth_url}" target="_self">Re-connect Google</a></div>',
                unsafe_allow_html=True)
    st.caption("Share the room code above. Others sign in with Google to join.")

    st.markdown("---")
    cA, cB = st.columns(2)
    with cA:
        if st.button("New room", use_container_width=True):
            st.session_state.room_id = None
            st.session_state.messages = []
            st.session_state.pending_room = None
            st.query_params.clear()
            st.rerun()
    with cB:
        if st.button("Leave", use_container_width=True):
            st.session_state.room_id = None
            st.session_state.messages = []
            st.session_state.pending_room = None
            st.query_params.clear()
            st.rerun()

    st.markdown("""
        <div class="privacy-note">
            <span class="privacy-note-title">Privacy by Design</span>
            We only request the freebusy scope to read availability - never event
            details. Each member authenticates with their own Google account.
        </div>
    """, unsafe_allow_html=True)


# Main area
st.markdown('<div class="brand-line"></div>', unsafe_allow_html=True)
st.markdown("# Smart Scheduler")
st.markdown(f'<div class="tagline">Room <strong>{room_id}</strong> - {len(members)} member(s) connected. '
            'Ask the agent to find a time that works for everyone.</div>', unsafe_allow_html=True)
st.markdown("---")

# Input form FIRST (stays at the top, doesn't move when chat grows)
st.markdown('<div class="section-label">Ask the Scheduler</div>', unsafe_allow_html=True)
with st.form(key="agent_form", clear_on_submit=True):
    prompt = st.text_input("Your request", placeholder="e.g. find 30 minutes this week",
                           label_visibility="collapsed")
    submitted = st.form_submit_button("Send")
if submitted and prompt:
    full_prompt = f"Room members: {members}\n\nUser request: {prompt}"
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.spinner("Analyzing calendars..."):
        try:
            answer = st.session_state.chat.send_message(full_prompt).text
        except Exception as e:
            answer = f"Error: {e}"
    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.rerun()

st.markdown("---")

# Chat history (newest at the bottom, below the fixed input)
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
