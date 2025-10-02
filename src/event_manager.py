# import uuid # No longer needed for generating event_ids
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta

import json

from src.notification import send_notification
from src.child import Child


from src.database import SessionLocal
from src.event import Event
from src.badge import award_points
from src.shift import Shift
from src.residency_period import ResidencyPeriod
# User and Child models might be needed if we want to validate existence of user_id/child_id before linking
# from src.user import User
# from src.child import Child

# events_storage is removed

def _parse_datetime(datetime_str: str):
    """Helper to parse string to datetime. Returns None if format is wrong."""
    if not datetime_str:
        return None
    try:
        return datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
    except ValueError:
        print(f"Warning: Could not parse datetime string: {datetime_str}")
        return None

def create_event(title: str, description: str, start_time_str: str, end_time_str: str,
                 linked_user_id: int = None, linked_child_id: int = None,
                 destination: str = None):
                 source: str = 'user'):
    db = SessionLocal()
    try:
        start_time_dt = _parse_datetime(start_time_str)
        end_time_dt = _parse_datetime(end_time_str)

        if not start_time_dt or not end_time_dt:
            print("Error: Invalid start or end time format for event.")
            return None

        # Note: linked_user_id and linked_child_id are now user_id and child_id in the Event model
        new_event = Event(
            title=title,
            description=description,
            destination=destination,
            start_time=start_time_dt,
            end_time=end_time_dt,
            user_id=linked_user_id, # This is the FK field in Event model
            child_id=linked_child_id, # This is the FK field in Event model
            completed=0
            source=source
        )
        db.add(new_event)
        db.commit()
        db.refresh(new_event)
        # Notify linked user or parents of linked child
        if new_event.user_id:
            send_notification(new_event.user_id, {
                "type": "event_created",
                "event": new_event.to_dict(include_user=False, include_child=False)
            })
        elif new_event.child_id:
            child = db.query(Child).filter(Child.id == new_event.child_id).first()
            if child:
                for parent in child.parents:
                    send_notification(parent.id, {
                        "type": "event_created",
                        "event": new_event.to_dict(include_user=False, include_child=False)
                    })
        return new_event
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error creating event: {e}")
        return None
    finally:
        db.close()

def get_event_details(event_id: int):
    db = SessionLocal()
    try:
        event = db.query(Event).filter(Event.id == event_id).first()
        return event
    except SQLAlchemyError as e:
        print(f"Database error getting event details: {e}")
        return None
    finally:
        db.close()

def get_events_for_user(user_id: int):
    db = SessionLocal()
    try:
        # Event model has 'user_id' as the foreign key field
        events = db.query(Event).filter(Event.user_id == user_id).all()
        return events
    except SQLAlchemyError as e:
        print(f"Database error getting events for user: {e}")
        return []
    finally:
        db.close()

def get_events_for_child(child_id: int):
    db = SessionLocal()
    try:
        # Event model has 'child_id' as the foreign key field
        events = db.query(Event).filter(Event.child_id == child_id).all()
        return events
    except SQLAlchemyError as e:
        print(f"Database error getting events for child: {e}")
        return []
    finally:
        db.close()

def update_event(event_id: int, title: str = None, description: str = None,
                 start_time_str: str = None, end_time_str: str = None,
                 linked_user_id: int = None, linked_child_id: int = None,
                 destination: str = None,
                 unlink_user: bool = False, unlink_child: bool = False): # Added unlink flags
                 completed: bool | None = None,
                 unlink_user: bool = False, unlink_child: bool = False):
    db = SessionLocal()
    try:
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            print("Error: Event not found.")
            return None

        updated = False
        if title is not None:
            event.title = title
            updated = True
        if description is not None:
            event.description = description
            updated = True
        if destination is not None:
            event.destination = destination
            updated = True
        if start_time_str is not None:
            start_time_dt = _parse_datetime(start_time_str)
            if start_time_dt:
                event.start_time = start_time_dt
                updated = True
            else:
                print("Warning: Invalid start time format, not updated.")
        if end_time_str is not None:
            end_time_dt = _parse_datetime(end_time_str)
            if end_time_dt:
                event.end_time = end_time_dt
                updated = True
            else:
                print("Warning: Invalid end time format, not updated.")

        if unlink_user:
            event.user_id = None
            updated = True
        elif linked_user_id is not None:
            event.user_id = linked_user_id
            updated = True

        if unlink_child:
            event.child_id = None
            updated = True
        elif linked_child_id is not None:
            event.child_id = linked_child_id
            updated = True

        if completed is not None and bool(event.completed) != completed:
            event.completed = 1 if completed else 0
            updated = True
            if completed and event.user_id:
                award_points(event.user_id, 10, "event_completed")

        if updated:
            db.commit()
            db.refresh(event)
            if event.user_id:
                send_notification(event.user_id, {
                    "type": "event_updated",
                    "event": event.to_dict(include_user=False, include_child=False)
                })
            elif event.child_id:
                child = db.query(Child).filter(Child.id == event.child_id).first()
                if child:
                    for parent in child.parents:
                        send_notification(parent.id, {
                            "type": "event_updated",
                            "event": event.to_dict(include_user=False, include_child=False)
                        })
        return event
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error updating event: {e}")
        return None
    finally:
        db.close()

def delete_event(event_id: int):
    db = SessionLocal()
    try:
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            print("Error: Event not found for deletion.")
            return False

        db.delete(event)
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error deleting event: {e}")
        return False
    finally:
        db.close()


def detect_conflicts(start_time_str: str, end_time_str: str,
                     user_id: int = None, child_id: int = None):
    """Check for shift or residency conflicts for a proposed event."""
    start_dt = _parse_datetime(start_time_str)
    end_dt = _parse_datetime(end_time_str)
    if not start_dt or not end_dt:
        return {"conflicts": ["invalid_datetime"]}

    db = SessionLocal()
    conflicts = []
    latest_end = None
    try:
        if user_id:
            overlapping_shifts = db.query(Shift).filter(
                Shift.user_id == user_id,
                Shift.start_time < end_dt,
                Shift.end_time > start_dt
            ).all()
            if overlapping_shifts:
                conflicts.append("shift")
                latest_end = max(s.end_time for s in overlapping_shifts)

        if child_id:
            periods = db.query(ResidencyPeriod).filter(
                ResidencyPeriod.child_id == child_id,
                ResidencyPeriod.start_datetime <= start_dt,
                ResidencyPeriod.end_datetime >= end_dt
            ).all()
            if not periods:
                conflicts.append("residency")
            elif user_id is not None and all(p.parent_id != user_id for p in periods):
                conflicts.append("residency_parent")
                latest_end = max(p.end_datetime for p in periods)

        suggestion = None
        if conflicts:
            shift_end = latest_end or end_dt
            suggested_start = (shift_end + timedelta(hours=1))
            suggested_end = suggested_start + (end_dt - start_dt)
            suggestion = {
                "suggested_start": suggested_start.strftime('%Y-%m-%d %H:%M'),
                "suggested_end": suggested_end.strftime('%Y-%m-%d %H:%M')
            }
        return {"conflicts": conflicts, **(suggestion or {})}
    finally:
        db.close()
