import unittest
import json
import os
import hashlib
import sys

# Adjust the path to include the root directory of the project
# This is crucial for the test runner to find the 'app' module and 'src'
sys_path_updated = False
if os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) not in sys.path:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    sys_path_updated = True


# Set environment variable for test database BEFORE importing app and database modules
os.environ["TEST_MODE_ENABLED"] = "1"

from app import app # Flask app instance
from src.database import initialize_database_for_application, create_tables, drop_tables, SessionLocal, Base, engine
from src.user import User # SQLAlchemy User model

class TestAuthAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Initialize the database (and engine, SessionLocal) for the test environment
        initialize_database_for_application()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False # Disable CSRF for testing forms if any; API tests usually don't need this
        app.config['SECRET_KEY'] = 'test_secret_key' # Ensure a secret key for session, etc.

        # Create tables after engine is configured for test DB
        # Ensure all models are imported so Base knows about them.
        # This should ideally be handled by having a central models import, e.g., in src/__init__.py
        # or by importing them explicitly here.
        from src import user, shift, child, event, shift_pattern, residency_period, api_token
        # Import all models including tokens
        create_tables()

    @classmethod
    def tearDownClass(cls):
        drop_tables()
        if "TEST_MODE_ENABLED" in os.environ:
            del os.environ["TEST_MODE_ENABLED"]
        # If path was updated, optionally remove it, though usually not necessary for test runs
        # global sys_path_updated
        # if sys_path_updated and os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) in sys.path:
        #     sys.path.pop(0)


    def setUp(self):
        self.client = app.test_client()
        self.db = SessionLocal()
        # Clean the User table before each test to ensure isolation
        self.db.query(User).delete()
        self.db.commit()

    def tearDown(self):
        self.db.query(User).delete() # Clean up any users created if a test failed before its own cleanup
        self.db.commit()
        self.db.close()

    def _register_user_api(self, name="Test User", email="test@example.com", password="password123"):
        return self.client.post('/api/v1/auth/register', json={
            "name": name,
            "email": email,
            "password": password
        })

    def test_register_success(self):
        response = self._register_user_api()
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data['message'], "User registered successfully")
        self.assertIn('user_id', data)
        self.assertEqual(data['name'], "Test User")

        # Verify user in DB
        user_in_db = self.db.query(User).filter_by(email="test@example.com").first()
        self.assertIsNotNone(user_in_db)
        self.assertEqual(user_in_db.name, "Test User")
        self.assertEqual(user_in_db.id, data['user_id'])

    def test_register_missing_fields(self):
        response = self.client.post('/api/v1/auth/register', json={"name": "Test"})
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("Missing", data['message'])

        response_missing_email = self.client.post('/api/v1/auth/register', json={
            "name": "Another User", "password": "password123"
        })
        self.assertEqual(response_missing_email.status_code, 400)

    def test_register_email_exists(self):
        self._register_user_api(email="exists@example.com") # First registration
        response = self._register_user_api(name="Another Name", email="exists@example.com", password="newpassword") # Second attempt
        self.assertEqual(response.status_code, 409) # Conflict
        data = response.get_json()
        self.assertEqual(data['message'], "Email already exists.")

    def test_login_success(self):
        # Register a user first
        reg_response = self._register_user_api(email="login_test@example.com", password="password123")
        self.assertEqual(reg_response.status_code, 201)

        # Attempt login
        response = self.client.post('/api/v1/auth/login', json={
            "email": "login_test@example.com",
            "password": "password123"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['message'], "Login successful")
        self.assertIn('user_id', data)
        self.assertEqual(data['email'], "login_test@example.com")

    def test_login_wrong_password(self):
        self._register_user_api(email="wrongpass@example.com", password="correctpassword")

        response = self.client.post('/api/v1/auth/login', json={
            "email": "wrongpass@example.com",
            "password": "incorrectpassword"
        })
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertEqual(data['message'], "Login failed: Invalid email or password.")

    def test_otp_endpoints(self):
        reg_response = self._register_user_api(email="otp_api@example.com")
        user_id = reg_response.get_json()['user_id']
        gen_resp = self.client.post('/auth/otp/generate', json={"user_id": user_id})
        self.assertEqual(gen_resp.status_code, 200)
        otp = gen_resp.get_json()['otp']
        verify_resp = self.client.post('/auth/otp/verify', json={"user_id": user_id, "otp": otp})
        self.assertEqual(verify_resp.status_code, 200)

    def test_login_user_not_found(self):
        response = self.client.post('/api/v1/auth/login', json={
            "email": "nosuchuser@example.com",
            "password": "password123"
        })
        self.assertEqual(response.status_code, 401) # auth.login returns None, API translates to 401
        data = response.get_json()
        self.assertEqual(data['message'], "Login failed: Invalid email or password.")


    def test_logout_success(self):
        # Logout is stateless for the API, just returns a message
        response = self.client.post('/api/v1/auth/logout')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['message'], "Logout successful")

if __name__ == '__main__':
    unittest.main()
