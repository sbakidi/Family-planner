from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database import Base

class Expense(Base):
    __tablename__ = 'expenses'

    id = Column(Integer, primary_key=True, index=True)
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    paid_by_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    child_id = Column(Integer, ForeignKey('children.id'), nullable=True)
    expense_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    notes = Column(String, nullable=True)

    payer = relationship("User")
    child = relationship("Child")

    def to_dict(self, include_payer=True, include_child=True):
        data = {
            "id": self.id,
            "description": self.description,
            "amount": self.amount,
            "paid_by_id": self.paid_by_id,
            "child_id": self.child_id,
            "expense_date": self.expense_date.isoformat() if self.expense_date else None,
            "notes": self.notes,
        }
        if include_payer and self.payer:
            data["payer"] = {"id": self.payer.id, "name": self.payer.name}
        if include_child and self.child:
            data["child"] = {"id": self.child.id, "name": self.child.name}
        return data

    def __repr__(self):
        return f"<Expense(id={self.id}, desc='{self.description}', amount={self.amount})>"
