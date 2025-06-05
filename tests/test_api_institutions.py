import unittest
import os
import hashlib
import sys
from datetime import date

sys_path_updated = False
if os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) not in sys.path:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    sys_path_updated = True

os.environ["TEST_MODE_ENABLED"] = "1"

from app import app
from src.database import initialize_database_for_application, create_tables, drop_tables, SessionLocal
from src.user import User
from src.child import Child
from src.institution import Institution
from src.consent import Consent

class TestAPIInstitutions(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database_for_application()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SECRET_KEY'] = 'test_secret_key_institutions'
        from src import user, shift, child, event, shift_pattern, residency_period, institution, consent, treatment_plan
        create_tables()

    @classmethod
    def tearDownClass(cls):
        drop_tables()
        if "TEST_MODE_ENABLED" in os.environ:
            del os.environ["TEST_MODE_ENABLED"]

    def setUp(self):
        self.client = app.test_client()
        self.db = SessionLocal()
        self.db.query(Consent).delete()
        self.db.query(Institution).delete()
        self.db.query(Child).delete()
        self.db.query(User).delete()
        self.db.commit()
        self.parent = self._create_user("Parent", "parent@example.com")
        self.child = self._create_child(self.parent.id)

    def tearDown(self):
        self.db.query(Consent).delete()
        self.db.query(Institution).delete()
        self.db.query(Child).delete()
        self.db.query(User).delete()
        self.db.commit()
        self.db.close()

    def _create_user(self, name, email):
        hashed_password = hashlib.sha256(b"pw").hexdigest()
        user = User(name=name, email=email, hashed_password=hashed_password)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def _create_child(self, parent_id):
        c = Child(name="Child", date_of_birth=date(2020,1,1))
        parent = self.db.query(User).get(parent_id)
        c.parents.append(parent)
        self.db.add(c)
        self.db.commit()
        self.db.refresh(c)
        return c

    def test_institution_event_requires_consent(self):
        inst_res = self.client.post('/institutions', json={"name": "School"})
        self.assertEqual(inst_res.status_code, 201)
        inst = inst_res.get_json()
        key = inst['api_key']
        # Attempt event without consent
        response = self.client.post(f"/institutions/{inst['id']}/events", json={
            "title": "Class Trip",
            "start_time": "2024-01-01 09:00",
            "end_time": "2024-01-01 15:00",
            "child_id": self.child.id
        }, headers={"X-API-Key": key})
        self.assertEqual(response.status_code, 403)
        # Give consent
        c_res = self.client.post(f"/children/{self.child.id}/institutions/{inst['id']}/consent")
        self.assertEqual(c_res.status_code, 201)
        # Retry event
        response2 = self.client.post(f"/institutions/{inst['id']}/events", json={
            "title": "Class Trip",
            "start_time": "2024-01-01 09:00",
            "end_time": "2024-01-01 15:00",
            "child_id": self.child.id
        }, headers={"X-API-Key": key})
        self.assertEqual(response2.status_code, 201)
        data = response2.get_json()
        self.assertEqual(data['child_id'], self.child.id)
        self.assertEqual(data['institution_id'], inst['id'])

if __name__ == '__main__':
    unittest.main()
