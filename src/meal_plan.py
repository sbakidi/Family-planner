from sqlalchemy import Column, Integer, String, Text, Date
from sqlalchemy.exc import SQLAlchemyError
from datetime import date
import json

from .database import Base, SessionLocal

class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    ingredients = Column(Text)  # JSON encoded list
    instructions = Column(Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "ingredients": json.loads(self.ingredients) if self.ingredients else [],
            "instructions": self.instructions,
        }

class MealPlan(Base):
    __tablename__ = "meal_plans"

    id = Column(Integer, primary_key=True, index=True)
    week_start = Column(Date, nullable=False)
    recipe_ids = Column(Text)  # JSON encoded list of recipe ids

    def to_dict(self, include_grocery=False):
        data = {
            "id": self.id,
            "week_start": self.week_start.isoformat() if self.week_start else None,
            "recipe_ids": json.loads(self.recipe_ids) if self.recipe_ids else [],
        }
        if include_grocery:
            data["grocery_list"] = generate_grocery_list(self)
        return data

def create_recipe(name, ingredients, instructions=None):
    db = SessionLocal()
    try:
        r = Recipe(name=name, ingredients=json.dumps(ingredients), instructions=instructions)
        db.add(r)
        db.commit()
        db.refresh(r)
        return r
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error creating recipe: {e}")
        return None
    finally:
        db.close()

def get_recipe(recipe_id):
    db = SessionLocal()
    try:
        return db.query(Recipe).get(recipe_id)
    finally:
        db.close()

def update_recipe(recipe_id, name=None, ingredients=None, instructions=None):
    db = SessionLocal()
    try:
        recipe = db.query(Recipe).get(recipe_id)
        if not recipe:
            return None
        if name is not None:
            recipe.name = name
        if ingredients is not None:
            recipe.ingredients = json.dumps(ingredients)
        if instructions is not None:
            recipe.instructions = instructions
        db.commit()
        db.refresh(recipe)
        return recipe
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error updating recipe: {e}")
        return None
    finally:
        db.close()

def delete_recipe(recipe_id):
    db = SessionLocal()
    try:
        recipe = db.query(Recipe).get(recipe_id)
        if not recipe:
            return False
        db.delete(recipe)
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error deleting recipe: {e}")
        return False
    finally:
        db.close()

def list_recipes():
    db = SessionLocal()
    try:
        return db.query(Recipe).all()
    finally:
        db.close()

def create_meal_plan(week_start_str, recipe_ids):
    db = SessionLocal()
    try:
        week_start = date.fromisoformat(week_start_str)
        plan = MealPlan(week_start=week_start, recipe_ids=json.dumps(recipe_ids))
        db.add(plan)
        db.commit()
        db.refresh(plan)
        return plan
    except (SQLAlchemyError, ValueError) as e:
        db.rollback()
        print(f"Error creating meal plan: {e}")
        return None
    finally:
        db.close()

def get_meal_plan(plan_id):
    db = SessionLocal()
    try:
        return db.query(MealPlan).get(plan_id)
    finally:
        db.close()

def list_meal_plans():
    db = SessionLocal()
    try:
        return db.query(MealPlan).all()
    finally:
        db.close()

def generate_grocery_list(plan):
    db = SessionLocal()
    try:
        ingredients = []
        ids = json.loads(plan.recipe_ids) if plan.recipe_ids else []
        for rid in ids:
            recipe = db.query(Recipe).get(rid)
            if recipe:
                ingredients.extend(json.loads(recipe.ingredients) if recipe.ingredients else [])
        return sorted(set(ingredients))
    finally:
        db.close()
