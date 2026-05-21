"""
Scheduler module.
Finds common free time slots between multiple people from their busy data.
"""

from datetime import datetime, timedelta, timezone
from dateutil import parser


def parse_busy_slots(freebusy_data: dict) -> dict[str, list[tuple]]:
    """
    Convert the Google Calendar API freebusy response into a clean structure.

    Args:
        freebusy_data: raw response from get_freebusy()

    Returns:
        dict mapping each email to a list of (start, end) datetime tuples
    """
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
) -> list[tuple]:
    """
    Find all free time slots where ALL people are available simultaneously.

    Algorithm: discretize the search window into 15-minute slots, mark each
    slot as busy if anyone is busy, then merge contiguous free slots.

    Args:
        busy_by_person: dict mapping each email to their busy intervals
        search_start: start of the search window
        search_end: end of the search window
        duration_minutes: minimum duration of a valid common slot (default 60)
        working_hours: tuple (start_hour, end_hour) e.g. (9, 18) for 9am-6pm
        include_weekends: whether to include Saturday and Sunday

    Returns:
        list of (start, end) tuples representing common free slots
    """
    slot_size = timedelta(minutes=15)
    duration = timedelta(minutes=duration_minutes)

    # Ensure search window is timezone-aware
    if search_start.tzinfo is None:
        search_start = search_start.replace(tzinfo=timezone.utc)
    if search_end.tzinfo is None:
        search_end = search_end.replace(tzinfo=timezone.utc)

    # Flatten all busy intervals from everyone into one list
    all_busy = []
    for slots in busy_by_person.values():
        for start, end in slots:
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
            all_busy.append((start, end))

    def is_anyone_busy(t: datetime) -> bool:
        """Check if at least one person is busy at instant t."""
        for start, end in all_busy:
            if start <= t < end:
                return True
        return False

    def in_working_hours(t: datetime) -> bool:
        """Check if t is within working hours and not on weekend (unless allowed)."""
        if not include_weekends and t.weekday() >= 5:
            return False
        return working_hours[0] <= t.hour < working_hours[1]

    # Step 1: find all free 15-min discrete slots
    free_slots = []
    current = search_start
    while current < search_end:
        if in_working_hours(current) and not is_anyone_busy(current):
            free_slots.append(current)
        current += slot_size

    if not free_slots:
        return []

    # Step 2: merge contiguous free slots into blocks
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


def format_slot(start: datetime, end: datetime) -> str:
    """Format a slot in a human-readable way."""
    day = start.strftime("%A %d %B")
    time_range = f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')}"
    return f"{day}: {time_range}"


if __name__ == "__main__":
    from calendar_client import get_freebusy

    # The two accounts we want to coordinate
    emails = [
        "tambeycecile@gmail.com",
        "cecile.tambey@student.ie.edu",
    ]

    # Search window: next 14 days
    start = datetime.now(timezone.utc)
    end = start + timedelta(days=14)

    print(f"Searching common free slots for {len(emails)} people:")
    for email in emails:
        print(f"  - {email}")
    print(f"\nTime range: next 14 days")
    print(f"Working hours: 9am - 6pm, weekdays only")
    print(f"Minimum duration: 60 minutes\n")

    # Step 1: get busy data from Google Calendar
    freebusy_data = get_freebusy(emails, start, end)

    # Step 2: parse into clean format
    busy_by_person = parse_busy_slots(freebusy_data)

    # Step 3: find common free slots
    common_slots = find_common_free_slots(
        busy_by_person,
        search_start=start,
        search_end=end,
        duration_minutes=60,
        working_hours=(9, 18),
    )

    print(f"Found {len(common_slots)} common free slots of at least 1 hour:\n")
    for slot_start, slot_end in common_slots[:15]:
        print(f"  {format_slot(slot_start, slot_end)}")
        