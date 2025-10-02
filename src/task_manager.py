from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

from src.database import SessionLocal
from src.task import Task


def _parse_datetime(datetime_str):
    if not datetime_str:
        return None
    try:
        return datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
    except ValueError:
        print(f"Warning: Could not parse datetime string: {datetime_str}")
        return None


def create_task(description, due_date_str=None, user_id=None, event_id=None):
    db = SessionLocal()
    try:
        due_dt = _parse_datetime(due_date_str) if due_date_str else None
        new_task = Task(
            description=description,
            due_date=due_dt,
            user_id=user_id,
            event_id=event_id,
            completed=False,
        )
        db.add(new_task)
        db.commit()
        db.refresh(new_task)
        return new_task
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error creating task: {e}")
        return None
    finally:
        db.close()


def get_task_details(task_id):
    db = SessionLocal()
    try:
        return db.query(Task).filter(Task.id == task_id).first()
    except SQLAlchemyError as e:
        print(f"Database error getting task details: {e}")
        return None
    finally:
        db.close()


def get_tasks_for_user(user_id):
    db = SessionLocal()
    try:
        return db.query(Task).filter(Task.user_id == user_id).all()
    except SQLAlchemyError as e:
        print(f"Database error getting tasks for user: {e}")
        return []
    finally:
        db.close()


def get_tasks_for_event(event_id):
    db = SessionLocal()
    try:
        return db.query(Task).filter(Task.event_id == event_id).all()
    except SQLAlchemyError as e:
        print(f"Database error getting tasks for event: {e}")
        return []
    finally:
        db.close()


def update_task(task_id, description=None, due_date_str=None, user_id=None, event_id=None, completed=None, unlink_user=False, unlink_event=False):
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            print("Error: Task not found.")
            return None

        updated = False
        if description is not None:
            task.description = description
            updated = True
        if due_date_str is not None:
            due_dt = _parse_datetime(due_date_str)
            if due_dt:
                task.due_date = due_dt
                updated = True
        if unlink_user:
            task.user_id = None
            updated = True
        elif user_id is not None:
            task.user_id = user_id
            updated = True
        if unlink_event:
            task.event_id = None
            updated = True
        elif event_id is not None:
            task.event_id = event_id
            updated = True
        if completed is not None:
            task.completed = bool(completed)
            updated = True
        if updated:
            db.commit()
            db.refresh(task)
        return task
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error updating task: {e}")
        return None
    finally:
        db.close()


def delete_task(task_id):
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            print("Error: Task not found for deletion.")
            return False
        db.delete(task)
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error deleting task: {e}")
        return False
    finally:
        db.close()
