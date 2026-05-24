"""
Rooms module — manages teams/rooms and member tokens via Supabase.
Each room has a unique code; members join and store their OAuth token in it.
"""

import os
import json
import random
import string
from datetime import datetime, timezone
from google.oauth2.credentials import Credentials


def _get_supabase():
    """Create a Supabase client from env vars or Streamlit secrets."""
    url = None
    key = None
    try:
        import streamlit as st
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")
    except Exception:
        pass

    if not url or not key:
        from dotenv import load_dotenv
        load_dotenv()
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

    from supabase import create_client
    return create_client(url, key)


def generate_room_code() -> str:
    """Generate a short unique room code like TEAM-XK42."""
    chars = string.ascii_uppercase + string.digits
    suffix = "".join(random.choices(chars, k=4))
    return f"TEAM-{suffix}"


def create_room(name: str = "Untitled") -> str:
    """Create a new room and return its code."""
    sb = _get_supabase()
    # Generate a code that doesn't already exist
    for _ in range(10):
        code = generate_room_code()
        existing = sb.table("rooms").select("id").eq("id", code).execute()
        if not existing.data:
            sb.table("rooms").insert({"id": code, "name": name}).execute()
            return code
    raise RuntimeError("Could not generate a unique room code")


def room_exists(room_id: str) -> bool:
    """Check whether a room exists."""
    sb = _get_supabase()
    result = sb.table("rooms").select("id").eq("id", room_id).execute()
    return bool(result.data)


def get_room_name(room_id: str) -> str:
    """Get a room's display name."""
    sb = _get_supabase()
    result = sb.table("rooms").select("name").eq("id", room_id).execute()
    if result.data:
        return result.data[0].get("name", "Untitled")
    return "Unknown"


def add_member(room_id: str, email: str, creds: Credentials):
    """Add (or update) a member's OAuth token in a room."""
    sb = _get_supabase()
    token_json = creds.to_json()
    # Upsert: if the member already exists in this room, update their token
    sb.table("members").upsert(
        {"room_id": room_id, "email": email, "token_json": token_json},
        on_conflict="room_id,email",
    ).execute()


def get_room_members(room_id: str) -> list[str]:
    """Return the list of member emails in a room."""
    sb = _get_supabase()
    result = sb.table("members").select("email").eq("room_id", room_id).execute()
    return [row["email"] for row in result.data]


def get_member_credentials(room_id: str, email: str) -> Credentials:
    """Load a member's OAuth credentials from the room."""
    sb = _get_supabase()
    result = (
        sb.table("members")
        .select("token_json")
        .eq("room_id", room_id)
        .eq("email", email)
        .execute()
    )
    if not result.data:
        raise ValueError(f"No credentials found for {email} in room {room_id}")
    token_data = json.loads(result.data[0]["token_json"])
    scopes = token_data.get("scopes", [
        "https://www.googleapis.com/auth/calendar.freebusy",
        "https://www.googleapis.com/auth/calendar.events",
    ])
    return Credentials.from_authorized_user_info(token_data, scopes)


def remove_member(room_id: str, email: str):
    """Remove a member from a room."""
    sb = _get_supabase()
    sb.table("members").delete().eq("room_id", room_id).eq("email", email).execute()

def get_rooms_for_email(email: str) -> list[dict]:
    """Return all rooms a given email is a member of, with room names."""
    sb = _get_supabase()
    # Get all room_ids where this email is a member
    member_rows = sb.table("members").select("room_id").eq("email", email).execute()
    room_ids = [r["room_id"] for r in member_rows.data]
    if not room_ids:
        return []
    # Get the room details
    rooms = sb.table("rooms").select("id, name").in_("id", room_ids).execute()
    return rooms.data