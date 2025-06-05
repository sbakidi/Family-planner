from sqlalchemy.exc import SQLAlchemyError
from src.database import SessionLocal
from src.grocery import GroceryItem


def add_item(name: str, quantity: str = None, user_id: int = None):
    db = SessionLocal()
    try:
        item = GroceryItem(name=name, quantity=quantity, user_id=user_id)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error adding grocery item: {e}")
        return None
    finally:
        db.close()


def get_items(user_id: int = None):
    db = SessionLocal()
    try:
        query = db.query(GroceryItem)
        if user_id is not None:
            query = query.filter(GroceryItem.user_id == user_id)
        return query.all()
    except SQLAlchemyError as e:
        print(f"Database error retrieving grocery items: {e}")
        return []
    finally:
        db.close()


def update_item(item_id: int, name: str = None, quantity: str = None, is_completed: bool = None):
    db = SessionLocal()
    try:
        item = db.query(GroceryItem).filter(GroceryItem.id == item_id).first()
        if not item:
            return None
        if name is not None:
            item.name = name
        if quantity is not None:
            item.quantity = quantity
        if is_completed is not None:
            item.is_completed = is_completed
        db.commit()
        db.refresh(item)
        return item
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error updating grocery item: {e}")
        return None
    finally:
        db.close()


def delete_item(item_id: int):
    db = SessionLocal()
    try:
        item = db.query(GroceryItem).filter(GroceryItem.id == item_id).first()
        if not item:
            return False
        db.delete(item)
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error deleting grocery item: {e}")
        return False
    finally:
        db.close()
