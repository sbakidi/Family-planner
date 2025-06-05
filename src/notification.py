import queue
from collections import defaultdict
import json
from src.database import SessionLocal
from src.user import User

# Queues per user for SSE messages
_user_queues = defaultdict(queue.Queue)

def get_user_queue(user_id: int):
    """Return the Queue object for a user."""
    return _user_queues[user_id]

def send_notification(user_id: int, message: dict):
    """Send a notification to a user if they have SSE enabled."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not getattr(user, "prefers_sse", True):
            return
    finally:
        db.close()
    _user_queues[user_id].put(json.dumps(message))
