from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.database import Base
from src.user import user_child_association_table
# Import ResidencyPeriod for the relationship
from src.residency_period import ResidencyPeriod

class Child(Base):
    __tablename__ = "children"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    date_of_birth = Column(DateTime)
    school_info = Column(String, nullable=True)
    # custody_schedule_info = Column(String, nullable=True) # Marked for deprecation/replacement

    # Many-to-Many relationship with User (Parents)
    parents = relationship(
        "User",
        secondary=user_child_association_table,
        back_populates="children"
    )

    # One-to-Many relationship with ResidencyPeriod
    residency_periods = relationship("ResidencyPeriod", back_populates="child", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Child(id={self.id}, name='{self.name}')>"

    def to_dict(self, include_parents=True, include_events=False, include_residency_periods=False):
        data = {
            "id": self.id,
            "name": self.name,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "school_info": self.school_info
            # "custody_schedule_info": self.custody_schedule_info # Deprecated
        }
        if include_parents and self.parents:
            data['parents'] = [{"id": parent.id, "name": parent.name} for parent in self.parents]

        # Placeholder for events if that relationship exists and is needed
        # if include_events and hasattr(self, 'events'):
        # data['events'] = [event.to_dict(include_child=False) for event in self.events]

        if include_residency_periods and self.residency_periods:
            data['residency_periods'] = [period.to_dict(include_child=False) for period in self.residency_periods]
        return data
