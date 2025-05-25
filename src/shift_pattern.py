from sqlalchemy import Column, Integer, String, JSON, ForeignKey
from sqlalchemy.orm import relationship
from src.database import Base

class ShiftPattern(Base):
    __tablename__ = 'shift_patterns'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    pattern_type = Column(String, nullable=False)  # e.g., 'Fixed', 'Rotating', 'OnDemand'
    definition = Column(JSON, nullable=False) 
    # Example for Rotating: {"cycle": [{"shift_type_name": "Day", "days": 2}, ...], "start_date_of_cycle": "YYYY-MM-DD"}
    # Example for Fixed: {"monday": "Day Shift", "tuesday": "Day Shift", ...}

    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)  # Nullable for global patterns
    owner = relationship("User", back_populates="shift_patterns") # Relationship to User

    def to_dict(self):
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "pattern_type": self.pattern_type,
            "definition": self.definition,
            "user_id": self.user_id
        }
        if self.owner:
            data['owner'] = {"id": self.owner.id, "name": self.owner.name}
        return data

    def __repr__(self):
        return f"<ShiftPattern(id={self.id}, name='{self.name}', user_id={self.user_id})>"
