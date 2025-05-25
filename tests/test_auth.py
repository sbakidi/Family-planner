import unittest
import sys
import os
import hashlib

# Adjust the path to include the root directory of the project
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set environment variable for test database BEFORE importing database and models
os.environ["TEST_MODE_ENABLED"] = "1"

from src.database import initialize_database_for_application, create_tables, drop_tables, SessionLocal, Base, engine
from src.user import User # SQLAlchemy User model
from src import auth # Auth module using SQLAlchemy

class TestAuth(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Initialize the database (and engine, SessionLocal) for the test environment
        initialize_database_for_application()
        # Ensure all models are known to Base
        # This might require importing all model files if not already done by initialize_database_for_application
        # For example: from src import user, shift, child, event # if they define models
        
    def setUp(self):
        # Create tables before each test
        # This ensures models are registered with Base.metadata
        # from src import user, shift, child, event # Ensure models are loaded
        create_tables()
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()
        # Drop tables after each test
        drop_tables()

    def test_register_new_user(self):
        # Call the register function (which now uses SQLAlchemy)
        registered_user = auth.register("Test User", "test@example.com", "password123")
        self.assertIsNotNone(registered_user)
        self.assertEqual(registered_user.name, "Test User")
        self.assertEqual(registered_user.email, "test@example.com")
        self.assertIsNotNone(registered_user.id) # Check if ID was assigned by DB

        # Verify in DB
        user_in_db = self.db.query(User).filter_by(email="test@example.com").first()
        self.assertIsNotNone(user_in_db)
        self.assertEqual(user_in_db.name, "Test User")
        self.assertEqual(user_in_db.id, registered_user.id)
        
        # Check hashed password (optional, implementation detail)
        expected_hash = hashlib.sha256("password123".encode()).hexdigest()
        self.assertEqual(user_in_db.hashed_password, expected_hash)

    def test_register_existing_user(self):
        # First, register a user
        auth.register("Test User", "test@example.com", "password123")
        
        # Try to register the same email again
        user2 = auth.register("Another User", "test@example.com", "password456")
        self.assertIsNone(user2) # Should return None if email already exists

        # Verify only one user with this email exists in DB
        count = self.db.query(User).filter_by(email="test@example.com").count()
        self.assertEqual(count, 1)

    def test_login_correct_credentials(self):
        # Register a user first (directly or via auth.register)
        auth.register("Test User", "test@example.com", "password123")
        
        # Try to login
        logged_in_user = auth.login("test@example.com", "password123")
        self.assertIsNotNone(logged_in_user)
        self.assertEqual(logged_in_user.name, "Test User")
        self.assertEqual(logged_in_user.email, "test@example.com")

    def test_login_non_existent_user(self):
        logged_in_user = auth.login("nonexistent@example.com", "password123")
        self.assertIsNone(logged_in_user)

    def test_login_incorrect_password(self):
        auth.register("Test User", "test@example.com", "password123")
        
        logged_in_user = auth.login("test@example.com", "wrongpassword")
        self.assertIsNone(logged_in_user)

    def test_logout(self):
        # Logout is a simple print and pass in the current implementation.
        # Test that it executes without error.
        try:
            auth.logout()
        except Exception as e:
            self.fail(f"auth.logout() raised an exception {e}")

if __name__ == '__main__':
    # This allows running tests directly.
    # Ensure TEST_MODE_ENABLED is set if running this file directly.
    # `python -m unittest tests.test_auth` from root is preferred.
    unittest.main()
