import unittest
import json
import os
import hashlib
import sys

if os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) not in sys.path:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ["TEST_MODE_ENABLED"] = "1"

from app import app
from src.database import initialize_database_for_application, create_tables, drop_tables, SessionLocal
from src.user import User
from src.grocery import GroceryItem


class TestAPIGrocery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        initialize_database_for_application()
        app.config['TESTING'] = True
        create_tables()

    @classmethod
    def tearDownClass(cls):
        drop_tables()
        if "TEST_MODE_ENABLED" in os.environ:
            del os.environ["TEST_MODE_ENABLED"]

    def setUp(self):
        self.client = app.test_client()
        self.db = SessionLocal()
        self.db.query(GroceryItem).delete()
        self.db.query(User).delete()
        self.db.commit()
        self.user = self._create_user_directly("Gro User", "gro@example.com", "pass")

    def tearDown(self):
        self.db.query(GroceryItem).delete()
        self.db.query(User).delete()
        self.db.commit()
        self.db.close()

    def _create_user_directly(self, name, email, password):
        hashed = hashlib.sha256(password.encode()).hexdigest()
        user = User(name=name, email=email, hashed_password=hashed)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def test_full_grocery_item_flow(self):
        # Create item
        resp = self.client.post('/grocery-items', json={"name": "Milk", "quantity": "2", "user_id": self.user.id})
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        item_id = data['id']
        self.assertEqual(data['name'], "Milk")

        # List items
        resp = self.client.get(f'/grocery-items?user_id={self.user.id}')
        self.assertEqual(resp.status_code, 200)
        items = resp.get_json()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['id'], item_id)

        # Update item
        resp = self.client.put(f'/grocery-items/{item_id}', json={"is_completed": True})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()['is_completed'])

        # Delete item
        resp = self.client.delete(f'/grocery-items/{item_id}')
        self.assertEqual(resp.status_code, 200)
        # Ensure deleted
        resp = self.client.get(f'/grocery-items?user_id={self.user.id}')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.get_json()), 0)


if __name__ == '__main__':
    unittest.main()
