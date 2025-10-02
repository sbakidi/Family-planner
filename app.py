from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash, Response
from sqlalchemy.exc import SQLAlchemyError
import os # For secret key

from src import auth, user, shift, child, event, grocery, task, institution, consent, treatment_plan  # Models
from src import shift_manager, child_manager, event_manager, shift_pattern_manager, grocery_manager, calendar_sync, shift_swap_manager, expense_manager, task_manager  # Managers
from src.notification import get_user_queue

from src.database import init_db, SessionLocal
# Import residency_period model for init_db
from src import residency_period

# Initialize the database (create tables if they don't exist)
# This should be called once when the application starts.
try:
    # Import models to ensure they are registered with Base before init_db() is called
    from src import user, shift, child, event, shift_swap, expense, task, institution, consent, treatment_plan  # Models
    # Import residency_period model for init_db
    from src import residency_period
    from datetime import datetime # For HTML form datetime-local conversion
    init_db()
except Exception as e:
    print(f"Error initializing database during app startup: {e}")
    # Depending on the application, you might want to exit or log this critical error.

app = Flask(__name__)
app.secret_key = os.urandom(24) # Generate a random secret key for sessions

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

        new_user = auth.register(name=name, email=email, password=password)

        if new_user:
            return jsonify(message="User registered successfully", user_id=new_user.id, name=new_user.name), 201
        else:
            db_session = SessionLocal()
            existing = db_session.query(user.User).filter(user.User.email == email).first()
            db_session.close()
            if existing:
                 return jsonify(message="Email already exists."), 409 # Conflict
            return jsonify(message="Registration failed. Possible database error or invalid input."), 400

    except Exception as e:
        print(f"Error in /auth/register: {e}")
        return jsonify(message="An unexpected error occurred during registration."), 500

# ... (rest of the file remains the same until the new routes)

@app.route('/events/<int:event_id>', methods=['DELETE'])
def api_delete_event(event_id):
    if event_manager.delete_event(event_id):
        return jsonify(message="Event deleted successfully"), 200
    return jsonify(message="Event not found or delete failed"), 404


# --- Institution and Consent API Endpoints ---

@app.route('/institutions', methods=['POST'])
def api_create_institution():
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify(message="Missing institution name"), 400
    api_key = os.urandom(16).hex()
    new_inst = institution.Institution(name=data['name'], type=data.get('type'), api_key=api_key)
    db = SessionLocal()
    try:
        db.add(new_inst)
        db.commit()
        db.refresh(new_inst)
        return jsonify({"id": new_inst.id, "api_key": new_inst.api_key}), 201
    finally:
        db.close()

def _verify_institution_api_key(inst_id, provided_key):
    db = SessionLocal()
    inst = db.query(institution.Institution).filter_by(id=inst_id).first()
    db.close()
    if not inst or inst.api_key != provided_key:
        return None
    return inst

@app.route('/institutions/<int:institution_id>/events', methods=['POST'])
def api_institution_push_event(institution_id):
    key = request.headers.get('X-API-Key')
    inst = _verify_institution_api_key(institution_id, key)
    if not inst:
        return jsonify(message="Unauthorized"), 401

    data = request.get_json()
    if not data or not all(k in data for k in ("title", "start_time", "end_time")):
        return jsonify(message="Missing title, start_time, or end_time"), 400

    child_id = data.get('child_id')
    if child_id:
        db = SessionLocal()
        consent_record = db.query(consent.Consent).filter_by(child_id=child_id, institution_id=institution_id, approved=True).first()
        db.close()
        if not consent_record:
            return jsonify(message="No consent for child"), 403

    new_event = event_manager.create_event(
        title=data['title'],
        description=data.get('description'),
        start_time_str=data['start_time'],
        end_time_str=data['end_time'],
        linked_child_id=child_id,
        institution_id=institution_id
    )
    if new_event:
        return jsonify(new_event.to_dict()), 201
    return jsonify(message="Failed to create event"), 400

@app.route('/institutions/<int:institution_id>/treatment-plans', methods=['POST'])
def api_institution_push_treatment(institution_id):
    key = request.headers.get('X-API-Key')
    inst = _verify_institution_api_key(institution_id, key)
    if not inst:
        return jsonify(message="Unauthorized"), 401

    data = request.get_json()
    if not data or 'child_id' not in data or 'description' not in data:
        return jsonify(message="Missing child_id or description"), 400
    child_id = data['child_id']
    db = SessionLocal()
    consent_record = db.query(consent.Consent).filter_by(child_id=child_id, institution_id=institution_id, approved=True).first()
    if not consent_record:
        db.close()
        return jsonify(message="No consent for child"), 403

    plan = treatment_plan.TreatmentPlan(
        child_id=child_id,
        institution_id=institution_id,
        description=data['description'],
        start_date=data.get('start_date'),
        end_date=data.get('end_date')
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    db.close()
    return jsonify(plan.to_dict()), 201

@app.route('/children/<int:child_id>/institutions/<int:institution_id>/consent', methods=['POST'])
def api_grant_consent(child_id, institution_id):
    db = SessionLocal()
    record = db.query(consent.Consent).filter_by(child_id=child_id, institution_id=institution_id).first()
    if record:
        record.approved = True
    else:
        record = consent.Consent(child_id=child_id, institution_id=institution_id, approved=True)
        db.add(record)
    db.commit()
    db.refresh(record)
    db.close()
    return jsonify(record.to_dict()), 201

@app.route('/children/<int:child_id>/institutions/<int:institution_id>/consent', methods=['DELETE'])
def api_revoke_consent(child_id, institution_id):
    db = SessionLocal()
    record = db.query(consent.Consent).filter_by(child_id=child_id, institution_id=institution_id).first()
    if record:
        record.approved = False
        db.commit()
        db.refresh(record)
        db.close()
        return jsonify(message="Consent revoked"), 200
    db.close()
    return jsonify(message="Consent not found"), 404

# ... (rest of the file from main branch continues here)
