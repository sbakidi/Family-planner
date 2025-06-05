import unittest
import json
import os
import hashlib
import sys
from datetime import datetime, date, timedelta
import sys

# Adjust path
sys_path_updated = False
if os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) not in sys.path:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    sys_path_updated = True

os.environ["TEST_MODE_ENABLED"] = "1"

from app import app # Flask app instance
from src.database import initialize_database_for_application, create_tables, drop_tables, SessionLocal, Base
from src.user import User, user_child_association_table
from src.child import Child
from src.residency_period import ResidencyPeriod

class TestAPIChildrenResidency(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database_for_application()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SECRET_KEY'] = 'test_secret_key_children_residency'
        # Ensure all models are imported for create_tables
        from src import user, shift, child, event, shift_pattern, residency_period
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
        # Order matters due to foreign key constraints if not using cascade delete on DB level for all.
        # ResidencyPeriod depends on Child and User.
        # Child depends on User (via association).
        # Shifts, Events, ShiftPatterns also depend on User/Child.
        # For these tests, focus on User, Child, ResidencyPeriod, and user_child_association.
        self.db.query(ResidencyPeriod).delete()
        self.db.execute(user_child_association_table.delete()) # Clear association table
        self.db.query(Child).delete()
        self.db.query(User).delete()
        self.db.commit()

        # Default users for tests
        self.user1 = self._create_user_directly(name="User One", email="user1@example.com", password="password1")
        self.user2 = self._create_user_directly(name="User Two", email="user2@example.com", password="password2")


    def tearDown(self):
        # Double check cleanup
        self.db.query(ResidencyPeriod).delete()
        self.db.execute(user_child_association_table.delete())
        self.db.query(Child).delete()
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

    def _create_child_for_user_api(self, user_id, child_name="Test Child", dob="2020-01-01"):
        response = self.client.post(f'/users/{user_id}/children', json={
            "name": child_name,
            "date_of_birth": dob,
            "school_info": "Test School"
        })
        self.assertEqual(response.status_code, 201, f"Failed to create child via API: {response.get_data(as_text=True)}")
        return response.get_json()

    # --- Test Methods for Children ---
    def test_create_child_success(self):
        child_data = self._create_child_for_user_api(self.user1.id, child_name="Charlie")
        self.assertEqual(child_data['name'], "Charlie")
        self.assertIsNotNone(child_data['id'])

        # Verify in DB
        child_in_db = self.db.query(Child).get(child_data['id'])
        self.assertIsNotNone(child_in_db)
        self.assertEqual(child_in_db.name, "Charlie")
        # Verify parent link
        self.assertIn(self.user1, child_in_db.parents)


    def test_get_child_details_success(self):
        child_data = self._create_child_for_user_api(self.user1.id, "Daisy")
        child_id = child_data['id']

        response = self.client.get(f'/children/{child_id}')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['name'], "Daisy")
        self.assertEqual(data['id'], child_id)

    def test_get_child_details_not_found(self):
        response = self.client.get('/children/99999')
        self.assertEqual(response.status_code, 404)

    def test_get_user_children_success(self):
        self._create_child_for_user_api(self.user1.id, "Child A")
        self._create_child_for_user_api(self.user1.id, "Child B")
        # Create a child for another user to ensure filtering
        self._create_child_for_user_api(self.user2.id, "Child C")

        response = self.client.get(f'/users/{self.user1.id}/children')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data), 2)
        child_names = {c['name'] for c in data}
        self.assertIn("Child A", child_names)
        self.assertIn("Child B", child_names)

    def test_update_child_info_success(self):
        child_data = self._create_child_for_user_api(self.user1.id, "Original Name")
        child_id = child_data['id']

        update_payload = {"name": "Updated Name", "school_info": "New School"}
        response = self.client.put(f'/children/{child_id}', json=update_payload)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['name'], "Updated Name")
        self.assertEqual(data['school_info'], "New School")

        # Verify in DB
        child_in_db = self.db.query(Child).get(child_id)
        self.assertEqual(child_in_db.name, "Updated Name")

    def test_delete_child_success(self):
        child_data = self._create_child_for_user_api(self.user1.id)
        child_id = child_data['id']

        # Add a residency period to check cascade (if configured in model, or handled by manager)
        # Model: residency_periods = relationship(..., cascade="all, delete-orphan")
        res_period = ResidencyPeriod(child_id=child_id, parent_id=self.user1.id,
                                     start_datetime=datetime(2023,1,1,10,0), end_datetime=datetime(2023,1,5,10,0))
        self.db.add(res_period)
        self.db.commit()
        res_period_id = res_period.id

        response = self.client.delete(f'/children/{child_id}')
        self.assertEqual(response.status_code, 200)

        self.assertIsNone(self.db.query(Child).get(child_id))
        self.assertIsNone(self.db.query(ResidencyPeriod).get(res_period_id)) # Check cascade

    def test_add_another_parent_to_child_success(self):
        child_data = self._create_child_for_user_api(self.user1.id)
        child_id = child_data['id']

        response = self.client.post(f'/children/{child_id}/parents', json={"user_id": self.user2.id})
        self.assertEqual(response.status_code, 200)

        # Verify in DB
        child_in_db = self.db.query(Child).get(child_id)
        parent_ids = {parent.id for parent in child_in_db.parents}
        self.assertIn(self.user1.id, parent_ids)
        self.assertIn(self.user2.id, parent_ids)

    def test_add_parent_to_child_child_not_found(self):
        response = self.client.post('/children/99999/parents', json={"user_id": self.user1.id})
        self.assertEqual(response.status_code, 404) # API should check child existence

    def test_add_parent_to_child_new_parent_not_found(self):
        child_data = self._create_child_for_user_api(self.user1.id)
        child_id = child_data['id']
        response = self.client.post(f'/children/{child_id}/parents', json={"user_id": 99999})
        self.assertEqual(response.status_code, 404) # API should check new parent existence


    # --- Test Methods for Residency Periods ---
    def test_create_residency_period_success(self):
        child_data = self._create_child_for_user_api(self.user1.id)
        child_id = child_data['id']

        payload = {
            "parent_id": self.user1.id,
            "start_datetime": "2024-01-01 10:00:00",
            "end_datetime": "2024-01-05 18:00:00",
            "notes": "Week with User One"
        }
        response = self.client.post(f'/children/{child_id}/residency-periods', json=payload)
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data['child_id'], child_id)
        self.assertEqual(data['parent_id'], self.user1.id)
        self.assertEqual(data['notes'], "Week with User One")
        self.assertIsNotNone(data['id'])

        period_in_db = self.db.query(ResidencyPeriod).get(data['id'])
        self.assertIsNotNone(period_in_db)

    def test_get_residency_periods_for_child_success(self):
        child_data = self._create_child_for_user_api(self.user1.id)
        child_id = child_data['id']

        # Add some periods
        rp1_payload = {"parent_id": self.user1.id, "start_datetime": "2024-01-01 10:00", "end_datetime": "2024-01-05 18:00"}
        rp2_payload = {"parent_id": self.user2.id, "start_datetime": "2024-01-05 18:00", "end_datetime": "2024-01-10 10:00"}
        self.client.post(f'/children/{child_id}/residency-periods', json=rp1_payload)
        self.client.post(f'/children/{child_id}/residency-periods', json=rp2_payload)

        response = self.client.get(f'/children/{child_id}/residency-periods')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data), 2)

    def test_get_residency_periods_for_child_with_date_filters(self):
        child_data = self._create_child_for_user_api(self.user1.id)
        child_id = child_data['id']
        self.client.post(f'/children/{child_id}/residency-periods', json={"parent_id": self.user1.id, "start_datetime": "2024-01-01 10:00", "end_datetime": "2024-01-05 18:00"})
        self.client.post(f'/children/{child_id}/residency-periods', json={"parent_id": self.user2.id, "start_datetime": "2024-01-05 18:00", "end_datetime": "2024-01-10 10:00"})
        self.client.post(f'/children/{child_id}/residency-periods', json={"parent_id": self.user1.id, "start_datetime": "2024-01-10 10:00", "end_datetime": "2024-01-15 18:00"})

        response = self.client.get(f'/children/{child_id}/residency-periods?start_date=2024-01-04&end_date=2024-01-11')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        # Expecting 3 periods: first one overlaps start, second is within, third overlaps end
        self.assertEqual(len(data), 3)

    def test_get_residency_period_details_success(self):
        child_data = self._create_child_for_user_api(self.user1.id)
        child_id = child_data['id']
        rp_res = self.client.post(f'/children/{child_id}/residency-periods', json={"parent_id": self.user1.id, "start_datetime": "2024-01-01 10:00", "end_datetime": "2024-01-05 18:00", "notes": "Test notes"})
        period_id = rp_res.get_json()['id']

        response = self.client.get(f'/residency-periods/{period_id}')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['id'], period_id)
        self.assertEqual(data['notes'], "Test notes")

    def test_get_residency_period_details_not_found(self):
        response = self.client.get('/residency-periods/99999')
        self.assertEqual(response.status_code, 404)

    def test_update_residency_period_success(self):
        child_data = self._create_child_for_user_api(self.user1.id)
        child_id = child_data['id']
        rp_res = self.client.post(f'/children/{child_id}/residency-periods', json={"parent_id": self.user1.id, "start_datetime": "2024-01-01 10:00", "end_datetime": "2024-01-05 18:00"})
        period_id = rp_res.get_json()['id']

        update_payload = {"notes": "Updated notes", "parent_id": self.user2.id}
        response = self.client.put(f'/residency-periods/{period_id}', json=update_payload)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['notes'], "Updated notes")
        self.assertEqual(data['parent_id'], self.user2.id)

        period_in_db = self.db.query(ResidencyPeriod).get(period_id)
        self.assertEqual(period_in_db.notes, "Updated notes")
        self.assertEqual(period_in_db.parent_id, self.user2.id)

    def test_delete_residency_period_success(self):
        child_data = self._create_child_for_user_api(self.user1.id)
        child_id = child_data['id']
        rp_res = self.client.post(f'/children/{child_id}/residency-periods', json={"parent_id": self.user1.id, "start_datetime": "2024-01-01 10:00", "end_datetime": "2024-01-05 18:00"})
        period_id = rp_res.get_json()['id']

        response = self.client.delete(f'/residency-periods/{period_id}')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(self.db.query(ResidencyPeriod).get(period_id))

    def test_get_child_residency_on_date_success(self):
        child_data = self._create_child_for_user_api(self.user1.id)
        child_id = child_data['id']
        self.client.post(f'/children/{child_id}/residency-periods', json={"parent_id": self.user1.id, "start_datetime": "2024-03-01 10:00", "end_datetime": "2024-03-05 18:00"})

        response = self.client.get(f'/children/{child_id}/residency?date=2024-03-03')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['parent_id'], self.user1.id)
        self.assertEqual(data[0]['parent']['name'], self.user1.name)

    def test_get_child_residency_on_date_no_period(self):
        child_data = self._create_child_for_user_api(self.user1.id)
        child_id = child_data['id']
        self.client.post(f'/children/{child_id}/residency-periods', json={"parent_id": self.user1.id, "start_datetime": "2024-03-01 10:00", "end_datetime": "2024-03-05 18:00"})

        response = self.client.get(f'/children/{child_id}/residency?date=2024-03-10')
        self.assertEqual(response.status_code, 404) # Expect 404 if no period found

if __name__ == '__main__':
    unittest.main()
