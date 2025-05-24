import unittest
import sys
import os
import uuid # For generating user_id, child_id, event_id for tests

# Adjust the path to include the root directory of the project
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.event import Event
from src import event_manager

class TestEventManager(unittest.TestCase):

    def setUp(self):
        # Reset the in-memory storage before each test
        event_manager.events_storage.clear()
        self.test_user_id = uuid.uuid4().hex
        self.test_child_id = uuid.uuid4().hex
        self.another_user_id = uuid.uuid4().hex
        self.another_child_id = uuid.uuid4().hex

    def test_create_event(self):
        event = event_manager.create_event("Birthday Party", "Party for Test Child", "2024-12-25 14:00", "2024-12-25 17:00",
                                           linked_child_id=self.test_child_id)
        self.assertIsNotNone(event)
        self.assertIsInstance(event, Event)
        self.assertEqual(event.title, "Birthday Party")
        self.assertEqual(event.linked_child_id, self.test_child_id)
        self.assertEqual(len(event_manager.events_storage), 1)
        self.assertEqual(event_manager.events_storage[0], event)

    def test_create_event_linked_to_user(self):
        event = event_manager.create_event("User Meeting", "Meeting for Test User", "2024-11-10 10:00", "2024-11-10 11:00",
                                           linked_user_id=self.test_user_id)
        self.assertIsNotNone(event)
        self.assertEqual(event.linked_user_id, self.test_user_id)
        self.assertIsNone(event.linked_child_id)

    def test_get_event_details_found(self):
        event = event_manager.create_event("Test Event", "Details", "2024-01-01 10:00", "2024-01-01 11:00")
        retrieved_event = event_manager.get_event_details(event.event_id)
        self.assertIsNotNone(retrieved_event)
        self.assertEqual(retrieved_event.event_id, event.event_id)

    def test_get_event_details_not_found(self):
        non_existent_event_id = uuid.uuid4().hex
        retrieved_event = event_manager.get_event_details(non_existent_event_id)
        self.assertIsNone(retrieved_event)

    def test_get_events_for_user_found(self):
        event1 = event_manager.create_event("User Event 1", "", "2024-01-01 10:00", "2024-01-01 11:00", linked_user_id=self.test_user_id)
        event2 = event_manager.create_event("User Event 2", "", "2024-01-02 10:00", "2024-01-02 11:00", linked_user_id=self.test_user_id)
        # Event for another user
        event_manager.create_event("Other User Event", "", "2024-01-01 10:00", "2024-01-01 11:00", linked_user_id=self.another_user_id)
        # Event not linked to any user
        event_manager.create_event("Unlinked Event", "", "2024-01-01 10:00", "2024-01-01 11:00")
        
        user_events = event_manager.get_events_for_user(self.test_user_id)
        self.assertEqual(len(user_events), 2)
        event_ids_retrieved = [e.event_id for e in user_events]
        self.assertIn(event1.event_id, event_ids_retrieved)
        self.assertIn(event2.event_id, event_ids_retrieved)

    def test_get_events_for_user_not_found(self):
        user_events = event_manager.get_events_for_user(self.test_user_id)
        self.assertEqual(len(user_events), 0)

    def test_get_events_for_child_found(self):
        event1 = event_manager.create_event("Child Event 1", "", "2024-01-01 10:00", "2024-01-01 11:00", linked_child_id=self.test_child_id)
        event2 = event_manager.create_event("Child Event 2", "", "2024-01-02 10:00", "2024-01-02 11:00", linked_child_id=self.test_child_id)
        # Event for another child
        event_manager.create_event("Other Child Event", "", "2024-01-01 10:00", "2024-01-01 11:00", linked_child_id=self.another_child_id)
        
        child_events = event_manager.get_events_for_child(self.test_child_id)
        self.assertEqual(len(child_events), 2)
        event_ids_retrieved = [e.event_id for e in child_events]
        self.assertIn(event1.event_id, event_ids_retrieved)
        self.assertIn(event2.event_id, event_ids_retrieved)

    def test_get_events_for_child_not_found(self):
        child_events = event_manager.get_events_for_child(self.test_child_id)
        self.assertEqual(len(child_events), 0)

    def test_update_event_found(self):
        event = event_manager.create_event("Original Title", "Desc", "2024-01-01 10:00", "2024-01-01 11:00")
        updated_event = event_manager.update_event(event.event_id, title="Updated Title", linked_user_id=self.test_user_id)
        
        self.assertIsNotNone(updated_event)
        self.assertEqual(updated_event.title, "Updated Title")
        self.assertEqual(updated_event.linked_user_id, self.test_user_id)
        
        retrieved_event = event_manager.get_event_details(event.event_id)
        self.assertEqual(retrieved_event.title, "Updated Title")

    def test_update_event_not_found(self):
        non_existent_event_id = uuid.uuid4().hex
        updated_event = event_manager.update_event(non_existent_event_id, title="Doesn't Matter")
        self.assertIsNone(updated_event)

    def test_delete_event_found(self):
        event1 = event_manager.create_event("Event 1", "", "2024-01-01 10:00", "2024-01-01 11:00")
        event2 = event_manager.create_event("Event 2", "", "2024-01-02 10:00", "2024-01-02 11:00")
        self.assertEqual(len(event_manager.events_storage), 2)
        
        result = event_manager.delete_event(event1.event_id)
        self.assertTrue(result)
        self.assertEqual(len(event_manager.events_storage), 1)
        self.assertEqual(event_manager.events_storage[0].event_id, event2.event_id)

    def test_delete_event_not_found(self):
        event_manager.create_event("Event 1", "", "2024-01-01 10:00", "2024-01-01 11:00")
        non_existent_event_id = uuid.uuid4().hex
        
        result = event_manager.delete_event(non_existent_event_id)
        self.assertFalse(result)
        self.assertEqual(len(event_manager.events_storage), 1)

if __name__ == '__main__':
    unittest.main()
