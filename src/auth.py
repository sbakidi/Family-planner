import hashlib
import uuid
from src.user import User

users_db = {}  # In-memory store for user data
# Example: users_db = {'email@example.com': {'password_hash': 'hashed_password', 'user_id': 'uuid_hex', 'name': 'User Name'}}

def register(name, email, password):
    if email in users_db:
        print("Error: Email already exists.")
        return None
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    user_id = uuid.uuid4().hex
    
    users_db[email] = {
        'password_hash': password_hash,
        'user_id': user_id,
        'name': name
    }
    
    new_user = User(user_id=user_id, name=name, email=email)
    # Note: The User class currently doesn't store the password hash.
    # This might be something to consider if the User object is meant to be the single source of truth.
    return new_user

def login(email, password):
    if email not in users_db:
        print("Error: Email not found.")
        return None
    
    user_data = users_db[email]
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    if password_hash == user_data['password_hash']:
        # Create and return a User object
        return User(user_id=user_data['user_id'], name=user_data['name'], email=email)
    else:
        print("Error: Incorrect password.")
        return None

def logout():
    print("User logged out")
    pass
