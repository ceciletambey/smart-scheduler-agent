"""
Calendar client — room-aware version.
Loads member credentials from Supabase (per room) and queries busy times
or creates events using each member's own OAuth token.

Uses events.list() instead of the freebusy API so that subscribed calendars
(university courses, work calendars from other Workspace domains) are included.
The freebusy API silently returns empty busy arrays for those calendar IDs
because it can't cross Workspace domain boundaries, even though the user's
OAuth token can read those calendars directly.
"""

from datetime import datetime, timedelta
from googleapiclient.discovery import build

from rooms import get_room_members, get_member_credentials


def get_freebusy(room_id: str, start_time: datetime, end_time: datetime) -> dict:
    """
    Query busy times for all members across ALL their calendars, including
    subscribed calendars from other domains (university, work, etc.).
    """
    emails = get_room_members(room_id)
    result = {}

    time_min = start_time.isoformat().replace("+00:00", "Z")
    time_max = end_time.isoformat().replace("+00:00", "Z")

    for email in emails:
        try:
            creds = get_member_credentials(room_id, email)
            service = build("calendar", "v3", credentials=creds)

            cal_list = service.calendarList().list().execute()
            cal_items = cal_list.get("items", [])
            cal_ids = [
                c["id"] for c in cal_items
                if c.get("accessRole") in ("owner", "writer", "reader")
                and not c.get("hidden", False)
            ]
            if not cal_ids:
                cal_ids = [email]

            merged_busy = []
            for cid in cal_ids:
                try:
                    events_result = service.events().list(
                        calendarId=cid,
                        timeMin=time_min,
                        timeMax=time_max,
                        singleEvents=True,
                        orderBy="startTime",
                        maxResults=250,
                    ).execute()
                    for event in events_result.get("items", []):
                        if event.get("status") == "cancelled":
                            continue
                        if event.get("transparency") == "transparent":
                            continue
                        attendees = event.get("attendees", [])
                        if any(
                            a.get("self") and a.get("responseStatus") == "declined"
                            for a in attendees
                        ):
                            continue
                        start = event.get("start", {})
                        end = event.get("end", {})
                        start_str = start.get("dateTime") or start.get("date")
                        end_str = end.get("dateTime") or end.get("date")
                        # Skip all-day events (date-only strings have no "T")
                        if start_str and end_str and "T" in str(start_str):
                            merged_busy.append({"start": start_str, "end": end_str})
                except Exception:
                    pass  # Skip calendars we can't read events from

            result[email] = {"busy": merged_busy}
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
