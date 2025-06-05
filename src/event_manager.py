# import uuid # No longer needed for generating event_ids
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

from src.database import SessionLocal
from src.event import Event
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
                 institution_id: int = None):
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
            start_time=start_time_dt,
            end_time=end_time_dt,
            user_id=linked_user_id, # This is the FK field in Event model
            child_id=linked_child_id, # This is the FK field in Event model
            institution_id=institution_id
        )
        db.add(new_event)
        db.commit()
        db.refresh(new_event)
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

def get_events_for_institution(institution_id: int):
    db = SessionLocal()
    try:
        events = db.query(Event).filter(Event.institution_id == institution_id).all()
        return events
    except SQLAlchemyError as e:
        print(f"Database error getting events for institution: {e}")
        return []
    finally:
        db.close()

def update_event(event_id: int, title: str = None, description: str = None,
                 start_time_str: str = None, end_time_str: str = None,
                 linked_user_id: int = None, linked_child_id: int = None,
                 institution_id: int = None,
                 unlink_user: bool = False, unlink_child: bool = False,
                 unlink_institution: bool = False):
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

        if unlink_institution:
            event.institution_id = None
            updated = True
        elif institution_id is not None:
            event.institution_id = institution_id
            updated = True

        if updated:
            db.commit()
            db.refresh(event)
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
