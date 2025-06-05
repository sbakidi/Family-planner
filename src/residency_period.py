from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.database import Base

class ResidencyPeriod(Base):
    __tablename__ = 'residency_periods'

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(Integer, ForeignKey('children.id'), nullable=False)
    parent_id = Column(Integer, ForeignKey('users.id'), nullable=False) # The parent with whom the child resides
    start_datetime = Column(DateTime, nullable=False)
    end_datetime = Column(DateTime, nullable=False)
    notes = Column(String, nullable=True)

    # Relationships
    child = relationship("Child", back_populates="residency_periods")
    parent = relationship("User") # Assuming User model does not need a back_populates like "custodial_periods" for now

    def to_dict(self, include_child=False, include_parent=True):
        data = {
            "id": self.id,
            "child_id": self.child_id,
            "parent_id": self.parent_id,
            "start_datetime": self.start_datetime.isoformat() if self.start_datetime else None,
            "end_datetime": self.end_datetime.isoformat() if self.end_datetime else None,
            "notes": self.notes
        }
        if include_child and self.child:
            data['child'] = {"id": self.child.id, "name": self.child.name}
        if include_parent and self.parent:
            data['parent'] = {"id": self.parent.id, "name": self.parent.name}
        return data

    def __repr__(self):
        return f"<ResidencyPeriod(id={self.id}, child_id={self.child_id}, parent_id={self.parent_id}, start='{self.start_datetime}', end='{self.end_datetime}')>"
