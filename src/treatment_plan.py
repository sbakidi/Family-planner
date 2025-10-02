from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from src.database import Base

class TreatmentPlan(Base):
    __tablename__ = "treatment_plans"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(Integer, ForeignKey('children.id'), nullable=False)
    institution_id = Column(Integer, ForeignKey('institutions.id'), nullable=False)
    description = Column(String)
    start_date = Column(Date)
    end_date = Column(Date)

    child = relationship("Child")
    institution = relationship("Institution", back_populates="treatment_plans")

    def to_dict(self):
        return {
            "id": self.id,
            "child_id": self.child_id,
            "institution_id": self.institution_id,
            "description": self.description,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
        }
