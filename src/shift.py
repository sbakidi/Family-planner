from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.database import Base
from zoneinfo import ZoneInfo
# Removed unused import: import datetime

class Shift(Base):
    __tablename__ = "shifts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    start_time = Column(DateTime)
    end_time = Column(DateTime)

    user_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="shifts")

    # Link to the ShiftPattern that generated this shift
    source_pattern_id = Column(Integer, ForeignKey('shift_patterns.id'), nullable=True)
    source_pattern = relationship("ShiftPattern") # No back_populates needed if ShiftPattern doesn't list shifts

    def __repr__(self):
        return f"<Shift(id={self.id}, name='{self.name}', user_id={self.user_id}, source_pattern_id={self.source_pattern_id})>"

    def to_dict(self, include_owner=True, include_source_pattern_details=False, timezone='UTC'):
        local_start = self.start_time.replace(tzinfo=ZoneInfo('UTC')).astimezone(ZoneInfo(timezone)) if self.start_time else None
        local_end = self.end_time.replace(tzinfo=ZoneInfo('UTC')).astimezone(ZoneInfo(timezone)) if self.end_time else None
        data = {
            "id": self.id,
            "name": self.name,
            "start_time": local_start.isoformat() if local_start else None,
            "end_time": local_end.isoformat() if local_end else None,
            "user_id": self.user_id,
            "source_pattern_id": self.source_pattern_id
        }
        if include_owner and self.owner:
            data['owner'] = {"id": self.owner.id, "name": self.owner.name}

        if include_source_pattern_details and self.source_pattern:
            # Simple representation of the source pattern
            data['source_pattern_details'] = {
                "id": self.source_pattern.id,
                "name": self.source_pattern.name,
                "pattern_type": self.source_pattern.pattern_type
            }
        elif self.source_pattern_id and not self.source_pattern:
             # If ID is there but object not loaded, just include ID (already done)
             pass
        return data
