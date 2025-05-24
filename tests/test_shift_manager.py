import unittest
import sys
import os
import uuid # For generating user_id for tests

# Adjust the path to include the root directory of the project
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.shift import Shift
from src import shift_manager

class TestShiftManager(unittest.TestCase):

    def setUp(self):
        # Reset the in-memory storage before each test
        shift_manager.shifts_storage.clear()
        # Create a dummy user ID for testing purposes
        self.test_user_id = uuid.uuid4().hex

    def test_add_shift(self):
        shift = shift_manager.add_shift(self.test_user_id, "2024-01-01 09:00", "2024-01-01 17:00", "Day Shift")
        self.assertIsNotNone(shift)
        self.assertIsInstance(shift, Shift)
        self.assertEqual(shift.user_id, self.test_user_id)
        self.assertEqual(shift.name, "Day Shift")
        self.assertEqual(len(shift_manager.shifts_storage), 1)
        self.assertEqual(shift_manager.shifts_storage[0], shift)

    def test_get_user_shifts_found(self):
        shift_manager.add_shift(self.test_user_id, "2024-01-01 09:00", "2024-01-01 17:00", "Day Shift")
        shift_manager.add_shift(self.test_user_id, "2024-01-02 09:00", "2024-01-02 17:00", "Next Day Shift")
        
        other_user_id = uuid.uuid4().hex
        shift_manager.add_shift(other_user_id, "2024-01-01 10:00", "2024-01-01 18:00", "Other User Shift")
        
        user_shifts = shift_manager.get_user_shifts(self.test_user_id)
        self.assertEqual(len(user_shifts), 2)
        self.assertTrue(all(s.user_id == self.test_user_id for s in user_shifts))

    def test_get_user_shifts_not_found(self):
        user_shifts = shift_manager.get_user_shifts(self.test_user_id)
        self.assertEqual(len(user_shifts), 0)

    def test_update_shift_found(self):
        shift = shift_manager.add_shift(self.test_user_id, "2024-01-01 09:00", "2024-01-01 17:00", "Original Name")
        updated_shift = shift_manager.update_shift(shift.shift_id, new_name="Updated Name", new_start_time="2024-01-01 08:00")
        
        self.assertIsNotNone(updated_shift)
        self.assertEqual(updated_shift.name, "Updated Name")
        self.assertEqual(updated_shift.start_time, "2024-01-01 08:00")
        self.assertEqual(updated_shift.end_time, "2024-01-01 17:00") # Original end time
        
        # Verify in storage
        retrieved_shift = shift_manager.shifts_storage[0]
        self.assertEqual(retrieved_shift.name, "Updated Name")

    def test_update_shift_not_found(self):
        non_existent_shift_id = uuid.uuid4().hex
        updated_shift = shift_manager.update_shift(non_existent_shift_id, new_name="Doesn't Matter")
        self.assertIsNone(updated_shift)

    def test_delete_shift_found(self):
        shift1 = shift_manager.add_shift(self.test_user_id, "2024-01-01 09:00", "2024-01-01 17:00", "Shift 1")
        shift2 = shift_manager.add_shift(self.test_user_id, "2024-01-02 09:00", "2024-01-02 17:00", "Shift 2")
        self.assertEqual(len(shift_manager.shifts_storage), 2)
        
        result = shift_manager.delete_shift(shift1.shift_id)
        self.assertTrue(result)
        self.assertEqual(len(shift_manager.shifts_storage), 1)
        self.assertEqual(shift_manager.shifts_storage[0].shift_id, shift2.shift_id)

    def test_delete_shift_not_found(self):
        shift_manager.add_shift(self.test_user_id, "2024-01-01 09:00", "2024-01-01 17:00", "Shift 1")
        non_existent_shift_id = uuid.uuid4().hex
        
        result = shift_manager.delete_shift(non_existent_shift_id)
        self.assertFalse(result)
        self.assertEqual(len(shift_manager.shifts_storage), 1)

if __name__ == '__main__':
    unittest.main()
