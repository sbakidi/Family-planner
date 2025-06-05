from sqlalchemy import Column, Integer, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from src.database import Base

class Consent(Base):
    __tablename__ = "consents"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(Integer, ForeignKey('children.id'), nullable=False)
    institution_id = Column(Integer, ForeignKey('institutions.id'), nullable=False)
    approved = Column(Boolean, default=True)

    child = relationship("Child")
    institution = relationship("Institution")

    __table_args__ = (UniqueConstraint('child_id', 'institution_id', name='_child_institution_uc'),)

    def to_dict(self, include_child=False, include_institution=False):
        data = {
            "id": self.id,
            "child_id": self.child_id,
            "institution_id": self.institution_id,
            "approved": self.approved
        }
        if include_child and self.child:
            data['child'] = {"id": self.child.id, "name": self.child.name}
        if include_institution and self.institution:
            data['institution'] = {"id": self.institution.id, "name": self.institution.name}
        return data
