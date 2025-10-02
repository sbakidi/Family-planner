from datetime import datetime, timedelta
from typing import List, Tuple

from src import event_manager, shift_manager, child_manager


def _parse_datetime(dt_str: str) -> datetime:
    """Parse a '%Y-%m-%d %H:%M' formatted string to a datetime object."""
    return datetime.strptime(dt_str, "%Y-%m-%d %H:%M")


def check_overbooking(user_id: int, start: datetime, end: datetime) -> bool:
    """Return True if the user has an event or shift overlapping the period."""
    for ev in event_manager.get_events_for_user(user_id):
        if ev.start_time < end and ev.end_time > start:
            return True
    for sh in shift_manager.get_user_shifts(user_id):
        if sh.start_time < end and sh.end_time > start:
            return True
    return False


def suggest_next_slot(user_id: int, desired_start: datetime, desired_end: datetime) -> Tuple[datetime, datetime]:
    """Return the next available slot after conflicts. Simple rule-based logic."""
    conflicts_end: List[datetime] = []
    for ev in event_manager.get_events_for_user(user_id):
        if ev.start_time < desired_end and ev.end_time > desired_start:
            conflicts_end.append(ev.end_time)
    for sh in shift_manager.get_user_shifts(user_id):
        if sh.start_time < desired_end and sh.end_time > desired_start:
            conflicts_end.append(sh.end_time)
    if not conflicts_end:
        return desired_start, desired_end

    latest_end = max(conflicts_end)
    duration = desired_end - desired_start
    new_start = latest_end + timedelta(minutes=15)
    return new_start, new_start + duration


def schedule_event(user_id: int, title: str, description: str, start_time_str: str, end_time_str: str, child_id: int = None):
    """Create an event using the best available slot. Returns (event, adjusted)."""
    desired_start = _parse_datetime(start_time_str)
    desired_end = _parse_datetime(end_time_str)

    adjusted = False
    if check_overbooking(user_id, desired_start, desired_end):
        desired_start, desired_end = suggest_next_slot(user_id, desired_start, desired_end)
        adjusted = True

    start_str = desired_start.strftime("%Y-%m-%d %H:%M")
    end_str = desired_end.strftime("%Y-%m-%d %H:%M")

    event = event_manager.create_event(
        title=title,
        description=description,
        start_time_str=start_str,
        end_time_str=end_str,
        linked_user_id=user_id,
        linked_child_id=child_id,
    )
    return event, adjusted


def find_overlapping_events(events) -> List[int]:
    """Return list of event IDs that overlap with any other in the list."""
    overbooked = set()
    for i, e1 in enumerate(events):
        for j, e2 in enumerate(events):
            if i == j:
                continue
            if e1.start_time < e2.end_time and e1.end_time > e2.start_time:
                overbooked.add(e1.id)
                overbooked.add(e2.id)
    return list(overbooked)

