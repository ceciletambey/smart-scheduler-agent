"""
Calendar client module.
Multi-user OAuth: each Google account has its own token, stored in tokens/.
Privacy-preserving: only queries the freebusy endpoint, never event details.
"""

import os
import re
from datetime import datetime, timedelta, timezone
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


# Only request the minimal scope needed: read free/busy data
SCOPES = ["https://www.googleapis.com/auth/calendar.freebusy"]

CREDENTIALS_FILE = "credentials.json"
TOKENS_DIR = "tokens"


def _email_to_filename(email: str) -> str:
    """Convert an email to a safe filename. e.g. 'a@b.com' -> 'a_at_b_com.json'"""
    safe = re.sub(r"[^a-zA-Z0-9]", "_", email)
    return f"{safe}.json"


def _token_path(email: str) -> str:
    """Get the path where the token for this email is stored."""
    os.makedirs(TOKENS_DIR, exist_ok=True)
    return os.path.join(TOKENS_DIR, _email_to_filename(email))


def authenticate_user(email: str) -> Credentials:
    """
    Authenticate a specific user via OAuth and store their token.

    On first call for a given email, opens a browser window for that user to log in.
    On subsequent calls, reuses the cached token.

    Args:
        email: the Gmail address of the user to authenticate

    Returns:
        Credentials object for this user
    """
    token_path = _token_path(email)
    creds = None

    # Load existing token if available
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # If no valid credentials, launch OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print(f"\n>>> Please log in with: {email} <<<\n")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_path, "w") as token:
            token.write(creds.to_json())

    return creds


def get_calendar_service_for_user(email: str):
    """Get a Google Calendar service authenticated as a specific user."""
    creds = authenticate_user(email)
    return build("calendar", "v3", credentials=creds)


def get_freebusy(emails: list[str], start_time: datetime, end_time: datetime) -> dict:
    """
    Query free/busy data for multiple users.

    Each user must have authenticated at least once (their token is in tokens/).
    We use the FIRST authenticated user's credentials to make the query,
    since the freebusy endpoint can query any calendar the user has access to.

    For true multi-user support where each user only exposes their own freebusy,
    we query each user's calendar using their own credentials.

    Args:
        emails: list of Google email addresses to query
        start_time: start of the search window (UTC)
        end_time: end of the search window (UTC)

    Returns:
        dict mapping each email to its busy slots
    """
    result = {}

    for email in emails:
        try:
            # Use THIS user's own credentials to query THEIR OWN freebusy
            service = get_calendar_service_for_user(email)

            body = {
                "timeMin": start_time.isoformat().replace("+00:00", "Z"),
                "timeMax": end_time.isoformat().replace("+00:00", "Z"),
                "items": [{"id": email}],
            }
            response = service.freebusy().query(body=body).execute()
            result[email] = response["calendars"][email]
        except Exception as e:
            result[email] = {"busy": [], "errors": [{"reason": str(e)}]}

    return result


def list_authenticated_users() -> list[str]:
    """List all users who have an existing token."""
    if not os.path.exists(TOKENS_DIR):
        return []
    emails = []
    for filename in os.listdir(TOKENS_DIR):
        if filename.endswith(".json"):
            # Reverse the filename -> email transformation
            # This is approximate, but works for display purposes
            name = filename.replace(".json", "")
            # Try to reconstruct: a_at_b_com -> a@b.com
            if "_at_" in name:
                local, _, domain = name.partition("_at_")
                domain = domain.replace("_", ".")
                emails.append(f"{local}@{domain}")
            else:
                emails.append(name)
    return emails


if __name__ == "__main__":
    # Test: authenticate the two accounts and fetch their freebusy
    start = datetime.now(timezone.utc)
    end = start + timedelta(days=14)

    emails_to_test = [
        "tambeycecile@gmail.com",
        "cecile.tambey@student.ie.edu",
    ]

    print(f"Fetching busy slots for {len(emails_to_test)} users...")
    print(f"Time range: next 14 days\n")

    busy_data = get_freebusy(emails_to_test, start, end)

    for email, data in busy_data.items():
        print(f"=== {email} ===")
        busy = data.get("busy", [])
        if not busy:
            print("  No busy slots.")
        for slot in busy:
            print(f"  BUSY: {slot['start']} -> {slot['end']}")
        for err in data.get("errors", []):
            print(f"  ERROR: {err}")
        print()