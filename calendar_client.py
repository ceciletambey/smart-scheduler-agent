"""
Calendar client — room-aware version.
Loads member credentials from Supabase (per room) and queries free/busy
or creates events using each member's own OAuth token.
"""

from datetime import datetime, timedelta
from googleapiclient.discovery import build

from rooms import get_room_members, get_member_credentials


def get_freebusy(room_id: str, start_time: datetime, end_time: datetime) -> dict:
    """
    Query free/busy for all members of a room, each using their own credentials.
    Privacy-preserving: only busy/free ranges, never event details.
    """
    emails = get_room_members(room_id)
    result = {}

    for email in emails:
        try:
            creds = get_member_credentials(room_id, email)
            service = build("calendar", "v3", credentials=creds)
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
    room_id: str,
    organizer_email: str,
    attendee_emails: list[str],
    title: str,
    start_iso: str,
    duration_minutes: int = 60,
    add_google_meet: bool = True,
) -> dict:
    """Create an event on the organizer's calendar with a Google Meet link."""
    try:
        creds = get_member_credentials(room_id, organizer_email)
        service = build("calendar", "v3", credentials=creds)

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
            "meet_link": created.get("hangoutLink", "No video link"),
            "attendees_invited": attendee_emails,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}