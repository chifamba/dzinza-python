# Modify app.py for better logging, error handling, API authentication, CORS, and input validation

import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, abort
from flask_cors import CORS
from src.user_management import UserManagement, VALID_ROLES, generate_reset_token
from src.family_tree import FamilyTree
from src.relationship import VALID_RELATIONSHIP_TYPES
from src.audit_log import log_audit
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime



# --- Configuration ---
SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'a_very_strong_dev_secret_key_39$@5_v2')
if SECRET_KEY == 'a_very_strong_dev_secret_key_39$@5_v2':
    logging.warning("WARNING: Using default Flask secret key. Set FLASK_SECRET_KEY environment variable for production.")
APP_ROOT = os.path.dirname(os.path.abspath(__file__))  # /backend
PROJECT_ROOT = os.path.dirname(APP_ROOT)  # /
DATA_DIR = os.path.join(APP_ROOT, 'data')  # /backend/data
LOG_DIR = os.path.join(PROJECT_ROOT, 'logs', 'backend')  # /logs/backend

USERS_FILE = os.path.join(DATA_DIR, 'users.json')
FAMILY_TREE_FILE = os.path.join(DATA_DIR, 'family_tree.json')
AUDIT_LOG_FILE = os.path.join(LOG_DIR, 'audit.log')
APP_LOG_FILE = os.path.join(LOG_DIR, 'app.log')


# --- Application Setup ---
TEMPLATE_FOLDER = os.path.join(APP_ROOT, 'src', 'templates')
app = Flask(__name__, template_folder=TEMPLATE_FOLDER)
app.secret_key = SECRET_KEY

# --- Configure CORS ---
# Allow requests from the typical Vite development server origin (port 5173)
# Add other origins if needed (e.g., production frontend URL)
CORS(app, supports_credentials=True, origins=["http://localhost:5173", "http://127.0.0.1:5173"])
app.logger.info("CORS configured for origin: http://localhost:5173")

# --- Configure Logging ---
# (Logging setup remains the same)
os.makedirs(LOG_DIR, exist_ok=True)
log_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
file_handler = RotatingFileHandler(APP_LOG_FILE, maxBytes=1024*1024*5, backupCount=5)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.DEBUG if app.debug else logging.INFO)
app.logger.removeHandler(app.logger.handlers[0]) if app.logger.handlers else None
app.logger.addHandler(file_handler)
app.logger.addHandler(console_handler)
app.logger.setLevel(logging.INFO)
app.logger.info("Flask application starting up...")

# --- Initialize Core Components ---
# (Initialization remains the same)
os.makedirs(DATA_DIR, exist_ok=True)
user_manager = UserManagement(USERS_FILE, AUDIT_LOG_FILE)
family_tree = FamilyTree(FAMILY_TREE_FILE, AUDIT_LOG_FILE)
try:
    family_tree.load_tree(loaded_by="system_startup")
    app.logger.info("Family tree loaded successfully.")
except Exception as e:
    app.logger.exception("Failed to load family tree on startup!")
    family_tree = FamilyTree(FAMILY_TREE_FILE, AUDIT_LOG_FILE)


# --- Validation Helper ---
# (Validation helper remains the same)
def validate_person_data(data, is_edit=False):
    errors = {}
    if not is_edit and (not data.get('first_name') or not str(data.get('first_name')).strip()):
        errors['first_name'] = 'First name is required and cannot be empty.'
    if 'first_name' in data and (not data.get('first_name') or not str(data.get('first_name')).strip()):
         errors['first_name'] = 'First name cannot be empty.'
    if 'last_name' in data and data.get('last_name') is None:
         data['last_name'] = ''

    dob = data.get('birth_date') 
    dod = data.get('death_date')

    if dob and not family_tree._is_valid_date(dob):
        errors['birth_date'] = 'Invalid date format (YYYY-MM-DD).'
    if dod and not family_tree._is_valid_date(dod):
        errors['death_date'] = 'Invalid date format (YYYY-MM-DD).'

    if dob and dod and 'birth_date' not in errors and 'death_date' not in errors:
        try:
            if datetime.strptime(dod, '%Y-%m-%d').date() < datetime.strptime(dob, '%Y-%m-%d').date():
                errors['death_date'] = 'Date of Death cannot be before Date of Birth.'
        except ValueError: pass

    if 'gender' in data and data.get('gender') and data['gender'] not in ['Male', 'Female', 'Other']:
         errors['gender'] = 'Invalid gender value. Use Male, Female, or Other.'

    return errors

# --- Decorators ---
# (Decorators remain the same)
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            log_audit(AUDIT_LOG_FILE, 'anonymous', 'access_denied', f'login required for {request.endpoint}')
            app.logger.warning(f"Login required attempt for endpoint '{request.endpoint}' from IP {request.remote_addr}")
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def api_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            log_audit(AUDIT_LOG_FILE, 'anonymous', 'api_access_denied', f'login required for API endpoint {request.endpoint}')
            app.logger.warning(f"API login required attempt for endpoint '{request.endpoint}' from IP {request.remote_addr}")
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if session.get('user_role') != 'admin':
            flash('You do not have permission to access this page.', 'danger')
            log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'access_denied', f'admin required (role: {session.get("user_role")}) for {request.endpoint}')
            app.logger.warning(f"Admin required attempt (role: {session.get('user_role')}) for endpoint '{request.endpoint}' by user '{session.get('username')}'")
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def api_admin_required(f):
    @wraps(f)
    @api_login_required
    def decorated_function(*args, **kwargs):
        if session.get('user_role') != 'admin':
            log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'api_access_denied', f'admin required (role: {session.get("user_role")}) for API endpoint {request.endpoint}')
            app.logger.warning(f"API admin required attempt (role: {session.get('user_role')}) for endpoint '{request.endpoint}' by user '{session.get('username')}'")
            return jsonify({"error": "Administrator privileges required"}), 403
        return f(*args, **kwargs)
    return decorated_function

# --- Custom Error Handlers ---
# (Error handlers remain the same)
@app.errorhandler(404)
def not_found_error(error):
    app.logger.warning(f"404 Not Found error: {request.path} (Referrer: {request.referrer})")
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({"error": "Not Found"}), 404
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    app.logger.exception("500 Internal Server Error")
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({"error": "Internal Server Error"}), 500
    return render_template('errors/500.html'), 500

@app.errorhandler(403)
def forbidden_error(error):
    app.logger.warning(f"403 Forbidden error accessing {request.path} by user '{session.get('username', 'anonymous')}'")
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({"error": "Forbidden"}), 403
    return render_template('errors/403.html'), 403

@app.errorhandler(401)
def unauthorized_error(error):
    app.logger.warning(f"401 Unauthorized error accessing {request.path}")
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({"error": "Unauthorized"}), 401
    flash("Authentication required.", "warning")
    return redirect(url_for('login', next=request.url))

@app.errorhandler(400)
def bad_request_error(error):
    description = error.description if hasattr(error, 'description') else "Bad Request"
    app.logger.warning(f"400 Bad Request error: {description}")
    # Ensure the response includes the details if available
    response_data = {"error": description}
    if isinstance(description, dict): # Handle cases where description might be validation errors
        response_data = {"error": "Validation failed", "details": description}
    return jsonify(response_data), 400


@app.route('/logout')
@login_required
def logout():
    username = session.get('username', 'unknown'); role = session.get('user_role', 'unknown')
    session.clear()
    flash('You have been logged out.', 'info'); log_audit(AUDIT_LOG_FILE, username, 'logout', f'success - role: {role}')
    app.logger.info(f"User '{username}' logged out.")
    return redirect(url_for('api_get_session'))


# --- API Authentication Routes ---
# (API Auth routes remain the same)
@app.route('/api/login', methods=['POST'])
def api_login():
    try:
        data = request.get_json()
        if not data or not data.get('username') or not data.get('password'):
            app.logger.warning("API Login: Missing username or password in payload.")
            return jsonify({"error": "Username and password are required."}), 400
        username = data['username'].strip()
        password = data['password']
        user = user_manager.login_user(username, password)
        if user:
            session['user_id'] = user.user_id; session['username'] = user.username; session['user_role'] = user.role
            log_audit(AUDIT_LOG_FILE, username, 'api_login', 'success')
            app.logger.info(f"API Login: User '{username}' logged in successfully.")
            return jsonify({"message": "Login successful!", "user": {"id": user.user_id, "username": user.username, "role": user.role}}), 200
        else:
            log_audit(AUDIT_LOG_FILE, username, 'api_login', 'failure - invalid credentials or user not found')
            app.logger.warning(f"API Login: Failed login attempt for username: {username}")
            return jsonify({"error": "Invalid username or password."}), 401
    except Exception as e:
        app.logger.exception("API Login: An unexpected error occurred.")
        log_audit(AUDIT_LOG_FILE, "unknown", 'api_login', f'error: {e}')
        return jsonify({"error": "An unexpected error occurred during login."}), 500

@app.route('/api/register', methods=['POST'])
def api_register():
    try:
        data = request.get_json()
        if not data or not data.get('username') or not data.get('password'):
            app.logger.warning("API Register: Missing username or password in payload.")
            return jsonify({"error": "Username and password are required."}), 400
        username = data['username'].strip()
        password = data['password']
        if not username: return jsonify({"error": "Username cannot be empty."}), 400
        if not password: return jsonify({"error": "Password cannot be empty."}), 400
        if user_manager.find_user_by_username(username):
            log_audit(AUDIT_LOG_FILE, username, 'api_register_attempt', 'failure - username exists')
            return jsonify({"error": f"Username '{username}' is already taken."}), 409
        user = user_manager.register_user(username, password)
        if user:
            log_audit(AUDIT_LOG_FILE, username, 'api_register', f'success - role: {user.role}')
            app.logger.info(f"API Registration: User '{username}' registered successfully.")
            return jsonify({"message": "Registration successful!", "user": {"id": user.user_id, "username": user.username, "role": user.role}}), 201
        else:
            app.logger.error(f"API Registration: User registration failed unexpectedly for username: {username}")
            log_audit(AUDIT_LOG_FILE, username, 'api_register', 'failure - unexpected error in user_manager')
            return jsonify({"error": "Registration failed due to an unexpected error."}), 500
    except Exception as e:
        app.logger.exception("API Register: An unexpected error occurred.")
        log_audit(AUDIT_LOG_FILE, "unknown", 'api_register', f'error: {e}')
        return jsonify({"error": "An unexpected error occurred during registration."}), 500

@app.route('/api/logout', methods=['POST'])
@api_login_required
def api_logout():
    username = session.get('username', 'unknown'); role = session.get('user_role', 'unknown')
    try:
        session.clear()
        log_audit(AUDIT_LOG_FILE, username, 'api_logout', f'success - role: {role}')
        app.logger.info(f"API Logout: User '{username}' logged out.")
        return jsonify({"message": "Logout successful"}), 200
    except Exception as e:
        app.logger.exception("API Logout: An unexpected error occurred.")
        log_audit(AUDIT_LOG_FILE, username, 'api_logout', f'error: {e}')
        return jsonify({"error": "An unexpected error occurred during logout."}), 500

@app.route('/api/session', methods=['GET'])
def api_get_session():
    if 'user_id' in session:
        return jsonify({"isAuthenticated": True, "user": {"id": session['user_id'], "username": session['username'], "role": session['user_role']}}), 200
    else:
        return jsonify({"isAuthenticated": False, "user": None}), 200


# --- API Family Tree Data Routes ---
# (API Tree routes remain the same, validation added within)
@app.route('/api/people', methods=['GET'])
@api_login_required
def get_all_people():
    try:
        people = [person.to_dict() for person in family_tree.people.values()]
        return jsonify(people)
    except Exception as e:
        app.logger.exception("Error getting all people data for API")
        return jsonify({"error": "Failed to retrieve people data"}), 500

@app.route('/api/people/<person_id>', methods=['GET'])
@api_login_required
def get_person(person_id):
    try:
        person = family_tree.find_person(person_id=person_id)
        if person:
            return jsonify(person.to_dict())
        else:
            app.logger.warning(f"API Get Person: Person ID {person_id} not found.")
            return jsonify({"error": "Person not found"}), 404
    except Exception as e:
        app.logger.exception(f"Error getting person data for API with id: {person_id}")
        return jsonify({"error": "Failed to retrieve person data"}), 500

@app.route('/api/people', methods=['POST'])
@api_login_required
def api_add_person():
    try:
        data = request.get_json()
        if not data: return jsonify({"error": "Request body cannot be empty."}), 400
        validation_errors = validate_person_data(data, is_edit=False)
        if validation_errors:
            app.logger.warning(f"API Add Person validation failed: {validation_errors}")
            return jsonify({"error": "Validation failed", "details": validation_errors}), 400
        first_name = str(data.get('first_name')).strip()
        last_name = str(data.get('last_name', '')).strip()
        nickname = str(data.get('nickname', '')).strip() or None
        dob = data.get('birth_date') or None
        dod = data.get('death_date') or None
        gender = data.get('gender') or None
        pob = str(data.get('place_of_birth', '')).strip() or None
        pod = str(data.get('place_of_death', '')).strip() or None
        person = family_tree.add_person(first_name=first_name, last_name=last_name, nickname=nickname, dob=dob, dod=dod, gender=gender, pob=pob, pod=pod, added_by=session.get('username', 'api_user'))
        if person:
            app.logger.info(f"API Add Person: Person '{person.get_display_name()}' added by '{session.get('username')}'")
            return jsonify(person.to_dict()), 201
        else:
            app.logger.error(f"API Add Person: family_tree.add_person failed unexpectedly after validation for user '{session.get('username')}'")
            return jsonify({"error": "Failed to add person after validation. Check server logs."}), 500
    except Exception as e:
        app.logger.exception("API Add Person: An unexpected error occurred.")
        return jsonify({"error": "An unexpected error occurred while adding person."}), 500

@app.route('/api/people/<person_id>', methods=['PUT'])
@api_login_required
def api_edit_person(person_id):
    try:
        data = request.get_json()
        if not data: return jsonify({"error": "Request body cannot be empty."}), 400
        person = family_tree.find_person(person_id=person_id)
        if not person: return jsonify({"error": f"Person with ID {person_id} not found."}), 404
        validation_errors = validate_person_data(data, is_edit=True)
        if validation_errors:
            app.logger.warning(f"API Edit Person validation failed for {person_id}: {validation_errors}")
            return jsonify({"error": "Validation failed", "details": validation_errors}), 400
        updated_data = {}
        for key in ['first_name', 'last_name', 'nickname', 'birth_date', 'death_date', 'gender', 'place_of_birth', 'place_of_death', 'notes']:
            if key in data:
                value = data[key]
                if key in ['nickname', 'birth_date', 'death_date', 'gender', 'notes', 'place_of_birth', 'place_of_death']: updated_data[key] = str(value).strip() if value is not None and str(value).strip() else None
                elif key == 'last_name': updated_data[key] = str(value).strip() if value is not None else ''
                elif key == 'first_name': updated_data[key] = str(value).strip()
        if not updated_data: return jsonify({"message": "No update data provided."}), 200
        success = family_tree.edit_person(person_id, updated_data, edited_by=session.get('username', 'api_user'))
        if success:
            updated_person = family_tree.find_person(person_id=person_id)
            app.logger.info(f"API Edit Person: Person '{person_id}' updated by '{session.get('username')}'")
            return jsonify(updated_person.to_dict()), 200
        else:
            app.logger.warning(f"API Edit Person: edit_person failed or made no changes for ID {person_id} by user '{session.get('username')}'")
            return jsonify({"message": "No changes detected or update failed."}), 200
    except Exception as e:
        app.logger.exception(f"API Edit Person: An unexpected error occurred for ID {person_id}.")
        return jsonify({"error": "An unexpected error occurred while editing person."}), 500

@app.route('/api/people/<person_id>', methods=['DELETE'])
@api_login_required
def api_delete_person(person_id):
    try:
        person = family_tree.find_person(person_id=person_id)
        if not person: return jsonify({"error": f"Person with ID {person_id} not found."}), 404
        success = family_tree.delete_person(person_id, deleted_by=session.get('username', 'api_user'))
        if success:
            app.logger.info(f"API Delete Person: Person '{person_id}' deleted by '{session.get('username')}'")
            return '', 204
        else:
            app.logger.error(f"API Delete Person: delete_person failed for ID {person_id} by user '{session.get('username')}'")
            return jsonify({"error": "Failed to delete person."}), 500
    except Exception as e:
        app.logger.exception(f"API Delete Person: An unexpected error occurred for ID {person_id}.")
        return jsonify({"error": "An unexpected error occurred while deleting person."}), 500

@app.route('/api/relationships', methods=['GET'])
@api_login_required
def get_all_relationships():
    try:
        relationships = [rel.to_dict() for rel in family_tree.relationships.values()]
        return jsonify(relationships)
    except Exception as e:
        app.logger.exception("Error getting all relationships data for API")
        return jsonify({"error": "Failed to retrieve relationships data"}), 500

@app.route('/api/relationships', methods=['POST'])
@api_login_required
def api_add_relationship():
    try:
        data = request.get_json()
        if not data: return jsonify({"error": "Request body cannot be empty."}), 400
        person1_id = data.get('person1_id')
        person2_id = data.get('person2_id')
        rel_type = data.get('rel_type')
        attributes = data.get('attributes', {})
        errors = {}
        if not person1_id: errors['person1_id'] = 'Person 1 ID is required.'
        if not person2_id: errors['person2_id'] = 'Person 2 ID is required.'
        if not rel_type: errors['rel_type'] = 'Relationship type is required.'
        if person1_id and person1_id == person2_id: errors['person2_id'] = 'Cannot add relationship to the same person.'
        if rel_type and rel_type not in VALID_RELATIONSHIP_TYPES: errors['rel_type'] = f"Invalid relationship type '{rel_type}'. Valid types: {', '.join(VALID_RELATIONSHIP_TYPES)}"
        person1, person2 = None, None
        if person1_id and 'person1_id' not in errors:
            person1 = family_tree.find_person(person_id=person1_id)
            if not person1: errors['person1_id'] = f"Person with ID {person1_id} not found."
        if person2_id and 'person2_id' not in errors:
            person2 = family_tree.find_person(person_id=person2_id)
            if not person2: errors['person2_id'] = f"Person with ID {person2_id} not found."
        if errors:
            app.logger.warning(f"API Add Relationship validation failed: {errors}")
            return jsonify({"error": "Validation failed", "details": errors}), 400
        relationship = family_tree.add_relationship(person1_id=person1_id, person2_id=person2_id, relationship_type=rel_type, added_by=session.get('username', 'api_user'))
        if relationship:
             app.logger.info(f"API Add Relationship: Relationship '{rel_type}' added between '{person1_id}' and '{person2_id}' by '{session.get('username')}'")
             return jsonify(relationship.to_dict()), 201
        else:
            app.logger.error(f"API Add Relationship: family_tree.add_relationship failed for user '{session.get('username')}'")
            return jsonify({"error": "Failed to add relationship. It might already exist or persons may not be valid."}), 400
    except Exception as e:
        app.logger.exception("API Add Relationship: An unexpected error occurred.")
        return jsonify({"error": "An unexpected error occurred while adding relationship."}), 500

@app.route('/api/relationships/<relationship_id>', methods=['PUT'])
@api_login_required
def api_edit_relationship(relationship_id):
    try:
        data = request.get_json()
        if not data: return jsonify({"error": "Request body cannot be empty."}), 400
        rel = family_tree.relationships.get(relationship_id)
        if not rel: return jsonify({"error": f"Relationship with ID {relationship_id} not found."}), 404
        errors = {}
        new_type = data.get('rel_type')
        if 'rel_type' in data:
            if not new_type or not str(new_type).strip(): errors['rel_type'] = 'Relationship type cannot be empty.'
            elif new_type not in VALID_RELATIONSHIP_TYPES: errors['rel_type'] = f"Invalid relationship type '{new_type}'. Valid types: {', '.join(VALID_RELATIONSHIP_TYPES)}"
        if errors:
            app.logger.warning(f"API Edit Relationship validation failed for {relationship_id}: {errors}")
            return jsonify({"error": "Validation failed", "details": errors}), 400
        updated_data = {}
        if 'rel_type' in data: updated_data['rel_type'] = str(new_type).strip()
        if not updated_data: return jsonify({"message": "No update data provided."}), 200
        success = family_tree.edit_relationship(relationship_id, updated_data, edited_by=session.get('username', 'api_user'))
        if success:
            updated_rel = family_tree.relationships.get(relationship_id)
            app.logger.info(f"API Edit Relationship: Relationship '{relationship_id}' updated by '{session.get('username')}'")
            return jsonify(updated_rel.to_dict()), 200
        else:
            app.logger.warning(f"API Edit Relationship: edit_relationship failed or made no changes for ID {relationship_id} by user '{session.get('username')}'")
            return jsonify({"message": "No changes detected or update failed."}), 200
    except Exception as e:
        app.logger.exception(f"API Edit Relationship: An unexpected error occurred for ID {relationship_id}.")
        return jsonify({"error": "An unexpected error occurred while editing relationship."}), 500

@app.route('/api/relationships/<relationship_id>', methods=['DELETE'])
@api_login_required
def api_delete_relationship(relationship_id):
    try:
        rel = family_tree.relationships.get(relationship_id)
        if not rel: return jsonify({"error": f"Relationship with ID {relationship_id} not found."}), 404
        success = family_tree.delete_relationship(relationship_id, deleted_by=session.get('username', 'api_user'))
        if success:
            app.logger.info(f"API Delete Relationship: Relationship '{relationship_id}' deleted by '{session.get('username')}'")
            return '', 204
        else:
            app.logger.error(f"API Delete Relationship: delete_relationship failed for ID {relationship_id} by user '{session.get('username')}'")
            return jsonify({"error": "Failed to delete relationship."}), 500
    except Exception as e:
        app.logger.exception(f"API Delete Relationship: An unexpected error occurred for ID {relationship_id}.")
        return jsonify({"error": "An unexpected error occurred while deleting relationship."}), 500

# --- API Tree Visualization Data Route ---
@app.route('/api/tree_data')
@api_login_required
def tree_data():
    try:
        data = family_tree.get_nodes_links_data()
        return jsonify(data)
    except Exception as e:
        app.logger.exception("Error generating tree data for API")
        log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'get_tree_data', f'error: {e}')
        return jsonify({"error": "Failed to generate tree data"}), 500
# --- Password Reset Routes (API)---
@app.route('/request_password_reset', methods=['POST'])
def request_password_reset():
    try:
        data = request.get_json()
        if not data or 'email' not in data:
            return jsonify({"error": "Email is required."}), 400
        email = data['email']
        user = user_manager.find_user_by_email(email)
        if user:
            token = generate_reset_token(user.user_id)
            user_manager.send_email(email, "Password Reset Request", f"Click the following link to reset your password: http://your-frontend-url/reset_password/{token}")
            return jsonify({"message": "Password reset email sent if the email is registered."}), 200
        else:
            return jsonify({"message": "Password reset email sent if the email is registered."}), 200
    except Exception as e:
        logging.exception(f"Error requesting password reset for email: {email}", exc_info=True)
        return jsonify({"error": "An error occurred while processing the password reset request."}), 500

@app.route('/reset_password/<token>', methods=['POST'])
def reset_password_with_token(token):
    try:
        data = request.get_json()
        if not data or 'new_password' not in data:
            app.logger.warning(f"Reset Password: Missing 'new_password' in payload for token: {token}")
            return jsonify({"error": "New password is required."}), 400
        
        new_password = data['new_password']
        if not new_password:
            app.logger.warning(f"Reset Password: New password cannot be empty for token: {token}")
            return jsonify({"error": "New password cannot be empty."}), 400

        success = user_manager.reset_password(token, new_password)
        
        if success:
            app.logger.info(f"Reset Password: Password reset successful for token: {token}")
            return jsonify({"message": "Password reset successful."}), 200
        else:
            app.logger.warning(f"Reset Password: Invalid or expired token: {token}")
            return jsonify({"error": "Invalid or expired token."}), 400

    except Exception as e:
        app.logger.exception(f"Reset Password: An unexpected error occurred for token: {token}")
        log_audit(AUDIT_LOG_FILE, "unknown", 'reset_password', f'error: {e}')
        return jsonify({"error": "An unexpected error occurred during password reset."}), 500



# --- Admin Routes (Web Interface) ---
@app.route('/admin/users')
@admin_required # Will be removed when frontend will be ready
def manage_users():
    try: all_users = sorted(list(user_manager.users.values()), key=lambda u: u.username.lower() if u.username else ""); log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'view_admin_users', 'success'); return render_template('admin_users.html', users=all_users, valid_roles=VALID_ROLES)
    except Exception as e: app.logger.exception("Error retrieving users for admin page"); log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'view_admin_users', f'error: {e}'); flash("Error loading user list.", "danger"); return redirect(url_for('index'))

# --- Password Reset Routes (Web Interface - Mostly Deprecated) ---
# (Password reset routes remain the same - mostly deprecated)
@app.route('/request_password_reset', methods=['GET', 'POST'])
def request_password_reset_deprecated(): flash("Password reset should be initiated via the API or dedicated frontend.", "info"); return redirect(url_for('api_get_session'))
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password_with_token(token): flash("Password reset confirmation should be handled via the API or dedicated frontend.", "info"); return redirect(url_for('api_get_session')) #Will be removed when frontend will be ready


# --- Start main
# --- Main Execution ---
# (Main execution remains the same)
if __name__ == '__main__':
    if user_manager.users and not any(user.role == 'admin' for user in user_manager.users.values()):
         first_user_id = next(iter(user_manager.users))
         app.logger.warning(f"No admin user found. Making first user '{user_manager.users[first_user_id].username}' an admin for initial setup.")
         user_manager.set_user_role(first_user_id, 'admin', actor_username='system_startup')
    elif not user_manager.users:
         app.logger.info("No users found in user file.")
    port = int(os.environ.get('PORT', 8090))
    app.logger.info(f"Starting Flask server on host 0.0.0.0, port {port}")
    app.run(debug=os.environ.get('FLASK_DEBUG', '1') == '1', host='0.0.0.0', port=port)
