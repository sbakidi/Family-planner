import unittest
import sys
import os
import uuid # For generating user_id and child_id for tests

# Adjust the path to include the root directory of the project
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.child import Child
from src import child_manager

class TestChildManager(unittest.TestCase):

    def setUp(self):
        # Reset the in-memory storages before each test
        child_manager.children_storage.clear()
        child_manager.child_parent_link.clear()
        self.test_user_id = uuid.uuid4().hex
        self.another_user_id = uuid.uuid4().hex

    def test_add_child(self):
        child = child_manager.add_child(self.test_user_id, "Test Child", "2020-01-01")
        self.assertIsNotNone(child)
        self.assertIsInstance(child, Child)
        self.assertEqual(child.name, "Test Child")
        self.assertEqual(len(child_manager.children_storage), 1)
        self.assertIn(child.child_id, child_manager.child_parent_link)
        self.assertEqual(child_manager.child_parent_link[child.child_id], [self.test_user_id])

    def test_get_child_details_found(self):
        child = child_manager.add_child(self.test_user_id, "Test Child", "2020-01-01")
        retrieved_child = child_manager.get_child_details(child.child_id)
        self.assertIsNotNone(retrieved_child)
        self.assertEqual(retrieved_child.child_id, child.child_id)

    def test_get_child_details_not_found(self):
        non_existent_child_id = uuid.uuid4().hex
        retrieved_child = child_manager.get_child_details(non_existent_child_id)
        self.assertIsNone(retrieved_child)

    def test_get_user_children_found(self):
        child1 = child_manager.add_child(self.test_user_id, "Child One", "2020-01-01")
        child2 = child_manager.add_child(self.test_user_id, "Child Two", "2021-01-01")
        # Child belonging to another user
        child_manager.add_child(self.another_user_id, "Other User Child", "2019-01-01")
        
        user_children = child_manager.get_user_children(self.test_user_id)
        self.assertEqual(len(user_children), 2)
        child_ids_retrieved = [c.child_id for c in user_children]
        self.assertIn(child1.child_id, child_ids_retrieved)
        self.assertIn(child2.child_id, child_ids_retrieved)

    def test_get_user_children_not_found(self):
        user_children = child_manager.get_user_children(self.test_user_id)
        self.assertEqual(len(user_children), 0)

    def test_update_child_info_found(self):
        child = child_manager.add_child(self.test_user_id, "Original Name", "2020-01-01")
        updated_child = child_manager.update_child_info(child.child_id, name="Updated Name", school_info={"grade": "1"})
        
        self.assertIsNotNone(updated_child)
        self.assertEqual(updated_child.name, "Updated Name")
        self.assertEqual(updated_child.school_info["grade"], "1")
        
        # Verify in storage
        retrieved_child = child_manager.get_child_details(child.child_id)
        self.assertEqual(retrieved_child.name, "Updated Name")

    def test_update_child_info_not_found(self):
        non_existent_child_id = uuid.uuid4().hex
        updated_child = child_manager.update_child_info(non_existent_child_id, name="Doesn't Matter")
        self.assertIsNone(updated_child)

    def test_remove_child_found(self):
        child = child_manager.add_child(self.test_user_id, "Test Child", "2020-01-01")
        self.assertEqual(len(child_manager.children_storage), 1)
        self.assertIn(child.child_id, child_manager.child_parent_link)
        
        result = child_manager.remove_child(child.child_id)
        self.assertTrue(result)
        self.assertEqual(len(child_manager.children_storage), 0)
        self.assertNotIn(child.child_id, child_manager.child_parent_link)

    def test_remove_child_not_found(self):
        non_existent_child_id = uuid.uuid4().hex
        result = child_manager.remove_child(non_existent_child_id)
        self.assertFalse(result) # As per current implementation, it returns based on storage removal

    def test_add_parent_to_child_success(self):
        child = child_manager.add_child(self.test_user_id, "Test Child", "2020-01-01")
        result = child_manager.add_parent_to_child(child.child_id, self.another_user_id)
        self.assertTrue(result)
        self.assertIn(self.another_user_id, child_manager.child_parent_link[child.child_id])
        self.assertIn(self.test_user_id, child_manager.child_parent_link[child.child_id]) # Original parent still there

    def test_add_parent_to_child_already_exists(self):
        child = child_manager.add_child(self.test_user_id, "Test Child", "2020-01-01")
        result = child_manager.add_parent_to_child(child.child_id, self.test_user_id) # Add same parent
        self.assertFalse(result)

    def test_add_parent_to_child_id_not_found(self):
        non_existent_child_id = uuid.uuid4().hex
        result = child_manager.add_parent_to_child(non_existent_child_id, self.test_user_id)
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()
