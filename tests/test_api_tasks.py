import unittest
import os
import hashlib
import sys
from datetime import datetime

sys_path_updated = False
if os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) not in sys.path:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    sys_path_updated = True

os.environ["TEST_MODE_ENABLED"] = "1"

from app import app
from src.database import initialize_database_for_application, create_tables, drop_tables, SessionLocal
from src.user import User
from src.event import Event
from src.task import Task

class TestAPITasks(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database_for_application()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SECRET_KEY'] = 'test_secret_key_tasks'
        from src import user, shift, child, event, task, shift_pattern, residency_period
        create_tables()

    @classmethod
    def tearDownClass(cls):
        drop_tables()
        if "TEST_MODE_ENABLED" in os.environ:
            del os.environ["TEST_MODE_ENABLED"]

    def setUp(self):
        self.client = app.test_client()
        self.db = SessionLocal()
        self.db.query(Task).delete()
        self.db.query(Event).delete()
        self.db.query(User).delete()
        self.db.commit()

        self.user = self._create_user("Task User", "taskuser@example.com", "pass")
        self.event = self._create_event_for_user(self.user.id, "Task Event")

    def tearDown(self):
        self.db.query(Task).delete()
        self.db.query(Event).delete()
        self.db.query(User).delete()
        self.db.commit()
        self.db.close()

    def _create_user(self, name, email, password):
        hashed = hashlib.sha256(password.encode()).hexdigest()
        user = User(name=name, email=email, hashed_password=hashed)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def _create_event_for_user(self, user_id, title):
        event = Event(title=title, start_time=datetime(2024,1,1,10,0), end_time=datetime(2024,1,1,11,0), user_id=user_id)
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def _create_task_api(self, description, due_date=None, user_id=None, event_id=None):
        payload = {"description": description}
        if due_date:
            payload["due_date"] = due_date
        if user_id:
            payload["user_id"] = user_id
        if event_id:
            payload["event_id"] = event_id
        return self.client.post('/tasks', json=payload)

    # --- Tests ---
    def test_create_task_for_user_success(self):
        response = self._create_task_api("Buy milk", user_id=self.user.id)
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data['description'], "Buy milk")
        self.assertEqual(data['user_id'], self.user.id)
        task_in_db = self.db.query(Task).get(data['id'])
        self.assertIsNotNone(task_in_db)

    def test_get_task_details_success(self):
        res = self._create_task_api("Do homework", user_id=self.user.id, event_id=self.event.id)
        task_id = res.get_json()['id']
        response = self.client.get(f'/tasks/{task_id}')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['id'], task_id)
        self.assertEqual(data['event_id'], self.event.id)

    def test_get_tasks_for_user(self):
        self._create_task_api("A", user_id=self.user.id)
        self._create_task_api("B", user_id=self.user.id)
        response = self.client.get(f'/users/{self.user.id}/tasks')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data), 2)

    def test_update_task_completion(self):
        res = self._create_task_api("Finish project", user_id=self.user.id)
        task_id = res.get_json()['id']
        response = self.client.put(f'/tasks/{task_id}', json={"completed": True})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['completed'])
        self.assertTrue(self.db.query(Task).get(task_id).completed)

    def test_delete_task(self):
        res = self._create_task_api("Old Task", user_id=self.user.id)
        task_id = res.get_json()['id']
        response = self.client.delete(f'/tasks/{task_id}')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(self.db.query(Task).get(task_id))

if __name__ == '__main__':
    unittest.main()
