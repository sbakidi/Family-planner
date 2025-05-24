import uuid
from src.shift import Shift

shifts_storage = []  # In-memory store for Shift objects

def add_shift(user_id, start_time, end_time, name):
    shift_id = uuid.uuid4().hex
    new_shift = Shift(shift_id=shift_id, user_id=user_id, start_time=start_time, end_time=end_time, name=name)
    shifts_storage.append(new_shift)
    return new_shift

def get_user_shifts(user_id):
    user_shifts = [shift for shift in shifts_storage if shift.user_id == user_id]
    return user_shifts

def update_shift(shift_id, new_start_time=None, new_end_time=None, new_name=None):
    for shift in shifts_storage:
        if shift.shift_id == shift_id:
            if new_start_time is not None:
                shift.start_time = new_start_time
            if new_end_time is not None:
                shift.end_time = new_end_time
            if new_name is not None:
                shift.name = new_name
            return shift  # Or True
    return None  # Or False

def delete_shift(shift_id):
    global shifts_storage
    original_length = len(shifts_storage)
    shifts_storage = [shift for shift in shifts_storage if shift.shift_id != shift_id]
    return len(shifts_storage) < original_length
