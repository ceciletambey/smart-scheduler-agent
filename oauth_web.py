"""
Web OAuth flow with room support.
The room_id is carried through OAuth via the 'state' parameter.
"""

import os
import json
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials


SCOPES = [
    "https://www.googleapis.com/auth/calendar.freebusy",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]


def _get_client_config() -> dict:
    """Load OAuth client config from Streamlit secrets or local file."""
    try:
        import streamlit as st
        if "google_oauth" in st.secrets:
            return {
                "web": {
                    "client_id": st.secrets["google_oauth"]["client_id"],
                    "client_secret": st.secrets["google_oauth"]["client_secret"],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [st.secrets["google_oauth"]["redirect_uri"]],
                }
            }
    except Exception:
        pass
    with open("client_secret_web.json") as f:
        return json.load(f)


def get_redirect_uri() -> str:
    """Get the correct redirect URI (local or deployed)."""
    try:
        import streamlit as st
        if "google_oauth" in st.secrets:
            return st.secrets["google_oauth"]["redirect_uri"]
    except Exception:
        pass
    return "http://localhost:8501"


def build_flow() -> Flow:
    """Create an OAuth Flow object (PKCE disabled for Streamlit)."""
    config = _get_client_config()
    return Flow.from_client_config(
        config,
        scopes=SCOPES,
        redirect_uri=get_redirect_uri(),
        autogenerate_code_verifier=False,
    )


def get_authorization_url(room_id: str) -> str:
    """Generate the Google authorization URL, embedding the room_id in state."""
    flow = build_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=room_id,  # carry the room through the flow
    )
    return auth_url


def exchange_code_for_credentials(code: str) -> Credentials:
    """Exchange the authorization code for credentials."""
    flow = build_flow()
    flow.fetch_token(code=code)
    return flow.credentials


def get_user_email_from_credentials(creds: Credentials) -> str:
    """Fetch the authenticated user's email."""
    from googleapiclient.discovery import build
    service = build("oauth2", "v2", credentials=creds)
    info = service.userinfo().get().execute()
    return info.get("email", "unknown")