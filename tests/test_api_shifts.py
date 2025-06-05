import unittest
import json
import os
import hashlib # For direct user creation if needed, though auth API is preferred
import sys
from datetime import datetime, timedelta
import sys

# Adjust path
sys_path_updated = False
if os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) not in sys.path:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    sys_path_updated = True

os.environ["TEST_MODE_ENABLED"] = "1"

from app import app
from src.database import initialize_database_for_application, create_tables, drop_tables, SessionLocal, Base
from src.user import User
from src.shift import Shift
from src.shift_pattern import ShiftPattern

class TestAPIShifts(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database_for_application()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SECRET_KEY'] = 'test_secret_key_shifts'
        from src import user, shift, child, event, shift_pattern, residency_period # Ensure all models are known
        create_tables()

    @classmethod
    def tearDownClass(cls):
        drop_tables()
        if "TEST_MODE_ENABLED" in os.environ:
            del os.environ["TEST_MODE_ENABLED"]

    def setUp(self):
        self.client = app.test_client()
        self.db = SessionLocal()
        # Clean relevant tables before each test
        self.db.query(Shift).delete()
        self.db.query(ShiftPattern).delete()
        self.db.query(User).delete() # Users are prerequisites
        self.db.commit()

        # Create a default user for many tests
        self.test_user = self._create_user_directly(name="Default User", email="default@example.com", password="password")

    def tearDown(self):
        self.db.query(Shift).delete()
        self.db.query(ShiftPattern).delete()
        self.db.query(User).delete()
        self.db.commit()
        self.db.close()

    def _create_user_directly(self, name="Test User", email="test@example.com", password="password"):
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        user = User(name=name, email=email, hashed_password=hashed_password)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    # --- Test Methods for Shift Patterns ---
    def test_create_global_shift_pattern_success(self):
        response = self.client.post('/shift-patterns', json={
            "name": "Global Morning Pattern",
            "pattern_type": "Fixed",
            "definition": {"monday": {"name": "Morning", "start_time": "08:00", "end_time": "12:00"}}
        })
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data['name'], "Global Morning Pattern")
        self.assertIsNone(data['user_id'])
        pattern_in_db = self.db.query(ShiftPattern).filter_by(id=data['id']).first()
        self.assertIsNotNone(pattern_in_db)
        self.assertEqual(pattern_in_db.name, "Global Morning Pattern")

    def test_create_user_shift_pattern_success(self):
        response = self.client.post(f'/users/{self.test_user.id}/shift-patterns', json={
            "name": "User Specific Pattern",
            "pattern_type": "Rotating",
            "definition": {"cycle": [], "cycle_start_reference_date": "2024-01-01"}
        })
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data['name'], "User Specific Pattern")
        self.assertEqual(data['user_id'], self.test_user.id)
        pattern_in_db = self.db.query(ShiftPattern).get(data['id'])
        self.assertIsNotNone(pattern_in_db)
        self.assertEqual(pattern_in_db.user_id, self.test_user.id)

    def test_get_shift_pattern_success(self):
        pattern = ShiftPattern(name="Test Get Pattern", pattern_type="Fixed", definition={}, user_id=self.test_user.id)
        self.db.add(pattern)
        self.db.commit()
        response = self.client.get(f'/shift-patterns/{pattern.id}')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['name'], "Test Get Pattern")

    def test_get_shift_pattern_not_found(self):
        response = self.client.get('/shift-patterns/99999')
        self.assertEqual(response.status_code, 404)

    def test_get_global_shift_patterns(self):
        ShiftPattern.user_id = None # For static analysis if it complains
        p1 = ShiftPattern(name="Global 1", pattern_type="Fixed", definition={}, user_id=None)
        p2 = ShiftPattern(name="User 1", pattern_type="Fixed", definition={}, user_id=self.test_user.id)
        self.db.add_all([p1, p2])
        self.db.commit()
        response = self.client.get('/shift-patterns')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], "Global 1")

    def test_get_user_shift_patterns(self):
        p1 = ShiftPattern(name="User Pattern A", pattern_type="Fixed", definition={}, user_id=self.test_user.id)
        p2 = ShiftPattern(name="User Pattern B", pattern_type="Fixed", definition={}, user_id=self.test_user.id)
        self.db.add_all([p1, p2])
        self.db.commit()
        response = self.client.get(f'/users/{self.test_user.id}/shift-patterns')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data), 2)

    def test_update_shift_pattern(self):
        pattern = ShiftPattern(name="Old Name", pattern_type="Fixed", definition={}, user_id=self.test_user.id)
        self.db.add(pattern)
        self.db.commit()
        response = self.client.put(f'/shift-patterns/{pattern.id}', json={"name": "New Name"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['name'], "New Name")
        self.db.refresh(pattern)
        self.assertEqual(pattern.name, "New Name")

    def test_delete_shift_pattern(self):
        pattern = ShiftPattern(name="To Delete", pattern_type="Fixed", definition={}, user_id=self.test_user.id)
        self.db.add(pattern)
        self.db.commit()
        pattern_id = pattern.id
        response = self.client.delete(f'/shift-patterns/{pattern_id}')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(self.db.query(ShiftPattern).get(pattern_id))

    # --- Test Methods for Shifts ---
    def test_create_shift_success(self):
        response = self.client.post(f'/users/{self.test_user.id}/shifts', json={
            "name": "Morning Shift",
            "start_time": "2024-07-01 09:00",
            "end_time": "2024-07-01 17:00"
        })
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data['name'], "Morning Shift")
        self.assertEqual(data['user_id'], self.test_user.id)
        shift_in_db = self.db.query(Shift).get(data['id'])
        self.assertIsNotNone(shift_in_db)

    def test_get_user_shifts_success(self):
        Shift.user_id = self.test_user.id # For static analysis
        s1 = Shift(name="Shift A", start_time=datetime(2024,1,1,9,0), end_time=datetime(2024,1,1,17,0), user_id=self.test_user.id)
        s2 = Shift(name="Shift B", start_time=datetime(2024,1,2,9,0), end_time=datetime(2024,1,2,17,0), user_id=self.test_user.id)
        self.db.add_all([s1, s2])
        self.db.commit()
        response = self.client.get(f'/users/{self.test_user.id}/shifts')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data), 2)

    def test_get_shift_details_success(self):
        shift = Shift(name="Detail Shift", start_time=datetime(2024,1,1,9,0), end_time=datetime(2024,1,1,17,0), user_id=self.test_user.id)
        self.db.add(shift)
        self.db.commit()
        response = self.client.get(f'/shifts/{shift.id}')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['name'], "Detail Shift")

    def test_get_shift_details_not_found(self):
        response = self.client.get('/shifts/99999')
        self.assertEqual(response.status_code, 404)

    def test_update_shift_success(self):
        shift = Shift(name="Old Shift Name", start_time=datetime(2024,1,1,9,0), end_time=datetime(2024,1,1,17,0), user_id=self.test_user.id)
        self.db.add(shift)
        self.db.commit()
        response = self.client.put(f'/shifts/{shift.id}', json={"name": "New Shift Name"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['name'], "New Shift Name")
        self.db.refresh(shift)
        self.assertEqual(shift.name, "New Shift Name")

    def test_delete_shift_success(self):
        shift = Shift(name="To Delete Shift", start_time=datetime(2024,1,1,9,0), end_time=datetime(2024,1,1,17,0), user_id=self.test_user.id)
        self.db.add(shift)
        self.db.commit()
        shift_id = shift.id
        response = self.client.delete(f'/shifts/{shift_id}')
        self.assertEqual(response.status_code, 200) # API returns 200
        self.assertIsNone(self.db.query(Shift).get(shift_id))

    # --- Test Methods for Generating Shifts from Pattern ---
    def test_generate_shifts_from_pattern_success(self):
        pattern_data = {
            "name": "Test Rotating Pattern",
            "pattern_type": "Rotating",
            "definition": {
                "cycle": [
                    {"name": "Work", "days": 2, "start_time": "09:00", "end_time": "17:00"},
                    {"name": "Off", "days": 1}
                ],
                "cycle_start_reference_date": "2024-01-01" # A Monday
            }
        }
        pattern_response = self.client.post(f'/users/{self.test_user.id}/shift-patterns', json=pattern_data)
        self.assertEqual(pattern_response.status_code, 201)
        pattern_id = pattern_response.get_json()['id']

        generation_response = self.client.post(
            f'/users/{self.test_user.id}/shift-patterns/{pattern_id}/generate-shifts',
            json={"start_date": "2024-01-01", "end_date": "2024-01-03"} # Mon, Tue, Wed
        )
        self.assertEqual(generation_response.status_code, 201)
        generated_shifts_data = generation_response.get_json()
        self.assertEqual(len(generated_shifts_data), 2) # Work, Work, Off

        for shift_data in generated_shifts_data:
            self.assertEqual(shift_data['source_pattern_id'], pattern_id)
            self.assertEqual(shift_data['user_id'], self.test_user.id)
            self.assertEqual(shift_data['name'], "Work")

        shifts_in_db = self.db.query(Shift).filter_by(user_id=self.test_user.id).all()
        self.assertEqual(len(shifts_in_db), 2)


if __name__ == '__main__':
    unittest.main()
