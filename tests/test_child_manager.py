import unittest
import sys
import os
from datetime import date # For date_of_birth comparison

# Adjust the path to include the root directory of the project
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set environment variable for test database
os.environ["TEST_MODE_ENABLED"] = "1"

from src.database import initialize_database_for_application, create_tables, drop_tables, SessionLocal
from src.user import User
from src.child import Child
from src import child_manager, auth # For creating test users (parents)

class TestChildManager(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database_for_application()
        # from src import user, shift, child, event # Ensure all models are loaded

    def setUp(self):
        create_tables()
        self.db = SessionLocal()

        # Create dummy users (parents)
        self.parent1 = auth.register("Parent One", "parent1@example.com", "pass1")
        self.parent2 = auth.register("Parent Two", "parent2@example.com", "pass2")
        self.assertIsNotNone(self.parent1)
        self.assertIsNotNone(self.parent2)
        self.parent1_id = self.parent1.id
        self.parent2_id = self.parent2.id

    def tearDown(self):
        self.db.close()
        drop_tables()

    def test_add_child(self):
        dob_str = "2020-01-01"
        child = child_manager.add_child(self.parent1_id, "Test Child", dob_str, school_info="Playschool")

        self.assertIsNotNone(child)
        self.assertIsInstance(child, Child)
        self.assertEqual(child.name, "Test Child")
        self.assertEqual(child.date_of_birth, date(2020, 1, 1))
        self.assertEqual(child.school_info, "Playschool")
        self.assertIsNotNone(child.id)

        # Verify in DB and relationship
        child_in_db = self.db.query(Child).filter_by(id=child.id).first()
        self.assertIsNotNone(child_in_db)
        self.assertEqual(child_in_db.name, "Test Child")
        self.assertIn(self.parent1, child_in_db.parents) # Check if parent1 is in the parents list

    def test_get_child_details_found(self):
        child = child_manager.add_child(self.parent1_id, "Test Child", "2020-01-01")
        retrieved_child = child_manager.get_child_details(child.id)
        self.assertIsNotNone(retrieved_child)
        self.assertEqual(retrieved_child.id, child.id)
        self.assertEqual(retrieved_child.name, "Test Child")

    def test_get_child_details_not_found(self):
        non_existent_child_id = 99999
        retrieved_child = child_manager.get_child_details(non_existent_child_id)
        self.assertIsNone(retrieved_child)

    def test_get_user_children_found(self):
        child1 = child_manager.add_child(self.parent1_id, "Child One", "2020-01-01")
        child2 = child_manager.add_child(self.parent1_id, "Child Two", "2021-01-01")
        # Child belonging to another parent (parent2)
        child_manager.add_child(self.parent2_id, "Other Parent Child", "2019-01-01")

        parent1_children = child_manager.get_user_children(self.parent1_id)
        self.assertEqual(len(parent1_children), 2)
        child_ids_retrieved = [c.id for c in parent1_children]
        self.assertIn(child1.id, child_ids_retrieved)
        self.assertIn(child2.id, child_ids_retrieved)

    def test_get_user_children_not_found(self):
        # Parent1 exists but has no children added yet
        user_children = child_manager.get_user_children(self.parent1_id)
        self.assertEqual(len(user_children), 0)

    def test_update_child_info_found(self):
        child = child_manager.add_child(self.parent1_id, "Original Name", "2020-01-01")

        updated_name = "Updated Name"
        updated_dob_str = "2020-02-02"
        updated_school = "New School"
        updated_child = child_manager.update_child_info(
            child.id,
            name=updated_name,
            date_of_birth_str=updated_dob_str,
            school_info=updated_school
        )

        self.assertIsNotNone(updated_child)
        self.assertEqual(updated_child.name, updated_name)
        self.assertEqual(updated_child.date_of_birth, date(2020, 2, 2))
        self.assertEqual(updated_child.school_info, updated_school)

        # Verify in DB
        child_in_db = self.db.query(Child).filter_by(id=child.id).first()
        self.assertEqual(child_in_db.name, updated_name)

    def test_update_child_info_not_found(self):
        non_existent_child_id = 99999
        updated_child = child_manager.update_child_info(non_existent_child_id, name="Doesn't Matter")
        self.assertIsNone(updated_child)

    def test_remove_child_found(self):
        child = child_manager.add_child(self.parent1_id, "Test Child", "2020-01-01")
        child_id = child.id

        # Ensure child is in parent's list
        self.db.refresh(self.parent1) # Refresh to see relationship change
        self.assertIn(child, self.parent1.children)

        count_before = self.db.query(Child).count()
        result = child_manager.remove_child(child_id)
        self.assertTrue(result)

        count_after = self.db.query(Child).count()
        self.assertEqual(count_after, count_before - 1)
        self.assertIsNone(self.db.query(Child).filter_by(id=child_id).first())

        # Verify child is removed from parent's list (SQLAlchemy might require refresh)
        self.db.refresh(self.parent1)
        self.assertNotIn(child_id, [c.id for c in self.parent1.children])


    def test_remove_child_not_found(self):
        non_existent_child_id = 99999
        result = child_manager.remove_child(non_existent_child_id)
        self.assertFalse(result)

    def test_add_parent_to_child_success(self):
        child = child_manager.add_child(self.parent1_id, "Test Child", "2020-01-01")

        # Initially, only parent1 is associated
        self.assertIn(self.parent1, child.parents)
        self.assertNotIn(self.parent2, child.parents)

        result = child_manager.add_parent_to_child(child.id, self.parent2_id)
        self.assertTrue(result)

        # Verify in DB
        self.db.refresh(child) # Refresh to see updated relationships
        self.assertIn(self.parent1, child.parents)
        self.assertIn(self.parent2, child.parents)

    def test_add_parent_to_child_already_exists(self):
        child = child_manager.add_child(self.parent1_id, "Test Child", "2020-01-01")
        result = child_manager.add_parent_to_child(child.id, self.parent1_id) # Add same parent
        self.assertFalse(result) # Manager returns False if parent already linked

    def test_add_parent_to_child_id_not_found(self):
        non_existent_child_id = 99999
        result = child_manager.add_parent_to_child(non_existent_child_id, self.parent1_id)
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()
