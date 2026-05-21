"""
Smart Scheduler Agent.
Conversational agent powered by Gemini that finds common free slots
between multiple people using natural language understanding.
"""

import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import google.generativeai as genai

from calendar_client import get_freebusy
from scheduler import parse_busy_slots, find_common_free_slots


load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


# ============================================================
# TOOL: the function Gemini can call automatically
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

    Use this tool whenever the user wants to schedule a meeting between
    multiple people. The tool only reveals free/busy data, never event
    details, titles, or participants, preserving everyone's privacy.

    Args:
        attendee_emails: list of Google email addresses of participants
        duration_minutes: desired meeting duration in minutes (default 60)
        days_ahead: how many days into the future to search (default 7)
        working_hours_start: start hour, 24h format (default 9 for 9am)
        working_hours_end: end hour, 24h format (default 18 for 6pm)
        include_weekends: whether to include Saturday and Sunday (default False)

    Returns:
        dict with success status and list of available slots
    """
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

        # Format for the LLM to understand
        formatted_slots = []
        for s, e in common_slots[:10]:
            formatted_slots.append({
                "day": s.strftime("%A %d %B %Y"),
                "start_time": s.strftime("%H:%M"),
                "end_time": e.strftime("%H:%M"),
                "duration_hours": round((e - s).total_seconds() / 3600, 1),
            })

        # Detect permission errors per attendee
        errors_per_person = {}
        for email, data in freebusy.items():
            errs = data.get("errors", [])
            if errs:
                errors_per_person[email] = errs

        return {
            "success": True,
            "attendees": attendee_emails,
            "duration_minutes_requested": duration_minutes,
            "search_days": days_ahead,
            "available_slots": formatted_slots,
            "total_slots_found": len(common_slots),
            "permission_errors": errors_per_person,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# AGENT: Gemini with function calling
# ============================================================

SYSTEM_PROMPT = """You are an intelligent meeting scheduling assistant.

Your role: help the user find common free time slots between multiple people
using the find_meeting_slots tool, without ever revealing the details of their
schedules. You only see busy/free time ranges, never event titles or contents.

When the user asks you to find a meeting slot:

1. Identify the participants from their emails (ask if missing)
2. Identify the desired duration (default to 60 min if not specified)
3. Identify the time constraints:
   - "tomorrow" -> days_ahead=1
   - "this week" -> days_ahead=7
   - "next week" -> days_ahead=14
   - "this month" -> days_ahead=30
   - "morning" -> working_hours_start=9, working_hours_end=12
   - "afternoon" -> working_hours_start=13, working_hours_end=18
   - "evening / end of day" -> working_hours_start=16, working_hours_end=20
   - "weekend" -> include_weekends=True
4. Call find_meeting_slots with the right parameters
5. Present the 3-5 best slots clearly to the user

If essential info is missing (e.g. emails), ask for it before calling the tool.

Be concise, professional, and helpful. Always respond in English.
"""


# Build the Gemini model with the tool
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    system_instruction=SYSTEM_PROMPT,
    tools=[find_meeting_slots],
)

# Start a chat session with automatic function calling
chat = model.start_chat(enable_automatic_function_calling=True)


def run_agent(user_message: str) -> str:
    """Send a message to the agent and return its response."""
    response = chat.send_message(user_message)
    return response.text


# ============================================================
# CLI loop
# ============================================================

def main():
    print("=" * 70)
    print("  Smart Scheduler Agent")
    print("=" * 70)
    print("I find common free slots between multiple people,")
    print("without revealing the details of their calendars.\n")
    print("Example requests:")
    print('  "Find 1h this week with tambeycecile@gmail.com')
    print('   and cecile.tambey@student.ie.edu"')
    print('  "30 min tomorrow morning with X and Y"')
    print('  "2h meeting next week between 2pm and 5pm"')
    print("\nType 'quit' to exit.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break
        if not user_input:
            continue

        try:
            response = run_agent(user_input)
            print(f"\nAgent: {response}\n")
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()