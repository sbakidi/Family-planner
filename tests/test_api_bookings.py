import unittest
import os
import hashlib
import sys

sys_path_updated = False
if os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) not in sys.path:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    sys_path_updated = True

os.environ["TEST_MODE_ENABLED"] = "1"

from app import app
from src.database import initialize_database_for_application, create_tables, drop_tables, SessionLocal
from src.user import User
from src.booking import Booking
from src.event import Event

class TestAPIBookings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        initialize_database_for_application()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SECRET_KEY'] = 'test_secret_key_bookings'
        from src import user, shift, child, event, booking, shift_pattern, residency_period
        create_tables()

    @classmethod
    def tearDownClass(cls):
        drop_tables()
        if "TEST_MODE_ENABLED" in os.environ:
            del os.environ["TEST_MODE_ENABLED"]

    def setUp(self):
        self.client = app.test_client()
        self.db = SessionLocal()
        self.db.query(Booking).delete()
        self.db.query(Event).delete()
        self.db.query(User).delete()
        self.db.commit()
        self.user = self._create_user_directly(email="booker@example.com")

    def tearDown(self):
        self.db.query(Booking).delete()
        self.db.query(Event).delete()
        self.db.query(User).delete()
        self.db.commit()
        self.db.close()

    def _create_user_directly(self, name="Book User", email="book@example.com", password="pass"):
        hashed = hashlib.sha256(password.encode()).hexdigest()
        u = User(name=name, email=email, hashed_password=hashed)
        self.db.add(u)
        self.db.commit()
        self.db.refresh(u)
        return u

    def _create_booking_api(self, service="Consult", start="2024-01-01 10:00", end="2024-01-01 11:00", user_id=None):
        payload = {
            "service": service,
            "start_time": start,
            "end_time": end,
            "user_id": user_id or self.user.id
        }
        return self.client.post('/bookings', json=payload)

    def test_create_booking_creates_event(self):
        response = self._create_booking_api()
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn('event_id', data)
        booking_in_db = self.db.query(Booking).get(data['id'])
        self.assertIsNotNone(booking_in_db)
        self.assertIsNotNone(booking_in_db.event_id)
        event_in_db = self.db.query(Event).get(booking_in_db.event_id)
        self.assertIsNotNone(event_in_db)
        self.assertEqual(event_in_db.title, f"Booking: {booking_in_db.service}")

    def test_get_user_bookings(self):
        self._create_booking_api(service="A")
        self._create_booking_api(service="B")
        other_user = self._create_user_directly(name="Other", email="o@example.com")
        self._create_booking_api(service="C", user_id=other_user.id)

        resp = self.client.get(f'/users/{self.user.id}/bookings')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(len(data), 2)
        services = {b['service'] for b in data}
        self.assertIn("A", services)
        self.assertIn("B", services)

if __name__ == '__main__':
    unittest.main()
