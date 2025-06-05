import unittest
import sys
import os
from datetime import datetime

# Adjust the path to include the root directory of the project
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set environment variable for test database
os.environ["TEST_MODE_ENABLED"] = "1"

from src.database import initialize_database_for_application, create_tables, drop_tables, SessionLocal
from src.user import User
from src.child import Child
from src.event import Event
from src import event_manager, auth, child_manager, shift_manager # For creating test users and children

class TestEventManager(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database_for_application()
        # from src import user, shift, child, event # Ensure all models are loaded

    def setUp(self):
        create_tables()
        self.db = SessionLocal()

        # Create dummy user and child for linking events
        self.test_user = auth.register("Event User", "eventuser@example.com", "pass")
        self.assertIsNotNone(self.test_user)
        self.test_user_id = self.test_user.id

        self.test_child = child_manager.add_child(self.test_user_id, "Event Child", "2022-01-01")
        self.assertIsNotNone(self.test_child)
        self.test_child_id = self.test_child.id

        self.another_user = auth.register("Another EventUser", "eventuser2@example.com", "pass")
        self.another_user_id = self.another_user.id
        self.another_child = child_manager.add_child(self.another_user_id, "Another EventChild", "2023-01-01")
        self.another_child_id = self.another_child.id


    def tearDown(self):
        self.db.close()
        drop_tables()

    def test_create_event_linked_to_child(self):
        start_str = "2024-12-25 14:00"
        end_str = "2024-12-25 17:00"
        event = event_manager.create_event(
            title="Birthday Party",
            description="Party for Test Child",
            start_time_str=start_str,
            end_time_str=end_str,
            linked_child_id=self.test_child_id
        )
        self.assertIsNotNone(event)
        self.assertIsInstance(event, Event)
        self.assertEqual(event.title, "Birthday Party")
        self.assertEqual(event.child_id, self.test_child_id) # SQLAlchemy model uses child_id
        self.assertIsNone(event.user_id)
        self.assertEqual(event.start_time, datetime.strptime(start_str, '%Y-%m-%d %H:%M'))

        # Verify in DB
        event_in_db = self.db.query(Event).filter_by(id=event.id).first()
        self.assertIsNotNone(event_in_db)
        self.assertEqual(event_in_db.child_id, self.test_child_id)

    def test_create_event_linked_to_user(self):
        start_str = "2024-11-10 10:00"
        end_str = "2024-11-10 11:00"
        event = event_manager.create_event(
            title="User Meeting",
            description="Meeting for Test User",
            start_time_str=start_str,
            end_time_str=end_str,
            linked_user_id=self.test_user_id
        )
        self.assertIsNotNone(event)
        self.assertEqual(event.user_id, self.test_user_id) # SQLAlchemy model uses user_id
        self.assertIsNone(event.child_id)

    def test_get_event_details_found(self):
        event = event_manager.create_event("Test Event", "Details", "2024-01-01 10:00", "2024-01-01 11:00")
        retrieved_event = event_manager.get_event_details(event.id)
        self.assertIsNotNone(retrieved_event)
        self.assertEqual(retrieved_event.id, event.id)
        self.assertEqual(retrieved_event.title, "Test Event")

    def test_get_event_details_not_found(self):
        non_existent_event_id = 99999
        retrieved_event = event_manager.get_event_details(non_existent_event_id)
        self.assertIsNone(retrieved_event)

    def test_get_events_for_user_found(self):
        event1 = event_manager.create_event("User Event 1", "", "2024-01-01 10:00", "2024-01-01 11:00", linked_user_id=self.test_user_id)
        event2 = event_manager.create_event("User Event 2", "", "2024-01-02 10:00", "2024-01-02 11:00", linked_user_id=self.test_user_id)
        event_manager.create_event("Other User Event", "", "2024-01-01 10:00", "2024-01-01 11:00", linked_user_id=self.another_user_id)
        event_manager.create_event("Child-only Event", "", "2024-01-01 10:00", "2024-01-01 11:00", linked_child_id=self.test_child_id)

        user_events = event_manager.get_events_for_user(self.test_user_id)
        self.assertEqual(len(user_events), 2)
        event_ids_retrieved = [e.id for e in user_events]
        self.assertIn(event1.id, event_ids_retrieved)
        self.assertIn(event2.id, event_ids_retrieved)

    def test_get_events_for_user_not_found(self):
        user_events = event_manager.get_events_for_user(self.test_user_id) # User exists, but no events yet
        self.assertEqual(len(user_events), 0)

    def test_get_events_for_child_found(self):
        event1 = event_manager.create_event("Child Event 1", "", "2024-01-01 10:00", "2024-01-01 11:00", linked_child_id=self.test_child_id)
        event2 = event_manager.create_event("Child Event 2", "", "2024-01-02 10:00", "2024-01-02 11:00", linked_child_id=self.test_child_id)
        event_manager.create_event("Other Child Event", "", "2024-01-01 10:00", "2024-01-01 11:00", linked_child_id=self.another_child_id)

        child_events = event_manager.get_events_for_child(self.test_child_id)
        self.assertEqual(len(child_events), 2)
        event_ids_retrieved = [e.id for e in child_events]
        self.assertIn(event1.id, event_ids_retrieved)
        self.assertIn(event2.id, event_ids_retrieved)

    def test_get_events_for_child_not_found(self):
        child_events = event_manager.get_events_for_child(self.test_child_id) # Child exists, no events yet
        self.assertEqual(len(child_events), 0)

    def test_update_event_found(self):
        event = event_manager.create_event("Original Title", "Desc", "2024-01-01 10:00", "2024-01-01 11:00")
        updated_event = event_manager.update_event(
            event.id,
            title="Updated Title",
            linked_user_id=self.test_user_id,
            start_time_str="2024-01-01 10:30"
        )

        self.assertIsNotNone(updated_event)
        self.assertEqual(updated_event.title, "Updated Title")
        self.assertEqual(updated_event.user_id, self.test_user_id)
        self.assertEqual(updated_event.start_time, datetime.strptime("2024-01-01 10:30", '%Y-%m-%d %H:%M'))

        # Verify in DB
        retrieved_event = self.db.query(Event).filter_by(id=event.id).first()
        self.assertEqual(retrieved_event.title, "Updated Title")
        self.assertEqual(retrieved_event.user_id, self.test_user_id)

    def test_update_event_unlink_user(self):
        event = event_manager.create_event("User Linked Event", "Desc", "2024-01-01 10:00", "2024-01-01 11:00", linked_user_id=self.test_user_id)
        self.assertEqual(event.user_id, self.test_user_id)

        updated_event = event_manager.update_event(event.id, unlink_user=True)
        self.assertIsNotNone(updated_event)
        self.assertIsNone(updated_event.user_id)


    def test_update_event_not_found(self):
        non_existent_event_id = 99999
        updated_event = event_manager.update_event(non_existent_event_id, title="Doesn't Matter")
        self.assertIsNone(updated_event)

    def test_delete_event_found(self):
        event1 = event_manager.create_event("Event 1", "", "2024-01-01 10:00", "2024-01-01 11:00")
        event2 = event_manager.create_event("Event 2", "", "2024-01-02 10:00", "2024-01-02 11:00")

        count_before = self.db.query(Event).count()
        self.assertEqual(count_before, 2)

        result = event_manager.delete_event(event1.id)
        self.assertTrue(result)

        count_after = self.db.query(Event).count()
        self.assertEqual(count_after, 1)

        remaining_event = self.db.query(Event).first()
        self.assertEqual(remaining_event.id, event2.id)

    def test_delete_event_not_found(self):
        event_manager.create_event("Event 1", "", "2024-01-01 10:00", "2024-01-01 11:00")
        non_existent_event_id = 99999

        result = event_manager.delete_event(non_existent_event_id)
        self.assertFalse(result)
        self.assertEqual(self.db.query(Event).count(), 1)

    def test_detect_conflicts(self):
        shift_manager.add_shift(self.test_user_id, "2024-06-01 09:00", "2024-06-01 17:00", "Work")
        child_manager.add_residency_period(self.db, self.test_child_id, self.another_user_id,
                                           "2024-06-02 00:00:00", "2024-06-03 00:00:00")
        self.db.commit()

        result = event_manager.detect_conflicts("2024-06-01 10:00", "2024-06-01 12:00",
                                                user_id=self.test_user_id,
                                                child_id=self.test_child_id)
        self.assertIn("shift", result["conflicts"])

        result2 = event_manager.detect_conflicts("2024-06-02 10:00", "2024-06-02 12:00",
                                                 user_id=self.test_user_id,
                                                 child_id=self.test_child_id)
        self.assertIn("residency_parent", result2["conflicts"])

if __name__ == '__main__':
    unittest.main()
