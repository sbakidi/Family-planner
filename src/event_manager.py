import uuid
from src.event import Event

events_storage = []  # In-memory store for Event objects

def create_event(title, description, start_time, end_time, linked_user_id=None, linked_child_id=None):
    event_id = uuid.uuid4().hex
    new_event = Event(event_id=event_id, title=title, description=description, 
                      start_time=start_time, end_time=end_time)
    if linked_user_id:
        new_event.linked_user_id = linked_user_id
    if linked_child_id:
        new_event.linked_child_id = linked_child_id
    
    events_storage.append(new_event)
    return new_event

def get_event_details(event_id):
    for event in events_storage:
        if event.event_id == event_id:
            return event
    return None

def get_events_for_user(user_id):
    user_events = [event for event in events_storage if event.linked_user_id == user_id]
    return user_events

def get_events_for_child(child_id):
    child_events = [event for event in events_storage if event.linked_child_id == child_id]
    return child_events

def update_event(event_id, title=None, description=None, start_time=None, end_time=None, linked_user_id=None, linked_child_id=None):
    event = get_event_details(event_id)
    if event:
        if title is not None:
            event.title = title
        if description is not None:
            event.description = description
        if start_time is not None:
            event.start_time = start_time
        if end_time is not None:
            event.end_time = end_time
        if linked_user_id is not None: # Consider how to handle unlinking: linked_user_id = "" or None
            event.linked_user_id = linked_user_id
        if linked_child_id is not None: # Consider how to handle unlinking
            event.linked_child_id = linked_child_id
        return event # Or True
    return None # Or False

def delete_event(event_id):
    global events_storage
    original_length = len(events_storage)
    events_storage = [event for event in events_storage if event.event_id != event_id]
    return len(events_storage) < original_length
