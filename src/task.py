from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from src.database import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(String, nullable=False)
    due_date = Column(DateTime, nullable=True)
    completed = Column(Boolean, default=False)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)

    user = relationship("User")
    event = relationship("Event")

    def __repr__(self):
        return f"<Task(id={self.id}, description='{self.description}')>"

    def to_dict(self, include_user=True, include_event=True):
        data = {
            "id": self.id,
            "description": self.description,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "completed": self.completed,
            "user_id": self.user_id,
            "event_id": self.event_id,
        }
        if include_user and self.user:
            data["user"] = {"id": self.user.id, "name": self.user.name}
        if include_event and self.event:
            data["event"] = {"id": self.event.id, "title": self.event.title}
        return data
