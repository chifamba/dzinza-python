# backend/app.py
import os
import logging
from functools import wraps
from flask import Flask, request, session, jsonify, abort, current_app
from flask_cors import CORS
# Assuming user_management, family_tree etc. are correctly imported from src
from src.user_management import UserManagement
from src.family_tree import FamilyTree
from src.relationship import VALID_RELATIONSHIP_TYPES
from src.audit_log import log_audit
from logging.handlers import RotatingFileHandler
from datetime import date # Correct import for date

# --- Configuration ---
SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'a_very_strong_dev_secret_key_39$@5_v2')
if SECRET_KEY == 'a_very_strong_dev_secret_key_39$@5_v2':
    logging.warning("SECURITY WARNING: Using default Flask secret key. Set FLASK_SECRET_KEY environment variable for production.")

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(APP_ROOT)
DATA_DIR = os.path.join(APP_ROOT, 'data') # Standardize data dir
LOG_DIR = os.path.join(PROJECT_ROOT, 'logs', 'backend')

USERS_FILE = os.path.join(DATA_DIR, 'users.json')
FAMILY_TREE_FILE = os.path.join(DATA_DIR, 'family_tree.json')

AUDIT_LOG_FILE = os.path.join(LOG_DIR, 'audit.log')
APP_LOG_FILE = os.path.join(LOG_DIR, 'app.log')

# --- Application Setup ---
app = Flask(__name__)
app.secret_key = SECRET_KEY

# --- Configure CORS ---
# Adjust origins for your specific development and production frontend URLs
CORS(app, supports_credentials=True, origins=["http://localhost:5173", "http://127.0.0.1:5173"])
logging.info("CORS configured for development origins.") # Use logging module directly for setup logs

# --- Configure Logging ---
os.makedirs(LOG_DIR, exist_ok=True)
log_formatter = logging.Formatter('%(asctime)s %(levelname)-8s [%(name)s] %(message)s [in %(pathname)s:%(lineno)d]')

# File Handler (Rotating)
# Use 'app' logger for general application logs
file_handler = RotatingFileHandler(APP_LOG_FILE, maxBytes=1024*1024*5, backupCount=5, encoding='utf-8')
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)

# Console Handler (for development visibility)
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
# Set console level based on FLASK_DEBUG environment variable
console_handler.setLevel(logging.DEBUG if os.environ.get('FLASK_DEBUG') == '1' else logging.INFO)

# Get the Flask app's logger and configure it
# Using 'current_app.logger' inside functions/routes is preferred after app context is available.
# For initial setup, we configure the root logger or Flask's default logger if needed.
# Here, we'll configure Flask's app logger directly.
if app.logger.handlers: app.logger.handlers.clear() # Remove default handler if present
app.logger.addHandler(file_handler)
app.logger.addHandler(console_handler)
app.logger.setLevel(logging.DEBUG if os.environ.get('FLASK_DEBUG') == '1' else logging.INFO) # Set level for the app logger itself

app.logger.info("Flask application starting up...") # Use app logger

# --- Initialize Core Components ---
os.makedirs(DATA_DIR, exist_ok=True)
user_manager = None
family_tree = None
try:
    # Pass the app logger to components if they need logging before request context
    user_manager = UserManagement(USERS_FILE, AUDIT_LOG_FILE)
    family_tree = FamilyTree(FAMILY_TREE_FILE, AUDIT_LOG_FILE)
    app.logger.info("User manager and family tree initialized successfully.")
except Exception as e:
    app.logger.critical(f"CRITICAL ERROR: Failed to initialize core components: {e}", exc_info=True)
    # App might be unusable, endpoints using these will fail later with 503 checks

# --- Validation Helper ---
def validate_person_data(data, is_edit=False):
    """Validates data for adding or editing a person."""
    errors = {}
    # Use .get with default to avoid KeyError if field is missing
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    dob = data.get('birth_date')
    dod = data.get('death_date')
    gender = data.get('gender')

    # Required fields check
    if not is_edit and (first_name is None or not str(first_name).strip()):
        errors['first_name'] = 'First name is required and cannot be empty.'
    elif 'first_name' in data and (first_name is None or not str(first_name).strip()):
         errors['first_name'] = 'First name cannot be empty.'

    # Ensure last_name is always a string, even if empty
    if 'last_name' in data and last_name is None:
         data['last_name'] = '' # Normalize None to empty string

    # Date validation
    if dob and not FamilyTree._is_valid_date(dob):
        errors['birth_date'] = 'Invalid date format (YYYY-MM-DD).'
    if dod and not FamilyTree._is_valid_date(dod):
        errors['death_date'] = 'Invalid date format (YYYY-MM-DD).'

    # Date comparison validation (only if both dates are present and valid so far)
    if dob and dod and 'birth_date' not in errors and 'death_date' not in errors:
        try:
            # Use date.fromisoformat for robust parsing
            if date.fromisoformat(dod) < date.fromisoformat(dob):
                errors['death_date'] = 'Date of Death cannot be before Date of Birth.'
        except (ValueError, TypeError) as date_err:
             # Log the specific error during comparison phase
             app.logger.warning(f"Date comparison validation error: {date_err}", exc_info=True)
             errors['date_comparison'] = 'Invalid date format for comparison.'

    # Gender validation
    if gender and gender not in ['Male', 'Female', 'Other']:
         errors['gender'] = 'Invalid gender value. Use Male, Female, or Other.'

    return errors

# --- Decorators ---
def api_login_required(f):
    """Decorator to ensure user is logged in for API endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check session *before* checking component initialization
        if 'user_id' not in session:
            # Logged by audit log already, maybe add IP here if needed
            current_app.logger.warning(f"API Authentication Required: Endpoint '{request.endpoint}' accessed without login (IP: {request.remote_addr}).")
            # Audit log call moved to the actual failure point for consistency
            log_audit(AUDIT_LOG_FILE, 'anonymous', 'api_access_denied', f'login required for API endpoint {request.endpoint}')
            return jsonify({"error": "Authentication required"}), 401

        # Check if core components initialized properly *after* confirming login attempt
        if not user_manager or not family_tree:
             current_app.logger.error(f"API Service Unavailable: Endpoint '{request.endpoint}' accessed but core components not initialized.")
             # Log audit for service unavailability attempt? Maybe too noisy.
             return jsonify({"error": "Service temporarily unavailable. Please try again later."}), 503
        return f(*args, **kwargs)
    return decorated_function

def api_admin_required(f):
    """Decorator to ensure user has admin role for API endpoints."""
    @wraps(f)
    @api_login_required # Chain decorators: ensures login and component checks first
    def decorated_function(*args, **kwargs):
        user_role = session.get("user_role")
        username = session.get('username', 'unknown_user') # Get username for logging
        if user_role != 'admin':
            current_app.logger.warning(f"API Authorization Failed: User '{username}' (Role: {user_role}) attempted to access admin endpoint '{request.endpoint}'.")
            log_audit(AUDIT_LOG_FILE, username, 'api_access_denied', f'admin required (role: {user_role}) for API endpoint {request.endpoint}')
            return jsonify({"error": "Administrator privileges required"}), 403
        return f(*args, **kwargs)
    return decorated_function

# --- Custom Error Handlers ---
@app.errorhandler(400)
def handle_bad_request(error):
    """Handles 400 Bad Request errors, often due to parsing or validation."""
    # Extract description, default if missing
    description = getattr(error, 'description', "Invalid request format or data.")
    current_app.logger.warning(f"API Bad Request (400): {description} - Endpoint: {request.endpoint}, IP: {request.remote_addr}")
    # Structure the response based on whether description is detailed validation errors
    response_data = {"error": "Bad Request", "message": description}
    if isinstance(description, dict): # Assume validation errors
        response_data = {"error": "Validation failed", "details": description}
    return jsonify(response_data), 400

@app.errorhandler(401)
def handle_unauthorized(error):
    """Handles 401 Unauthorized errors (specific handler for clarity)."""
    description = getattr(error, 'description', "Authentication required.")
    current_app.logger.warning(f"API Unauthorized (401): {description} - Endpoint: {request.endpoint}, IP: {request.remote_addr}")
    return jsonify({"error": "Unauthorized", "message": description}), 401

@app.errorhandler(403)
def handle_forbidden(error):
    """Handles 403 Forbidden errors (specific handler for clarity)."""
    description = getattr(error, 'description', "Permission denied.")
    current_app.logger.warning(f"API Forbidden (403): {description} - Endpoint: {request.endpoint}, User: {session.get('username', 'anonymous')}, IP: {request.remote_addr}")
    return jsonify({"error": "Forbidden", "message": description}), 403

@app.errorhandler(404)
def handle_not_found(error):
    """Handles 404 Not Found errors."""
    current_app.logger.warning(f"API Not Found (404): Path '{request.path}' - IP: {request.remote_addr}, Referrer: {request.referrer}")
    return jsonify({"error": "Not Found", "message": f"The requested URL '{request.path}' was not found on this server."}), 404

@app.errorhandler(500)
def handle_internal_server_error(error):
    """Handles 500 Internal Server errors."""
    # Log the exception with traceback
    current_app.logger.exception(f"API Internal Server Error (500): Endpoint: {request.endpoint}, User: {session.get('username', 'anonymous')}, IP: {request.remote_addr}")
    # Do not expose internal error details to the client
    return jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred. Please try again later."}), 500

@app.errorhandler(503)
def handle_service_unavailable(error):
    """Handles 503 Service Unavailable errors."""
    description = getattr(error, 'description', "Service temporarily unavailable.")
    current_app.logger.error(f"API Service Unavailable (503): {description} - Endpoint: {request.endpoint}, IP: {request.remote_addr}")
    return jsonify({"error": "Service Unavailable", "message": description}), 503

# --- API Authentication Routes ---
@app.route('/api/login', methods=['POST'])
def api_login():
    """API endpoint for user login."""
    # Check component initialization *before* processing request
    if not user_manager:
        current_app.logger.error("API Login attempt failed: User manager not initialized.")
        return jsonify({"error": "Authentication service unavailable."}), 503

    try:
        data = request.get_json()
        if not data or not data.get('username') or not data.get('password'):
            current_app.logger.warning("API Login: Missing username or password in payload.")
            # Use abort(400) to trigger the error handler for consistent response format
            abort(400, description="Username and password are required.")

        username = data['username'].strip()
        password = data['password']
        current_app.logger.debug(f"API Login attempt for username: '{username}'")

        user = user_manager.login_user(username, password)

        if user:
            session['user_id'] = user.user_id
            session['username'] = user.username
            session['user_role'] = user.role
            # Session is now set, log success
            current_app.logger.info(f"API Login Successful: User '{username}' (Role: {user.role}) logged in from IP {request.remote_addr}.")
            log_audit(AUDIT_LOG_FILE, username, 'api_login', 'success')
            return jsonify({"message": "Login successful!", "user": {"id": user.user_id, "username": user.username, "role": user.role}}), 200
        else:
            # Log specific reason if possible (handled internally by user_manager logging)
            current_app.logger.warning(f"API Login Failed: Invalid credentials or user not found for username '{username}' from IP {request.remote_addr}.")
            log_audit(AUDIT_LOG_FILE, username, 'api_login', 'failure - invalid credentials or user not found')
            # Use abort(401) for consistency
            abort(401, description="Invalid username or password.")

    except Exception as e:
        # Catch unexpected errors during login process
        current_app.logger.exception(f"API Login Error: Unexpected error during login for username '{data.get('username', 'unknown') if data else 'unknown'}'.")
        log_audit(AUDIT_LOG_FILE, data.get('username', 'unknown') if data else 'unknown', 'api_login', f'unexpected error: {e}')
        # Trigger 500 handler
        abort(500)


@app.route('/api/register', methods=['POST'])
def api_register():
    """API endpoint for user registration."""
    if not user_manager:
        current_app.logger.error("API Register attempt failed: User manager not initialized.")
        return jsonify({"error": "Registration service unavailable."}), 503

    try:
        data = request.get_json()
        if not data or not data.get('username') or not data.get('password'):
            current_app.logger.warning("API Register: Missing username or password.")
            abort(400, description="Username and password are required.")

        username = data['username'].strip()
        password = data['password']

        # Basic validation
        if not username: abort(400, description="Username cannot be empty.")
        if not password: abort(400, description="Password cannot be empty.") # Consider adding password complexity rules

        current_app.logger.debug(f"API Register attempt for username: '{username}'")

        # Check if username exists
        if user_manager.find_user_by_username(username):
            current_app.logger.warning(f"API Register Failed: Username '{username}' already taken.")
            log_audit(AUDIT_LOG_FILE, username, 'api_register_attempt', 'failure - username exists')
            return jsonify({"error": f"Username '{username}' is already taken."}), 409 # Conflict

        # Attempt registration
        user = user_manager.register_user(username, password) # Default role 'basic'

        if user:
            current_app.logger.info(f"API Registration Successful: User '{username}' (Role: {user.role}) registered from IP {request.remote_addr}.")
            log_audit(AUDIT_LOG_FILE, username, 'api_register', f'success - role: {user.role}')
            return jsonify({"message": "Registration successful!", "user": {"id": user.user_id, "username": user.username, "role": user.role}}), 201
        else:
            # Registration failed for other reasons (logged within user_manager)
            current_app.logger.error(f"API Registration Failed: Unexpected error during registration for username '{username}'. Check user_manager logs.")
            log_audit(AUDIT_LOG_FILE, username, 'api_register', 'failure - unexpected error in user_manager')
            # Use abort(500) as it's an internal issue
            abort(500, description="Registration failed due to an internal error.")

    except Exception as e:
        current_app.logger.exception(f"API Register Error: Unexpected error during registration for username '{data.get('username', 'unknown') if data else 'unknown'}'.")
        log_audit(AUDIT_LOG_FILE, data.get('username', 'unknown') if data else 'unknown', 'api_register', f'unexpected error: {e}')
        abort(500)

@app.route('/api/logout', methods=['POST'])
@api_login_required # Ensures user is logged in and components are initialized
def api_logout():
    """API endpoint for user logout."""
    username = session.get('username', 'unknown_user') # Get username before clearing
    role = session.get('user_role', 'unknown_role')
    user_id = session.get('user_id', 'unknown_id')
    ip_addr = request.remote_addr

    try:
        session.clear()
        current_app.logger.info(f"API Logout Successful: User '{username}' (ID: {user_id}, Role: {role}) logged out from IP {ip_addr}.")
        log_audit(AUDIT_LOG_FILE, username, 'api_logout', f'success - role: {role}')
        return jsonify({"message": "Logout successful"}), 200
    except Exception as e:
        # Less likely to have errors here, but catch just in case
        current_app.logger.exception(f"API Logout Error: Unexpected error during logout for user '{username}'.")
        log_audit(AUDIT_LOG_FILE, username, 'api_logout', f'unexpected error: {e}')
        abort(500)


@app.route('/api/session', methods=['GET'])
def api_get_session():
    """API endpoint to check current authentication status."""
    if 'user_id' in session:
        # User is authenticated
        user_data = {
            "id": session['user_id'],
            "username": session['username'],
            "role": session['user_role']
        }
        current_app.logger.debug(f"API Session Check: User '{session['username']}' is authenticated.")
        return jsonify({"isAuthenticated": True, "user": user_data}), 200
    else:
        # User is not authenticated
        current_app.logger.debug("API Session Check: No authenticated user.")
        return jsonify({"isAuthenticated": False, "user": None}), 200


# --- API Family Tree Data Routes ---

# GET /api/people - Retrieve all people
@app.route('/api/people', methods=['GET'])
@api_login_required
def get_all_people():
    """API endpoint to get a list of all people."""
    username = session.get('username', 'api_user')
    current_app.logger.debug(f"API Get All People requested by '{username}'.")
    try:
        # Use the summary method for potentially better performance if full details aren't needed
        # people_summary = family_tree.get_people_summary()
        # return jsonify(people_summary)

        # Or return full details if needed by frontend list view
        people_list = [person.to_dict() for person in family_tree.people.values()]
        current_app.logger.info(f"API Get All People: Retrieved {len(people_list)} people for user '{username}'.")
        return jsonify(people_list)
    except Exception as e:
        current_app.logger.exception(f"API Get All People Error: Failed to retrieve people data for user '{username}'.")
        abort(500, description="Failed to retrieve people data.")

# GET /api/people/{person_id} - Retrieve a specific person
@app.route('/api/people/<person_id>', methods=['GET'])
@api_login_required
def get_person(person_id):
    """API endpoint to get details for a specific person."""
    username = session.get('username', 'api_user')
    current_app.logger.debug(f"API Get Person requested by '{username}' for ID: {person_id}.")
    try:
        person = family_tree.find_person(person_id=person_id)
        if person:
            current_app.logger.info(f"API Get Person: Retrieved person '{person.get_display_name()}' (ID: {person_id}) for user '{username}'.")
            return jsonify(person.to_dict())
        else:
            current_app.logger.warning(f"API Get Person Failed: Person ID '{person_id}' not found for user '{username}'.")
            abort(404, description="Person not found.") # Use abort for consistency
    except Exception as e:
        current_app.logger.exception(f"API Get Person Error: Failed to retrieve person data for ID '{person_id}', user '{username}'.")
        abort(500, description="Failed to retrieve person data.")

# POST /api/people - Add a new person
@app.route('/api/people', methods=['POST'])
@api_login_required
def api_add_person():
    """API endpoint to add a new person."""
    username = session.get('username', 'api_user')
    current_app.logger.debug(f"API Add Person attempt by '{username}'.")
    try:
        data = request.get_json()
        if not data:
            abort(400, description="Request body cannot be empty.")

        validation_errors = validate_person_data(data, is_edit=False)
        if validation_errors:
            current_app.logger.warning(f"API Add Person Validation Failed for user '{username}': {validation_errors}")
            # Use abort with description for the 400 handler
            abort(400, description=validation_errors)

        # Extract data safely after validation
        first_name = str(data.get('first_name')).strip()
        last_name = str(data.get('last_name', '')).strip()
        # ... (extract other fields similarly, using .get with defaults or None)
        nickname = str(data.get('nickname', '')).strip() or None
        dob = data.get('birth_date') or None
        dod = data.get('death_date') or None
        gender = data.get('gender') or None
        pob = str(data.get('place_of_birth', '')).strip() or None
        pod = str(data.get('place_of_death', '')).strip() or None
        notes = str(data.get('notes', '')).strip() or None
        attributes = data.get('attributes', {}) # Get attributes if provided

        person = family_tree.add_person(
            first_name=first_name, last_name=last_name, nickname=nickname,
            dob=dob, dod=dod, gender=gender, pob=pob, pod=pod, notes=notes,
            added_by=username, **attributes # Pass attributes as kwargs
        )

        if person:
            current_app.logger.info(f"API Add Person Successful: Person '{person.get_display_name()}' (ID: {person.person_id}) added by '{username}'.")
            log_audit(AUDIT_LOG_FILE, username, 'api_add_person', f'success - id: {person.person_id}, name: {person.get_full_name()}')
            return jsonify(person.to_dict()), 201
        else:
            # Failure occurred within family_tree.add_person (already logged there)
            current_app.logger.error(f"API Add Person Failed: family_tree.add_person returned None for user '{username}' after validation.")
            abort(500, description="Failed to add person due to an internal error after validation.")

    except Exception as e:
        current_app.logger.exception(f"API Add Person Error: Unexpected error for user '{username}'.")
        log_audit(AUDIT_LOG_FILE, username, 'api_add_person', f'unexpected error: {e}')
        abort(500)

# PUT /api/people/{person_id} - Edit an existing person
@app.route('/api/people/<person_id>', methods=['PUT'])
@api_login_required
def api_edit_person(person_id):
    """API endpoint to edit an existing person."""
    username = session.get('username', 'api_user')
    current_app.logger.debug(f"API Edit Person attempt by '{username}' for ID: {person_id}.")
    try:
        data = request.get_json()
        if not data:
            abort(400, description="Request body cannot be empty.")

        # Find person first
        person = family_tree.find_person(person_id=person_id)
        if not person:
            current_app.logger.warning(f"API Edit Person Failed: Person ID '{person_id}' not found for user '{username}'.")
            abort(404, description="Person not found.")

        validation_errors = validate_person_data(data, is_edit=True)
        if validation_errors:
            current_app.logger.warning(f"API Edit Person Validation Failed for user '{username}', ID '{person_id}': {validation_errors}")
            abort(400, description=validation_errors)

        # Prepare update data dict carefully (pass only fields present in request)
        updated_data = {}
        allowed_fields = ['first_name', 'last_name', 'nickname', 'birth_date', 'death_date', 'gender', 'place_of_birth', 'place_of_death', 'notes', 'attributes']
        for key in allowed_fields:
            if key in data:
                updated_data[key] = data[key] # Pass raw value, let edit_person handle processing/stripping

        if not updated_data:
            current_app.logger.info(f"API Edit Person: No update data provided by '{username}' for ID '{person_id}'.")
            # Return 200 OK with a message, as PUT implies the state is achieved (no change needed)
            return jsonify({"message": "No update data provided, no changes made."}), 200

        original_name = person.get_display_name() # Get name before potential change
        success = family_tree.edit_person(person_id, updated_data, edited_by=username)

        if success:
            updated_person = family_tree.find_person(person_id=person_id) # Re-fetch to get final state
            current_app.logger.info(f"API Edit Person Successful: Person '{original_name}' (ID: {person_id}) updated to '{updated_person.get_display_name()}' by '{username}'.")
            # Audit log handled by edit_person
            return jsonify(updated_person.to_dict()), 200
        else:
            # edit_person returned False, meaning no changes were effectively made (logged within edit_person)
            current_app.logger.info(f"API Edit Person: No effective changes made by '{username}' for ID '{person_id}'.")
            # Return 200 OK, state is as requested (no change)
            return jsonify({"message": "No effective changes detected or update failed internally."}), 200

    except Exception as e:
        current_app.logger.exception(f"API Edit Person Error: Unexpected error for user '{username}', ID '{person_id}'.")
        log_audit(AUDIT_LOG_FILE, username, 'api_edit_person', f'unexpected error for id {person_id}: {e}')
        abort(500)

# DELETE /api/people/{person_id} - Delete a person
@app.route('/api/people/<person_id>', methods=['DELETE'])
@api_login_required
def api_delete_person(person_id):
    """API endpoint to delete a person."""
    username = session.get('username', 'api_user')
    current_app.logger.debug(f"API Delete Person attempt by '{username}' for ID: {person_id}.")
    try:
        # Find person first to log name before deletion
        person = family_tree.find_person(person_id=person_id)
        if not person:
            current_app.logger.warning(f"API Delete Person Failed: Person ID '{person_id}' not found for user '{username}'.")
            abort(404, description="Person not found.")

        person_name = person.get_display_name() # Get name for logging
        success = family_tree.delete_person(person_id, deleted_by=username)

        if success:
            current_app.logger.info(f"API Delete Person Successful: Person '{person_name}' (ID: {person_id}) deleted by '{username}'.")
            # Audit log handled by delete_person
            return '', 204 # No Content
        else:
            # Should not happen if person was found, implies internal error in delete_person
            current_app.logger.error(f"API Delete Person Failed: delete_person returned False for ID '{person_id}', user '{username}' after person was found.")
            abort(500, description="Failed to delete person due to an internal error.")

    except Exception as e:
        current_app.logger.exception(f"API Delete Person Error: Unexpected error for user '{username}', ID '{person_id}'.")
        log_audit(AUDIT_LOG_FILE, username, 'api_delete_person', f'unexpected error for id {person_id}: {e}')
        abort(500)


# GET /api/relationships - Retrieve all relationships
@app.route('/api/relationships', methods=['GET'])
@api_login_required
def get_all_relationships():
    """API endpoint to get a list of all relationships."""
    username = session.get('username', 'api_user')
    current_app.logger.debug(f"API Get All Relationships requested by '{username}'.")
    try:
        # Use summary for potentially better performance
        # relationships_summary = family_tree.get_relationships_summary()
        # return jsonify(relationships_summary)

        # Or return full details
        relationships_list = [rel.to_dict() for rel in family_tree.relationships.values()]
        current_app.logger.info(f"API Get All Relationships: Retrieved {len(relationships_list)} relationships for user '{username}'.")
        return jsonify(relationships_list)
    except Exception as e:
        current_app.logger.exception(f"API Get All Relationships Error: Failed to retrieve relationships data for user '{username}'.")
        abort(500, description="Failed to retrieve relationships data.")

# POST /api/relationships - Add a new relationship
@app.route('/api/relationships', methods=['POST'])
@api_login_required
def api_add_relationship():
    """API endpoint to add a new relationship."""
    username = session.get('username', 'api_user')
    current_app.logger.debug(f"API Add Relationship attempt by '{username}'.")
    try:
        data = request.get_json()
        if not data:
            abort(400, description="Request body cannot be empty.")

        person1_id = data.get('person1_id')
        person2_id = data.get('person2_id')
        rel_type = data.get('rel_type')
        attributes = data.get('attributes', {}) # Get attributes, default to empty dict

        # --- Validation ---
        errors = {}
        if not person1_id: errors['person1_id'] = 'Person 1 ID is required.'
        if not person2_id: errors['person2_id'] = 'Person 2 ID is required.'
        if not rel_type: errors['rel_type'] = 'Relationship type is required.'
        # Prevent self-relationship
        if person1_id and person1_id == person2_id:
            errors['person2_id'] = 'Cannot add relationship to the same person.'
        # Validate relationship type
        if rel_type and rel_type not in VALID_RELATIONSHIP_TYPES:
            errors['rel_type'] = f"Invalid relationship type '{rel_type}'. Valid types: {', '.join(VALID_RELATIONSHIP_TYPES)}"
        # Check if persons exist (only if IDs provided and no previous errors for them)
        person1, person2 = None, None
        if person1_id and 'person1_id' not in errors:
            person1 = family_tree.find_person(person_id=person1_id)
            if not person1: errors['person1_id'] = f"Person with ID {person1_id} not found."
        if person2_id and 'person2_id' not in errors:
            person2 = family_tree.find_person(person_id=person2_id)
            if not person2: errors['person2_id'] = f"Person with ID {person2_id} not found."

        if errors:
            current_app.logger.warning(f"API Add Relationship Validation Failed for user '{username}': {errors}")
            abort(400, description=errors)

        # Attempt to add the relationship
        relationship = family_tree.add_relationship(
            person1_id=person1_id, person2_id=person2_id,
            relationship_type=rel_type, attributes=attributes, added_by=username
        )

        if relationship:
            current_app.logger.info(f"API Add Relationship Successful: Relationship '{rel_type}' (ID: {relationship.rel_id}) added between '{person1_id}' and '{person2_id}' by '{username}'.")
            # Audit log handled by add_relationship
            return jsonify(relationship.to_dict()), 201
        else:
            # Failure likely due to duplicate or internal error (logged within add_relationship)
            current_app.logger.error(f"API Add Relationship Failed: family_tree.add_relationship returned None for user '{username}' after validation.")
            # Use 409 Conflict if duplicate is the most likely reason
            abort(409, description="Failed to add relationship. It might already exist or an internal error occurred.")

    except Exception as e:
        current_app.logger.exception(f"API Add Relationship Error: Unexpected error for user '{username}'.")
        log_audit(AUDIT_LOG_FILE, username, 'api_add_relationship', f'unexpected error: {e}')
        abort(500)

# PUT /api/relationships/{relationship_id} - Edit an existing relationship
@app.route('/api/relationships/<relationship_id>', methods=['PUT'])
@api_login_required
def api_edit_relationship(relationship_id):
    """API endpoint to edit an existing relationship."""
    username = session.get('username', 'api_user')
    current_app.logger.debug(f"API Edit Relationship attempt by '{username}' for ID: {relationship_id}.")
    try:
        data = request.get_json()
        if not data:
            abort(400, description="Request body cannot be empty.")

        # Find relationship first
        rel = family_tree.relationships.get(relationship_id)
        if not rel:
            current_app.logger.warning(f"API Edit Relationship Failed: Relationship ID '{relationship_id}' not found for user '{username}'.")
            abort(404, description="Relationship not found.")

        # --- Validation ---
        errors = {}
        new_type = data.get('rel_type')
        if 'rel_type' in data: # Only validate if field is present
            if not new_type or not str(new_type).strip():
                errors['rel_type'] = 'Relationship type cannot be empty.'
            elif new_type not in VALID_RELATIONSHIP_TYPES:
                errors['rel_type'] = f"Invalid relationship type '{new_type}'. Valid types: {', '.join(VALID_RELATIONSHIP_TYPES)}"
        # Validate attributes if present (ensure it's a dictionary)
        if 'attributes' in data and not isinstance(data.get('attributes'), dict):
            errors['attributes'] = 'Attributes must be a valid JSON object (dictionary).'

        if errors:
            current_app.logger.warning(f"API Edit Relationship Validation Failed for user '{username}', ID '{relationship_id}': {errors}")
            abort(400, description=errors)

        # Prepare update data dict
        updated_data = {}
        if 'rel_type' in data: updated_data['rel_type'] = str(new_type).strip()
        if 'attributes' in data: updated_data['attributes'] = data['attributes'] # Pass dict

        if not updated_data:
            current_app.logger.info(f"API Edit Relationship: No update data provided by '{username}' for ID '{relationship_id}'.")
            return jsonify({"message": "No update data provided, no changes made."}), 200

        original_type = rel.rel_type # Get type before potential change
        success = family_tree.edit_relationship(relationship_id, updated_data, edited_by=username)

        if success:
            updated_rel = family_tree.relationships.get(relationship_id) # Re-fetch
            current_app.logger.info(f"API Edit Relationship Successful: Relationship ID '{relationship_id}' (Type: {original_type} -> {updated_rel.rel_type}) updated by '{username}'.")
            # Audit log handled by edit_relationship
            return jsonify(updated_rel.to_dict()), 200
        else:
            current_app.logger.info(f"API Edit Relationship: No effective changes made by '{username}' for ID '{relationship_id}'.")
            return jsonify({"message": "No effective changes detected or update failed internally."}), 200

    except Exception as e:
        current_app.logger.exception(f"API Edit Relationship Error: Unexpected error for user '{username}', ID '{relationship_id}'.")
        log_audit(AUDIT_LOG_FILE, username, 'api_edit_relationship', f'unexpected error for id {relationship_id}: {e}')
        abort(500)

# DELETE /api/relationships/{relationship_id} - Delete a relationship
@app.route('/api/relationships/<relationship_id>', methods=['DELETE'])
@api_login_required
def api_delete_relationship(relationship_id):
    """API endpoint to delete a relationship."""
    username = session.get('username', 'api_user')
    current_app.logger.debug(f"API Delete Relationship attempt by '{username}' for ID: {relationship_id}.")
    try:
        # Find relationship first for logging details
        rel = family_tree.relationships.get(relationship_id)
        if not rel:
            current_app.logger.warning(f"API Delete Relationship Failed: Relationship ID '{relationship_id}' not found for user '{username}'.")
            abort(404, description="Relationship not found.")

        rel_type = rel.rel_type # Get details before deletion
        p1_id = rel.person1_id
        p2_id = rel.person2_id
        success = family_tree.delete_relationship(relationship_id, deleted_by=username)

        if success:
            current_app.logger.info(f"API Delete Relationship Successful: Relationship '{rel_type}' (ID: {relationship_id}) between '{p1_id}' and '{p2_id}' deleted by '{username}'.")
            # Audit log handled by delete_relationship
            return '', 204 # No Content
        else:
            # Should not happen if relationship was found
            current_app.logger.error(f"API Delete Relationship Failed: delete_relationship returned False for ID '{relationship_id}', user '{username}' after relationship was found.")
            abort(500, description="Failed to delete relationship due to an internal error.")

    except Exception as e:
        current_app.logger.exception(f"API Delete Relationship Error: Unexpected error for user '{username}', ID '{relationship_id}'.")
        log_audit(AUDIT_LOG_FILE, username, 'api_delete_relationship', f'unexpected error for id {relationship_id}: {e}')
        abort(500)


# --- API Tree Visualization Data Route ---
@app.route('/api/tree_data')
@api_login_required
def tree_data():
    """
    Retrieves node and link data for the family tree visualization.
    Supports optional 'start_node' and 'depth' query parameters for lazy loading.
    """
    username = session.get('username', 'api_user')
    start_node_id = request.args.get('start_node')
    depth_str = request.args.get('depth')
    max_depth = None

    # Validate depth parameter
    if depth_str:
        try:
            max_depth = int(depth_str)
            if max_depth < 0:
                current_app.logger.warning(f"API Tree Data: Invalid depth '{depth_str}' requested by '{username}'. Must be non-negative.")
                abort(400, description="Depth must be a non-negative integer.")
        except ValueError:
            current_app.logger.warning(f"API Tree Data: Invalid depth format '{depth_str}' requested by '{username}'. Must be an integer.")
            abort(400, description="Depth must be an integer.")

    # Log the request details
    log_params = f"start={start_node_id}, depth={max_depth}" if start_node_id else f"full tree requested"
    current_app.logger.info(f"API Tree Data request by '{username}': {log_params}.")
    log_audit(AUDIT_LOG_FILE, username, 'get_tree_data', f'params: {log_params}')

    try:
        # Call the method in family_tree to get filtered/full data
        data = family_tree.get_nodes_links_data(start_node_id=start_node_id, max_depth=max_depth)
        current_app.logger.debug(f"API Tree Data: Generated {len(data.get('nodes',[]))} nodes, {len(data.get('links',[]))} links for '{username}'.")
        return jsonify(data)
    except Exception as e:
        current_app.logger.exception(f"API Tree Data Error: Failed to generate tree data for user '{username}'. Params: {log_params}.")
        log_audit(AUDIT_LOG_FILE, username, 'get_tree_data', f'error generating data: {e}')
        abort(500, description="Failed to generate tree data.")


# --- Main Execution ---
if __name__ == '__main__':
    # Check for admin user only if user_manager initialized successfully
    if user_manager:
        if user_manager.users and not any(user.role == 'admin' for user in user_manager.users.values()):
            try:
                first_user_id = next(iter(user_manager.users))
                first_username = user_manager.users[first_user_id].username
                app.logger.warning(f"No admin user found. Making first user '{first_username}' (ID: {first_user_id}) an admin for initial setup.")
                user_manager.set_user_role(first_user_id, 'admin', actor_username='system_startup')
            except StopIteration:
                 app.logger.info("User file exists but contains no users.")
            except Exception as admin_err:
                 app.logger.error(f"Error setting initial admin role: {admin_err}", exc_info=True)
        elif not user_manager.users:
            app.logger.info("No users found in user file. First registered user may need manual promotion to admin if required.")
    else:
        app.logger.error("User manager failed to initialize. Cannot perform admin check or run application correctly.")
        # Exit if core components failed? Depends on desired behavior.
        # exit(1) # Or raise an exception

    port = int(os.environ.get('PORT', 8090))
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.logger.info(f"Starting Flask server on host 0.0.0.0, port {port}, Debug: {debug_mode}")

    # Consider using a production-ready WSGI server like 'waitress' or 'gunicorn'
    # instead of app.run() for deployment.
    # Example using waitress (install with pip install waitress):
    # from waitress import serve
    # serve(app, host='0.0.0.0', port=port)
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
