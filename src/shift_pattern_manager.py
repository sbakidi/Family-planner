from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from src.database import SessionLocal
from src.shift_pattern import ShiftPattern
from src.user import User # Import User if needed for validating user_id, though FK constraint handles existence

def create_shift_pattern(name: str, description: str, pattern_type: str, definition: dict, user_id: int = None):
    db = SessionLocal()
    try:
        # Optional: Validate user_id if provided, though FK constraint will do this.
        # if user_id:
        #     user = db.query(User).filter(User.id == user_id).first()
        #     if not user:
        #         print(f"Error: User with id {user_id} not found.")
        #         return None

        new_pattern = ShiftPattern(
            name=name,
            description=description,
            pattern_type=pattern_type,
            definition=definition,
            user_id=user_id
        )
        db.add(new_pattern)
        db.commit()
        db.refresh(new_pattern)
        return new_pattern
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error creating shift pattern: {e}")
        return None
    finally:
        db.close()

from datetime import datetime, date, timedelta

def generate_shifts_from_pattern(db_session: Session, pattern_id: int, user_id: int,
                                start_date_str: str, end_date_str: str,
                                holidays=None, exceptions=None):
    pattern = db_session.query(ShiftPattern).filter(ShiftPattern.id == pattern_id).first()
    if not pattern:
        raise ValueError(f"ShiftPattern with id {pattern_id} not found.")

    user = db_session.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User with id {user_id} not found.")

    try:
        start_date_obj = date.fromisoformat(start_date_str)
        end_date_obj = date.fromisoformat(end_date_str)
    except ValueError:
        raise ValueError("Invalid date format. Please use YYYY-MM-DD.")

    holidays_set = set(date.fromisoformat(d) for d in holidays) if holidays else set()
    exceptions = exceptions or {}

    if start_date_obj > end_date_obj:
        raise ValueError("Start date cannot be after end date.")

    created_shifts = []

    if pattern.pattern_type == 'Rotating':
        # Example definition: {"cycle": [{"name": "Day", "days": 2, "start_time": "08:00", "end_time": "16:00"},
        #                              {"name": "Night", "days": 2, "start_time": "20:00", "end_time": "04:00"}, # Overnight
        #                              {"name": "Off", "days": 3}],
        #                   "cycle_start_reference_date": "2024-01-01"}
        if not pattern.definition or 'cycle' not in pattern.definition or 'cycle_start_reference_date' not in pattern.definition:
            raise ValueError("Invalid Rotating pattern definition. Missing 'cycle' or 'cycle_start_reference_date'.")

        cycle_def = pattern.definition['cycle']
        cycle_start_ref_date = date.fromisoformat(pattern.definition['cycle_start_reference_date'])

        total_cycle_days = sum(item['days'] for item in cycle_def)
        if total_cycle_days == 0:
            raise ValueError("Rotating pattern cycle has zero total days.")

        current_date = start_date_obj
        while current_date <= end_date_obj:
            if current_date in holidays_set:
                current_date += timedelta(days=1)
                continue

            exception_def = exceptions.get(current_date.isoformat())
            if exception_def == 'off':
                current_date += timedelta(days=1)
                continue

            days_from_ref = (current_date - cycle_start_ref_date).days
            current_day_in_cycle = days_from_ref % total_cycle_days

            # Determine current segment in cycle
            temp_days_count = 0
            current_segment = None
            for segment in cycle_def:
                if current_day_in_cycle < temp_days_count + segment['days']:
                    current_segment = segment
                    break
                temp_days_count += segment['days']

            if current_segment and current_segment.get('name', '').lower() != 'off':
                shift_name = current_segment['name']
                start_time_str = current_segment.get('start_time')
                end_time_str = current_segment.get('end_time')

                if isinstance(exception_def, dict):
                    shift_name = exception_def.get('name', shift_name)
                    start_time_str = exception_def.get('start_time', start_time_str)
                    end_time_str = exception_def.get('end_time', end_time_str)

                if not start_time_str or not end_time_str:
                    print(f"Warning: Skipping shift for {current_date} due to missing start/end time in segment {shift_name}")
                    current_date += timedelta(days=1)
                    continue

                shift_start_datetime = datetime.combine(current_date, datetime.strptime(start_time_str, "%H:%M").time())
                shift_end_datetime = datetime.combine(current_date, datetime.strptime(end_time_str, "%H:%M").time())

                if shift_end_datetime < shift_start_datetime: # Overnight shift
                    shift_end_datetime += timedelta(days=1)

                from src.shift import Shift # Local import to avoid circular dependency issues at module level
                new_shift = Shift(
                    name=shift_name,
                    start_time=shift_start_datetime,
                    end_time=shift_end_datetime,
                    user_id=user_id,
                    source_pattern_id=pattern_id
                )
                db_session.add(new_shift)
                created_shifts.append(new_shift)

            current_date += timedelta(days=1)

    elif pattern.pattern_type == 'Fixed':
        # Example definition: {"monday": {"name": "Mon Work", "start_time": "09:00", "end_time": "17:00"},
        #                      "tuesday": "Off", ...}
        if not pattern.definition:
            raise ValueError("Invalid Fixed pattern definition. It's empty.")

        current_date = start_date_obj
        while current_date <= end_date_obj:
            if current_date in holidays_set:
                current_date += timedelta(days=1)
                continue

            exception_def = exceptions.get(current_date.isoformat())
            if exception_def == 'off':
                current_date += timedelta(days=1)
                continue

            day_name = current_date.strftime("%A").lower()  # Monday, Tuesday, ...
            segment_def = pattern.definition.get(day_name)

            if isinstance(segment_def, dict) and segment_def.get('name', '').lower() != 'off':
                shift_name = segment_def['name']
                start_time_str = segment_def.get('start_time')
                end_time_str = segment_def.get('end_time')

                if isinstance(exception_def, dict):
                    shift_name = exception_def.get('name', shift_name)
                    start_time_str = exception_def.get('start_time', start_time_str)
                    end_time_str = exception_def.get('end_time', end_time_str)

                if not start_time_str or not end_time_str:
                    print(f"Warning: Skipping fixed shift for {current_date} due to missing start/end time in segment {shift_name}")
                    current_date += timedelta(days=1)
                    continue

                shift_start_datetime = datetime.combine(current_date, datetime.strptime(start_time_str, "%H:%M").time())
                shift_end_datetime = datetime.combine(current_date, datetime.strptime(end_time_str, "%H:%M").time())

                if shift_end_datetime < shift_start_datetime: # Overnight
                    shift_end_datetime += timedelta(days=1)

                from src.shift import Shift # Local import
                new_shift = Shift(
                    name=shift_name,
                    start_time=shift_start_datetime,
                    end_time=shift_end_datetime,
                    user_id=user_id,
                    source_pattern_id=pattern_id
                )
                db_session.add(new_shift)
                created_shifts.append(new_shift)

            current_date += timedelta(days=1)
    else:
        raise ValueError(f"Unsupported pattern type: {pattern.pattern_type}")

    # Commit is done by the caller (API endpoint) to manage session lifecycle
    # db_session.commit()
    return created_shifts

def get_shift_pattern(pattern_id: int):
    db = SessionLocal()
    try:
        pattern = db.query(ShiftPattern).filter(ShiftPattern.id == pattern_id).first()
        return pattern
    except SQLAlchemyError as e:
        print(f"Database error getting shift pattern: {e}")
        return None
    finally:
        db.close()

def get_shift_patterns_for_user(user_id: int):
    db = SessionLocal()
    try:
        patterns = db.query(ShiftPattern).filter(ShiftPattern.user_id == user_id).all()
        return patterns
    except SQLAlchemyError as e:
        print(f"Database error getting user shift patterns: {e}")
        return []
    finally:
        db.close()

def get_global_shift_patterns():
    db = SessionLocal()
    try:
        # Global patterns are those where user_id is NULL
        patterns = db.query(ShiftPattern).filter(ShiftPattern.user_id == None).all()
        return patterns
    except SQLAlchemyError as e:
        print(f"Database error getting global shift patterns: {e}")
        return []
    finally:
        db.close()

def update_shift_pattern(pattern_id: int, name: str = None, description: str = None,
                         pattern_type: str = None, definition: dict = None):
    db = SessionLocal()
    try:
        pattern = db.query(ShiftPattern).filter(ShiftPattern.id == pattern_id).first()
        if not pattern:
            print("Error: Shift pattern not found.")
            return None

        updated = False
        if name is not None:
            pattern.name = name
            updated = True
        if description is not None:
            pattern.description = description
            updated = True
        if pattern_type is not None:
            pattern.pattern_type = pattern_type
            updated = True
        if definition is not None:
            pattern.definition = definition
            updated = True

        if updated:
            db.commit()
            db.refresh(pattern)
        return pattern
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error updating shift pattern: {e}")
        return None
    finally:
        db.close()

def delete_shift_pattern(pattern_id: int):
    db = SessionLocal()
    try:
        pattern = db.query(ShiftPattern).filter(ShiftPattern.id == pattern_id).first()
        if not pattern:
            print("Error: Shift pattern not found for deletion.")
            return False

        db.delete(pattern)
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error deleting shift pattern: {e}")
        return False
    finally:
        db.close()
