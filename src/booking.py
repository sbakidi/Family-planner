from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.database import Base

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    service = Column(String, index=True)
    start_time = Column(DateTime)
    end_time = Column(DateTime)

    user_id = Column(Integer, ForeignKey("users.id"))
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)

    user = relationship("User")
    event = relationship("Event")

    def __repr__(self):
        return f"<Booking(id={self.id}, service='{self.service}')>"

    def to_dict(self, include_user=True, include_event=True):
        data = {
            "id": self.id,
            "service": self.service,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "user_id": self.user_id,
            "event_id": self.event_id,
        }
        if include_user and self.user:
            data["user"] = {"id": self.user.id, "name": self.user.name}
        if include_event and self.event:
            data["event"] = {"id": self.event.id, "title": self.event.title}
        return data
