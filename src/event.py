from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.database import Base
import datetime # For default values or type hints if needed

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, nullable=True)
    destination = Column(String, nullable=True)
    start_time = Column(DateTime) # Previous: start_time (str)
    end_time = Column(DateTime)   # Previous: end_time (str)

    # Foreign keys to link event to a user and/or a child
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Previous: linked_user_id (str, uuid)
    child_id = Column(Integer, ForeignKey("children.id"), nullable=True) # Previous: linked_child_id (str, uuid)

    # Relationships (optional, but good for accessing related objects)
    # If an event can be linked to a User, this defines how to access that User object
    user = relationship("User") # No back_populates needed if User model doesn't have a direct list of events like this.
                                # If User had `events = relationship("Event")`, then back_populates would be needed here.

    # If an event can be linked to a Child, this defines how to access that Child object
    child = relationship("Child") # Similarly, no back_populates if Child model doesn't have a direct list of events.

    # Removed __init__ as SQLAlchemy handles it.
    # Previous Event model had: event_id, title, description, start_time, end_time, linked_user_id, linked_child_id
    # event_id (uuid) is replaced by id (Integer PK).
    # linked_user_id and linked_child_id are now user_id and child_id, FKs to respective tables.
    # start_time and end_time should be DateTime objects.

    def __repr__(self):
        return f"<Event(id={self.id}, title='{self.title}')>"

    def to_dict(self, include_user=True, include_child=True):
        data = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "destination": self.destination,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "user_id": self.user_id,
            "child_id": self.child_id
        }
        # Optionally include simplified representations of linked user/child
        if include_user and self.user: # self.user is the relationship attribute
            data['user'] = {"id": self.user.id, "name": self.user.name}
        if include_child and self.child: # self.child is the relationship attribute
            data['child'] = {"id": self.child.id, "name": self.child.name}
        return data
