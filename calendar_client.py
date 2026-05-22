"""
Calendar client module.
Multi-user OAuth: each Google account has its own token, stored in tokens/.
Supports free/busy queries (privacy-preserving) and event creation with Google Meet.
"""

import os
import re
from datetime import datetime, timedelta, timezone
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


# Scopes: read free/busy AND create/manage events
SCOPES = [
    "https://www.googleapis.com/auth/calendar.freebusy",
    "https://www.googleapis.com/auth/calendar.events",
]

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
    Authenticate a specific user via OAuth and store their token + email.
    """
    token_path = _token_path(email)
    creds = None

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print(f"\n>>> Please log in with: {email} <<<\n")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # Store the token AND the real email alongside it
        import json
        token_data = json.loads(creds.to_json())
        token_data["_email"] = email  # store the real email
        with open(token_path, "w") as token:
            json.dump(token_data, token)

    return creds


def get_calendar_service_for_user(email: str):
    """Get a Google Calendar service authenticated as a specific user."""
    creds = authenticate_user(email)
    return build("calendar", "v3", credentials=creds)


def get_freebusy(emails: list[str], start_time: datetime, end_time: datetime) -> dict:
    """
    Query free/busy data for multiple users.

    Each user is queried using THEIR OWN credentials, so the app only sees
    busy/free ranges, never event details. Privacy-preserving by design.

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


def create_event(
    organizer_email: str,
    attendee_emails: list[str],
    title: str,
    start_iso: str,
    duration_minutes: int = 60,
    add_google_meet: bool = True,
) -> dict:
    """
    Create a calendar event on the organizer's calendar and invite attendees.
    Optionally generates a Google Meet video link automatically.

    Args:
        organizer_email: email of the person creating the event
        attendee_emails: list of emails to invite
        title: event title
        start_iso: ISO format start datetime, e.g. "2026-05-26T14:00:00"
        duration_minutes: event duration (default 60)
        add_google_meet: whether to attach a Google Meet link (default True)

    Returns:
        dict with success status, event link, and meet link
    """
    try:
        service = get_calendar_service_for_user(organizer_email)

        start = datetime.fromisoformat(start_iso)
        end = start + timedelta(minutes=duration_minutes)

        event_body = {
            "summary": title,
            "start": {"dateTime": start.isoformat(), "timeZone": "Europe/Madrid"},
            "end": {"dateTime": end.isoformat(), "timeZone": "Europe/Madrid"},
            "attendees": [{"email": e} for e in attendee_emails],
        }

        conference_version = 0
        if add_google_meet:
            event_body["conferenceData"] = {
                "createRequest": {
                    "requestId": f"meet-{int(start.timestamp())}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            }
            conference_version = 1

        created = service.events().insert(
            calendarId="primary",
            body=event_body,
            conferenceDataVersion=conference_version,
            sendUpdates="all",
        ).execute()

        return {
            "success": True,
            "title": title,
            "event_link": created.get("htmlLink", ""),
            "meet_link": created.get("hangoutLink", "No video link generated"),
            "attendees_invited": attendee_emails,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_authenticated_users() -> list[str]:
    """List all users who have an existing token, reading the real email from each file."""
    if not os.path.exists(TOKENS_DIR):
        return []
    import json
    emails = []
    for filename in os.listdir(TOKENS_DIR):
        if filename.endswith(".json"):
            try:
                with open(os.path.join(TOKENS_DIR, filename)) as f:
                    data = json.load(f)
                real_email = data.get("_email")
                if real_email:
                    emails.append(real_email)
            except Exception:
                pass
    return emails


if __name__ == "__main__":
    start = datetime.now(timezone.utc)
    end = start + timedelta(days=14)

    emails_to_test = [
        "tambeycecile@gmail.com",
        "cecile.tambey@student.ie.edu",
    ]

    print(f"Fetching busy slots for {len(emails_to_test)} users...\n")
    busy_data = get_freebusy(emails_to_test, start, end)

    for email, data in busy_data.items():
        print(f"=== {email} ===")
        for slot in data.get("busy", []):
            print(f"  BUSY: {slot['start']} -> {slot['end']}")
        for err in data.get("errors", []):
            print(f"  ERROR: {err}")
        print()