from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

from src.database import SessionLocal
from src.expense import Expense


def _parse_datetime(dt_str: str):
    if not dt_str:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    print(f"Warning: Could not parse datetime string: {dt_str}")
    return None


def add_expense(description: str, amount: float, paid_by_id: int, child_id: int = None,
                expense_date_str: str = None, notes: str = None):
    db = SessionLocal()
    try:
        expense_date = _parse_datetime(expense_date_str) or datetime.utcnow()
        new_expense = Expense(
            description=description,
            amount=amount,
            paid_by_id=paid_by_id,
            child_id=child_id,
            expense_date=expense_date,
            notes=notes,
        )
        db.add(new_expense)
        db.commit()
        db.refresh(new_expense)
        return new_expense
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error adding expense: {e}")
        return None
    finally:
        db.close()


def get_expense(expense_id: int):
    db = SessionLocal()
    try:
        return db.query(Expense).filter(Expense.id == expense_id).first()
    finally:
        db.close()


def get_expenses_for_child(child_id: int):
    db = SessionLocal()
    try:
        return db.query(Expense).filter(Expense.child_id == child_id).all()
    finally:
        db.close()


def get_all_expenses():
    db = SessionLocal()
    try:
        return db.query(Expense).all()
    finally:
        db.close()


def update_expense(expense_id: int, description: str = None, amount: float = None,
                   paid_by_id: int = None, child_id: int = None,
                   expense_date_str: str = None, notes: str = None):
    db = SessionLocal()
    try:
        exp = db.query(Expense).filter(Expense.id == expense_id).first()
        if not exp:
            print("Expense not found")
            return None
        if description is not None:
            exp.description = description
        if amount is not None:
            exp.amount = amount
        if paid_by_id is not None:
            exp.paid_by_id = paid_by_id
        if child_id is not None:
            exp.child_id = child_id
        if expense_date_str is not None:
            dt = _parse_datetime(expense_date_str)
            if dt:
                exp.expense_date = dt
        if notes is not None:
            exp.notes = notes
        db.commit()
        db.refresh(exp)
        return exp
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error updating expense: {e}")
        return None
    finally:
        db.close()


def delete_expense(expense_id: int):
    db = SessionLocal()
    try:
        exp = db.query(Expense).filter(Expense.id == expense_id).first()
        if not exp:
            return False
        db.delete(exp)
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error deleting expense: {e}")
        return False
    finally:
        db.close()

