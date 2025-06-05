# import uuid # No longer needed for generating child_ids
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

from src.database import SessionLocal
from src.child import Child
from src.user import User # Needed for associating with parent

# children_storage and child_parent_link are removed

def _parse_date(date_str: str):
    """Helper to parse string to date. Returns None if format is wrong."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        print(f"Warning: Could not parse date string: {date_str}")
        return None

def add_child(user_id: int, name: str, date_of_birth_str: str, school_info: str = None, custody_schedule_info: str = None):
    db = SessionLocal()
    try:
        parent_user = db.query(User).filter(User.id == user_id).first()
        if not parent_user:
            print("Error: Parent user not found.")
            return None

        dob_date = _parse_date(date_of_birth_str)
        if not dob_date:
            print("Error: Invalid date of birth format.")
            return None

        new_child = Child(
            name=name,
            date_of_birth=dob_date,
            school_info=school_info,
            custody_schedule_info=custody_schedule_info
        )

        # Add parent to child's list of parents for many-to-many relationship
        new_child.parents.append(parent_user)

        db.add(new_child)
        db.commit()
        db.refresh(new_child)
        return new_child
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error adding child: {e}")
        return None
    finally:
        db.close()

# --- ResidencyPeriod specific functions ---
from src.residency_period import ResidencyPeriod
from sqlalchemy import and_ # For combining filter conditions

def _parse_datetime_for_residency(datetime_str: str):
    """Helper to parse string to datetime for residency periods."""
    if not datetime_str:
        return None
    try:
        # Expecting "YYYY-MM-DD HH:MM:SS" or "YYYY-MM-DD HH:MM"
        if len(datetime_str) == 16: # YYYY-MM-DD HH:MM
             return datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
        return datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        print(f"Warning: Could not parse datetime string for residency: {datetime_str}")
        return None

def add_residency_period(db_session: Session, child_id: int, parent_id: int,
                         start_datetime_str: str, end_datetime_str: str, notes: str = None):
    child = db_session.query(Child).filter(Child.id == child_id).first()
    if not child:
        raise ValueError(f"Child with id {child_id} not found.")
    parent = db_session.query(User).filter(User.id == parent_id).first()
    if not parent:
        raise ValueError(f"Parent (User) with id {parent_id} not found.")

    start_dt = _parse_datetime_for_residency(start_datetime_str)
    end_dt = _parse_datetime_for_residency(end_datetime_str)

    if not start_dt or not end_dt:
        raise ValueError("Invalid start or end datetime format. Use YYYY-MM-DD HH:MM[:SS].")
    if start_dt >= end_dt:
        raise ValueError("Start datetime must be before end datetime.")

    new_period = ResidencyPeriod(
        child_id=child_id,
        parent_id=parent_id,
        start_datetime=start_dt,
        end_datetime=end_dt,
        notes=notes
    )
    db_session.add(new_period)
    # db_session.commit() # Commit handled by caller (API)
    # db_session.refresh(new_period)
    return new_period

def get_residency_periods_for_child(db_session: Session, child_id: int,
                                    start_filter_date_str: str = None, end_filter_date_str: str = None):
    query = db_session.query(ResidencyPeriod).filter(ResidencyPeriod.child_id == child_id)

    if start_filter_date_str:
        start_filter_dt = _parse_datetime_for_residency(start_filter_date_str + " 00:00:00") # Start of day
        if start_filter_dt:
            query = query.filter(ResidencyPeriod.end_datetime >= start_filter_dt)

    if end_filter_date_str:
        end_filter_dt = _parse_datetime_for_residency(end_filter_date_str + " 23:59:59") # End of day
        if end_filter_dt:
            query = query.filter(ResidencyPeriod.start_datetime <= end_filter_dt)

    return query.order_by(ResidencyPeriod.start_datetime).all()

def get_residency_period_details(db_session: Session, period_id: int):
    return db_session.query(ResidencyPeriod).filter(ResidencyPeriod.id == period_id).first()

def update_residency_period(db_session: Session, period_id: int, parent_id: int = None,
                            start_datetime_str: str = None, end_datetime_str: str = None, notes: str = None):
    period = db_session.query(ResidencyPeriod).filter(ResidencyPeriod.id == period_id).first()
    if not period:
        raise ValueError(f"ResidencyPeriod with id {period_id} not found.")

    updated = False
    if parent_id is not None:
        parent_user = db_session.query(User).filter(User.id == parent_id).first()
        if not parent_user:
            raise ValueError(f"Parent (User) with id {parent_id} not found for update.")
        period.parent_id = parent_id
        updated = True

    if start_datetime_str is not None:
        start_dt = _parse_datetime_for_residency(start_datetime_str)
        if not start_dt:
            raise ValueError("Invalid start datetime format for update.")
        period.start_datetime = start_dt
        updated = True

    if end_datetime_str is not None:
        end_dt = _parse_datetime_for_residency(end_datetime_str)
        if not end_dt:
            raise ValueError("Invalid end datetime format for update.")
        period.end_datetime = end_dt
        updated = True

    if period.start_datetime >= period.end_datetime:
        raise ValueError("Start datetime must be before end datetime after update.")

    if notes is not None: # Allow setting notes to empty string
        period.notes = notes
        updated = True

    # if updated: # db_session.commit() handled by caller
    return period

def delete_residency_period(db_session: Session, period_id: int):
    period = db_session.query(ResidencyPeriod).filter(ResidencyPeriod.id == period_id).first()
    if not period:
        return False # Or raise ValueError

    db_session.delete(period)
    # db_session.commit() # Handled by caller
    return True

def get_child_residency_on_date(db_session: Session, child_id: int, date_str: str):
    target_date = _parse_date(date_str) # Use existing helper from child_manager
    if not target_date:
        raise ValueError("Invalid date format. Please use YYYY-MM-DD.")

    # Find periods that are active on the target_date
    # A period is active if target_date is between period.start_datetime (inclusive)
    # and period.end_datetime (exclusive, or inclusive depending on definition)
    # For simplicity, let's say target_date should be >= period.start_date and < period.end_date

    # Convert target_date to datetime objects for comparison, covering the whole day
    target_datetime_start = datetime.combine(target_date, datetime.min.time())
    target_datetime_end = datetime.combine(target_date, datetime.max.time())

    active_periods = db_session.query(ResidencyPeriod).filter(
        ResidencyPeriod.child_id == child_id,
        ResidencyPeriod.start_datetime <= target_datetime_end, # Period starts on or before end of target day
        ResidencyPeriod.end_datetime >= target_datetime_start    # Period ends on or after start of target day
    ).all()

    # This could return multiple periods if they overlap or if one ends and another starts on the same day.
    # For a simple "who is the child with" it might need more specific logic if overlaps are complex.
    # For now, returning all active periods.
    return active_periods

def get_child_details(child_id: int):
    db = SessionLocal()
    try:
        child = db.query(Child).filter(Child.id == child_id).first()
        return child
    except SQLAlchemyError as e:
        print(f"Database error getting child details: {e}")
        return None
    finally:
        db.close()

def get_user_children(user_id: int):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            return user.children # Accesses the 'children' relationship attribute
        return [] # Return empty list if user not found
    except SQLAlchemyError as e:
        print(f"Database error getting user children: {e}")
        return []
    finally:
        db.close()

def update_child_info(child_id: int, name: str = None, date_of_birth_str: str = None,
                      school_info: str = None, custody_schedule_info: str = None):
    db = SessionLocal()
    try:
        child = db.query(Child).filter(Child.id == child_id).first()
        if not child:
            print("Error: Child not found.")
            return None

        updated = False
        if name is not None:
            child.name = name
            updated = True
        if date_of_birth_str is not None:
            dob_date = _parse_date(date_of_birth_str)
            if dob_date:
                child.date_of_birth = dob_date
                updated = True
            else:
                 print("Warning: Invalid date of birth format, not updated.")
        if school_info is not None:
            child.school_info = school_info
            updated = True
        if custody_schedule_info is not None:
            child.custody_schedule_info = custody_schedule_info
            updated = True

        if updated:
            db.commit()
            db.refresh(child)
        return child
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error updating child info: {e}")
        return None
    finally:
        db.close()

def remove_child(child_id: int):
    db = SessionLocal()
    try:
        child = db.query(Child).filter(Child.id == child_id).first()
        if not child:
            print("Error: Child not found for deletion.")
            return False

        # SQLAlchemy handles removal from association table due to relationship cascade,
        # if configured (default is "save-update, merge").
        # Explicitly clearing child.parents might be needed if cascade isn't set as expected
        # or if you want to be sure before deleting the child object itself.
        # child.parents.clear() # Optional: Explicitly remove associations

        db.delete(child)
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error removing child: {e}")
        return False
    finally:
        db.close()

def add_parent_to_child(child_id: int, user_id: int):
    db = SessionLocal()
    try:
        child = db.query(Child).filter(Child.id == child_id).first()
        parent_to_add = db.query(User).filter(User.id == user_id).first()

        if not child:
            print("Error: Child not found.")
            return False
        if not parent_to_add:
            print("Error: User (parent) not found.")
            return False

        if parent_to_add in child.parents:
            print("Info: User is already a parent of this child.")
            return False # Or True, depending on desired idempotent behavior

        child.parents.append(parent_to_add)
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error adding parent to child: {e}")
        return False
    finally:
        db.close()
