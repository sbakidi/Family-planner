import unittest
import os
import sys

sys_path_updated = False
if os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) not in sys.path:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    sys_path_updated = True

os.environ["TEST_MODE_ENABLED"] = "1"

from app import app
from src.database import initialize_database_for_application, create_tables, drop_tables, SessionLocal
from src import meal_plan

class TestMealPlanAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        initialize_database_for_application()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SECRET_KEY'] = 'test_secret_key_meal'
        from src import user, shift, child, event, shift_pattern, residency_period, meal_plan as mp
        create_tables()

    @classmethod
    def tearDownClass(cls):
        drop_tables()
        if "TEST_MODE_ENABLED" in os.environ:
            del os.environ["TEST_MODE_ENABLED"]

    def setUp(self):
        self.client = app.test_client()
        self.db = SessionLocal()
        self.db.query(meal_plan.MealPlan).delete()
        self.db.query(meal_plan.Recipe).delete()
        self.db.commit()

    def tearDown(self):
        self.db.query(meal_plan.MealPlan).delete()
        self.db.query(meal_plan.Recipe).delete()
        self.db.commit()
        self.db.close()

    def test_recipe_crud(self):
        resp = self.client.post('/recipes', json={"name": "Pancakes", "ingredients": ["flour", "milk"], "instructions": "Mix"})
        self.assertEqual(resp.status_code, 201)
        r_id = resp.get_json()['id']

        resp = self.client.get(f'/recipes/{r_id}')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['name'], "Pancakes")

        resp = self.client.put(f'/recipes/{r_id}', json={"name": "Best Pancakes"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['name'], "Best Pancakes")

        resp = self.client.delete(f'/recipes/{r_id}')
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(self.db.query(meal_plan.Recipe).get(r_id))

    def test_meal_plan_grocery_generation(self):
        r1 = self.client.post('/recipes', json={"name": "Omelette", "ingredients": ["eggs", "milk"]}).get_json()
        r2 = self.client.post('/recipes', json={"name": "Cake", "ingredients": ["milk", "flour"]}).get_json()
        resp = self.client.post('/meal-plans', json={"week_start": "2024-08-05", "recipe_ids": [r1['id'], r2['id']]})
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertEqual(set(data['grocery_list']), {"eggs", "milk", "flour"})
        plan_id = data['id']

        resp = self.client.get(f'/meal-plans/{plan_id}/groceries')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(set(resp.get_json()['grocery_list']), {"eggs", "milk", "flour"})

if __name__ == '__main__':
    unittest.main()
