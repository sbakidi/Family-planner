import unittest
import sys
import os

# Adjust the path to include the root directory of the project
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.user import User
from src import auth # Import the auth module

class TestAuth(unittest.TestCase):

    def setUp(self):
        # Reset the in-memory database before each test
        auth.users_db.clear()

    def test_register_new_user(self):
        user = auth.register("Test User", "test@example.com", "password123")
        self.assertIsNotNone(user)
        self.assertIsInstance(user, User)
        self.assertEqual(user.name, "Test User")
        self.assertEqual(user.email, "test@example.com")
        self.assertIn("test@example.com", auth.users_db)
        self.assertEqual(auth.users_db["test@example.com"]['name'], "Test User")

    def test_register_existing_user(self):
        auth.register("Test User", "test@example.com", "password123")
        user2 = auth.register("Another User", "test@example.com", "password456")
        self.assertIsNone(user2) # Should return None if email already exists

    def test_login_correct_credentials(self):
        auth.register("Test User", "test@example.com", "password123")
        user = auth.login("test@example.com", "password123")
        self.assertIsNotNone(user)
        self.assertIsInstance(user, User)
        self.assertEqual(user.name, "Test User")
        self.assertEqual(user.email, "test@example.com")

    def test_login_non_existent_user(self):
        user = auth.login("nonexistent@example.com", "password123")
        self.assertIsNone(user)

    def test_login_incorrect_password(self):
        auth.register("Test User", "test@example.com", "password123")
        user = auth.login("test@example.com", "wrongpassword")
        self.assertIsNone(user)

    def test_logout(self):
        # Logout is a simple print and pass, so just ensure it runs without error
        try:
            auth.logout()
        except Exception as e:
            self.fail(f"logout() raised an exception {e}")

if __name__ == '__main__':
    unittest.main()
