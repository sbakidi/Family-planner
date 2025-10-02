from datetime import datetime
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from src.database import SessionLocal
from src.budget import ExpenseCategory, ExpenseTransaction


def add_category(name: str):
    db = SessionLocal()
    try:
        category = ExpenseCategory(name=name)
        db.add(category)
        db.commit()
        db.refresh(category)
        return category
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error adding category: {e}")
        return None
    finally:
        db.close()


def get_categories():
    db = SessionLocal()
    try:
        return db.query(ExpenseCategory).all()
    finally:
        db.close()


def add_transaction(category_id: int, amount: float, date_str: str, description: str = None):
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        print("Invalid date format for transaction.")
        return None

    db = SessionLocal()
    try:
        tx = ExpenseTransaction(
            description=description,
            amount=amount,
            date=date_obj,
            category_id=category_id
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)
        return tx
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error adding transaction: {e}")
        return None
    finally:
        db.close()


def get_transactions():
    db = SessionLocal()
    try:
        return db.query(ExpenseTransaction).order_by(ExpenseTransaction.date.desc()).all()
    finally:
        db.close()


def get_monthly_summary(year: int, month: int):
    db = SessionLocal()
    try:
        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date()
        else:
            end_date = datetime(year, month + 1, 1).date()

        results = (
            db.query(ExpenseCategory.name, func.sum(ExpenseTransaction.amount))
            .join(ExpenseTransaction.category)
            .filter(ExpenseTransaction.date >= start_date, ExpenseTransaction.date < end_date)
            .group_by(ExpenseCategory.name)
            .all()
        )
        return {name: total for name, total in results}
    finally:
        db.close()
