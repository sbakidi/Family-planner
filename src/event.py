class Event:
    def __init__(self, event_id, title, description, start_time, end_time):
        self.event_id = event_id
        self.title = title
        self.description = description
        self.start_time = start_time
        self.end_time = end_time
        self.linked_user_id = None  # Placeholder for linked user ID
        self.linked_child_id = None  # Placeholder for linked child ID
