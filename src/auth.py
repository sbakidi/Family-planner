import hashlib
# import uuid # No longer needed for generating user IDs by auth module
from sqlalchemy.orm import Session # Not directly used, but good to know SessionLocal returns this type
from sqlalchemy.exc import SQLAlchemyError

from src.database import SessionLocal
from src.user import User # SQLAlchemy User model

# users_db is removed, data will be stored in SQLite via SQLAlchemy

def register(name, email, password):
    db = SessionLocal()
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            print("Error: Email already exists.")
            return None

        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        # Note: User.id is an auto-incrementing Integer PK.
        # The previous user_id (uuid) is not directly used here unless the model changes.
        new_user = User(name=name, email=email, hashed_password=hashed_password)

        db.add(new_user)
        db.commit()
        db.refresh(new_user) # To get the auto-generated ID

        # The returned User object is now an SQLAlchemy model instance.
        # The CLI (main.py) expects a User object with attributes like id, name, email.
        # The previous User class had user_id, name, email. The SQLAlchemy User model has id, name, email.
        # This should be compatible enough for current_user in main.py if it expects .name and .email,
        # and .user_id attribute is now .id
        return new_user
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error during registration: {e}")
        return None
    finally:
        db.close()

def login(email, password):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print("Error: Email not found.")
            return None

        # Verify password
        password_hash_to_check = hashlib.sha256(password.encode()).hexdigest()
        if user.hashed_password == password_hash_to_check:
            # Return the User object (SQLAlchemy model instance)
            # Ensure attributes used in main.py (e.g., user.name, user.id) are present
            return user
        else:
            print("Error: Incorrect password.")
            return None
    except SQLAlchemyError as e:
        print(f"Database error during login: {e}")
        return None
    finally:
        db.close()

def logout():
    # Logout in a CLI/stateless context might not need DB interaction
    # It typically involves clearing client-side session state.
    # For this app, current_user is set to None in main.py.
    print("User logged out (client-side state cleared).")
    pass
