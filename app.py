from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from sqlalchemy.exc import SQLAlchemyError
import os # For secret key

from src import auth, user, shift, child, event # Models
from src import shift_manager, child_manager, event_manager, shift_pattern_manager # Managers
# Plugin system
from src.plugins import PluginManager
from src.database import init_db, SessionLocal
# Import residency_period model for init_db
from src import residency_period

# Initialize the database (create tables if they don't exist)
# This should be called once when the application starts.
try:
    # Import models to ensure they are registered with Base before init_db() is called
    from src import user, shift, child, event # Models
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

# Optional: A generic error handler for unhandled exceptions
@app.errorhandler(Exception)
def handle_generic_error(e):
    # Log the error e
    print(f"An unhandled exception occurred: {e}") # Basic logging
    response = jsonify(message="An unexpected error occurred on the server.")
    response.status_code = 500
    return response

@app.route('/auth/register', methods=['POST'])
def register_user():
    try:
        data = request.get_json()
        if not data or not all(k in data for k in ("name", "email", "password")):
            return jsonify(message="Missing name, email, or password in request"), 400

        name = data.get('name')
        email = data.get('email')
        password = data.get('password')

        # The auth.register function now uses SQLAlchemy and handles DB interaction
        new_user = auth.register(name=name, email=email, password=password)

        if new_user:
            # new_user is an SQLAlchemy User model instance
            return jsonify(message="User registered successfully", user_id=new_user.id, name=new_user.name), 201
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


@app.route('/auth/login', methods=['POST'])
def login_user():
    try:
        data = request.get_json()
        if not data or not all(k in data for k in ("email", "password")):
            return jsonify(message="Missing email or password"), 400

        email = data.get('email')
        password = data.get('password')

        # auth.login now uses SQLAlchemy
        logged_in_user = auth.login(email=email, password=password)

        if logged_in_user:
            # logged_in_user is an SQLAlchemy User model instance
            return jsonify(message="Login successful", user_id=logged_in_user.id, name=logged_in_user.name, email=logged_in_user.email), 200
        else:
            # auth.login prints "Error: Email not found." or "Error: Incorrect password."
            return jsonify(message="Login failed: Invalid email or password."), 401 # Unauthorized

    except Exception as e:
        print(f"Error in /auth/login: {e}")
        return jsonify(message="An unexpected error occurred during login."), 500


@app.route('/auth/logout', methods=['POST'])
def logout_user():
    # In a stateless API (common with tokens), logout is often handled client-side by deleting the token.
    # Server-side logout might involve invalidating a token if using a denylist.
    # For this basic version, we just acknowledge the request.
    # auth.logout() itself just prints a message.
    auth.logout()
    return jsonify(message="Logout successful"), 200


# --- Child API Endpoints ---

@app.route('/users/<int:user_id>/children', methods=['POST'])
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

@app.route('/children/<int:child_id>', methods=['GET'])
def api_get_child_details(child_id):
    child_obj = child_manager.get_child_details(child_id)
    if child_obj:
        return jsonify(child_obj.to_dict(include_parents=True)), 200
    return jsonify(message="Child not found"), 404

@app.route('/users/<int:user_id>/children', methods=['GET'])
def api_get_user_children(user_id):
    # Optional: Validate user_id exists
    children_list = child_manager.get_user_children(user_id)
    return jsonify([c.to_dict(include_parents=False) for c in children_list]), 200 # include_parents=False to simplify

@app.route('/children/<int:child_id>', methods=['PUT'])
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

@app.route('/children/<int:child_id>', methods=['DELETE'])
def api_delete_child(child_id):
    if child_manager.remove_child(child_id):
        return jsonify(message="Child deleted successfully"), 200 # Or 204
    return jsonify(message="Child not found or delete failed"), 404

@app.route('/children/<int:child_id>/parents', methods=['POST'])
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

@app.route('/events', methods=['POST'])
def api_create_event():
    data = request.get_json()
    if not data or not all(k in data for k in ("title", "start_time", "end_time")):
        return jsonify(message="Missing title, start_time, or end_time for event"), 400

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

@app.route('/events/<int:event_id>', methods=['GET'])
def api_get_event_details(event_id):
    event_obj = event_manager.get_event_details(event_id)
    if event_obj:
        return jsonify(event_obj.to_dict()), 200
    return jsonify(message="Event not found"), 404

@app.route('/users/<int:user_id>/events', methods=['GET'])
def api_get_user_events(user_id):
    # Optional: Validate user_id exists
    events_list = event_manager.get_events_for_user(user_id)
    return jsonify([e.to_dict(include_user=False) for e in events_list]), 200 # Don't include user again

@app.route('/children/<int:child_id>/events', methods=['GET'])
def api_get_child_events(child_id):
    # Optional: Validate child_id exists
    events_list = event_manager.get_events_for_child(child_id)
    return jsonify([e.to_dict(include_child=False) for e in events_list]), 200 # Don't include child again

@app.route('/events/<int:event_id>', methods=['PUT'])
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
        unlink_user=unlink_user,
        unlink_child=unlink_child
    )
    if updated_event_obj:
        return jsonify(updated_event_obj.to_dict()), 200
    return jsonify(message="Event not found or update failed"), 404 # Or 400

@app.route('/events/<int:event_id>', methods=['DELETE'])
def api_delete_event(event_id):
    if event_manager.delete_event(event_id):
        return jsonify(message="Event deleted successfully"), 200 # Or 204
    return jsonify(message="Event not found or delete failed"), 404


# --- Shift Pattern API Endpoints ---

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

@app.route('/users/<int:user_id>/shift-patterns', methods=['POST'])
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

@app.route('/shift-patterns/<int:pattern_id>', methods=['GET'])
def api_get_shift_pattern(pattern_id):
    pattern = shift_pattern_manager.get_shift_pattern(pattern_id)
    if pattern:
        return jsonify(pattern.to_dict()), 200
    return jsonify(message="Shift pattern not found"), 404

@app.route('/shift-patterns', methods=['GET'])
def api_get_global_shift_patterns():
    patterns = shift_pattern_manager.get_global_shift_patterns()
    return jsonify([p.to_dict() for p in patterns]), 200

@app.route('/users/<int:user_id>/shift-patterns', methods=['GET'])
def api_get_user_shift_patterns(user_id):
    # Optional: Validate user_id exists
    db = SessionLocal()
    target_user = db.query(user.User).filter(user.User.id == user_id).first()
    db.close()
    if not target_user:
        return jsonify(message=f"User with id {user_id} not found."), 404

    patterns = shift_pattern_manager.get_shift_patterns_for_user(user_id)
    return jsonify([p.to_dict() for p in patterns]), 200

@app.route('/shift-patterns/<int:pattern_id>', methods=['PUT'])
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

@app.route('/shift-patterns/<int:pattern_id>', methods=['DELETE'])
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

@app.route('/users/<int:user_id>/shift-patterns/<int:pattern_id>/generate-shifts', methods=['POST'])
def api_generate_shifts_from_pattern(user_id, pattern_id):
    data = request.get_json()
    if not data or not all(k in data for k in ("start_date", "end_date")):
        return jsonify(message="Missing start_date or end_date in request"), 400

    start_date_str = data['start_date']
    end_date_str = data['end_date']

    db = SessionLocal()
    try:
        created_shifts = shift_pattern_manager.generate_shifts_from_pattern(
            db_session=db,
            pattern_id=pattern_id,
            user_id=user_id,
            start_date_str=start_date_str,
            end_date_str=end_date_str
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

        if not name or not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('register.html'), 400

        new_user = auth.register(name=name, email=email, password=password)

        if new_user:
            session['user_id'] = new_user.id
            session['user_name'] = new_user.name
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
    user_children = child_manager.get_user_children(user_id=user_id) # For the dropdown

    # Enhance event objects with child names if linked
    # This is a bit inefficient here; ideally, a JOIN in the query or a method in the model would do this.
    # For now, let's try to add child names if a child_id exists for simplicity in template.
    # This is not ideal as it leads to N+1 queries if not careful or if ORM doesn't auto-load.
    # event_manager.get_events_for_user already returns Event objects with child relationship loaded if accessed.

    return render_template('events.html', events=user_events, children=user_children)

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


    # Events created via web are always linked to the current user.
    # event_manager.create_event handles its own DB session.
    new_event = event_manager.create_event(
        title=title,
        description=description,
        start_time_str=start_time_formatted,
        end_time_str=end_time_formatted,
        linked_user_id=user_id, # Auto-link to current user
        linked_child_id=linked_child_id if linked_child_id else None # Ensure None if 0 or empty
    )

    if new_event:
        flash('Event added successfully!', 'success')
    else:
        # event_manager.create_event prints detailed errors
        flash('Failed to add event. Please check your input or try again.', 'danger')

    return redirect(url_for('events_view'))


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


# The previous residency period POST route:
@app.route('/children/<int:child_id>/residency-periods', methods=['POST'])
def api_add_residency_period(child_id):
    data = request.get_json()
    if not data or not all(k in data for k in ("parent_id", "start_datetime", "end_datetime")):
        return jsonify(message="Missing parent_id, start_datetime, or end_datetime"), 400

    db = SessionLocal()
    try:
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

@app.route('/children/<int:child_id>/residency-periods', methods=['GET'])
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

@app.route('/residency-periods/<int:period_id>', methods=['GET'])
def api_get_residency_period_details(period_id):
    db = SessionLocal()
    try:
        period = child_manager.get_residency_period_details(db_session=db, period_id=period_id)
        if period:
            return jsonify(period.to_dict(include_child=True, include_parent=True)), 200
        return jsonify(message="Residency period not found"), 404
    finally:
        db.close()

@app.route('/residency-periods/<int:period_id>', methods=['PUT'])
def api_update_residency_period(period_id):
    data = request.get_json()
    if not data:
        return jsonify(message="No data provided for update"), 400

    db = SessionLocal()
    try:
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

@app.route('/residency-periods/<int:period_id>', methods=['DELETE'])
def api_delete_residency_period(period_id):
    db = SessionLocal()
    try:
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


if __name__ == '__main__':
    # Note: For development, app.run(debug=True) is fine.
    # For production, use a WSGI server like Gunicorn or uWSGI.
    # Example: gunicorn app:app -w 4
    app.run(debug=True, host='0.0.0.0', port=5000)
