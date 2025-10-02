# import uuid # No longer needed for generating shift_ids by this module
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from zoneinfo import ZoneInfo
from datetime import datetime # For string to datetime conversion
import json

from src.notification import send_notification

from src.database import SessionLocal
from src.shift import Shift
# from src.user import User # Not strictly needed if only user_id is used and no User object operations

# shifts_storage is removed, data will be stored in SQLite via SQLAlchemy

def _parse_datetime(datetime_str, timezone_str='UTC'):
    """Parse a datetime string in the given timezone and return naive UTC."""
    if not datetime_str:
        return None
    try:
        naive = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
        local = naive.replace(tzinfo=ZoneInfo(timezone_str))
        utc = local.astimezone(ZoneInfo('UTC'))
        return utc.replace(tzinfo=None)
    except ValueError:
        print(f"Warning: Could not parse datetime string: {datetime_str}")
        return None

def add_shift(user_id: int, start_time_str: str, end_time_str: str, name: str, timezone: str = 'UTC'):
    db = SessionLocal()
    try:
        start_time_dt = _parse_datetime(start_time_str, timezone)
        end_time_dt = _parse_datetime(end_time_str, timezone)

        if not start_time_dt or not end_time_dt:
            print("Error: Invalid start or end time format.")
            return None

        # Assuming user_id is the integer PK from the User model
        new_shift = Shift(
            user_id=user_id,
            start_time=start_time_dt,
            end_time=end_time_dt,
            name=name
        )
        db.add(new_shift)
        db.commit()
        db.refresh(new_shift)
        send_notification(user_id, {
            "type": "shift_created",
            "shift": new_shift.to_dict(include_owner=False)
        })
        return new_shift
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error adding shift: {e}")
        return None
    finally:
        db.close()

def get_user_shifts(user_id: int):
    db = SessionLocal()
    try:
        # Assuming user_id is the integer PK from the User model
        shifts = db.query(Shift).filter(Shift.user_id == user_id).all()
        return shifts
    except SQLAlchemyError as e:
        print(f"Database error getting user shifts: {e}")
        return [] # Return empty list on error
    finally:
        db.close()

def update_shift(shift_id: int, new_start_time_str: str = None, new_end_time_str: str = None, new_name: str = None, timezone: str = 'UTC'):
    db = SessionLocal()
    try:
        shift = db.query(Shift).filter(Shift.id == shift_id).first()
        if not shift:
            print("Error: Shift not found.")
            return None

        updated = False
        if new_start_time_str is not None:
            new_start_time_dt = _parse_datetime(new_start_time_str, timezone)
            if new_start_time_dt:
                shift.start_time = new_start_time_dt
                updated = True
            else:
                print("Warning: Invalid new start time format, not updated.")
        if new_end_time_str is not None:
            new_end_time_dt = _parse_datetime(new_end_time_str, timezone)
            if new_end_time_dt:
                shift.end_time = new_end_time_dt
                updated = True
            else:
                print("Warning: Invalid new end time format, not updated.")
        if new_name is not None:
            shift.name = new_name
            updated = True

        if updated:
            db.commit()
            db.refresh(shift)
            send_notification(shift.user_id, {
                "type": "shift_updated",
                "shift": shift.to_dict(include_owner=False)
            })
        return shift
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error updating shift: {e}")
        return None
    finally:
        db.close()

def delete_shift(shift_id: int):
    db = SessionLocal()
    try:
        shift = db.query(Shift).filter(Shift.id == shift_id).first()
        if not shift:
            print("Error: Shift not found for deletion.")
            return False

        db.delete(shift)
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error deleting shift: {e}")
        return False
    finally:
        db.close()
