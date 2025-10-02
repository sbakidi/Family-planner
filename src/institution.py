from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from src.database import Base

class Institution(Base):
    __tablename__ = "institutions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    type = Column(String)
    api_key = Column(String, unique=True, nullable=False)

    events = relationship("Event", back_populates="institution")
    treatment_plans = relationship("TreatmentPlan", back_populates="institution")

    def to_dict(self):
        return {"id": self.id, "name": self.name, "type": self.type}
