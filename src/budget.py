from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import relationship

from src.database import Base

class ExpenseCategory(Base):
    __tablename__ = "expense_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

    transactions = relationship("ExpenseTransaction", back_populates="category")

    def __repr__(self):
        return f"<ExpenseCategory(id={self.id}, name='{self.name}')>"

    def to_dict(self, include_transactions=False):
        data = {
            "id": self.id,
            "name": self.name
        }
        if include_transactions:
            data["transactions"] = [t.to_dict(include_category=False) for t in self.transactions]
        return data

class ExpenseTransaction(Base):
    __tablename__ = "expense_transactions"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(String, nullable=True)
    amount = Column(Float)
    date = Column(Date)
    category_id = Column(Integer, ForeignKey("expense_categories.id"))

    category = relationship("ExpenseCategory", back_populates="transactions")

    def __repr__(self):
        return f"<ExpenseTransaction(id={self.id}, amount={self.amount})>"

    def to_dict(self, include_category=True):
        data = {
            "id": self.id,
            "description": self.description,
            "amount": self.amount,
            "date": self.date.isoformat() if self.date else None,
            "category_id": self.category_id
        }
        if include_category and self.category:
            data["category"] = {"id": self.category.id, "name": self.category.name}
        return data
