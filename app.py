from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash, Response, send_from_directory, Blueprint, g
from sqlalchemy.exc import SQLAlchemyError
import os  # For secret key
from werkzeug.utils import secure_filename

from src import badge
from src import auth, user, shift, child, event, grocery, task, booking, document, meal_plan, album, photo  # Models
from datetime import datetime
from src import shift_manager, child_manager, event_manager, shift_pattern_manager, photo_manager, grocery_manager, calendar_sync, shift_swap_manager, expense_manager, task_manager, school_import, booking_manager # Managers and utilities
from src.notification import get_user_queue


# Plugin system
from src.plugins import PluginManager
from src import shift_manager, child_manager, event_manager, shift_pattern_manager
from src import ai_scheduler  # Simple scheduling heuristics
from src.database import init_db, SessionLocal
from src.token_manager import token_required, generate_token_for_user
# Import residency_period model for init_db
from src import analytics
from src import residency_period

# Initialize the database (create tables if they don't exist)
# This should be called once when the application starts.
try:
    # Import models to ensure they are registered with Base before init_db() is called
    from src import user, shift, child, event, shift_swap, expense, task, booking, document, meal_plan, album, photo   # Models
    # Import residency_period model for init_db
    from src import residency_period
    from datetime import datetime # For HTML form datetime-local conversion
    init_db()
except Exception as e:
    print(f"Error initializing database during app startup: {e}")
    # Depending on the application, you might want to exit or log this critical error.

app = Flask(__name__)
app.secret_key = os.urandom(24) # Generate a random secret key for sessions
plugin_manager = PluginManager(app)
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# API blueprint
api_bp = Blueprint('api_v1', __name__)

# Simple OpenAPI spec endpoint
@api_bp.route('/openapi.json')
def openapi_spec():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Family Planner API", "version": "1.0"},
        "paths": {}
    }
    return jsonify(spec)

# Optional: A generic error handler for unhandled exceptions
@app.errorhandler(Exception)
def handle_generic_error(e):
    # Log the error e
    print(f"An unhandled exception occurred: {e}") # Basic logging
    response = jsonify(message="An unexpected error occurred on the server.")
    response.status_code = 500
    return response

@api_bp.route('/auth/register', methods=['POST'])
def register_user():
    try:
        data = request.get_json()
        if not data or not all(k in data for k in ("name", "email", "password")):
            return jsonify(message="Missing name, email, or password in request"), 400

        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        role = data.get('role', 'parent')

        # The auth.register function now uses SQLAlchemy and handles DB interaction
        new_user = auth.register(name=name, email=email, password=password, role=role)

        if new_user:
            # new_user is an SQLAlchemy User model instance
            return jsonify(message="User registered successfully", user_id=new_user.id, name=new_user.name, role=new_user.role), 201
        else:
            # auth.register prints "Error: Email already exists." or DB error.
            # We can return a more generic message or rely on the print for now.
            # For a production API, consistent error messages are better.
            # Check if the user object is None due to existing email or other error
            # This part may need refinement based on how auth.register signals specific errors
            db_session = SessionLocal()
            existing = db_session.query(user.User).filter(user.User.email == email).first()
            db_session.close()
            if existing:
                 return jsonify(message="Email already exists."), 409 # Conflict
            return jsonify(message="Registration failed. Possible database error or invalid input."), 400

    except Exception as e: # Catch any other unexpected errors during registration
        print(f"Error in /auth/register: {e}") # Log it
        return jsonify(message="An unexpected error occurred during registration."), 500


@api_bp.route('/auth/login', methods=['POST'])
def login_user():
    try:
        data = request.get_json()
        if not data or not all(k in data for k in ("email", "password")):
            return jsonify(message="Missing email or password"), 400

        email = data.get('email')
        password = data.get('password')
        otp = data.get('otp')

        # auth.login now uses SQLAlchemy
        logged_in_user = auth.login(email=email, password=password, otp=otp)

        if logged_in_user:

            token = generate_token_for_user(logged_in_user.id)
            # logged_in_user is an SQLAlchemy User model instance
            return jsonify(message="Login successful", user_id=logged_in_user.id, name=logged_in_user.name, email=logged_in_user.email, token=token, role=logged_in_user.role), 200

        else:
            # auth.login prints "Error: Email not found." or "Error: Incorrect password."
            return jsonify(message="Login failed: Invalid email or password."), 401 # Unauthorized

    except Exception as e:
        print(f"Error in /auth/login: {e}")
        return jsonify(message="An unexpected error occurred during login."), 500


@api_bp.route('/auth/logout', methods=['POST'])
@token_required
def logout_user():
    # In a stateless API (common with tokens), logout is often handled client-side by deleting the token.
    # Server-side logout might involve invalidating a token if using a denylist.
    # For this basic version, we just acknowledge the request.
    # auth.logout() itself just prints a message.
    auth.logout()
    return jsonify(message="Logout successful"), 200


@app.route('/auth/otp/generate', methods=['POST'])
def generate_otp_route():
    data = request.get_json()
    if not data or 'user_id' not in data:
        return jsonify(message="Missing user_id"), 400
    otp = auth.generate_otp(data['user_id'])
    if otp is None:
        return jsonify(message="OTP generation failed"), 400
    return jsonify(otp=otp), 200


@app.route('/auth/otp/verify', methods=['POST'])
def verify_otp_route():
    data = request.get_json()
    if not data or not all(k in data for k in ('user_id', 'otp')):
        return jsonify(message="Missing user_id or otp"), 400
    if auth.verify_otp(data['user_id'], data['otp']):
        return jsonify(message="OTP verified"), 200
    else:
        return jsonify(message="Invalid OTP"), 400


# --- Child API Endpoints ---

@api_bp.route('/users/<int:user_id>/children', methods=['POST'])
@token_required
def api_add_child(user_id):
    data = request.get_json()
    if not data or not all(k in data for k in ("name", "date_of_birth")):
        return jsonify(message="Missing name or date_of_birth for child"), 400

    # Basic validation for user_id (as parent) could be done here if desired
    # db = SessionLocal()
    # parent_user = db.query(user.User).filter(user.User.id == user_id).first()
    # db.close()
    # if not parent_user:
    #     return jsonify(message="Parent user not found"), 404

    new_child_obj = child_manager.add_child(
        user_id=user_id,
        name=data['name'],
        date_of_birth_str=data['date_of_birth'],
        school_info=data.get('school_info'), # Optional
        custody_schedule_info=data.get('custody_schedule_info') # Optional
    )
    if new_child_obj:
        return jsonify(new_child_obj.to_dict(include_parents=True)), 201
    else:
        # child_manager.add_child prints errors
        return jsonify(message="Failed to add child. Invalid input or parent user not found."), 400

@api_bp.route('/children/<int:child_id>', methods=['GET'])
@token_required
def api_get_child_details(child_id):
    child_obj = child_manager.get_child_details(child_id)
    if child_obj:
        return jsonify(child_obj.to_dict(include_parents=True)), 200
    return jsonify(message="Child not found"), 404

@api_bp.route('/users/<int:user_id>/children', methods=['GET'])
@token_required
def api_get_user_children(user_id):
    # Optional: Validate user_id exists
    children_list = child_manager.get_user_children(user_id)
    return jsonify([c.to_dict(include_parents=False) for c in children_list]), 200 # include_parents=False to simplify

@api_bp.route('/children/<int:child_id>', methods=['PUT'])
@token_required
def api_update_child(child_id):
    data = request.get_json()
    if not data:
        return jsonify(message="No data provided for update"), 400

    updated_child_obj = child_manager.update_child_info(
        child_id=child_id,
        name=data.get('name'),
        date_of_birth_str=data.get('date_of_birth'),
        school_info=data.get('school_info'),
        custody_schedule_info=data.get('custody_schedule_info')
    )
    if updated_child_obj:
        return jsonify(updated_child_obj.to_dict(include_parents=True)), 200
    return jsonify(message="Child not found or update failed"), 404 # Or 400

@api_bp.route('/children/<int:child_id>', methods=['DELETE'])
@token_required
def api_delete_child(child_id):
    if child_manager.remove_child(child_id):
        return jsonify(message="Child deleted successfully"), 200 # Or 204
    return jsonify(message="Child not found or delete failed"), 404

@api_bp.route('/children/<int:child_id>/parents', methods=['POST'])
@token_required
def api_add_parent_to_child(child_id):
    data = request.get_json()
    if not data or 'user_id' not in data:
        return jsonify(message="Missing user_id (for parent) in request"), 400

    other_parent_user_id = data['user_id']

    # child_manager.add_parent_to_child handles logic for existence of child/user
    # and if already a parent.
    success = child_manager.add_parent_to_child(child_id, other_parent_user_id)

    if success:
        return jsonify(message="Parent added to child successfully"), 200
    else:
        # Check if child or user not found, or if already a parent
        db = SessionLocal()
        child_exists = db.query(child.Child).filter(child.Child.id == child_id).count() > 0
        user_exists = db.query(user.User).filter(user.User.id == other_parent_user_id).count() > 0
        db.close()

        if not child_exists:
            return jsonify(message="Child not found"), 404
        if not user_exists:
            return jsonify(message="User (parent) not found"), 404

        # If both exist, the failure was likely due to already being a parent (or other logic in manager)
        return jsonify(message="Failed to add parent. User might already be a parent or other error."), 400


# --- Event API Endpoints ---

@api_bp.route('/events', methods=['POST'])
@token_required
def api_create_event():
    data = request.get_json()
    if not data or not all(k in data for k in ("title", "start_time", "end_time")):
        return jsonify(message="Missing title, start_time, or end_time for event"), 400

    conflict_info = event_manager.detect_conflicts(
        start_time_str=data['start_time'],
        end_time_str=data['end_time'],
        user_id=data.get('user_id'),
        child_id=data.get('child_id')
    )
    if conflict_info.get('conflicts'):
        return jsonify({"message": "conflict", **conflict_info}), 409

    new_event_obj = event_manager.create_event(
        title=data['title'],
        description=data.get('description'),
        start_time_str=data['start_time'],
        end_time_str=data['end_time'],
        linked_user_id=data.get('user_id'), # Optional
        linked_child_id=data.get('child_id') # Optional
    )
    if new_event_obj:
        return jsonify(new_event_obj.to_dict()), 201
    else:
        # event_manager.create_event prints errors
        return jsonify(message="Failed to create event. Invalid input or linked user/child not found."), 400

@api_bp.route('/events/<int:event_id>', methods=['GET'])
@token_required
def api_get_event_details(event_id):
    event_obj = event_manager.get_event_details(event_id)
    if event_obj:
        return jsonify(event_obj.to_dict()), 200
    return jsonify(message="Event not found"), 404

@api_bp.route('/users/<int:user_id>/events', methods=['GET'])
@token_required
def api_get_user_events(user_id):
    # Optional: Validate user_id exists
    events_list = event_manager.get_events_for_user(user_id)
    return jsonify([e.to_dict(include_user=False) for e in events_list]), 200 # Don't include user again

@api_bp.route('/children/<int:child_id>/events', methods=['GET'])
@token_required
def api_get_child_events(child_id):
    # Optional: Validate child_id exists
    events_list = event_manager.get_events_for_child(child_id)
    return jsonify([e.to_dict(include_child=False) for e in events_list]), 200 # Don't include child again

@api_bp.route('/events/<int:event_id>', methods=['PUT'])
@token_required
def api_update_event(event_id):
    data = request.get_json()
    if not data:
        return jsonify(message="No data provided for update"), 400

    # Handle explicit unlinking if 'user_id': null or 'child_id': null is passed
    unlink_user = 'user_id' in data and data['user_id'] is None
    unlink_child = 'child_id' in data and data['child_id'] is None

    updated_event_obj = event_manager.update_event(
        event_id=event_id,
        title=data.get('title'),
        description=data.get('description'),
        start_time_str=data.get('start_time'),
        end_time_str=data.get('end_time'),
        linked_user_id=data.get('user_id') if not unlink_user else None,
        linked_child_id=data.get('child_id') if not unlink_child else None,
        completed=data.get('completed'),
        unlink_user=unlink_user,
        unlink_child=unlink_child
    )
    if updated_event_obj:
        return jsonify(updated_event_obj.to_dict()), 200
    return jsonify(message="Event not found or update failed"), 404 # Or 400

@api_bp.route('/events/<int:event_id>', methods=['DELETE'])
@token_required
def api_delete_event(event_id):
    if event_manager.delete_event(event_id):
        return jsonify(message="Event deleted successfully"), 200 # Or 204
    return jsonify(message="Event not found or delete failed"), 404


@app.route('/import-school-calendar', methods=['POST'])
def api_import_school_calendar():
    if 'file' not in request.files:
        return jsonify(message='No file provided'), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify(message='No file provided'), 400

    temp_path = os.path.join('/tmp', file.filename)
    file.save(temp_path)
    imported = school_import.import_school_calendar(temp_path)
    os.remove(temp_path)

    return jsonify(imported=len(imported)), 200

# --- Task API Endpoints ---

@app.route('/tasks', methods=['POST'])
def api_create_task():
    data = request.get_json()
    if not data or 'description' not in data:
        return jsonify(message="Missing description for task"), 400

    new_task_obj = task_manager.create_task(
        description=data['description'],
        due_date_str=data.get('due_date'),
        user_id=data.get('user_id'),
        event_id=data.get('event_id'),
    )
    if new_task_obj:
        return jsonify(new_task_obj.to_dict()), 201
    return jsonify(message="Failed to create task"), 400


@app.route('/tasks/<int:task_id>', methods=['GET'])
def api_get_task_details(task_id):
    task_obj = task_manager.get_task_details(task_id)
    if task_obj:
        return jsonify(task_obj.to_dict()), 200
    return jsonify(message="Task not found"), 404


@app.route('/users/<int:user_id>/tasks', methods=['GET'])
def api_get_user_tasks(user_id):
    tasks_list = task_manager.get_tasks_for_user(user_id)
    return jsonify([t.to_dict(include_user=False) for t in tasks_list]), 200


@app.route('/events/<int:event_id>/tasks', methods=['GET'])
def api_get_event_tasks(event_id):
    tasks_list = task_manager.get_tasks_for_event(event_id)
    return jsonify([t.to_dict(include_event=False) for t in tasks_list]), 200


@app.route('/tasks/<int:task_id>', methods=['PUT'])
def api_update_task(task_id):
    data = request.get_json()
    if not data:
        return jsonify(message="No data provided for update"), 400

    unlink_user = 'user_id' in data and data['user_id'] is None
    unlink_event = 'event_id' in data and data['event_id'] is None

    updated_task = task_manager.update_task(
        task_id=task_id,
        description=data.get('description'),
        due_date_str=data.get('due_date'),
        user_id=data.get('user_id') if not unlink_user else None,
        event_id=data.get('event_id') if not unlink_event else None,
        completed=data.get('completed'),
        unlink_user=unlink_user,
        unlink_event=unlink_event,
    )
    if updated_task:
        return jsonify(updated_task.to_dict()), 200
    return jsonify(message="Task not found or update failed"), 404


@app.route('/tasks/<int:task_id>', methods=['DELETE'])
def api_delete_task(task_id):
    if task_manager.delete_task(task_id):
        return jsonify(message="Task deleted successfully"), 200
    return jsonify(message="Task not found or delete failed"), 404




# --- Shift Pattern API Endpoints ---


@api_bp.route('/shift-patterns', methods=['POST'])
@token_required

@app.route('/bookings', methods=['POST'])
def api_create_booking():
    data = request.get_json()
    if not data or not all(k in data for k in ('service', 'start_time', 'end_time', 'user_id')):
        return jsonify(message="Missing required booking fields"), 400

    booking_obj = booking_manager.create_booking(
        service=data['service'],
        start_time_str=data['start_time'],
        end_time_str=data['end_time'],
        user_id=data['user_id']
    )
    if booking_obj:
        return jsonify(booking_obj.to_dict()), 201
    return jsonify(message="Failed to create booking"), 400

@app.route('/bookings/<int:booking_id>', methods=['GET'])
def api_get_booking_details(booking_id):
    booking = booking_manager.get_booking_details(booking_id)
    if booking:
        return jsonify(booking.to_dict()), 200
    return jsonify(message="Booking not found"), 404

@app.route('/users/<int:user_id>/bookings', methods=['GET'])
def api_get_user_bookings(user_id):
    bookings = booking_manager.get_bookings_for_user(user_id)
    return jsonify([b.to_dict(include_user=False) for b in bookings]), 200

@app.route('/bookings/<int:booking_id>', methods=['PUT'])
def api_update_booking(booking_id):
    data = request.get_json()
    if not data:
        return jsonify(message="No data provided for update"), 400

    updated = booking_manager.update_booking(
        booking_id=booking_id,
        service=data.get('service'),
        start_time_str=data.get('start_time'),
        end_time_str=data.get('end_time')
    )
    if updated:
        return jsonify(updated.to_dict()), 200
    return jsonify(message="Booking not found or update failed"), 404

@app.route('/bookings/<int:booking_id>', methods=['DELETE'])
def api_delete_booking(booking_id):
    if booking_manager.delete_booking(booking_id):
        return jsonify(message="Booking deleted successfully"), 200
    return jsonify(message="Booking not found or delete failed"), 404


@app.route('/shift-patterns', methods=['POST'])

def api_create_global_shift_pattern():
    data = request.get_json()
    if not data or not all(k in data for k in ("name", "pattern_type", "definition")):
        return jsonify(message="Missing name, pattern_type, or definition"), 400

    pattern = shift_pattern_manager.create_shift_pattern(
        name=data['name'],
        description=data.get('description'),
        pattern_type=data['pattern_type'],
        definition=data['definition'],
        user_id=None # Global pattern
    )
    if pattern:
        return jsonify(pattern.to_dict()), 201
    return jsonify(message="Failed to create global shift pattern"), 400

@api_bp.route('/users/<int:user_id>/shift-patterns', methods=['POST'])
@token_required
def api_create_user_shift_pattern(user_id):
    data = request.get_json()
    if not data or not all(k in data for k in ("name", "pattern_type", "definition")):
        return jsonify(message="Missing name, pattern_type, or definition"), 400

    # Optional: Validate user_id exists
    db = SessionLocal()
    target_user = db.query(user.User).filter(user.User.id == user_id).first()
    db.close()
    if not target_user:
        return jsonify(message=f"User with id {user_id} not found."), 404

    pattern = shift_pattern_manager.create_shift_pattern(
        name=data['name'],
        description=data.get('description'),
        pattern_type=data['pattern_type'],
        definition=data['definition'],
        user_id=user_id
    )
    if pattern:
        return jsonify(pattern.to_dict()), 201
    return jsonify(message="Failed to create user-specific shift pattern"), 400

@api_bp.route('/shift-patterns/<int:pattern_id>', methods=['GET'])
@token_required
def api_get_shift_pattern(pattern_id):
    pattern = shift_pattern_manager.get_shift_pattern(pattern_id)
    if pattern:
        return jsonify(pattern.to_dict()), 200
    return jsonify(message="Shift pattern not found"), 404

@api_bp.route('/shift-patterns', methods=['GET'])
@token_required
def api_get_global_shift_patterns():
    patterns = shift_pattern_manager.get_global_shift_patterns()
    return jsonify([p.to_dict() for p in patterns]), 200

@api_bp.route('/users/<int:user_id>/shift-patterns', methods=['GET'])
@token_required
def api_get_user_shift_patterns(user_id):
    # Optional: Validate user_id exists
    db = SessionLocal()
    target_user = db.query(user.User).filter(user.User.id == user_id).first()
    db.close()
    if not target_user:
        return jsonify(message=f"User with id {user_id} not found."), 404

    patterns = shift_pattern_manager.get_shift_patterns_for_user(user_id)
    return jsonify([p.to_dict() for p in patterns]), 200

@api_bp.route('/shift-patterns/<int:pattern_id>', methods=['PUT'])
@token_required
def api_update_shift_pattern(pattern_id):
    data = request.get_json()
    if not data:
        return jsonify(message="No data provided for update"), 400

    # Basic ownership/admin check - This is simplified.
    # A real app would use @jwt_required or similar and check current_user.id
    # For now, we'll assume if a pattern has a user_id, only that user can update it.
    # Global patterns (user_id=None) might be admin-only. This logic is NOT fully implemented here.

    # pattern_to_update = shift_pattern_manager.get_shift_pattern(pattern_id)
    # if not pattern_to_update:
    #     return jsonify(message="Shift pattern not found"), 404
    # if pattern_to_update.user_id is not None:
    #     # This is a user-specific pattern, implement ownership check if auth is integrated
    #     # For example: if current_user.id != pattern_to_update.user_id: return jsonify(message="Forbidden"), 403
    #     pass

    updated_pattern = shift_pattern_manager.update_shift_pattern(
        pattern_id=pattern_id,
        name=data.get('name'),
        description=data.get('description'),
        pattern_type=data.get('pattern_type'),
        definition=data.get('definition')
    )
    if updated_pattern:
        return jsonify(updated_pattern.to_dict()), 200
    return jsonify(message="Shift pattern not found or update failed"), 404 # Or 400

@api_bp.route('/shift-patterns/<int:pattern_id>', methods=['DELETE'])
@token_required
def api_delete_shift_pattern(pattern_id):
    # Similar ownership/admin check as in PUT would be needed here.
    # pattern_to_delete = shift_pattern_manager.get_shift_pattern(pattern_id)
    # if not pattern_to_delete:
    #     return jsonify(message="Shift pattern not found"), 404
    # if pattern_to_delete.user_id is not None:
    #     # This is a user-specific pattern, implement ownership check
    #     pass

    if shift_pattern_manager.delete_shift_pattern(pattern_id):
        return jsonify(message="Shift pattern deleted successfully"), 200 # Or 204
    return jsonify(message="Shift pattern not found or delete failed"), 404

@api_bp.route('/users/<int:user_id>/shift-patterns/<int:pattern_id>/generate-shifts', methods=['POST'])
@token_required
def api_generate_shifts_from_pattern(user_id, pattern_id):
    data = request.get_json()
    if not data or not all(k in data for k in ("start_date", "end_date")):
        return jsonify(message="Missing start_date or end_date in request"), 400

    start_date_str = data['start_date']
    end_date_str = data['end_date']
    holidays = data.get('holidays')
    exceptions = data.get('exceptions')

    db = SessionLocal()
    try:
        created_shifts = shift_pattern_manager.generate_shifts_from_pattern(
            db_session=db,
            pattern_id=pattern_id,
            user_id=user_id,
            start_date_str=start_date_str,
            end_date_str=end_date_str,
            holidays=holidays,
            exceptions=exceptions
        )
        db.commit() # Commit here after successful generation
        return jsonify([s.to_dict(include_source_pattern_details=True) for s in created_shifts]), 201
    except ValueError as ve:
        db.rollback()
        # ValueError is raised by manager for known issues like "not found" or "invalid date"
        return jsonify(message=str(ve)), 400
    except SQLAlchemyError as sqla_e: # Catch potential DB errors not caught by manager
        db.rollback()
        print(f"SQLAlchemyError during shift generation: {sqla_e}")
        return jsonify(message="Database error during shift generation."), 500
    except Exception as e: # Catch any other unexpected errors
        db.rollback()
        print(f"Unexpected error during shift generation: {e}")
        return jsonify(message="An unexpected error occurred during shift generation."), 500
    finally:
        db.close()
        
@app.route('/shift-swaps', methods=['POST', 'PUT'])
def api_shift_swaps():
    if request.method == 'POST':
        data = request.get_json()
        if not data or not all(k in data for k in ('from_shift_id', 'to_shift_id')):
            return jsonify(message="Missing from_shift_id or to_shift_id"), 400

        swap = shift_swap_manager.propose_swap(data['from_shift_id'], data['to_shift_id'])
        if swap:
            return jsonify(swap.to_dict()), 201
        return jsonify(message="Failed to create swap request"), 400

    data = request.get_json()
    if not data or 'request_id' not in data:
        return jsonify(message="Missing request_id"), 400

    if data.get('approve', True):
        result = shift_swap_manager.approve_swap(data['request_id'])
    else:
        result = shift_swap_manager.reject_swap(data['request_id'])

    if result:
        return jsonify(result.to_dict()), 200
    return jsonify(message="Swap request not found or already processed"), 404

# --- Meal Plan API Endpoints ---

@app.route('/recipes', methods=['POST'])
def api_create_recipe():
    data = request.get_json()
    if not data or not all(k in data for k in ("name", "ingredients")):
        return jsonify(message="Missing name or ingredients"), 400
    recipe = meal_plan.create_recipe(
        name=data['name'],
        ingredients=data['ingredients'],
        instructions=data.get('instructions')
    )
    if recipe:
        return jsonify(recipe.to_dict()), 201
    return jsonify(message="Failed to create recipe"), 400

@app.route('/recipes/<int:recipe_id>', methods=['GET'])
def api_get_recipe(recipe_id):
    recipe = meal_plan.get_recipe(recipe_id)
    if recipe:
        return jsonify(recipe.to_dict()), 200
    return jsonify(message="Recipe not found"), 404

@app.route('/recipes/<int:recipe_id>', methods=['PUT'])
def api_update_recipe(recipe_id):
    data = request.get_json()
    if not data:
        return jsonify(message="No data provided for update"), 400
    updated = meal_plan.update_recipe(
        recipe_id,
        name=data.get('name'),
        ingredients=data.get('ingredients'),
        instructions=data.get('instructions')
    )
    if updated:
        return jsonify(updated.to_dict()), 200
    return jsonify(message="Recipe not found"), 404

@app.route('/recipes/<int:recipe_id>', methods=['DELETE'])
def api_delete_recipe(recipe_id):
    if meal_plan.delete_recipe(recipe_id):
        return jsonify(message="Recipe deleted successfully"), 200
    return jsonify(message="Recipe not found"), 404

@app.route('/recipes', methods=['GET'])
def api_list_recipes():
    recipes = meal_plan.list_recipes()
    return jsonify([r.to_dict() for r in recipes]), 200

@app.route('/meal-plans', methods=['POST'])
def api_create_meal_plan():
    data = request.get_json()
    if not data or not all(k in data for k in ("week_start", "recipe_ids")):
        return jsonify(message="Missing week_start or recipe_ids"), 400
    plan = meal_plan.create_meal_plan(
        week_start_str=data['week_start'],
        recipe_ids=data['recipe_ids']
    )
    if plan:
        return jsonify(plan.to_dict(include_grocery=True)), 201
    return jsonify(message="Failed to create meal plan"), 400

@app.route('/meal-plans', methods=['GET'])
def api_list_meal_plans():
    plans = meal_plan.list_meal_plans()
    return jsonify([p.to_dict() for p in plans]), 200

@app.route('/meal-plans/<int:plan_id>', methods=['GET'])
def api_get_meal_plan(plan_id):
    plan = meal_plan.get_meal_plan(plan_id)
    if plan:
        return jsonify(plan.to_dict(include_grocery=True)), 200
    return jsonify(message="Meal plan not found"), 404

@app.route('/meal-plans/<int:plan_id>/groceries', methods=['GET'])
def api_get_meal_plan_groceries(plan_id):
    plan = meal_plan.get_meal_plan(plan_id)
    if not plan:
        return jsonify(message="Meal plan not found"), 404
    return jsonify(grocery_list=meal_plan.generate_grocery_list(plan)), 200

# --- Grocery Item Endpoints ---
@app.route('/grocery-items', methods=['POST'])
def api_add_grocery_item():
    data = request.get_json() or {}
    name = data.get('name')
    if not name:
        return jsonify(message="Missing item name"), 400
    quantity = data.get('quantity')
    user_id = data.get('user_id')
    item = grocery_manager.add_item(name=name, quantity=quantity, user_id=user_id)
    if item:
        return jsonify(item.to_dict()), 201
    return jsonify(message="Failed to create item"), 400


@app.route('/grocery-items', methods=['GET'])
def api_get_grocery_items():
    user_id = request.args.get('user_id', type=int)
    items = grocery_manager.get_items(user_id=user_id)
    return jsonify([i.to_dict() for i in items]), 200


@app.route('/grocery-items/<int:item_id>', methods=['PUT'])
def api_update_grocery_item(item_id):
    data = request.get_json() or {}
    item = grocery_manager.update_item(
        item_id,
        name=data.get('name'),
        quantity=data.get('quantity'),
        is_completed=data.get('is_completed')
    )
    if item:
        return jsonify(item.to_dict()), 200
    return jsonify(message="Item not found"), 404


@app.route('/grocery-items/<int:item_id>', methods=['DELETE'])
def api_delete_grocery_item(item_id):
    if grocery_manager.delete_item(item_id):
        return jsonify(message="Item deleted"), 200
    return jsonify(message="Item not found"), 404


# --- Album and Photo API Endpoints ---

@app.route('/albums', methods=['POST'])
def api_create_album():
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify(message="Missing album name"), 400
    album_obj = photo_manager.add_album(
        name=data['name'],
        description=data.get('description'),
        user_id=data.get('user_id'),
        is_public=data.get('is_public', False)
    )
    if album_obj:
        return jsonify(album_obj.to_dict()), 201
    return jsonify(message="Failed to create album"), 400


@app.route('/albums', methods=['GET'])
def api_get_albums():
    user_id = request.args.get('user_id', type=int)
    albums = photo_manager.get_albums(user_id=user_id)
    return jsonify([a.to_dict() for a in albums]), 200


@app.route('/photos', methods=['POST'])
def api_upload_photo():
    data = request.get_json()
    if not data or 'filename' not in data:
        return jsonify(message="Missing filename"), 400
    photo_obj = photo_manager.add_photo(
        filename=data['filename'],
        title=data.get('title'),
        description=data.get('description'),
        tags=data.get('tags'),
        user_id=data.get('user_id'),
        album_id=data.get('album_id'),
        is_public=data.get('is_public', False)
    )
    if photo_obj:
        return jsonify(photo_obj.to_dict()), 201
    return jsonify(message="Failed to add photo"), 400


@app.route('/photos', methods=['GET'])
def api_get_photos():
    album_id = request.args.get('album_id', type=int)
    search = request.args.get('search')
    photos = photo_manager.search_photos(album_id=album_id, search=search)
    return jsonify([p.to_dict() for p in photos]), 200

# --- ResidencyPeriod API Endpoints ---
# (This section should remain as is, the new web routes for shifts will be added before/after this block,
#  but outside of the API endpoint definitions. Let's add Web Routes section after logout.)

# --- Web Page Routes (HTML) ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'parent')

        if not name or not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('register.html'), 400

        new_user = auth.register(name=name, email=email, password=password, role=role)

        if new_user:
            session['user_id'] = new_user.id
            session['user_name'] = new_user.name
            session['role'] = new_user.role
            flash(f'Welcome, {new_user.name}! You have been successfully registered and logged in.', 'success')
            return redirect(url_for('index'))
        else:
            db_s = SessionLocal()
            existing = db_s.query(user.User).filter(user.User.email == email).first()
            db_s.close()
            if existing:
                 flash('Email already registered. Please login or use a different email.', 'warning')
            else:
                flash('Registration failed due to an unexpected error. Please try again.', 'danger')
            return render_template('register.html')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash('Email and password are required.', 'danger')
            return render_template('login.html'), 400

        logged_in_user = auth.login(email=email, password=password)

        if logged_in_user:
            session['user_id'] = logged_in_user.id
            session['user_name'] = logged_in_user.name
            session['role'] = logged_in_user.role
            flash(f'Welcome back, {logged_in_user.name}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Login failed. Invalid email or password.', 'danger')
            return render_template('login.html')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    session.pop('role', None)
    flash('You have been successfully logged out.', 'success')
    return redirect(url_for('index'))

# --- Plugin Management Web Route ---
@app.route('/admin/plugins', methods=['GET', 'POST'])
def manage_plugins():
    if request.method == 'POST':
        plugin_name = request.form.get('plugin')
        action = request.form.get('action')
        if action == 'enable':
            plugin_manager.enable_plugin(plugin_name)
        elif action == 'disable':
            plugin_manager.disable_plugin(plugin_name)
        return redirect(url_for('manage_plugins'))
    plugins = plugin_manager.list_plugins()
    return render_template('plugins.html', plugins=plugins)
@app.route('/notifications/stream')
def notifications_stream():
    if 'user_id' not in session:
        return "Unauthorized", 401

    user_id = session['user_id']
    q = get_user_queue(user_id)

    def event_stream():
        while True:
            data = q.get()
            yield f"data: {data}\n\n"

    return Response(event_stream(), mimetype='text/event-stream')

# --- Shift Web Routes ---

@app.route('/shifts', methods=['GET'])
def shifts_view():
    if 'user_id' not in session:
        flash('Please login to view your shifts.', 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id']
    user_shifts = shift_manager.get_user_shifts(user_id=user_id) # Managers handle their own sessions

    return render_template('shifts.html', shifts=user_shifts)

@app.route('/shifts/add', methods=['POST'])
def add_shift():
    if 'user_id' not in session:
        flash('Please login to add a shift.', 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id']
    name = request.form.get('name')
    start_time_str_html = request.form.get('start_time') # HTML datetime-local format: YYYY-MM-DDTHH:MM
    end_time_str_html = request.form.get('end_time')

    if not name or not start_time_str_html or not end_time_str_html:
        flash('All fields (name, start time, end time) are required.', 'danger')
        return redirect(url_for('shifts_view'))

    try:
        start_time_formatted = datetime.fromisoformat(start_time_str_html).strftime('%Y-%m-%d %H:%M')
        end_time_formatted = datetime.fromisoformat(end_time_str_html).strftime('%Y-%m-%d %H:%M')
    except ValueError:
        flash('Invalid datetime format submitted.', 'danger')
        return redirect(url_for('shifts_view'))

    new_shift = shift_manager.add_shift(
        user_id=user_id,
        name=name,
        start_time_str=start_time_formatted,
        end_time_str=end_time_formatted
    ) # Managers handle their own sessions

    if new_shift:
        flash('Shift added successfully!', 'success')
    else:
        flash('Failed to add shift. Please check your input or try again.', 'danger')

    return redirect(url_for('shifts_view'))


# --- Album and Photo Web Routes ---

@app.route('/albums', methods=['GET'])
def albums_view():
    albums = photo_manager.get_albums()
    return render_template('albums.html', albums=albums)


@app.route('/photos', methods=['GET'])
def photos_view():
    search = request.args.get('search')
    photos = photo_manager.search_photos(search=search)
    return render_template('photos.html', photos=photos)


# --- API Endpoints (JSON) ---
# (Existing API endpoints for auth, shifts, children, events, shift_patterns, residency_periods follow)


# --- Event Web Routes ---

@app.route('/events', methods=['GET'])
def events_view():
    if 'user_id' not in session:
        flash('Please login to view your events.', 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id']
    # Managers handle their own DB sessions
    user_events = event_manager.get_events_for_user(user_id=user_id)
    user_children = child_manager.get_user_children(user_id=user_id)  # For the dropdown
    overbooked_ids = ai_scheduler.find_overlapping_events(user_events)

    # Enhance event objects with child names if linked
    # This is a bit inefficient here; ideally, a JOIN in the query or a method in the model would do this.
    # For now, let's try to add child names if a child_id exists for simplicity in template.
    # This is not ideal as it leads to N+1 queries if not careful or if ORM doesn't auto-load.
    # event_manager.get_events_for_user already returns Event objects with child relationship loaded if accessed.

    return render_template('events.html', events=user_events, children=user_children, overbooked_ids=overbooked_ids)

@app.route('/events/add-web', methods=['POST'])
def add_event_web():
    if 'user_id' not in session:
        flash('Please login to add an event.', 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id']
    title = request.form.get('title')
    description = request.form.get('description')
    start_time_str_html = request.form.get('start_time') # HTML datetime-local
    end_time_str_html = request.form.get('end_time')     # HTML datetime-local
    child_id_str = request.form.get('child_id')

    if not title or not start_time_str_html or not end_time_str_html:
        flash('Title, start time, and end time are required for an event.', 'danger')
        return redirect(url_for('events_view'))

    try:
        start_time_formatted = datetime.fromisoformat(start_time_str_html).strftime('%Y-%m-%d %H:%M')
        end_time_formatted = datetime.fromisoformat(end_time_str_html).strftime('%Y-%m-%d %H:%M')
    except ValueError:
        flash('Invalid datetime format submitted for event.', 'danger')
        return redirect(url_for('events_view'))

    linked_child_id = None
    if child_id_str and child_id_str.isdigit(): # Check if it's a digit before int()
        linked_child_id = int(child_id_str)
        # Optional: Validate if this child_id belongs to the current user
        user_children_ids = [c.id for c in child_manager.get_user_children(user_id=user_id)]
        if linked_child_id not in user_children_ids:
            flash('Invalid child selected for the event.', 'danger')
            return redirect(url_for('events_view'))
    elif child_id_str: # If not empty and not a digit (or empty string from "-- None --")
        flash('Invalid child ID format.', 'danger') # Or just ignore if it's empty string
        return redirect(url_for('events_view'))


    conflict_info = event_manager.detect_conflicts(
        start_time_str=start_time_formatted,
        end_time_str=end_time_formatted,
        user_id=user_id,
        child_id=linked_child_id
    )
    if conflict_info.get('conflicts'):
        flash('Conflict detected with existing schedule.', 'danger')
        if conflict_info.get('suggested_start'):
            flash(f"Suggested: {conflict_info['suggested_start']} - {conflict_info['suggested_end']}", 'info')
        return redirect(url_for('events_view'))

    new_event = event_manager.create_event(
        title=title,
        description=description,
        start_time_str=start_time_formatted,
        end_time_str=end_time_formatted,
        child_id=linked_child_id if linked_child_id else None,
        linked_user_id=user_id,
        linked_child_id=linked_child_id if linked_child_id else None
    )

    if new_event:
        if adjusted:
            flash('Requested time was busy. Event scheduled for ' + new_event.start_time.strftime('%Y-%m-%d %H:%M'), 'warning')
        else:
            flash('Event added successfully!', 'success')
    else:
        flash('Failed to add event. Please check your input or try again.', 'danger')

    return redirect(url_for('events_view'))


@app.route('/events/<int:event_id>/complete-web', methods=['POST'])
def complete_event_web(event_id):
    if 'user_id' not in session:
        flash('Please login.', 'warning')
        return redirect(url_for('login'))

    updated = event_manager.update_event(event_id=event_id, completed=True)
    if updated:
        flash('Event marked completed!', 'success')
    else:
        flash('Could not update event.', 'danger')
    return redirect(url_for('events_view'))


@app.route('/leaderboard', methods=['GET'])
def leaderboard_view():
    db = SessionLocal()
    try:
        standings = (
            db.query(badge.Badge, user.User)
            .join(user.User, badge.Badge.user_id == user.User.id)
            .order_by(badge.Badge.points.desc())
            .all()
        )
        results = [
            {"name": u.name, "points": b.points, "badges": b.badges.split(',') if b.badges else []}
            for b, u in standings
        ]
    finally:
        db.close()
    return render_template('leaderboard.html', leaders=results)


# --- Booking Web Routes ---
@app.route('/bookings', methods=['GET'])
def bookings_view():
    if 'user_id' not in session:
        flash('Please login to view your bookings.', 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id']
    user_bookings = booking_manager.get_bookings_for_user(user_id=user_id)
    return render_template('bookings.html', bookings=user_bookings)

@app.route('/bookings/add-web', methods=['POST'])
def add_booking_web():
    if 'user_id' not in session:
        flash('Please login to add a booking.', 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id']
    service = request.form.get('service')
    start_time_str_html = request.form.get('start_time')
    end_time_str_html = request.form.get('end_time')

    if not service or not start_time_str_html or not end_time_str_html:
        flash('All fields are required for a booking.', 'danger')
        return redirect(url_for('bookings_view'))

    try:
        start_formatted = datetime.fromisoformat(start_time_str_html).strftime('%Y-%m-%d %H:%M')
        end_formatted = datetime.fromisoformat(end_time_str_html).strftime('%Y-%m-%d %H:%M')
    except ValueError:
        flash('Invalid datetime format submitted for booking.', 'danger')
        return redirect(url_for('bookings_view'))

    new_booking = booking_manager.create_booking(
        service=service,
        start_time_str=start_formatted,
        end_time_str=end_formatted,
        user_id=user_id
    )
    if new_booking:
        flash('Booking added successfully!', 'success')
    else:
        flash('Failed to add booking. Please try again.', 'danger')

    return redirect(url_for('bookings_view'))

# --- Task Web Routes ---

@app.route('/tasks', methods=['GET'])
def tasks_view():
    if 'user_id' not in session:
        flash('Please login to view your tasks.', 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id']
    user_tasks = task_manager.get_tasks_for_user(user_id=user_id)
    user_events = event_manager.get_events_for_user(user_id=user_id)
    return render_template('tasks.html', tasks=user_tasks, events=user_events)


@app.route('/tasks/add-web', methods=['POST'])
def add_task_web():
    if 'user_id' not in session:
        flash('Please login to add a task.', 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id']
    description = request.form.get('description')
    due_date_str_html = request.form.get('due_date')
    event_id_str = request.form.get('event_id')

    if not description:
        flash('Task description is required.', 'danger')
        return redirect(url_for('tasks_view'))

    due_date_formatted = None
    if due_date_str_html:
        try:
            due_date_formatted = datetime.fromisoformat(due_date_str_html).strftime('%Y-%m-%d %H:%M')
        except ValueError:
            flash('Invalid datetime format submitted for task.', 'danger')
            return redirect(url_for('tasks_view'))

    linked_event_id = None
    if event_id_str and event_id_str.isdigit():
        linked_event_id = int(event_id_str)
        user_event_ids = [e.id for e in event_manager.get_events_for_user(user_id=user_id)]
        if linked_event_id not in user_event_ids:
            flash('Invalid event selected for the task.', 'danger')
            return redirect(url_for('tasks_view'))
    elif event_id_str:
        flash('Invalid event ID format.', 'danger')
        return redirect(url_for('tasks_view'))

    new_task = task_manager.create_task(
        description=description,
        due_date_str=due_date_formatted,
        user_id=user_id,
        event_id=linked_event_id
    )

    if new_task:
        flash('Task added successfully!', 'success')
    else:
        flash('Failed to add task. Please try again.', 'danger')

    return redirect(url_for('tasks_view'))

# --- Expense Web Routes ---

@app.route('/expenses', methods=['GET'])
def expenses_view():
    if 'user_id' not in session:
        flash('Please login to view expenses.', 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id']
    expenses_list = expense_manager.get_all_expenses()
    children = child_manager.get_user_children(user_id=user_id)
    return render_template('expenses.html', expenses=expenses_list, children=children)


@app.route('/expenses', methods=['POST'])
def add_expense():
    if 'user_id' not in session:
        flash('Please login to add an expense.', 'warning')
        return redirect(url_for('login'))

    description = request.form.get('description')
    amount_str = request.form.get('amount')
    child_id_str = request.form.get('child_id')

    if not description or not amount_str:
        flash('Description and amount are required.', 'danger')
        return redirect(url_for('expenses_view'))

    try:
        amount = float(amount_str)
    except ValueError:
        flash('Invalid amount.', 'danger')
        return redirect(url_for('expenses_view'))

    child_id = int(child_id_str) if child_id_str and child_id_str.isdigit() else None

    new_exp = expense_manager.add_expense(
        description=description,
        amount=amount,
        paid_by_id=session['user_id'],
        child_id=child_id
    )
    if new_exp:
        flash('Expense added successfully!', 'success')
    else:
        flash('Failed to add expense.', 'danger')
    return redirect(url_for('expenses_view'))




# --- Child Web Routes ---

@app.route('/children', methods=['GET'])
def children_view():
    if 'user_id' not in session:
        flash('Please login to view your children.', 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id']
    # child_manager.get_user_children expects user_id and handles its own DB session
    user_children = child_manager.get_user_children(user_id=user_id)

    return render_template('children.html', children=user_children)

@app.route('/children/add-web', methods=['POST']) # Renamed to avoid API conflict
def add_child_web():
    if 'user_id' not in session:
        flash('Please login to add a child.', 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id']
    name = request.form.get('name')
    date_of_birth_str = request.form.get('date_of_birth') # HTML date input format: YYYY-MM-DD
    school_info = request.form.get('school_info')
    # custody_schedule_info = request.form.get('custody_schedule_info') # If using the old field

    if not name or not date_of_birth_str:
        flash('Child\'s name and date of birth are required.', 'danger')
        return redirect(url_for('children_view'))

    # child_manager.add_child expects date_of_birth_str in '%Y-%m-%d' format, which HTML date input provides.
    # It also handles its own DB session.
    new_child = child_manager.add_child(
        user_id=user_id,
        name=name,
        date_of_birth_str=date_of_birth_str,
        school_info=school_info
        # custody_schedule_info=custody_schedule_info # Pass if using the old field
    )

    if new_child:
        flash('Child added successfully!', 'success')
    else:
        # child_manager.add_child prints detailed errors
        flash('Failed to add child. Please check your input or try again.', 'danger')

    return redirect(url_for('children_view'))

@app.route("/analytics")
def analytics_view():
    if "user_id" not in session:
        flash("Please login to view analytics.", "warning")
        return redirect(url_for("login"))
    user_id = session["user_id"]
    data = analytics.get_monthly_analytics(user_id)
    return render_template("analytics.html", data=data)



# --- Document Web Routes ---

@app.route('/documents', methods=['GET', 'POST'])
def documents_view():
    if 'user_id' not in session:
        flash('Please login to manage documents.', 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id']

    if request.method == 'POST':
        uploaded = request.files.get('file')
        child_id_str = request.form.get('child_id')
        child_id = int(child_id_str) if child_id_str and child_id_str.isdigit() else None

        if not uploaded or uploaded.filename == '':
            flash('No file selected.', 'danger')
            return redirect(url_for('documents_view'))

        filename = secure_filename(uploaded.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        uploaded.save(file_path)

        db = SessionLocal()
        try:
            doc_record = document.Document(filename=filename, user_id=user_id, child_id=child_id)
            db.add(doc_record)
            db.commit()
            flash('File uploaded successfully.', 'success')
        except Exception as e:
            db.rollback()
            flash('Failed to save document.', 'danger')
            print(f'Error saving document: {e}')
        finally:
            db.close()
        return redirect(url_for('documents_view'))

    db = SessionLocal()
    docs = db.query(document.Document).filter(document.Document.user_id == user_id).all()
    db.close()
    user_children = child_manager.get_user_children(user_id=user_id)
    return render_template('documents.html', documents=docs, children=user_children)


@app.route('/uploads/<path:filename>')
def download_document(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


# The previous residency period POST route:
@api_bp.route('/children/<int:child_id>/residency-periods', methods=['POST'])
@token_required
def api_add_residency_period(child_id):
    data = request.get_json()
    if not data or not all(k in data for k in ("parent_id", "start_datetime", "end_datetime")):
        return jsonify(message="Missing parent_id, start_datetime, or end_datetime"), 400

    db = SessionLocal()
    try:
        if not auth.user_has_role(data['parent_id'], 'parent'):
            return jsonify(message="Only parents may create residency periods."), 403
        # The child_manager functions now expect db_session as the first argument
        new_period = child_manager.add_residency_period(
            db_session=db,
            child_id=child_id,
            parent_id=data['parent_id'],
            start_datetime_str=data['start_datetime'],
            end_datetime_str=data['end_datetime'],
            notes=data.get('notes')
        )
        db.commit()
        db.refresh(new_period) # To get ID and other DB-generated values
        return jsonify(new_period.to_dict()), 201
    except ValueError as ve:
        db.rollback()
        return jsonify(message=str(ve)), 400 # e.g., child/parent not found, invalid dates
    except SQLAlchemyError as sqla_e:
        db.rollback()
        print(f"SQLAlchemyError adding residency period: {sqla_e}")
        return jsonify(message="Database error adding residency period."), 500
    except Exception as e:
        db.rollback()
        print(f"Unexpected error adding residency period: {e}")
        return jsonify(message="An unexpected error occurred."), 500
    finally:
        db.close()

@api_bp.route('/children/<int:child_id>/residency-periods', methods=['GET'])
@token_required
def api_get_residency_periods_for_child(child_id):
    start_date_filter = request.args.get('start_date') # YYYY-MM-DD
    end_date_filter = request.args.get('end_date')     # YYYY-MM-DD

    db = SessionLocal()
    try:
        # Validate child_id exists
        target_child = db.query(child.Child).filter(child.Child.id == child_id).first()
        if not target_child:
            return jsonify(message="Child not found"), 404

        periods = child_manager.get_residency_periods_for_child(
            db_session=db,
            child_id=child_id,
            start_filter_date_str=start_date_filter,
            end_filter_date_str=end_date_filter
        )
        return jsonify([p.to_dict() for p in periods]), 200
    except Exception as e: # Catch-all for unexpected errors
        print(f"Error getting residency periods: {e}")
        return jsonify(message="An unexpected error occurred."), 500
    finally:
        db.close()

@api_bp.route('/residency-periods/<int:period_id>', methods=['GET'])
@token_required
def api_get_residency_period_details(period_id):
    db = SessionLocal()
    try:
        period = child_manager.get_residency_period_details(db_session=db, period_id=period_id)
        if period:
            return jsonify(period.to_dict(include_child=True, include_parent=True)), 200
        return jsonify(message="Residency period not found"), 404
    finally:
        db.close()

@api_bp.route('/residency-periods/<int:period_id>', methods=['PUT'])
@token_required
def api_update_residency_period(period_id):
    data = request.get_json()
    if not data:
        return jsonify(message="No data provided for update"), 400

    db = SessionLocal()
    try:
        if data.get('parent_id') and not auth.user_has_role(data.get('parent_id'), 'parent'):
            return jsonify(message="Only parents may update residency periods."), 403
        if not data.get('parent_id'):
            existing = child_manager.get_residency_period_details(db_session=db, period_id=period_id)
            if existing and not auth.user_has_role(existing.parent_id, 'parent'):
                return jsonify(message="Only parents may update residency periods."), 403
        updated_period = child_manager.update_residency_period(
            db_session=db,
            period_id=period_id,
            parent_id=data.get('parent_id'),
            start_datetime_str=data.get('start_datetime'),
            end_datetime_str=data.get('end_datetime'),
            notes=data.get('notes')
        )
        db.commit()
        db.refresh(updated_period)
        return jsonify(updated_period.to_dict()), 200
    except ValueError as ve:
        db.rollback()
        return jsonify(message=str(ve)), 400 # Or 404 if "not found"
    except SQLAlchemyError as sqla_e:
        db.rollback()
        print(f"SQLAlchemyError updating residency period: {sqla_e}")
        return jsonify(message="Database error updating residency period."), 500
    except Exception as e:
        db.rollback()
        print(f"Unexpected error updating residency period: {e}")
        return jsonify(message="An unexpected error occurred."), 500
    finally:
        db.close()

@api_bp.route('/residency-periods/<int:period_id>', methods=['DELETE'])
@token_required
def api_delete_residency_period(period_id):
    db = SessionLocal()
    try:
        period = child_manager.get_residency_period_details(db_session=db, period_id=period_id)
        if not period:
            return jsonify(message="Residency period not found"), 404
        if not auth.user_has_role(period.parent_id, 'parent'):
            return jsonify(message="Only parents may delete residency periods."), 403
        success = child_manager.delete_residency_period(db_session=db, period_id=period_id)
        if success:
            db.commit()
            return jsonify(message="Residency period deleted successfully"), 200 # Or 204
        return jsonify(message="Residency period not found"), 404
    except SQLAlchemyError as sqla_e: # If delete causes DB error (e.g. FK issue if not handled by cascade)
        db.rollback()
        print(f"SQLAlchemyError deleting residency period: {sqla_e}")
        return jsonify(message="Database error deleting residency period."), 500
    except Exception as e:
        db.rollback()
        print(f"Unexpected error deleting residency period: {e}")
        return jsonify(message="An unexpected error occurred."), 500
    finally:
        db.close()


@api_bp.route('/children/<int:child_id>/residency', methods=['GET'])
@token_required

# ----- Residency change request endpoints -----

@app.route('/residency-periods/<int:period_id>/propose-change', methods=['POST'])
def api_propose_residency_change(period_id):
    data = request.get_json()
    if not data:
        return jsonify(message="No change data provided"), 400

    db = SessionLocal()
    try:
        period = child_manager.get_residency_period_details(db_session=db, period_id=period_id)
        if not period:
            return jsonify(message="Residency period not found"), 404

        period.proposed_start_datetime = child_manager._parse_datetime_for_residency(data.get('start_datetime')) if data.get('start_datetime') else None
        period.proposed_end_datetime = child_manager._parse_datetime_for_residency(data.get('end_datetime')) if data.get('end_datetime') else None
        period.change_notes = data.get('notes')
        period.approval_status = 'pending'
        db.commit()
        db.refresh(period)
        return jsonify(period.to_dict()), 200
    except Exception as e:
        db.rollback()
        print(f"Error proposing change: {e}")
        return jsonify(message="Error proposing change"), 500
    finally:
        db.close()


@app.route('/residency-periods/<int:period_id>/accept-change', methods=['POST'])
def api_accept_residency_change(period_id):
    db = SessionLocal()
    try:
        period = child_manager.get_residency_period_details(db_session=db, period_id=period_id)
        if not period:
            return jsonify(message="Residency period not found"), 404

        if period.proposed_start_datetime:
            period.start_datetime = period.proposed_start_datetime
        if period.proposed_end_datetime:
            period.end_datetime = period.proposed_end_datetime
        if period.change_notes:
            period.notes = period.change_notes

        period.proposed_start_datetime = None
        period.proposed_end_datetime = None
        period.change_notes = None
        period.approval_status = 'approved'
        db.commit()
        db.refresh(period)
        return jsonify(period.to_dict()), 200
    except Exception as e:
        db.rollback()
        print(f"Error accepting change: {e}")
        return jsonify(message="Error accepting change"), 500
    finally:
        db.close()


@app.route('/residency-periods/<int:period_id>/decline-change', methods=['POST'])
def api_decline_residency_change(period_id):
    db = SessionLocal()
    try:
        period = child_manager.get_residency_period_details(db_session=db, period_id=period_id)
        if not period:
            return jsonify(message="Residency period not found"), 404

        period.proposed_start_datetime = None
        period.proposed_end_datetime = None
        period.change_notes = None
        period.approval_status = 'declined'
        db.commit()
        db.refresh(period)
        return jsonify(period.to_dict()), 200
    except Exception as e:
        db.rollback()
        print(f"Error declining change: {e}")
        return jsonify(message="Error declining change"), 500
    finally:
        db.close()

@app.route('/children/<int:child_id>/residency', methods=['GET'])

def api_get_child_residency_on_date(child_id):
    date_param = request.args.get('date')
    if not date_param:
        return jsonify(message="Missing 'date' query parameter (YYYY-MM-DD)"), 400

    db = SessionLocal()
    try:
        # Validate child_id exists
        target_child = db.query(child.Child).filter(child.Child.id == child_id).first()
        if not target_child:
            db.close()
            return jsonify(message="Child not found"), 404

        active_periods = child_manager.get_child_residency_on_date(
            db_session=db,
            child_id=child_id,
            date_str=date_param
        )
        # For simplicity, if multiple periods overlap (which shouldn't ideally happen for 'who is child with now'),
        # we just return all. A more sophisticated logic might be needed to pick the most relevant one.
        if not active_periods:
            return jsonify(message=f"No residency period found for child {child_id} on {date_param}."), 404

        # Return details of the parent(s) the child is with.
        # If multiple periods, this will list them all.
        return jsonify([p.to_dict(include_child=False, include_parent=True) for p in active_periods]), 200
    except ValueError as ve: # Raised by manager for invalid date format
        return jsonify(message=str(ve)), 400
    except Exception as e:
        print(f"Error getting child residency on date: {e}")
        return jsonify(message="An unexpected error occurred."), 500
    finally:
        db.close()

# Register API blueprint
app.register_blueprint(api_bp, url_prefix="/api/v1")


# --- Google Calendar Endpoints ---

@app.route('/users/<int:user_id>/calendar/sync', methods=['POST'])
def api_sync_calendar(user_id):
    events = calendar_sync.sync_user_calendar(user_id)
    return jsonify(message="Calendar synced", events=len(events)), 200



if __name__ == '__main__':
    # Note: For development, app.run(debug=True) is fine.
    # For production, use a WSGI server like Gunicorn or uWSGI.
    # Example: gunicorn app:app -w 4
    app.run(debug=True, host='0.0.0.0', port=5000)
