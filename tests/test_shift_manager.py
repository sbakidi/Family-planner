import unittest
import sys
import os
# import uuid # No longer needed for user_id generation in tests directly for manager
from datetime import datetime

# Adjust the path to include the root directory of the project
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set environment variable for test database
os.environ["TEST_MODE_ENABLED"] = "1"

from src.database import initialize_database_for_application, create_tables, drop_tables, SessionLocal
from src.user import User # SQLAlchemy User model
from src.shift import Shift # SQLAlchemy Shift model
from src import shift_manager, auth # For creating a test user

class TestShiftManager(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database_for_application()
        # from src import user, shift, child, event # Ensure all models are loaded for Base.metadata

    def setUp(self):
        create_tables()
        self.db = SessionLocal()
        
        # Create a dummy user for testing shift operations
        # Note: auth.register now uses SQLAlchemy and will commit this user.
        self.test_user = auth.register("Test ShiftUser", "shiftuser@example.com", "password")
        self.assertIsNotNone(self.test_user, "Test user setup failed in ShiftManager tests")
        self.test_user_id = self.test_user.id # Use the DB-generated ID

        self.another_user = auth.register("Another ShiftUser", "anotheruser@example.com", "password")
        self.another_user_id = self.another_user.id


    def tearDown(self):
        self.db.close()
        drop_tables()

    def test_add_shift(self):
        start_time_str = "2024-01-01 09:00"
        end_time_str = "2024-01-01 17:00"
        shift = shift_manager.add_shift(self.test_user_id, start_time_str, end_time_str, "Day Shift")
        
        self.assertIsNotNone(shift)
        self.assertIsInstance(shift, Shift)
        self.assertEqual(shift.user_id, self.test_user_id)
        self.assertEqual(shift.name, "Day Shift")
        self.assertEqual(shift.start_time, datetime.strptime(start_time_str, '%Y-%m-%d %H:%M'))
        self.assertEqual(shift.end_time, datetime.strptime(end_time_str, '%Y-%m-%d %H:%M'))

        # Verify in DB
        shift_in_db = self.db.query(Shift).filter_by(id=shift.id).first()
        self.assertIsNotNone(shift_in_db)
        self.assertEqual(shift_in_db.name, "Day Shift")

    def test_get_user_shifts_found(self):
        shift_manager.add_shift(self.test_user_id, "2024-01-01 09:00", "2024-01-01 17:00", "Day Shift")
        shift_manager.add_shift(self.test_user_id, "2024-01-02 09:00", "2024-01-02 17:00", "Next Day Shift")
        shift_manager.add_shift(self.another_user_id, "2024-01-01 10:00", "2024-01-01 18:00", "Other User Shift")
        
        user_shifts = shift_manager.get_user_shifts(self.test_user_id)
        self.assertEqual(len(user_shifts), 2)
        self.assertTrue(all(s.user_id == self.test_user_id for s in user_shifts))

    def test_get_user_shifts_not_found(self):
        # User exists but has no shifts
        user_shifts = shift_manager.get_user_shifts(self.test_user_id)
        self.assertEqual(len(user_shifts), 0)
        
        # User does not exist (simulated by a non-existent ID, though FK constraint might catch this earlier)
        # For this test, we'll rely on manager returning empty list for a valid user ID with no shifts.
        # Querying for a completely non-existent user_id is a different test case, likely for user management.

    def test_update_shift_found(self):
        original_shift = shift_manager.add_shift(self.test_user_id, "2024-01-01 09:00", "2024-01-01 17:00", "Original Name")
        
        updated_name = "Updated Name"
        updated_start_str = "2024-01-01 08:00"
        updated_shift = shift_manager.update_shift(original_shift.id, new_name=updated_name, new_start_time_str=updated_start_str)
        
        self.assertIsNotNone(updated_shift)
        self.assertEqual(updated_shift.name, updated_name)
        self.assertEqual(updated_shift.start_time, datetime.strptime(updated_start_str, '%Y-%m-%d %H:%M'))
        self.assertEqual(updated_shift.end_time, original_shift.end_time) # Original end time, as it wasn't updated

        # Verify in DB
        shift_in_db = self.db.query(Shift).filter_by(id=original_shift.id).first()
        self.assertEqual(shift_in_db.name, updated_name)
        self.assertEqual(shift_in_db.start_time, datetime.strptime(updated_start_str, '%Y-%m-%d %H:%M'))

    def test_update_shift_not_found(self):
        non_existent_shift_id = 99999 # Assuming this ID won't exist
        updated_shift = shift_manager.update_shift(non_existent_shift_id, new_name="Doesn't Matter")
        self.assertIsNone(updated_shift)

    def test_delete_shift_found(self):
        shift1 = shift_manager.add_shift(self.test_user_id, "2024-01-01 09:00", "2024-01-01 17:00", "Shift 1")
        shift2 = shift_manager.add_shift(self.test_user_id, "2024-01-02 09:00", "2024-01-02 17:00", "Shift 2")
        
        count_before_delete = self.db.query(Shift).count()
        self.assertEqual(count_before_delete, 2)
        
        result = shift_manager.delete_shift(shift1.id)
        self.assertTrue(result)
        
        count_after_delete = self.db.query(Shift).count()
        self.assertEqual(count_after_delete, 1)
        
        remaining_shift = self.db.query(Shift).first()
        self.assertEqual(remaining_shift.id, shift2.id)

    def test_delete_shift_not_found(self):
        shift_manager.add_shift(self.test_user_id, "2024-01-01 09:00", "2024-01-01 17:00", "Shift 1")
        non_existent_shift_id = 99999
        
        result = shift_manager.delete_shift(non_existent_shift_id)
        self.assertFalse(result)
        
        count_after_failed_delete = self.db.query(Shift).count()
        self.assertEqual(count_after_failed_delete, 1)

if __name__ == '__main__':
    unittest.main()
