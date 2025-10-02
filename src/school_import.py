import os
from datetime import datetime
from typing import List, Dict

from . import event_manager


def _parse_ics_datetime(value: str) -> datetime | None:
    """Parse basic iCalendar datetime strings."""
    value = value.strip()
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y%m%dT%H%M%S", "%Y%m%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def parse_ics(file_path: str) -> List[Dict[str, datetime]]:
    """Parse a very small subset of .ics files and return event info."""
    events: List[Dict[str, datetime]] = []
    if not os.path.exists(file_path):
        return events

    with open(file_path, "r", encoding="utf-8") as fh:
        in_event = False
        current: Dict[str, str] = {}
        for line in fh:
            line = line.strip()
            if line == "BEGIN:VEVENT":
                in_event = True
                current = {}
            elif line == "END:VEVENT":
                if in_event and {"SUMMARY", "DTSTART", "DTEND"} <= current.keys():
                    start = _parse_ics_datetime(current["DTSTART"])
                    end = _parse_ics_datetime(current["DTEND"])
                    if start and end:
                        events.append({
                            "title": current.get("SUMMARY", ""),
                            "description": current.get("DESCRIPTION"),
                            "start": start,
                            "end": end,
                        })
                in_event = False
            elif in_event:
                if ":" in line:
                    key, val = line.split(":", 1)
                    current[key] = val
    return events


def import_school_calendar(file_path: str):
    """Parse the given ICS file and store events with source='school'."""
    imported = []
    for evt in parse_ics(file_path):
        new_event = event_manager.create_event(
            title=evt["title"],
            description=evt.get("description"),
            start_time_str=evt["start"].strftime("%Y-%m-%d %H:%M"),
            end_time_str=evt["end"].strftime("%Y-%m-%d %H:%M"),
            source="school",
        )
        if new_event:
            imported.append(new_event)
    return imported
