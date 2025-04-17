# Modify app.py for better logging and error handling

import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, abort
# Removed CSRF imports
from src.user_management import UserManagement, VALID_ROLES
from src.photo_utils import generate_default_person_photo
from src.family_tree import FamilyTree
from src.relationship import VALID_RELATIONSHIP_TYPES as VALID_REL_TYPES
from src.db_utils import load_data, save_data
from src.audit_log import log_audit
import json
import logging
from logging.handlers import RotatingFileHandler # For file logging
from datetime import datetime

# --- Configuration ---
SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'a_very_strong_dev_secret_key_39$@5_v2')
if SECRET_KEY == 'a_very_strong_dev_secret_key_39$@5_v2':
    print("WARNING: Using default Flask secret key. Set FLASK_SECRET_KEY environment variable for production.")
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

# --- Configure Logging ---
os.makedirs(LOG_DIR, exist_ok=True) # Ensure log directory exists
log_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
# File Handler (Rotates logs)
file_handler = RotatingFileHandler(APP_LOG_FILE, maxBytes=1024*1024*5, backupCount=5) # 5MB per file, 5 backups
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO) # Log INFO level and above to file
# Console Handler (for development/debugging)
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.DEBUG if app.debug else logging.INFO) # More verbose if debug=True
# Remove default Flask handler and add ours
app.logger.removeHandler(app.logger.handlers[0]) if app.logger.handlers else None
app.logger.addHandler(file_handler)
app.logger.addHandler(console_handler)
app.logger.setLevel(logging.INFO) # Set overall level for the app logger
# Also configure root logger if other modules use logging.getLogger() without specific names
# logging.getLogger().addHandler(console_handler)
# logging.getLogger().addHandler(file_handler)
# logging.getLogger().setLevel(logging.INFO)
app.logger.info("Flask application starting up...")


# Add datetime to Jinja context
@app.context_processor
def inject_now():
    return {'now': datetime.utcnow}

# --- Initialize Core Components ---
os.makedirs(DATA_DIR, exist_ok=True)
user_manager = UserManagement(USERS_FILE, AUDIT_LOG_FILE)
family_tree = FamilyTree(FAMILY_TREE_FILE, AUDIT_LOG_FILE)
try:
    family_tree.load_tree(loaded_by="system_startup")
    app.logger.info("Family tree loaded successfully.")
except Exception as e:
    app.logger.exception("Failed to load family tree on startup!") # Log exception with stack trace
    family_tree = FamilyTree(FAMILY_TREE_FILE, AUDIT_LOG_FILE) # Start fresh


# --- Decorators (Keep existing login_required, admin_required) ---
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

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            log_audit(AUDIT_LOG_FILE, 'anonymous', 'access_denied', f'admin required (not logged in) for {request.endpoint}')
            app.logger.warning(f"Admin required attempt (not logged in) for endpoint '{request.endpoint}' from IP {request.remote_addr}")
            return redirect(url_for('login', next=request.url))
        if session.get('user_role') != 'admin':
            flash('You do not have permission to access this page.', 'danger')
            log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'access_denied', f'admin required (role: {session.get("user_role")}) for {request.endpoint}')
            app.logger.warning(f"Admin required attempt (role: {session.get('user_role')}) for endpoint '{request.endpoint}' by user '{session.get('username')}'")
            # return redirect(url_for('index')) # Redirecting to index might be confusing
            abort(403) # Forbidden - better practice, requires a 403 handler
        return f(*args, **kwargs)
    return decorated_function

# --- Custom Error Handlers ---
@app.errorhandler(404)
def not_found_error(error):
    app.logger.warning(f"404 Not Found error: {request.path} (Referrer: {request.referrer})")
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    # Log the exception with stack trace
    app.logger.exception("500 Internal Server Error")
    # Log minimal info to audit log if needed, but app log has details
    # log_audit(AUDIT_LOG_FILE, session.get('username', 'anonymous'), 'internal_server_error', f'Route: {request.endpoint}')
    return render_template('errors/500.html'), 500

@app.errorhandler(403)
def forbidden_error(error):
    app.logger.warning(f"403 Forbidden error accessing {request.path} by user '{session.get('username', 'anonymous')}'")
    return render_template('errors/403.html'), 403

@app.errorhandler(401)
def unauthorized_error(error):
    app.logger.warning(f"401 Unauthorized error accessing {request.path}")
    flash("Authentication required.", "warning")
    return redirect(url_for('login', next=request.url))

# --- Main Routes ---
@app.route('/')
def index():
    people = []; relationships = []
    is_admin = session.get('user_role') == 'admin'
    if 'user_id' in session:
        try:
            people = family_tree.get_people_summary()
            relationships = family_tree.get_relationships_summary()
        except Exception as e:
            app.logger.exception("Error getting tree summary data for index page") # Log full exception
            flash("Error loading family tree data.", "danger")
            log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'index_load_error', f'Error: {e}')
    # Pass form data dictionary for potential re-rendering with errors
    return render_template('index.html',
                           people=people,
                           relationships=relationships,
                           is_admin=is_admin,
                           add_person_form={}, # Empty dict initially
                           add_rel_form={})     # Empty dict initially

# --- Auth Routes ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session: flash("You are already logged in.", "info"); return redirect(url_for('index'))

    form_data = request.form.to_dict() if request.method == 'POST' else {}
    errors = {}

    if request.method == 'POST':
        username = form_data.get('username','').strip()
        password = form_data.get('password') # Don't strip password

        # --- Validation ---
        if not username: errors['username'] = 'Username is required.'
        if not password: errors['password'] = 'Password is required.'
        # Check if username exists (moved from user_manager for better feedback)
        if username and user_manager.find_user_by_username(username):
             errors['username'] = f"Username '{username}' is already taken."
             log_audit(AUDIT_LOG_FILE, username, 'register_attempt', 'failure - username exists')

        if not errors:
            # Attempt registration
            user = user_manager.register_user(username, password) # Default role is 'basic'
            if user:
                flash('Registration successful! Please log in.', 'success')
                log_audit(AUDIT_LOG_FILE, username, 'register', f'success - role: {user.role}')
                return redirect(url_for('login'))
            else:
                # Generic error if register_user failed for other reasons (e.g., hash error)
                app.logger.error(f"User registration failed unexpectedly for username: {username}")
                flash('Registration failed due to an unexpected error. Please try again later.', 'danger')
                log_audit(AUDIT_LOG_FILE, username, 'register', 'failure - unexpected error in user_manager')
                # Re-render form with errors
                return render_template('index.html', show_register=True, reg_form=form_data, reg_errors=errors)
        else:
             # Re-render form with validation errors
             flash('Please correct the errors below.', 'warning')
             return render_template('index.html', show_register=True, reg_form=form_data, reg_errors=errors)

    # GET request
    return render_template('index.html', show_register=True, reg_form={}, reg_errors={})

@app.route('/api/login', methods=['POST'])
def api_login():
    """
    RESTful API endpoint for user login.
    Expects a JSON payload with 'username' and 'password'.
    Returns a JSON response with username on successful login, 
    or an error message on failure.
    """
    try:
        data = request.get_json()
        if not data or 'username' not in data or 'password' not in data:
            app.logger.warning("API Login: Invalid JSON payload received.")
            return jsonify({"error": "Invalid JSON payload. 'username' and 'password' are required."}), 400

        username = data.get('username','').strip()
        password = data.get('password')

        user = user_manager.login_user(username, password)
        if user:
            session['user_id'] = user.user_id; session['username'] = user.username; session['user_role'] = user.role
            log_audit(AUDIT_LOG_FILE, username, 'api_login', 'success')
            app.logger.info(f"API Login: User '{username}' logged in successfully.")
            return jsonify({"message": "Login successful!", "username": user.username}), 200
        else:
            log_audit(AUDIT_LOG_FILE, username, 'api_login', 'failure - invalid credentials or user not found')
            app.logger.warning(f"API Login: Failed login attempt for username: {username}")
            return jsonify({"error": "Invalid username or password."}), 401

    except Exception as e:
        app.logger.exception("API Login: An unexpected error occurred.")
        log_audit(AUDIT_LOG_FILE, "unknown", 'api_login', f'error: {e}')
        return jsonify({"error": "An unexpected error occurred."}), 500


    """
    RESTful API endpoint for user registration.
    Expects a JSON payload with 'username' and 'password'.
    Returns a JSON response.
    """
    try:
        data = request.get_json() 
        if not data or 'username' not in data or 'password' not in data: 
            app.logger.warning("API Registration: Invalid JSON payload received.") 
            return jsonify({"error": "Invalid JSON payload. 'username' and 'password' are required."}), 400 
 
        username = data.get('username').strip() 
        password = data.get('password') 
 
        if not username: 
            app.logger.warning("API Registration: Username is required.") 
            return jsonify({"error": "Username is required."}), 400 
        if not password: 
            app.logger.warning("API Registration: Password is required.") 
            return jsonify({"error": "Password is required."}), 400 
 
        if user_manager.find_user_by_username(username): 
            app.logger.warning(f"API Registration: Username '{username}' already exists.") 
            log_audit(AUDIT_LOG_FILE, username, 'api_register_attempt', 'failure - username exists') 
            return jsonify({"error": f"Username '{username}' is already taken."}), 409  # 409 Conflict 
 
        user = user_manager.register_user(username, password) 
        if user: 
            log_audit(AUDIT_LOG_FILE, username, 'api_register', f'success - role: {user.role}') 
            app.logger.info(f"API Registration: User '{username}' registered successfully.") 
            return jsonify({"message": "Registration successful!", "username": user.username}), 201  # 201 Created
        else:
            app.logger.error(f"API Registration: User registration failed unexpectedly for username: {username}")
            log_audit(AUDIT_LOG_FILE, username, 'api_register', 'failure - unexpected error in user_manager')
            return jsonify({"error": "Registration failed due to an unexpected error. Please try again later."}), 500

    

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session: flash("You are already logged in.", "info"); return redirect(url_for('index'))

    next_url = request.args.get('next')
    form_data = request.form.to_dict() if request.method == 'POST' else {}
    errors = {}

    if request.method == 'POST':
        username = form_data.get('username','').strip()
        password = form_data.get('password') # Don't strip password

        if not username: errors['username'] = 'Username is required.'
        if not password: errors['password'] = 'Password is required.'

        if not errors:
            user = user_manager.login_user(username, password)
            if user:
                session['user_id'] = user.user_id; session['username'] = user.username; session['user_role'] = user.role
                flash(f'Welcome back, {user.username}!', 'success'); log_audit(AUDIT_LOG_FILE, username, 'login', 'success')
                app.logger.info(f"User '{username}' logged in successfully.")
                # Redirect
                dest_url = next_url or url_for('index')
                app.logger.info(f"Redirecting logged in user '{username}' to: {dest_url}")
                return redirect(dest_url)
            else:
                # Login failed (user not found or wrong password)
                errors['general'] = 'Invalid username or password.' # General error message
                flash('Invalid username or password.', 'danger') # Flash for visibility
                log_audit(AUDIT_LOG_FILE, username, 'login', 'failure - invalid credentials or user not found')
                app.logger.warning(f"Failed login attempt for username: {username}")
                return render_template('index.html', show_login=True, login_form=form_data, login_errors=errors, next=next_url)
        else:
             # Validation errors (empty fields)
             flash('Please enter both username and password.', 'warning')
             return render_template('index.html', show_login=True, login_form=form_data, login_errors=errors, next=next_url)

    # GET request
    return render_template('index.html', show_login=True, login_form={}, login_errors={}, next=next_url)

# Logout route (Keep existing)
@app.route('/api/people', methods=['POST'])
def api_add_person():
    """
    RESTful API endpoint for adding a new person to the family tree.
    Expects a JSON payload with person details.
    Returns a JSON response with the new person's ID if successful,
    or an error message on failure.
    """
    try:
        data = request.get_json()
        if not data or 'first_name' not in data:
            app.logger.warning("API Add Person: Invalid JSON payload received.")
            return jsonify({"error": "Invalid JSON payload. 'first_name' is required."}), 400

        person = family_tree.add_person(
                first_name=data.get('first_name'),
                last_name=data.get('last_name'),
                nickname=data.get('nickname'),
                dob=data.get('dob'),
                dod=data.get('dod'),
                gender=data.get('gender'),
                pob=data.get('pob'),
                pod=data.get('pod'))
        return jsonify({"person_id": person.person_id}), 201

    except Exception as e:
        app.logger.exception(f"API Add Person: An unexpected error occurred.")
        return jsonify({"error": "An unexpected error occurred."}), 500


@app.route('/api/people/<person_id>', methods=['PUT'])
def api_edit_person(person_id):
    """
    RESTful API endpoint for updating a person's details.
    Expects a JSON payload with the updated person details.
    Returns a JSON response with the person's ID if successful,
    or an error message if the person doesn't exist or an error occurred.
    """
    try:
        data = request.get_json()
        person = family_tree.find_person(person_id=person_id)
        if not person:
            app.logger.warning(f"API Edit Person: Person with ID {person_id} not found.")
            return jsonify({"error": f"Person with ID {person_id} not found."}), 404

        updated_data = {
                'first_name': data.get('first_name'),
                'last_name': data.get('last_name'),
                'nickname': data.get('nickname'),
                'birth_date': data.get('dob'),
                'death_date': data.get('dod'),
                'gender': data.get('gender'),
                'place_of_birth': data.get('pob'),
                'place_of_death': data.get('pod')
            }
        
        success = family_tree.edit_person(person_id, updated_data, edited_by='api_call')
        if success:
            return jsonify({"person_id": person_id}), 200
        else:
            app.logger.warning(f"API Edit Person: No changes made or an error occurred for ID {person_id}.")
            return jsonify({"error": "No changes made or an error occurred."}), 500
    
    except Exception as e:
        app.logger.exception(f"API Edit Person: An unexpected error occurred for ID {person_id}.")
        return jsonify({"error": "An unexpected error occurred."}), 500

@app.route('/api/people/<person_id>', methods=['DELETE'])
def api_delete_person(person_id):
    """
    RESTful API endpoint for deleting a person from the family tree.
    Deletes the person based on the provided person_id.
    Returns a JSON response with the deleted person's ID if successful,
    or an error message if the person doesn't exist or an error occurred.
    """
    try:
        person = family_tree.find_person(person_id=person_id)
        if not person:
            app.logger.warning(f"API Delete Person: Person with ID {person_id} not found.")
            return jsonify({"error": f"Person with ID {person_id} not found."}), 404
        
        success = family_tree.delete_person(person_id, deleted_by='api_call')
        if success:
            return jsonify({"person_id": person_id}), 200
        else:
            return jsonify({"error": "An error occurred while deleting the person."}), 500
    except Exception as e:
        app.logger.exception(f"API Delete Person: An unexpected error occurred for ID {person_id}.")
        return jsonify({"error": "An unexpected error occurred."}), 500

@app.route('/api/relationships', methods=['POST'])
def api_add_relationship():
    """
    RESTful API endpoint for adding a new relationship to the family tree.
    Expects a JSON payload with the IDs of the two people and the relationship type.
    Returns a JSON response with the relationship details if successful,
    or an error message if the relationship couldn't be added.
    """
    try:
        data = request.get_json()
        if not data or 'person1_id' not in data or 'person2_id' not in data or 'relationship_type' not in data:
            app.logger.warning("API Add Relationship: Invalid JSON payload received.")
            return jsonify({"error": "Invalid JSON payload. 'person1_id', 'person2_id', and 'relationship_type' are required."}), 400

        person1_id = data.get('person1_id')
        person2_id = data.get('person2_id')
        rel_type = data.get('relationship_type')

        if person1_id == person2_id:
            app.logger.warning(f"API Add Relationship: Cannot create relationship between the same person ({person1_id}).")
            return jsonify({"error": "Cannot create a relationship between the same person."}), 400
        
        if family_tree.find_relationship(person1_id, person2_id, rel_type):
            app.logger.warning(f"API Add Relationship: Relationship of type '{rel_type}' already exists between {person1_id} and {person2_id}.")
            return jsonify({"error": f"A '{rel_type}' relationship already exists between these two people."}), 409

        relationship = family_tree.add_relationship(
            person1_id=person1_id,
            person2_id=person2_id,
            relationship_type=rel_type,
            added_by="api_call"
        )
        return jsonify(relationship.to_dict()), 201

    except Exception as e:
        app.logger.exception(f"API Add Relationship: An unexpected error occurred.")
        return jsonify({"error": "An unexpected error occurred."}), 500

@app.route('/api/relationships/<relationship_id>', methods=['PUT'])
def api_edit_relationship(relationship_id):
    """
    RESTful API endpoint for updating a relationship in the family tree.
    Expects a JSON payload with the IDs of the two people and the relationship type to update.
    Returns a JSON response with the updated relationship details if successful,
    or an error message if the relationship couldn't be updated.
    """
    try:
        data = request.get_json()
        if not data or 'person1_id' not in data or 'person2_id' not in data or 'relationship_type' not in data:
            app.logger.warning("API Edit Relationship: Invalid JSON payload received.")
            return jsonify({"error": "Invalid JSON payload. 'person1_id', 'person2_id', and 'relationship_type' are required."}), 400

        person1_id = data.get('person1_id')
        person2_id = data.get('person2_id')
        rel_type = data.get('relationship_type')

        relationship = family_tree.find_relationship_by_id(relationship_id)
        if not relationship:
            app.logger.warning(f"API Edit Relationship: Relationship with ID {relationship_id} not found.")
            return jsonify({"error": f"Relationship with ID {relationship_id} not found."}), 404
        
        updated_data = {
            'rel_type': rel_type
        }
        success = family_tree.edit_relationship(relationship_id, updated_data, edited_by="api_call")
        if success:
            return jsonify(family_tree.find_relationship_by_id(relationship_id).to_dict()), 200
        else:
            app.logger.warning(f"API Edit Relationship: No changes made or an error occurred for ID {relationship_id}.")
            return jsonify({"error": "No changes made or an error occurred."}), 500

    except Exception as e:
        app.logger.exception(f"API Edit Relationship: An unexpected error occurred for ID {relationship_id}.")
        return jsonify({"error": "An unexpected error occurred."}), 500

@app.route('/api/relationships/<relationship_id>', methods=['DELETE'])
def api_delete_relationship(relationship_id):
    """
    RESTful API endpoint for deleting a relationship from the family tree.
    Deletes the relationship based on the provided relationship_id.
    Returns a JSON response with the deleted relationship's ID if successful,
    or an error message if the relationship doesn't exist or an error occurred.
    """
    try:
        relationship = family_tree.find_relationship_by_id(relationship_id)
        if not relationship:
            app.logger.warning(f"API Delete Relationship: Relationship with ID {relationship_id} not found.")
            return jsonify({"error": f"Relationship with ID {relationship_id} not found."}), 404

        success = family_tree.delete_relationship(relationship_id, deleted_by='api_call')
        if success:
            return jsonify({"relationship_id": relationship_id}), 200
        else:
            return jsonify({"error": "An error occurred while deleting the relationship."}), 500
    except Exception as e:
        app.logger.exception(f"API Delete Relationship: An unexpected error occurred for ID {relationship_id}.")
        return jsonify({"error": "An unexpected error occurred."}), 500




@app.route('/logout')
@login_required
def logout():
    username = session.get('username', 'unknown'); role = session.get('user_role', 'unknown')
    session.clear() # Clear the whole session
    flash('You have been logged out.', 'info'); log_audit(AUDIT_LOG_FILE, username, 'logout', f'success - role: {role}')
    app.logger.info(f"User '{username}' logged out.")
    return redirect(url_for('index'))


# --- Family Tree Modification Routes ---
@app.route('/add_person', methods=['POST'])
@login_required
def add_person():
    form_data = request.form.to_dict()
    errors = {}
    logged_in_username = session.get('username', 'unknown_user')

    # --- Validation ---
    first_name = form_data.get('first_name','').strip()
    last_name = form_data.get('last_name','').strip() # Optional
    dob = form_data.get('dob')
    dod = form_data.get('dod')

    if not first_name: errors['first_name'] = 'First name is required.'
    # Add date validation if needed (e.g., format, DOD >= DOB)
    if dob and not family_tree._is_valid_date(dob): errors['dob'] = 'Invalid date format (YYYY-MM-DD).'
    if dod and not family_tree._is_valid_date(dod): errors['dod'] = 'Invalid date format (YYYY-MM-DD).'
    if dob and dod and not errors.get('dob') and not errors.get('dod'):
         try:
             if datetime.strptime(dod, '%Y-%m-%d').date() < datetime.strptime(dob, '%Y-%m-%d').date():
                 errors['dod'] = 'Date of Death cannot be before Date of Birth.'
         except ValueError: pass # Ignore if dates are invalid, already caught above

    if not errors:
        try:
            person = family_tree.add_person(
                first_name=first_name,
                last_name=last_name,
                nickname=form_data.get('nickname','').strip(),
                dob=dob or None, # Pass None if empty
                dod=dod or None, # Pass None if empty
                gender=form_data.get('gender') or None,
                pob=form_data.get('pob','').strip() or None,
                pod=form_data.get('pod','').strip() or None,
                added_by=logged_in_username
            )
            if person:
                flash(f'Person "{person.get_display_name()}" added successfully!', 'success')
                return redirect(url_for('index')) # Success -> Redirect
            else:
                # Add_person failed for other reasons (logged internally)
                flash(f'Could not add person due to an unexpected error.', 'danger')
                # Re-render index, passing back form data and errors
                return render_template('index.html', people=family_tree.get_people_summary(), relationships=family_tree.get_relationships_summary(), is_admin=session.get('user_role') == 'admin', add_person_form=form_data, add_person_errors=errors, add_rel_form={}, add_rel_errors={})
        except Exception as e:
            app.logger.exception("Error adding person") # Log full exception
            log_audit(AUDIT_LOG_FILE, logged_in_username, 'add_person', f'error: {e}')
            flash('An unexpected error occurred while adding the person.', 'danger')
            # Re-render index, passing back form data and errors
            return render_template('index.html', people=family_tree.get_people_summary(), relationships=family_tree.get_relationships_summary(), is_admin=session.get('user_role') == 'admin', add_person_form=form_data, add_person_errors=errors, add_rel_form={}, add_rel_errors={})
    else:
        # Validation errors occurred
        flash('Please correct the errors in the Add Person form.', 'warning')
        # Re-render index, passing back form data and errors
        return render_template('index.html', people=family_tree.get_people_summary(), relationships=family_tree.get_relationships_summary(), is_admin=session.get('user_role') == 'admin', add_person_form=form_data, add_person_errors=errors, add_rel_form={}, add_rel_errors={})


@app.route('/edit_person/<person_id>', methods=['GET', 'POST'])
@login_required
def edit_person(person_id):
    person = family_tree.find_person(person_id=person_id)
    if not person:
        app.logger.warning(f"Edit attempt failed: Person ID {person_id} not found.")
        flash(f'Person with ID {person_id} not found.', 'danger')
        log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'edit_person_attempt', f'failure - person not found: {person_id}')
        return redirect(url_for('index'))

    form_data = request.form.to_dict() if request.method == 'POST' else person.to_dict() # Pre-fill with person data on GET
    errors = {}

    if request.method == 'POST':
        logged_in_username = session.get('username', 'unknown_user')
        # --- Validation ---
        first_name = form_data.get('first_name','').strip()
        last_name = form_data.get('last_name','').strip()
        dob = form_data.get('birth_date') # Name matches Person.to_dict() keys now
        dod = form_data.get('death_date')

        if not first_name: errors['first_name'] = 'First name is required.'
        if dob and not family_tree._is_valid_date(dob): errors['birth_date'] = 'Invalid date format (YYYY-MM-DD).'
        if dod and not family_tree._is_valid_date(dod): errors['death_date'] = 'Invalid date format (YYYY-MM-DD).'
        if dob and dod and not errors.get('birth_date') and not errors.get('death_date'):
             try:
                 if datetime.strptime(dod, '%Y-%m-%d').date() < datetime.strptime(dob, '%Y-%m-%d').date():
                     errors['death_date'] = 'Date of Death cannot be before Date of Birth.'
             except ValueError: pass

        if not errors:
            try:
                # Prepare data for update (use keys matching Person attributes)
                updated_data = {
                    'first_name': first_name,
                    'last_name': last_name,
                    'nickname': form_data.get('nickname','').strip() or None,
                    'birth_date': dob or None,
                    'death_date': dod or None,
                    'gender': form_data.get('gender') or None,
                    'place_of_birth': form_data.get('place_of_birth','').strip() or None,
                    'place_of_death': form_data.get('place_of_death','').strip() or None
                }

                success = family_tree.edit_person(person_id, updated_data, edited_by=logged_in_username)
                if success:
                    flash(f'Person "{person.get_display_name()}" updated successfully!', 'success')
                    return redirect(url_for('index'))
                else:
                    # Edit returned False (e.g., no changes made, or internal validation failed)
                    flash(f'No changes were made, or an error occurred while updating person "{person.get_display_name()}".', 'warning')
                    # Re-render edit form with current data and potential errors
                    return render_template('edit_person.html', person=person, form_data=form_data, errors=errors)
            except Exception as e:
                app.logger.exception(f"Error editing person {person_id}")
                log_audit(AUDIT_LOG_FILE, logged_in_username, 'edit_person', f'error for id {person_id}: {e}')
                flash('An unexpected error occurred while editing the person.', 'danger')
                # Re-render edit form with current data and potential errors
                return render_template('edit_person.html', person=person, form_data=form_data, errors=errors)
        else:
            # Validation errors occurred
            flash('Please correct the errors below.', 'warning')
            # Re-render edit form with submitted data and errors
            # Need to pass the original person object too for context
            return render_template('edit_person.html', person=person, form_data=form_data, errors=errors)

    # GET Request - Pass person data (as form_data) and empty errors
    return render_template('edit_person.html', person=person, form_data=form_data, errors={})


# Delete Person route (Keep existing - simple redirect)
@app.route('/delete_person/<person_id>', methods=['POST'])
@login_required
def delete_person(person_id):
    person = family_tree.find_person(person_id=person_id)
    if not person: flash(f'Person with ID {person_id} not found.', 'danger'); log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'delete_person_attempt', f'failure - person not found: {person_id}'); return redirect(url_for('index'))
    try:
        person_display_name = person.get_display_name(); logged_in_username = session.get('username', 'unknown_user')
        success = family_tree.delete_person(person_id, deleted_by=logged_in_username)
        if success: flash(f'Person "{person_display_name}" and related relationships deleted successfully!', 'success')
        else: flash(f'Could not delete person "{person_display_name}". An error occurred.', 'danger')
    except Exception as e: app.logger.exception(f"Error deleting person {person_id}"); log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'delete_person', f'error for id {person_id}: {e}'); flash('An unexpected error occurred while deleting the person.', 'danger')
    return redirect(url_for('index'))


@app.route('/add_relationship', methods=['POST'])
@login_required
def add_relationship():
    form_data = request.form.to_dict()
    errors = {}
    logged_in_username = session.get('username', 'unknown_user')

    # --- Validation ---
    person1_id = form_data.get('person1_id')
    person2_id = form_data.get('person2_id')
    rel_type = form_data.get('relationship_type')

    if not person1_id: errors['person1_id'] = 'Person 1 must be selected.'
    if not person2_id: errors['person2_id'] = 'Person 2 must be selected.'
    if not rel_type: errors['relationship_type'] = 'Relationship type must be selected.'
    if person1_id and person1_id == person2_id: errors['person2_id'] = 'Cannot add relationship to the same person.'
    # Check if relationship already exists (moved from family_tree for better feedback)
    if person1_id and person2_id and rel_type and not errors:
        if family_tree.find_relationship(person1_id, person2_id, rel_type):
             errors['general'] = f"A '{rel_type}' relationship already exists between these two people."

    if not errors:
        try:
            relationship = family_tree.add_relationship(
                person1_id=person1_id,
                person2_id=person2_id,
                relationship_type=rel_type,
                added_by=logged_in_username
            )
            if relationship:
                p1 = family_tree.find_person(person_id=person1_id); p2 = family_tree.find_person(person_id=person2_id)
                p1_name = p1.get_display_name() if p1 else f"ID {person1_id[:8]}"; p2_name = p2.get_display_name() if p2 else f"ID {person2_id[:8]}"
                flash(f'Relationship ({rel_type}) added between "{p1_name}" and "{p2_name}"!', 'success')
                return redirect(url_for('index'))
            else:
                # Add_relationship failed for other reasons (logged internally)
                flash('Could not add relationship due to an unexpected error.', 'danger')
                # Re-render index with form data/errors
                return render_template('index.html', people=family_tree.get_people_summary(), relationships=family_tree.get_relationships_summary(), is_admin=session.get('user_role') == 'admin', add_person_form={}, add_person_errors={}, add_rel_form=form_data, add_rel_errors=errors)
        except Exception as e:
            app.logger.exception("Error adding relationship")
            log_audit(AUDIT_LOG_FILE, logged_in_username, 'add_relationship', f'error: {e}')
            flash('An unexpected error occurred while adding the relationship.', 'danger')
            # Re-render index with form data/errors
            return render_template('index.html', people=family_tree.get_people_summary(), relationships=family_tree.get_relationships_summary(), is_admin=session.get('user_role') == 'admin', add_person_form={}, add_person_errors={}, add_rel_form=form_data, add_rel_errors=errors)
    else:
        # Validation errors occurred
        flash('Please correct the errors in the Add Relationship form.', 'warning')
        # Re-render index with form data/errors
        return render_template('index.html', people=family_tree.get_people_summary(), relationships=family_tree.get_relationships_summary(), is_admin=session.get('user_role') == 'admin', add_person_form={}, add_person_errors={}, add_rel_form=form_data, add_rel_errors=errors)


@app.route('/edit_relationship/<relationship_id>', methods=['GET', 'POST'])
@login_required
def edit_relationship(relationship_id):
    rel = family_tree.relationships.get(relationship_id)
    if not rel: flash(f'Relationship with ID {relationship_id} not found.', 'danger'); log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'edit_rel_attempt', f'failure - relationship not found: {relationship_id}'); return redirect(url_for('index'))
    person1 = family_tree.people.get(rel.person1_id); person2 = family_tree.people.get(rel.person2_id)
    if not person1 or not person2: flash(f'Cannot edit relationship {relationship_id} as one or both persons involved are missing.', 'danger'); log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'edit_rel_attempt', f'failure - person missing for rel {relationship_id}'); return redirect(url_for('index'))

    form_data = request.form.to_dict() if request.method == 'POST' else {'relationship_type': rel.rel_type} # Pre-fill on GET
    errors = {}

    if request.method == 'POST':
        logged_in_username = session.get('username', 'unknown_user')
        new_type = form_data.get('relationship_type','').strip()

        if not new_type: errors['relationship_type'] = 'Relationship type cannot be empty.'
        # Add other validation if editing more fields later

        if not errors:
            try:
                updated_data = {'rel_type': new_type}
                success = family_tree.edit_relationship(relationship_id, updated_data, edited_by=logged_in_username)
                if success:
                    flash(f'Relationship between "{person1.get_display_name()}" and "{person2.get_display_name()}" updated successfully!', 'success')
                    return redirect(url_for('index'))
                else:
                    flash(f'No changes were made or an error occurred updating relationship.', 'warning')
                    # Re-render edit form
                    return render_template('edit_relationship.html', relationship=rel, person1=person1, person2=person2, valid_types=VALID_REL_TYPES, form_data=form_data, errors=errors)
            except Exception as e:
                app.logger.exception(f"Error editing relationship {relationship_id}")
                log_audit(AUDIT_LOG_FILE, logged_in_username, 'edit_relationship', f'error for id {relationship_id}: {e}')
                flash('An unexpected error occurred while editing the relationship.', 'danger')
                 # Re-render edit form
                return render_template('edit_relationship.html', relationship=rel, person1=person1, person2=person2, valid_types=VALID_REL_TYPES, form_data=form_data, errors=errors)
        else:
            # Validation errors
            flash('Please correct the errors below.', 'warning')
            return render_template('edit_relationship.html', relationship=rel, person1=person1, person2=person2, valid_types=VALID_REL_TYPES, form_data=form_data, errors=errors)

    # GET Request
    return render_template('edit_relationship.html', relationship=rel, person1=person1, person2=person2, valid_types=VALID_REL_TYPES, form_data=form_data, errors={})


# Delete Relationship route (Keep existing - simple redirect)
@app.route('/delete_relationship/<relationship_id>', methods=['POST'])
@login_required
def delete_relationship(relationship_id):
    rel = family_tree.relationships.get(relationship_id)
    if not rel: flash(f'Relationship with ID {relationship_id} not found.', 'danger'); log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'delete_rel_attempt', f'failure - relationship not found: {relationship_id}'); return redirect(url_for('index'))
    try:
        p1 = family_tree.people.get(rel.person1_id); p2 = family_tree.people.get(rel.person2_id); p1_name = p1.get_display_name() if p1 else f"ID {rel.person1_id[:8]}"; p2_name = p2.get_display_name() if p2 else f"ID {rel.person2_id[:8]}"; rel_type = rel.rel_type; logged_in_username = session.get('username', 'unknown_user')
        success = family_tree.delete_relationship(relationship_id, deleted_by=logged_in_username)
        if success: flash(f'Relationship ({rel_type}) between "{p1_name}" and "{p2_name}" deleted successfully!', 'success')
        else: flash(f'Could not delete relationship. An error occurred.', 'danger')
    except Exception as e: app.logger.exception(f"Error deleting relationship {relationship_id}"); log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'delete_relationship', f'error for id {relationship_id}: {e}'); flash('An unexpected error occurred while deleting the relationship.', 'danger')
    return redirect(url_for('index'))


# Search Route (Keep existing)
@app.route('/search')
@login_required
def search():
    # (Keep existing implementation)
    query = request.args.get('q', '').strip(); dob_start = request.args.get('dob_start', '').strip(); dob_end = request.args.get('dob_end', '').strip(); location = request.args.get('location', '').strip()
    results = []; search_performed = bool(query or dob_start or dob_end or location)
    if search_performed:
        try: results = family_tree.search_people(query=query, dob_start=dob_start, dob_end=dob_end, location=location); log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'search_people', f'query: "{query}", dob_start: "{dob_start}", dob_end: "{dob_end}", location: "{location}", results: {len(results)}')
        except Exception as e: app.logger.exception("Error during search"); flash("An error occurred during the search.", "danger"); log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'search_people', f'error: {e}')
    return render_template('search_results.html', query=query, dob_start=dob_start, dob_end=dob_end, location=location, results=results, search_performed=search_performed)

@app.route('/api/people', methods=['GET'])
def get_all_people():
    try:
        people = [person.to_dict() for person in family_tree.get_all_people()]
        return jsonify(people)
    except Exception as e:
        app.logger.exception("Error getting all people data for API")
        return jsonify({"error": "Failed to get people data"}), 500

@app.route('/api/relationships', methods=['GET'])
def get_all_relationships():
    try:
        relationships = [rel.to_dict() for rel in family_tree.get_all_relationships()]
        return jsonify(relationships)
    except Exception as e:
        app.logger.exception("Error getting all relationships data for API")
        return jsonify({"error": "Failed to get relationships data"}), 500

@app.route('/api/people/<person_id>', methods=['GET'])
def get_person(person_id):
    try:
        person = family_tree.find_person(person_id=person_id)
        if person:
            return jsonify(person.to_dict())
        else:
            return jsonify({"error": "Person not found"}), 404
    except Exception as e:
        app.logger.exception(f"Error getting person data for API with id: {person_id}")
        return jsonify({"error": "Failed to get person data"}), 500


# API Endpoint (Keep existing)
@app.route('/api/tree_data')
@login_required
def tree_data():
    try:
        data = family_tree.get_nodes_links_data()

        # Adjust node data to match the required format
        for node in data['nodes']:
            person_id = node.get('id')
            person = family_tree.find_person(person_id=person_id)
            # Keep only required fields
            node['name'] = person.get_display_name()
            node['birth_date'] = person.birth_date
            node['birth_place'] = person.place_of_birth
            node['photoUrl'] = person.photoUrl if person.photoUrl else generate_default_person_photo(person_id)
            # Remove fields no longer needed
            node.pop('full_name', None); node.pop('gender', None); node.pop('pob', None)
        return jsonify(data)

    except Exception as e: app.logger.exception("Error generating tree data for API"); log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'get_tree_data', f'error: {e}'); return jsonify({"error": "Failed to generate tree data"}), 500

# Admin User Management Routes (Keep existing manage_users, set_user_role, delete_user_admin)
@app.route('/admin/users')
@admin_required
def manage_users():
    try: all_users = sorted(list(user_manager.users.values()), key=lambda u: u.username.lower() if u.username else ""); log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'view_admin_users', 'success'); return render_template('admin_users.html', users=all_users, valid_roles=VALID_ROLES)
    except Exception as e: app.logger.exception("Error retrieving users for admin page"); log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'view_admin_users', f'error: {e}'); flash("Error loading user list.", "danger"); return redirect(url_for('index'))

@app.route('/admin/set_role/<user_id>', methods=['POST'])
@admin_required
def set_user_role(user_id):
    new_role = request.form.get('role'); actor_username = session.get('username', 'unknown_admin')
    target_user = user_manager.find_user_by_id(user_id)
    if not target_user: flash(f"User with ID {user_id} not found.", "danger"); return redirect(url_for('manage_users'))
    if not new_role or new_role not in VALID_ROLES: flash(f"Invalid role specified: '{new_role}'.", "danger"); log_audit(AUDIT_LOG_FILE, actor_username, 'set_user_role_attempt', f"failure - invalid role '{new_role}' for user {user_id}"); return redirect(url_for('manage_users'))
    success = user_manager.set_user_role(user_id, new_role, actor_username=actor_username)
    if success: flash(f"Role for user '{target_user.username}' successfully updated to '{new_role}'.", "success")
    else: flash(f"Failed to update role for user '{target_user.username}'.", "danger")
    return redirect(url_for('manage_users'))

@app.route('/admin/delete_user/<user_id>', methods=['POST'])
@admin_required
def delete_user_admin(user_id):
    actor_username = session.get('username', 'unknown_admin'); target_user = user_manager.find_user_by_id(user_id)
    if not target_user: flash(f"User with ID {user_id} not found.", "danger"); return redirect(url_for('manage_users'))
    if user_id == session.get('user_id'): flash("Administrators cannot delete their own account.", "danger"); log_audit(AUDIT_LOG_FILE, actor_username, 'delete_user_admin', f"failure - attempted self-deletion: {user_id}"); return redirect(url_for('manage_users'))
    deleted_username = target_user.username
    success = user_manager.delete_user(user_id, actor_username=actor_username)
    if success: flash(f"User '{deleted_username}' deleted successfully.", "success")
    else: flash(f"Failed to delete user '{deleted_username}'.", "danger")
    return redirect(url_for('manage_users'))


# Password Reset Routes (Keep existing request_password_reset, reset_password_with_token)
@app.route('/request_password_reset', methods=['GET', 'POST'])
def request_password_reset():
    if 'user_id' in session: flash("You are already logged in.", "info"); return redirect(url_for('index'))
    form_data = request.form.to_dict() if request.method == 'POST' else {}
    errors = {}
    if request.method == 'POST':
        username = form_data.get('username','').strip()
        if not username: errors['username'] = 'Please enter your username.'
        if not errors:
            token = user_manager.generate_reset_token(username)
            if token:
                flash(f"Password reset requested for '{username}'. In a real app, a link would be emailed.", "info")
                app.logger.warning(f"PASSWORD RESET TOKEN (DISPLAYED FOR DEV ONLY): User={username}, Token={token}")
                log_audit(AUDIT_LOG_FILE, username, 'request_password_reset', 'success (token generated)')
                return redirect(url_for('login'))
            else:
                flash("If a user with that username exists, a password reset process has been initiated (check logs for token in this demo).", "info")
                log_audit(AUDIT_LOG_FILE, username, 'request_password_reset', 'failure or user not found')
                return redirect(url_for('login'))
        else:
            # Validation error
             flash('Please correct the errors below.', 'warning')
             return render_template('request_reset.html', form_data=form_data, errors=errors)
    # GET request
    return render_template('request_reset.html', form_data={}, errors={})


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password_with_token(token):
    if 'user_id' in session: flash("You are already logged in.", "info"); return redirect(url_for('index'))
    user = user_manager.verify_reset_token(token)
    if not user: flash("Invalid or expired password reset token.", "danger"); log_audit(AUDIT_LOG_FILE, f'token: {token[:8]}...', 'reset_password_view', 'failure - invalid/expired token'); return redirect(url_for('request_password_reset'))

    form_data = request.form.to_dict() if request.method == 'POST' else {}
    errors = {}
    if request.method == 'POST':
        new_password = form_data.get('password')
        confirm_password = form_data.get('confirm_password')
        if not new_password: errors['password'] = 'New password is required.'
        if not confirm_password: errors['confirm_password'] = 'Please confirm your new password.'
        if new_password and confirm_password and new_password != confirm_password: errors['confirm_password'] = 'Passwords do not match.'

        if not errors:
            success = user_manager.reset_password(token, new_password)
            if success: flash("Your password has been reset successfully. Please log in.", "success"); return redirect(url_for('login'))
            else: flash("Could not reset password. The token might have expired, or an error occurred.", "danger"); return redirect(url_for('request_password_reset'))
        else:
             # Validation errors
             flash('Please correct the errors below.', 'warning')
             return render_template('reset_password.html', token=token, form_data=form_data, errors=errors)

    # GET request
    log_audit(AUDIT_LOG_FILE, f'user: {user.username}', 'reset_password_view', 'success - token valid')
    return render_template('reset_password.html', token=token, form_data={}, errors={})


# --- Main Execution (Keep existing) ---
if __name__ == '__main__':
    # Ensure first user becomes admin if no admin exists
    if user_manager.users and not any(user.role == 'admin' for user in user_manager.users.values()):
         first_user_id = next(iter(user_manager.users))
         app.logger.warning(f"No admin user found. Making first user '{user_manager.users[first_user_id].username}' an admin for initial setup.")
         user_manager.set_user_role(first_user_id, 'admin', actor_username='system_startup')
    elif not user_manager.users:
         app.logger.info("No users found in user file.")

    app.logger.info(f"Starting Flask server on host 0.0.0.0, port {int(os.environ.get('PORT', 5001))}")
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5001)))