# backend/app.py
import os
import logging
from functools import wraps
from flask import Flask, request, session, jsonify, abort, current_app
from flask_cors import CORS
# Assuming user_management, family_tree etc. are correctly imported from src
from src.user_management import UserManagement, VALID_ROLES # Import VALID_ROLES
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
CORS(app, supports_credentials=True, origins=["http://localhost:5173", "http://127.0.0.1:5173"]) # Added default Vite port
logging.info("CORS configured for development origins.")

# --- Configure Logging ---
os.makedirs(LOG_DIR, exist_ok=True)
log_formatter = logging.Formatter('%(asctime)s %(levelname)-8s [%(name)s] %(message)s [in %(pathname)s:%(lineno)d]')

# File Handler (Rotating)
file_handler = RotatingFileHandler(APP_LOG_FILE, maxBytes=1024*1024*5, backupCount=5, encoding='utf-8')
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)

# Console Handler (for development visibility)
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
# Set console level based on FLASK_DEBUG environment variable
console_handler.setLevel(logging.DEBUG if os.environ.get('FLASK_DEBUG') == '1' else logging.INFO)

# Get the Flask app's logger and configure it
if app.logger.handlers: app.logger.handlers.clear()
app.logger.addHandler(file_handler)
app.logger.addHandler(console_handler)
app.logger.setLevel(logging.DEBUG if os.environ.get('FLASK_DEBUG') == '1' else logging.INFO)

app.logger.info("Flask application starting up...")

# --- Initialize Core Components ---
os.makedirs(DATA_DIR, exist_ok=True)
user_manager = None
family_tree = None
try:
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

def family_tree_required(f):
    """Decorator to ensure the family_tree service is initialized."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not family_tree:
            current_app.logger.error(f"Family tree service unavailable. Endpoint '{request.endpoint}' accessed.")
            return jsonify({"error": "Family tree service unavailable."}), 503
        return f(*args, **kwargs)
    return decorated_function
def api_login_required(f):
    """Decorator to ensure user is logged in for API endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check session *before* checking component initialization
        if 'user_id' not in session:
            current_app.logger.warning(f"API Authentication Required: Endpoint '{request.endpoint}' accessed without login (IP: {request.remote_addr}).")
            log_audit(AUDIT_LOG_FILE, 'anonymous', 'api_access_denied', f'login required for API endpoint {request.endpoint}')
            return jsonify({"error": "Authentication required"}), 401

        # Check if core components initialized properly *after* confirming login attempt
        if not user_manager or not family_tree:
             current_app.logger.error(f"API Service Unavailable: Endpoint '{request.endpoint}' accessed but core components not initialized.")
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
    description = getattr(error, 'description', "Invalid request format or data.")
    current_app.logger.warning(f"API Bad Request (400): {description} - Endpoint: {request.endpoint}, IP: {request.remote_addr}")
    response_data = {"error": "Bad Request", "message": description}
    if isinstance(description, dict): # Assume validation errors
        response_data = {"error": "Validation failed", "details": description}
    return jsonify(response_data), 400

@app.errorhandler(401)
def handle_unauthorized(error):
    """Handles 401 Unauthorized errors."""
    description = getattr(error, 'description', "Authentication required.")
    current_app.logger.warning(f"API Unauthorized (401): {description} - Endpoint: {request.endpoint}, IP: {request.remote_addr}")
    return jsonify({"error": "Unauthorized", "message": description}), 401

@app.errorhandler(403)
def handle_forbidden(error):
    """Handles 403 Forbidden errors."""
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
    current_app.logger.exception(f"API Internal Server Error (500): Endpoint: {request.endpoint}, User: {session.get('username', 'anonymous')}, IP: {request.remote_addr}")
    return jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred. Please try again later."}), 500

@app.errorhandler(503)
def handle_service_unavailable(error):
    """Handles 503 Service Unavailable errors."""
    description = getattr(error, 'description', "Service temporarily unavailable.")
    current_app.logger.error(f"API Service Unavailable (503): {description} - Endpoint: {request.endpoint}, IP: {request.remote_addr}")
    return jsonify({"error": "Service Unavailable", "message": description}), 503

# --- Password Validation ---
import re

def is_password_complex(password):
    """Validates password complexity."""
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):  # At least one uppercase letter
        return False
    if not re.search(r'[a-z]', password):  # At least one lowercase letter
        return False
    if not re.search(r'[0-9]', password):  # At least one digit
        return False
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):  # At least one special character
        return False
    return True

# --- API Authentication Routes ---
@app.route('/api/login', methods=['POST'])
def api_login():
    """API endpoint for user login."""
    if not user_manager:
        current_app.logger.error("API Login attempt failed: User manager not initialized.")
        return jsonify({"error": "Authentication service unavailable."}), 503

    try:
        data = request.get_json()
        if not data or not data.get('username') or not data.get('password'):
            abort(400, description="Username and password are required.")

        username = data['username'].strip()
        password = data['password']
        current_app.logger.debug(f"API Login attempt for username: '{username}'")

        user = user_manager.login_user(username, password)

        if user:
            session['user_id'] = user.user_id
            session['username'] = user.username
            session['user_role'] = user.role
            current_app.logger.info(f"API Login Successful: User '{username}' (Role: {user.role}) logged in from IP {request.remote_addr}.")
            # Audit log handled by user_manager
            return jsonify({"message": "Login successful!", "user": {"id": user.user_id, "username": user.username, "role": user.role}}), 200
        else:
            # Error already logged by user_manager
            current_app.logger.warning(f"API Login Failed for username '{username}' from IP {request.remote_addr}.")
            abort(401, description="Invalid username or password.")

    except Exception as e:
        current_app.logger.exception(f"API Login Error: Unexpected error during login for username '{data.get('username', 'unknown') if data else 'unknown'}'.")
        log_audit(AUDIT_LOG_FILE, data.get('username', 'unknown') if data else 'unknown', 'api_login', f'unexpected error: {e}')
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
            abort(400, description="Username and password are required.")

        username = data['username'].strip()
        password = data['password']

        if not username: abort(400, description="Username cannot be empty.")
        if not password: abort(400, description="Password cannot be empty.")

        current_app.logger.debug(f"API Register attempt for username: '{username}'")

        # Check if username exists (case-insensitive)
        if user_manager.find_user_by_username(username):
            current_app.logger.warning(f"API Register Failed: Username '{username}' already taken.")
            log_audit(AUDIT_LOG_FILE, username, 'api_register_attempt', 'failure - username exists')
            return jsonify({"error": f"Username '{username}' is already taken."}), 409

        user = user_manager.register_user(username, password) # Default role 'basic'

        if user:
            current_app.logger.info(f"API Registration Successful: User '{username}' (Role: {user.role}) registered from IP {request.remote_addr}.")
            # Audit log handled by user_manager
            return jsonify({"message": "Registration successful!", "user": {"id": user.user_id, "username": user.username, "role": user.role}}), 201
        else:
            current_app.logger.error(f"API Registration Failed: Unexpected error during registration for username '{username}'. Check user_manager logs.")
            log_audit(AUDIT_LOG_FILE, username, 'api_register', 'failure - unexpected error in user_manager')
            abort(500, description="Registration failed due to an internal error.")

    except Exception as e:
        current_app.logger.exception(f"API Register Error: Unexpected error during registration for username '{data.get('username', 'unknown') if data else 'unknown'}'.")
        log_audit(AUDIT_LOG_FILE, data.get('username', 'unknown') if data else 'unknown', 'api_register', f'unexpected error: {e}')
        abort(500)

@app.route('/api/logout', methods=['POST'])
@api_login_required
def api_logout():
    """API endpoint for user logout."""
    username = session.get('username', 'unknown_user')
    role = session.get('user_role', 'unknown_role')
    user_id = session.get('user_id', 'unknown_id')
    ip_addr = request.remote_addr

    try:
        session.clear()
        current_app.logger.info(f"API Logout Successful: User '{username}' (ID: {user_id}, Role: {role}) logged out from IP {ip_addr}.")
        log_audit(AUDIT_LOG_FILE, username, 'api_logout', f'success - role: {role}')
        return jsonify({"message": "Logout successful"}), 200
    except Exception as e:
        current_app.logger.exception(f"API Logout Error: Unexpected error during logout for user '{username}'.")
        log_audit(AUDIT_LOG_FILE, username, 'api_logout', f'unexpected error: {e}')
        abort(500)

@app.route('/api/session', methods=['GET'])
def api_get_session():
    """API endpoint to check current authentication status."""
    if 'user_id' in session:
        user_data = {
            "id": session.get('user_id'),
            "username": session.get('username'),
            "role": session.get('user_role')
        }
        current_app.logger.debug(f"API Session Check: User '{session.get('username')}' is authenticated.")
        return jsonify({"isAuthenticated": True, "user": user_data}), 200
    else:
        current_app.logger.debug("API Session Check: No authenticated user.")
        return jsonify({"isAuthenticated": False, "user": None}), 200

# --- Password Reset API Endpoints ---

@app.route('/api/request-password-reset', methods=['POST'])
def api_request_password_reset():
    """API endpoint to request a password reset email."""
    if not user_manager:
        current_app.logger.error("API Password Reset Request failed: User manager not initialized.")
        return jsonify({"error": "Password reset service unavailable."}), 503

    data = request.get_json()
    if not data or 'email' not in data:
        abort(400, description="Email address is required.")

    email = data['email'].strip()
    if not email: # Extra validation
         abort(400, description="Email address cannot be empty.")

    current_app.logger.info(f"API Password Reset Request received for email: {email}")

    try:
        # Call the combined request/send logic in user_manager
        success = user_manager.request_password_reset(email)

        # Always return a generic success message regardless of outcome
        # This prevents attackers from discovering registered email addresses.
        log_audit(AUDIT_LOG_FILE, email, 'request_password_reset', f'processed (outcome hidden from user)')
        return jsonify({"message": "If an account exists for this email, a password reset link has been sent."}), 200

    except Exception as e:
        # Catch unexpected errors during the process
        current_app.logger.exception(f"API Request Password Reset Error: Unexpected error for email '{email}'.")
        log_audit(AUDIT_LOG_FILE, email, 'request_password_reset', f'unexpected internal error: {e}')
        # Return a generic server error message
        abort(500, description="Could not process password reset request due to an internal error.")


@app.route('/api/reset-password/<token>', methods=['POST'])
def api_reset_password(token):
    """API endpoint to reset password using a token."""
    if not user_manager:
        current_app.logger.error("API Password Reset failed: User manager not initialized.")
        return jsonify({"error": "Password reset service unavailable."}), 503

    data = request.get_json()
    if not data or 'new_password' not in data:
        abort(400, description="New password is required.")

    new_password = data['new_password']
    # Add password validation here (e.g., minimum length and complexity)
    if not new_password or not is_password_complex(new_password):
        abort(400, description="New password must be at least 8 characters long and include uppercase, lowercase, numbers, and special characters.")

    current_app.logger.info(f"API Password Reset attempt with token: {token[:8]}...")

    try:
        success = user_manager.reset_password(token, new_password)

        if success:
            current_app.logger.info(f"Password successfully reset using token: {token[:8]}...")
            # Audit log handled by user_manager
            return jsonify({"message": "Password reset successfully."}), 200
        else:
            current_app.logger.warning(f"Password reset failed for token: {token[:8]}... (invalid/expired token or internal error)")
            log_audit(AUDIT_LOG_FILE, f"token:{token[:8]}...", 'reset_password', 'failure - invalid/expired token or internal error')
            abort(400, description="Invalid or expired password reset token, or password could not be reset.")
    except Exception as e:
        current_app.logger.exception(f"API Reset Password Error: Unexpected error for token '{token[:8]}...'.")
        log_audit(AUDIT_LOG_FILE, f"token:{token[:8]}...", 'reset_password', f'unexpected error: {e}')
        abort(500)


# --- Admin User Management API Endpoints ---

@app.route('/api/users', methods=['GET'])
@api_admin_required # Requires admin login
def api_get_all_users():
    """API endpoint for admins to get a list of all users."""
    admin_username = session.get('username', 'admin_user')
    current_app.logger.info(f"API Get All Users requested by admin '{admin_username}'.")
    try:
        all_users = user_manager.get_all_users()
        # Return user data excluding sensitive info (like password hash)
        users_list = [
            # Use user.to_dict() and then remove the hash, ensuring other fields are included
            {k: v for k, v in u.to_dict().items() if k != 'password_hash_b64'}
            for u in all_users if isinstance(u, object) # Ensure 'u' is an object before calling to_dict
        ]
        current_app.logger.debug(f"Retrieved {len(users_list)} users for admin '{admin_username}'.")
        return jsonify(users_list), 200
    except Exception as e:
        current_app.logger.exception(f"API Get All Users Error: Failed for admin '{admin_username}'.")
        abort(500, description="Failed to retrieve user list.")


@app.route('/api/users/<user_id>', methods=['DELETE'])
@api_admin_required # Requires admin login
def api_admin_delete_user(user_id):
    """API endpoint for admins to delete a user."""
    admin_username = session.get('username', 'admin_user')
    current_app.logger.info(f"API Delete User attempt by admin '{admin_username}' for user ID: {user_id}.")

    if not user_manager: # Check again as it might fail between login and this call
        return jsonify({"error": "User management service unavailable."}), 503

    # Prevent admin from deleting themselves
    if session.get('user_id') == user_id:
        current_app.logger.warning(f"Admin '{admin_username}' attempted self-deletion (ID: {user_id}).")
        log_audit(AUDIT_LOG_FILE, admin_username, 'api_delete_user', f'failure - admin self-deletion attempt for {user_id}')
        abort(403, description="Administrators cannot delete their own account.")

    user_to_delete = user_manager.find_user_by_id(user_id)
    if not user_to_delete:
        current_app.logger.warning(f"API Delete User Failed: User ID '{user_id}' not found by admin '{admin_username}'.")
        abort(404, description="User not found.")

    deleted_username = user_to_delete.username # Get username for logging before deletion
    try:
        success = user_manager.delete_user(user_id, actor_username=admin_username)

        if success:
            current_app.logger.info(f"API Delete User Successful: User '{deleted_username}' (ID: {user_id}) deleted by admin '{admin_username}'.")
            # Audit log handled by user_manager.delete_user
            return '', 204 # No Content
        else:
            # Should not happen if user was found, implies internal error in delete_user
            current_app.logger.error(f"API Delete User Failed: delete_user returned False for ID '{user_id}', admin '{admin_username}'.")
            abort(500, description="Failed to delete user due to an internal error.")
    except Exception as e:
        current_app.logger.exception(f"API Delete User Error: Unexpected error for admin '{admin_username}', user ID '{user_id}'.")
        log_audit(AUDIT_LOG_FILE, admin_username, 'api_delete_user', f'unexpected error for id {user_id}: {e}')
        abort(500)

@app.route('/api/users/<user_id>/role', methods=['PUT'])
@api_admin_required # Requires admin login
def api_admin_set_user_role(user_id):
    """API endpoint for admins to change a user's role."""
    admin_username = session.get('username', 'admin_user')
    current_app.logger.info(f"API Set User Role attempt by admin '{admin_username}' for user ID: {user_id}.")

    if not user_manager: # Check again
        return jsonify({"error": "User management service unavailable."}), 503

    data = request.get_json()
    if not data or 'role' not in data:
        abort(400, description="New role is required in request body.")

    new_role = data['role'].strip()
    if new_role not in VALID_ROLES:
        abort(400, description=f"Invalid role '{new_role}'. Valid roles are: {', '.join(VALID_ROLES)}")

    user_to_modify = user_manager.find_user_by_id(user_id)
    if not user_to_modify:
        current_app.logger.warning(f"API Set Role Failed: User ID '{user_id}' not found by admin '{admin_username}'.")
        abort(404, description="User not found.")

    # Optional: Prevent changing own role?
    # if session.get('user_id') == user_id:
    #     abort(403, description="Administrators cannot change their own role via this endpoint.")

    original_role = user_to_modify.role # Get role before change
    try:
        success = user_manager.set_user_role(user_id, new_role, actor_username=admin_username)

        if success:
            # Fetch user again to confirm change and return updated info
            updated_user = user_manager.find_user_by_id(user_id)
            current_app.logger.info(f"API Set Role Successful: Role for user '{user_to_modify.username}' (ID: {user_id}) changed from '{original_role}' to '{new_role}' by admin '{admin_username}'.")
            # Audit log handled by user_manager.set_user_role
            return jsonify({"user_id": user_id, "username": updated_user.username, "role": updated_user.role}), 200
        else:
            # Failure logged within user_manager (e.g., invalid role, save error)
            current_app.logger.error(f"API Set Role Failed: set_user_role returned False for ID '{user_id}', admin '{admin_username}'.")
            # Check if role was already the target role
            if original_role == new_role:
                 return jsonify({"message": f"User already has role '{new_role}'. No change made."}), 200
            else:
                 abort(500, description="Failed to set user role due to an internal error.")
    except Exception as e:
        current_app.logger.exception(f"API Set Role Error: Unexpected error for admin '{admin_username}', user ID '{user_id}'.")
        log_audit(AUDIT_LOG_FILE, admin_username, 'api_set_user_role', f'unexpected error for id {user_id}: {e}')
        abort(500)


# --- API Family Tree Data Routes ---
@app.route('/api/people', methods=['GET'])
@api_login_required
@family_tree_required
def get_all_people():
    """API endpoint to get a list of all people."""
    username = session.get('username', 'api_user')
    current_app.logger.debug(f"API Get All People requested by '{username}'.")
    # This check is now handled by the @family_tree_required decorator.
    pass
    try:
        # Return full details needed by frontend list/visualization
        people_list = [person.to_dict() for person in family_tree.people.values() if isinstance(person, object)]
        current_app.logger.info(f"API Get All People: Retrieved {len(people_list)} people for user '{username}'.")
        return jsonify(people_list)
    except Exception as e:
        current_app.logger.exception(f"API Get All People Error: Failed to retrieve people data for user '{username}'.")
        abort(500, description="Failed to retrieve people data.")

@app.route('/api/people/<person_id>', methods=['GET'])
@api_login_required
@family_tree_required
def get_person(person_id):
    """API endpoint to get details for a specific person."""
    username = session.get('username', 'api_user')
    current_app.logger.debug(f"API Get Person requested by '{username}' for ID: {person_id}.")
    if not family_tree: return jsonify({"error": "Family tree service unavailable."}), 503
    try:
        person = family_tree.find_person(person_id=person_id)
        if person:
            current_app.logger.info(f"API Get Person: Retrieved person '{person.get_display_name()}' (ID: {person_id}) for user '{username}'.")
            return jsonify(person.to_dict())
        else:
            current_app.logger.warning(f"API Get Person Failed: Person ID '{person_id}' not found for user '{username}'.")
            abort(404, description="Person not found.")
    except Exception as e:
        current_app.logger.exception(f"API Get Person Error: Failed to retrieve person data for ID '{person_id}', user '{username}'.")
        abort(500, description="Failed to retrieve person data.")

@app.route('/api/people', methods=['POST'])
@api_login_required
@family_tree_required
def api_add_person():
    """API endpoint to add a new person."""
    username = session.get('username', 'api_user')
    current_app.logger.debug(f"API Add Person attempt by '{username}'.")
    if not family_tree: return jsonify({"error": "Family tree service unavailable."}), 503
    try:
        data = request.get_json()
        if not data:
            abort(400, description="Request body cannot be empty.")

        validation_errors = validate_person_data(data, is_edit=False)
        if validation_errors:
            current_app.logger.warning(f"API Add Person Validation Failed for user '{username}': {validation_errors}")
            abort(400, description=validation_errors)

        first_name = str(data.get('first_name')).strip()
        last_name = str(data.get('last_name', '')).strip()
        nickname = str(data.get('nickname', '')).strip() or None
        dob = data.get('birth_date') or None
        dod = data.get('death_date') or None
        gender = data.get('gender') or None
        pob = str(data.get('place_of_birth', '')).strip() or None
        pod = str(data.get('place_of_death', '')).strip() or None
        notes = str(data.get('notes', '')).strip() or None
        attributes = data.get('attributes', {})

        person = family_tree.add_person(
            first_name=first_name, last_name=last_name, nickname=nickname,
            dob=dob, dod=dod, gender=gender, pob=pob, pod=pod, notes=notes,
            added_by=username, **attributes
        )

        if person:
            current_app.logger.info(f"API Add Person Successful: Person '{person.get_display_name()}' (ID: {person.person_id}) added by '{username}'.")
            log_audit(AUDIT_LOG_FILE, username, 'api_add_person', f'success - id: {person.person_id}, name: {person.get_full_name()}')
            return jsonify(person.to_dict()), 201
        else:
            current_app.logger.error(f"API Add Person Failed: family_tree.add_person returned None for user '{username}' after validation.")
            abort(500, description="Failed to add person due to an internal error after validation.")

    except Exception as e:
        current_app.logger.exception(f"API Add Person Error: Unexpected error for user '{username}'.")
        log_audit(AUDIT_LOG_FILE, username, 'api_add_person', f'unexpected error: {e}')
        abort(500)

@app.route('/api/people/<person_id>', methods=['PUT'])
@api_login_required
@family_tree_required
def api_edit_person(person_id):
    """API endpoint to edit an existing person."""
    username = session.get('username', 'api_user')
    current_app.logger.debug(f"API Edit Person attempt by '{username}' for ID: {person_id}.")
    if not family_tree: return jsonify({"error": "Family tree service unavailable."}), 503
    try:
        data = request.get_json()
        if not data:
            abort(400, description="Request body cannot be empty.")

        person = family_tree.find_person(person_id=person_id)
        if not person:
            current_app.logger.warning(f"API Edit Person Failed: Person ID '{person_id}' not found for user '{username}'.")
            abort(404, description="Person not found.")

        validation_errors = validate_person_data(data, is_edit=True)
        if validation_errors:
            current_app.logger.warning(f"API Edit Person Validation Failed for user '{username}', ID '{person_id}': {validation_errors}")
            abort(400, description=validation_errors)

        updated_data = {}
        allowed_fields = ['first_name', 'last_name', 'nickname', 'birth_date', 'death_date', 'gender', 'place_of_birth', 'place_of_death', 'notes', 'attributes']
        for key in allowed_fields:
            if key in data:
                updated_data[key] = data[key]

        if not updated_data:
            current_app.logger.info(f"API Edit Person: No update data provided by '{username}' for ID '{person_id}'.")
            return jsonify({"message": "No update data provided, no changes made."}), 200

        original_name = person.get_display_name()
        success = family_tree.edit_person(person_id, updated_data, edited_by=username)

        if success:
            updated_person = family_tree.find_person(person_id=person_id)
            current_app.logger.info(f"API Edit Person Successful: Person '{original_name}' (ID: {person_id}) updated to '{updated_person.get_display_name()}' by '{username}'.")
            return jsonify(updated_person.to_dict()), 200
        else:
            current_app.logger.info(f"API Edit Person: No effective changes made by '{username}' for ID '{person_id}'.")
            return jsonify({"message": "No effective changes detected or update failed internally."}), 200

    except Exception as e:
        current_app.logger.exception(f"API Edit Person Error: Unexpected error for user '{username}', ID '{person_id}'.")
        log_audit(AUDIT_LOG_FILE, username, 'api_edit_person', f'unexpected error for id {person_id}: {e}')
        abort(500)

@app.route('/api/people/<person_id>', methods=['DELETE'])
@api_login_required
@family_tree_required
def api_delete_person(person_id):
    """API endpoint to delete a person."""
    username = session.get('username', 'api_user')
    current_app.logger.debug(f"API Delete Person attempt by '{username}' for ID: {person_id}.")
    if not family_tree: return jsonify({"error": "Family tree service unavailable."}), 503
    try:
        person = family_tree.find_person(person_id=person_id)
        if not person:
            current_app.logger.warning(f"API Delete Person Failed: Person ID '{person_id}' not found for user '{username}'.")
            abort(404, description="Person not found.")

        person_name = person.get_display_name()
        success = family_tree.delete_person(person_id, deleted_by=username)

        if success:
            current_app.logger.info(f"API Delete Person Successful: Person '{person_name}' (ID: {person_id}) deleted by '{username}'.")
            return '', 204
        else:
            current_app.logger.error(f"API Delete Person Failed: delete_person returned False for ID '{person_id}', user '{username}' after person was found.")
            abort(500, description="Failed to delete person due to an internal error.")

    except Exception as e:
        current_app.logger.exception(f"API Delete Person Error: Unexpected error for user '{username}', ID '{person_id}'.")
        log_audit(AUDIT_LOG_FILE, username, 'api_delete_person', f'unexpected error for id {person_id}: {e}')
        abort(500)


@app.route('/api/relationships', methods=['GET'])
@api_login_required
@family_tree_required
def get_all_relationships():
    """API endpoint to get a list of all relationships."""
    username = session.get('username', 'api_user')
    current_app.logger.debug(f"API Get All Relationships requested by '{username}'.")
    if not family_tree: return jsonify({"error": "Family tree service unavailable."}), 503
    try:
        relationships_list = [rel.to_dict() for rel in family_tree.relationships.values() if isinstance(rel, object)]
        current_app.logger.info(f"API Get All Relationships: Retrieved {len(relationships_list)} relationships for user '{username}'.")
        return jsonify(relationships_list)
    except Exception as e:
        current_app.logger.exception(f"API Get All Relationships Error: Failed to retrieve relationships data for user '{username}'.")
        abort(500, description="Failed to retrieve relationships data.")

@app.route('/api/relationships', methods=['POST'])
@api_login_required
@family_tree_required
def api_add_relationship():
    """API endpoint to add a new relationship."""
    username = session.get('username', 'api_user')
    current_app.logger.debug(f"API Add Relationship attempt by '{username}'.")
    if not family_tree: return jsonify({"error": "Family tree service unavailable."}), 503
    try:
        data = request.get_json()
        if not data:
            abort(400, description="Request body cannot be empty.")

        person1_id = data.get('person1') # Match frontend key 'person1'
        person2_id = data.get('person2') # Match frontend key 'person2'
        rel_type = data.get('relationshipType') # Match frontend key 'relationshipType'
        attributes = data.get('attributes', {})

        errors = {}
        if not person1_id: errors['person1'] = 'Person 1 ID is required.'
        if not person2_id: errors['person2'] = 'Person 2 ID is required.'
        if not rel_type: errors['relationshipType'] = 'Relationship type is required.'
        if person1_id and person1_id == person2_id:
            errors['person2'] = 'Cannot add relationship to the same person.'
        if rel_type and rel_type not in VALID_RELATIONSHIP_TYPES:
            # Allow frontend flexibility, but log warning if not in predefined list
            # errors['relationshipType'] = f"Invalid relationship type '{rel_type}'. Valid types: {', '.join(VALID_RELATIONSHIP_TYPES)}"
            current_app.logger.warning(f"API Add Relationship: Received potentially non-standard relationship type '{rel_type}' from user '{username}'.")

        person1, person2 = None, None
        if person1_id and 'person1' not in errors:
            person1 = family_tree.find_person(person_id=person1_id)
            if not person1: errors['person1'] = f"Person with ID {person1_id} not found."
        if person2_id and 'person2' not in errors:
            person2 = family_tree.find_person(person_id=person2_id)
            if not person2: errors['person2'] = f"Person with ID {person2_id} not found."

        if errors:
            current_app.logger.warning(f"API Add Relationship Validation Failed for user '{username}': {errors}")
            abort(400, description=errors)

        relationship = family_tree.add_relationship(
            person1_id=person1_id, person2_id=person2_id,
            relationship_type=rel_type, attributes=attributes, added_by=username
        )

        if relationship:
            p1_name = person1.get_display_name() if person1 else person1_id
            p2_name = person2.get_display_name() if person2 else person2_id
            current_app.logger.info(f"API Add Relationship Successful: Relationship '{rel_type}' (ID: {relationship.rel_id}) added between '{p1_name}' and '{p2_name}' by '{username}'.")
            return jsonify(relationship.to_dict()), 201
        else:
            current_app.logger.error(f"API Add Relationship Failed: family_tree.add_relationship returned None for user '{username}' after validation.")
            abort(409, description="Failed to add relationship. It might already exist or an internal error occurred.")

    except Exception as e:
        current_app.logger.exception(f"API Add Relationship Error: Unexpected error for user '{username}'.")
        log_audit(AUDIT_LOG_FILE, username, 'api_add_relationship', f'unexpected error: {e}')
        abort(500)

@app.route('/api/relationships/<relationship_id>', methods=['PUT'])
@api_login_required
@family_tree_required
def api_edit_relationship(relationship_id):
    """API endpoint to edit an existing relationship."""
    username = session.get('username', 'api_user')
    current_app.logger.debug(f"API Edit Relationship attempt by '{username}' for ID: {relationship_id}.")
    if not family_tree: return jsonify({"error": "Family tree service unavailable."}), 503
    try:
        data = request.get_json()
        if not data:
            abort(400, description="Request body cannot be empty.")

        rel = family_tree.relationships.get(relationship_id)
        if not rel:
            current_app.logger.warning(f"API Edit Relationship Failed: Relationship ID '{relationship_id}' not found for user '{username}'.")
            abort(404, description="Relationship not found.")

        errors = {}
        new_type = data.get('relationshipType') # Match frontend key
        if 'relationshipType' in data:
            if not new_type or not str(new_type).strip():
                errors['relationshipType'] = 'Relationship type cannot be empty.'
            elif new_type not in VALID_RELATIONSHIP_TYPES:
                 current_app.logger.warning(f"API Edit Relationship: Received potentially non-standard relationship type '{new_type}' from user '{username}' for rel ID {relationship_id}.")
                 # Decide if this should be an error or just a warning
                 # errors['relationshipType'] = f"Invalid relationship type '{new_type}'. Valid types: {', '.join(VALID_RELATIONSHIP_TYPES)}"

        if 'attributes' in data and not isinstance(data.get('attributes'), dict):
            errors['attributes'] = 'Attributes must be a valid JSON object (dictionary).'
        # Validate person IDs if they are included (ensure they exist)
        new_p1_id = data.get('person1')
        new_p2_id = data.get('person2')
        if 'person1' in data:
             if not family_tree.find_person(person_id=new_p1_id): errors['person1'] = f"Person with ID {new_p1_id} not found."
        if 'person2' in data:
             if not family_tree.find_person(person_id=new_p2_id): errors['person2'] = f"Person with ID {new_p2_id} not found."
        if 'person1' in data and 'person2' in data and new_p1_id == new_p2_id:
             errors['person2'] = 'Cannot set relationship to the same person.'

        if errors:
            current_app.logger.warning(f"API Edit Relationship Validation Failed for user '{username}', ID '{relationship_id}': {errors}")
            abort(400, description=errors)

        updated_data = {}
        # Map frontend keys to backend keys if necessary
        if 'relationshipType' in data: updated_data['rel_type'] = str(new_type).strip()
        if 'attributes' in data: updated_data['attributes'] = data['attributes']
        # Allow changing persons in relationship? Be careful with implications.
        if 'person1' in data: updated_data['person1_id'] = new_p1_id
        if 'person2' in data: updated_data['person2_id'] = new_p2_id


        if not updated_data:
            current_app.logger.info(f"API Edit Relationship: No update data provided by '{username}' for ID '{relationship_id}'.")
            return jsonify({"message": "No update data provided, no changes made."}), 200

        original_type = rel.rel_type
        original_p1 = rel.person1_id
        original_p2 = rel.person2_id
        success = family_tree.edit_relationship(relationship_id, updated_data, edited_by=username)

        if success:
            updated_rel = family_tree.relationships.get(relationship_id)
            current_app.logger.info(f"API Edit Relationship Successful: Relationship ID '{relationship_id}' (Type: {original_type} -> {updated_rel.rel_type}, P1: {original_p1}->{updated_rel.person1_id}, P2: {original_p2}->{updated_rel.person2_id}) updated by '{username}'.")
            return jsonify(updated_rel.to_dict()), 200
        else:
            current_app.logger.info(f"API Edit Relationship: No effective changes made by '{username}' for ID '{relationship_id}'.")
            return jsonify({"message": "No effective changes detected or update failed internally."}), 200

    except Exception as e:
        current_app.logger.exception(f"API Edit Relationship Error: Unexpected error for user '{username}', ID '{relationship_id}'.")
        log_audit(AUDIT_LOG_FILE, username, 'api_edit_relationship', f'unexpected error for id {relationship_id}: {e}')
        abort(500)


@app.route('/api/relationships/<relationship_id>', methods=['DELETE'])
@api_login_required
@family_tree_required
def api_delete_relationship(relationship_id):
    """API endpoint to delete a relationship."""
    username = session.get('username', 'api_user')
    current_app.logger.debug(f"API Delete Relationship attempt by '{username}' for ID: {relationship_id}.")
    if not family_tree: return jsonify({"error": "Family tree service unavailable."}), 503
    try:
        rel = family_tree.relationships.get(relationship_id)
        if not rel:
            current_app.logger.warning(f"API Delete Relationship Failed: Relationship ID '{relationship_id}' not found for user '{username}'.")
            abort(404, description="Relationship not found.")

        rel_type = rel.rel_type
        p1_id = rel.person1_id
        p2_id = rel.person2_id
        success = family_tree.delete_relationship(relationship_id, deleted_by=username)

        if success:
            current_app.logger.info(f"API Delete Relationship Successful: Relationship '{rel_type}' (ID: {relationship_id}) between '{p1_id}' and '{p2_id}' deleted by '{username}'.")
            return '', 204
        else:
            current_app.logger.error(f"API Delete Relationship Failed: delete_relationship returned False for ID '{relationship_id}', user '{username}'.")
            abort(500, description="Failed to delete relationship due to an internal error.")

    except Exception as e:
        current_app.logger.exception(f"API Delete Relationship Error: Unexpected error for user '{username}', ID '{relationship_id}'.")
        log_audit(AUDIT_LOG_FILE, username, 'api_delete_relationship', f'unexpected error for id {relationship_id}: {e}')
        abort(500)

@app.route('/api/tree_data')
@api_login_required
@family_tree_required
def tree_data():
    """
    Retrieves node and link data for the family tree visualization.
    Supports optional 'start_node' and 'depth' query parameters for lazy loading.
    """
    username = session.get('username', 'api_user')
    start_node_id = request.args.get('start_node')
    depth_str = request.args.get('depth')
    max_depth = None

    if not family_tree: return jsonify({"error": "Family tree service unavailable."}), 503

    if depth_str:
        try:
            max_depth = int(depth_str)
            if max_depth < 0:
                abort(400, description="Depth must be a non-negative integer.")
        except ValueError:
            abort(400, description="Depth must be an integer.")

    log_params = f"start={start_node_id}, depth={max_depth}" if start_node_id else f"full tree requested"
    current_app.logger.info(f"API Tree Data request by '{username}': {log_params}.")
    log_audit(AUDIT_LOG_FILE, username, 'get_tree_data', f'params: {log_params}')

    try:
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
        if user_manager.users and not any(isinstance(user, object) and getattr(user, 'role', None) == 'admin' for user in user_manager.users.values()):
            try:
                first_user_id = next(iter(user_manager.users)) # Get the first user ID
                user = user_manager.users[first_user_id]
                if isinstance(user, object): # Check if it's an object
                    first_username = getattr(user, 'username', 'unknown')
                    app.logger.warning(f"No admin user found. Making first user '{first_username}' (ID: {first_user_id}) an admin for initial setup.")
                    user_manager.set_user_role(first_user_id, 'admin', actor_username='system_startup')
                else:
                    app.logger.error(f"First item in user manager (ID: {first_user_id}) is not a valid user object.")

            except StopIteration:
                 app.logger.info("User file exists but contains no users.")
            except Exception as admin_err:
                 app.logger.error(f"Error setting initial admin role: {admin_err}", exc_info=True)
        elif not user_manager.users:
            app.logger.info("No users found in user file. First registered user may need manual promotion to admin if required.")
    else:
        app.logger.error("User manager failed to initialize. Cannot perform admin check or run application correctly.")
        # Consider exiting if core components fail
        # exit(1)

    port = int(os.environ.get('PORT', 8090))
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.logger.info(f"Starting Flask server on host 0.0.0.0, port {port}, Debug: {debug_mode}")

    # Use app.run for development only
    app.run(debug=debug_mode, host='0.0.0.0', port=port)