"""
Scheduler module.
Finds common free time slots between multiple people from their busy data.
Timezone-aware: working hours are evaluated in local time (default Europe/Madrid).
"""

from datetime import datetime, timedelta, timezone
from dateutil import parser
import pytz


DEFAULT_TIMEZONE = "Europe/Madrid"


def parse_busy_slots(freebusy_data: dict) -> dict[str, list[tuple]]:
    """Convert the Google Calendar API freebusy response into a clean structure."""
    result = {}
    for email, data in freebusy_data.items():
        slots = []
        for busy in data.get("busy", []):
            start = parser.parse(busy["start"])
            end = parser.parse(busy["end"])
            slots.append((start, end))
        result[email] = slots
    return result


def find_common_free_slots(
    busy_by_person: dict[str, list[tuple]],
    search_start: datetime,
    search_end: datetime,
    duration_minutes: int = 60,
    working_hours: tuple = (9, 18),
    include_weekends: bool = False,
    timezone_name: str = DEFAULT_TIMEZONE,
) -> list[tuple]:
    """
    Find all free time slots where ALL people are available simultaneously.
    Working hours are evaluated in LOCAL time (timezone_name), not UTC.
    """
    slot_size = timedelta(minutes=15)
    duration = timedelta(minutes=duration_minutes)
    local_tz = pytz.timezone(timezone_name)

    if search_start.tzinfo is None:
        search_start = search_start.replace(tzinfo=timezone.utc)
    if search_end.tzinfo is None:
        search_end = search_end.replace(tzinfo=timezone.utc)

    all_busy = []
    for slots in busy_by_person.values():
        for start, end in slots:
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
            all_busy.append((start, end))

    def is_anyone_busy(t: datetime) -> bool:
        for start, end in all_busy:
            if start <= t < end:
                return True
        return False

    def in_working_hours(t: datetime) -> bool:
        local_t = t.astimezone(local_tz)
        if not include_weekends and local_t.weekday() >= 5:
            return False
        return working_hours[0] <= local_t.hour < working_hours[1]

    free_slots = []
    current = search_start
    while current < search_end:
        if in_working_hours(current) and not is_anyone_busy(current):
            free_slots.append(current)
        current += slot_size

    if not free_slots:
        return []

    merged = []
    block_start = free_slots[0]
    block_end = free_slots[0] + slot_size

    for slot in free_slots[1:]:
        if slot == block_end:
            block_end = slot + slot_size
        else:
            if block_end - block_start >= duration:
                merged.append((block_start, block_end))
            block_start = slot
            block_end = slot + slot_size

    if block_end - block_start >= duration:
        merged.append((block_start, block_end))

    return merged


def format_slot(
    start: datetime,
    end: datetime,
    timezone_name: str = DEFAULT_TIMEZONE,
) -> str:
    """Format a slot in human-readable LOCAL time."""
    local_tz = pytz.timezone(timezone_name)
    local_start = start.astimezone(local_tz)
    local_end = end.astimezone(local_tz)
    day = local_start.strftime("%A %d %B")
    time_range = f"{local_start.strftime('%H:%M')} - {local_end.strftime('%H:%M')}"
    return f"{day}: {time_range}"


if __name__ == "__main__":
    from calendar_client import get_freebusy

    emails = [
        "tambeycecile@gmail.com",
        "cecile.tambey@student.ie.edu",
    ]
    start = datetime.now(timezone.utc)
    end = start + timedelta(days=14)

    freebusy_data = get_freebusy(emails, start, end)
    busy_by_person = parse_busy_slots(freebusy_data)
    common_slots = find_common_free_slots(
        busy_by_person,
        search_start=start,
        search_end=end,
        duration_minutes=60,
        working_hours=(9, 18),
        timezone_name="Europe/Madrid",
    )

    print(f"Found {len(common_slots)} common free slots:\n")
    for s, e in common_slots[:15]:
        print(f"  {format_slot(s, e)}")