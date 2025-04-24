import os
import logging
from functools import wraps
from flask import Flask, request, session, jsonify, abort, current_app
from flask_cors import CORS
from src.user_management import VALID_ROLES # Import VALID_ROLES
from src.relationship import Relationship, VALID_RELATIONSHIP_TYPES, RelationshipModel # Import Relationship for type hints if needed
from src.audit_log import log_audit
from logging.handlers import RotatingFileHandler
from datetime import date, timedelta
from src.user_management import UserManagement  # Import UserManagement class
from src.family_tree import FamilyTree  # Import FamilyTree class
from sqlalchemy.exc import SQLAlchemyError
from fastapi import FastAPI
from werkzeug.exceptions import HTTPException, Unauthorized, InternalServerError, NotFound, BadRequest, Forbidden
from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import sessionmaker
from .services import get_all_users, get_user_by_id, create_user, get_all_people_db, get_person_by_id_db, create_person_db, get_all_events, get_event_by_id, create_event, update_event, delete_event, get_all_sources, get_source_by_id, create_source, update_source, delete_source, get_all_citations, get_citation_by_id, create_citation, update_citation, delete_citation

from .services import get_all_person_attributes, get_person_attribute_by_id, create_person_attribute, update_person_attribute, delete_person_attribute, get_all_relationships, get_relationship_by_id, create_relationship, update_relationship, delete_relationship, get_all_relationship_attributes, get_relationship_attribute_by_id, create_relationship_attribute, update_relationship_attribute, delete_relationship_attribute, get_all_media, get_media_by_id, create_media, update_media, delete_media
app = FastAPI()

# --- Database Setup ---
Base = declarative_base()
db_engine = None
SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'a_very_strong_dev_secret_key_39$@5_v2')
if SECRET_KEY == 'a_very_strong_dev_secret_key_39$@5_v2':
    logging.warning("SECURITY WARNING: Using default Flask secret key. Set FLASK_SECRET_KEY environment variable for production.")

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(APP_ROOT)
LOG_DIR = os.path.join(PROJECT_ROOT, 'logs', 'backend')

AUDIT_LOG_FILE = os.path.join(LOG_DIR, 'audit.log')


# --- Database Engine & Session ---

def create_tables(engine):
    """Creates all tables in the database using the provided engine."""
    Base.metadata.create_all(engine)


def get_db_session_factory(db_engine):
    """
    Create a session factory function to be called when needed, using the provided database engine.
    """
    return sessionmaker(autocommit=False, autoflush=False, bind=db_engine)


def get_db_session(session_factory):
    """
    Creates a database session from the factory, to be used in each request.
    """
    return session_factory()




# --- Configuration ---

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    logging.critical("DATABASE_URL environment variable not set. Exiting.")
    exit(1)

# --- Database Models ---
class User(Base):
    __tablename__ = 'users'
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    password_hash_b64 = Column(String, nullable=False)  # Store password hash as base64 string
    role = Column(String, nullable=False, default='basic')  # Add the role column

    def to_dict(self):
        """Convert the user object to a dictionary."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "password_hash_b64": self.password_hash_b64,
            "role": self.role
        }

class Person(Base):
    __tablename__ = 'people'
    person_id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String)  # Allow NULL for last_name
    nickname = Column(String)
    birth_date = Column(Date)
    death_date = Column(Date)
    gender = Column(String)
    place_of_birth = Column(String)
    place_of_death = Column(String)
    notes = Column(String)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    military_service = Column(String)
    education_history = Column(String)
    occupation_history = Column(String)
    confidence = Column(String)

class RelationshipModel(Base):
    __tablename__ = 'relationships'
    rel_id = Column(Integer, primary_key=True, autoincrement=True)
    person1_id = Column(Integer, ForeignKey('people.person_id'), nullable=False)
    person2_id = Column(Integer, ForeignKey('people.person_id'), nullable=False)
    rel_type = Column(String)
    start_date = Column(Date)
    end_date = Column(Date)
    added_by = Column(String)
    edited_by = Column(String)
    deleted_by = Column(String)
    # Define relationships (optional for SQLAlchemy ORM)
    person1 = relationship("Person", foreign_keys=[person1_id])
    person2 = relationship("Person", foreign_keys=[person2_id])


# --- Logging Setup ---
    
APP_LOG_FILE = os.path.join(LOG_DIR, 'app.log')

# --- Application Setup ---
flask_app = Flask(__name__)
app.secret_key = SECRET_KEY
# Configure session cookie settings for security (optional but recommended)
app.config.update(
    SESSION_COOKIE_SECURE=os.environ.get('FLASK_ENV') == 'production', # Only send cookie over HTTPS in production
    SESSION_COOKIE_HTTPONLY=True,  # Prevent client-side JS access
    SESSION_COOKIE_SAMESITE='Lax', # Mitigate CSRF ('Strict' can be too restrictive)
    # Set permanent session lifetime (used if session.permanent = True)
    PERMANENT_SESSION_LIFETIME=timedelta(days=7) # Example: sessions expire after 7 days
)


# --- Configure CORS ---
# Adjust origins for your specific development and production frontend URLs
CORS(app, supports_credentials=True, origins=["http://localhost:5173", "http://127.0.0.1:5173"])  # Added default Vite port
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
if flask_app.logger.handlers: flask_app.logger.handlers.clear()
flask_app.logger.addHandler(file_handler)
flask_app.logger.addHandler(console_handler)
flask_app.logger.setLevel(logging.DEBUG if os.environ.get('FLASK_DEBUG') == '1' else logging.INFO)

flask_app.logger.info("Flask application starting up...")


# --- Database Session Setup ---
try:
    db_engine = create_engine(DATABASE_URL)
    create_tables(db_engine)
    db_session_factory = get_db_session_factory(db_engine)
    
    db_session = get_db_session(db_session_factory)
    
    flask_app.logger.info("Database engine created successfully.")
except SQLAlchemyError as e:
    flask_app.logger.critical(f"CRITICAL ERROR: Database engine creation failed: {e}", exc_info=True)
    logging.exception("Failed to create database engine")
    exit(1)

# --- Initialize Core Components ---
user_manager = None
family_tree = None
try:   
    user_manager = UserManagement(db_session, AUDIT_LOG_FILE)    
    family_tree = FamilyTree(db_session_factory, AUDIT_LOG_FILE)

    flask_app.logger.info("User manager and family tree initialized successfully.")
except Exception as e:
    flask_app.logger.critical(f"CRITICAL ERROR: Failed to initialize core components: {e}", exc_info=True)
    logging.exception("Failed to initialize flask_application")
    # App might be unusable, endpoints using these will fail later with 503 checks


# --- Initial data ---
def populate_database(db_session):
    """Populates the database with initial data if it's empty."""
    # Check if there are any users
    existing_users = db_session.query(User).count()    
    if existing_users == 0:
        app.logger.info("Database is empty, populating with initial data.")
        # Create an initial admin user
        admin_user = User(username='admin', password_hash_b64=user_manager.hash_password('admin'), role='admin')
        db_session.add(admin_user)        
        
        # Create some initial people
        person1 = Person(first_name='John', last_name='Doe', birth_date=date(1980, 1, 1), user_id=admin_user.user_id)
        person2 = Person(first_name='Jane', last_name='Doe', birth_date=date(1982, 5, 5), user_id=admin_user.user_id)
        db_session.add_all([person1, person2])

        # Create some initial relationships
        relationship1 = RelationshipModel(person1_id=person1.person_id, person2_id=person2.person_id, rel_type='married')
        db_session.add_all([relationship1])
        
        db_session.commit()
        flask_app.logger.info("Database populated with initial data.")


# --- Validation Helper ---
def validate_person_data(data, is_edit=False):
    """
    Validates incoming data for creating or updating a Person.

    Checks for required fields (first_name on create), valid date formats
    (YYYY-MM-DD), ensures death date is not before birth date, and validates
    gender values.

    Args:
        data (dict): The dictionary containing person data from the request.
        is_edit (bool): Flag indicating if this is for an edit operation
                        (doesn't require first_name if not provided).

    Returns:
        dict: A dictionary of validation errors, keyed by field name.
              Returns an empty dictionary if validation passes.
    """
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
             flask_app.logger.warning(f"Date comparison validation error: {date_err}", exc_info=True)
             # Add a user-friendly error message
             errors['date_comparison'] = 'Invalid date format for comparison.'

    # Gender validation
    if gender and gender not in ['Male', 'Female', 'Other']:
         errors['gender'] = 'Invalid gender value. Use Male, Female, or Other.'

    return errors

# --- Decorators ---
def api_login_required(f):
    """
    Decorator for API endpoints requiring user authentication.

    Checks if 'user_id' is present in the session. If not, returns a 401
    Unauthorized response. Also checks if core components (user_manager,
    family_tree) are initialized, returning 503 Service Unavailable if not.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check session *before* checking component initialization
        if 'user_id' not in session:
            current_app.logger.warning(f"API Authentication Required: Endpoint '{request.endpoint}' accessed without login (IP: {request.remote_addr}).")
            log_audit(AUDIT_LOG_FILE, 'anonymous', 'api_access_denied', f'login required for API endpoint {request.endpoint}')            
            # Use abort to trigger the 401 handler
            abort(401, description="Authentication required.")

        # Check if core components initialized properly *after* confirming login attempt
        if not user_manager or not family_tree:
             current_app.logger.error(f"API Service Unavailable: Endpoint '{request.endpoint}' accessed but core components not initialized.")
             # Use abort to trigger the 503 handler
             abort(503, description="Service temporarily unavailable. Please try again later.")
        return f(*args, **kwargs)
    return decorated_function

def api_admin_required(f):
    """
    Decorator for API endpoints requiring administrator privileges.

    Chains `api_login_required` first. Checks if the 'user_role' in the
    session is 'admin'. If not, returns a 403 Forbidden response.
    """
    @wraps(f)
    @api_login_required # Chain decorators: ensures login and component checks first
    def decorated_function(*args, **kwargs):
        user_role = session.get("user_role")
        username = session.get('username', 'unknown_user') # Get username for logging
        if user_role != 'admin':
            current_app.logger.warning(f"API Authorization Failed: User '{username}' (Role: {user_role}) attempted to access admin endpoint '{request.endpoint}'.")
            log_audit(AUDIT_LOG_FILE, username, 'api_access_denied', f'admin required (role: {user_role}) for API endpoint {request.endpoint}')
            # Use abort to trigger the 403 handler
            abort(403, description="Administrator privileges required.")
        return f(*args, **kwargs)
    return decorated_function

# --- Custom Error Handlers ---
@app.errorhandler(BadRequest) # 400
def handle_bad_request(error: BadRequest):
    """Handles 400 Bad Request errors, often due to parsing or validation."""
    description = getattr(error, 'description', "Invalid request format or data.")    
    current_app.logger.warning(f"API Bad Request (400): {description} - Endpoint: {request.endpoint}, IP: {request.remote_addr}")
    # Structure the response based on whether description is detailed validation errors
    response_data = {"error": "Bad Request", "message": description}
    if isinstance(description, dict): # Assume validation errors
        response_data = {"error": "Validation failed", "details": description}
    return jsonify(response_data), 400

@app.errorhandler(Unauthorized) # 401
def handle_unauthorized(error: Unauthorized):
    """Handles 401 Unauthorized errors."""
    description = getattr(error, 'description', "Authentication required.")
    current_app.logger.warning(f"API Unauthorized (401): {description} - Endpoint: {request.endpoint}, IP: {request.remote_addr}")
    return jsonify({"error": "Unauthorized", "message": description}), 401

@app.errorhandler(Forbidden) # 403
def handle_forbidden(error: Forbidden):
    """Handles 403 Forbidden errors."""
    description = getattr(error, 'description', "Permission denied.")
    current_app.logger.warning(f"API Forbidden (403): {description} - Endpoint: {request.endpoint}, User: {session.get('username', 'anonymous')}, IP: {request.remote_addr}")
    return jsonify({"error": "Forbidden", "message": description}), 403

@app.errorhandler(NotFound) # 404
def handle_not_found(error: NotFound):
    """Handles 404 Not Found errors."""
    current_app.logger.warning(f"API Not Found (404): Path '{request.path}' - IP: {request.remote_addr}, Referrer: {request.referrer}")
    return jsonify({"error": "Not Found", "message": f"The requested URL '{request.path}' was not found on this server."}), 404

@app.errorhandler(InternalServerError) # 500
def handle_internal_server_error(error: InternalServerError):
    """Handles 500 Internal Server errors."""
    # Log the original exception if available
    original_exception = getattr(error, 'original_exception', None)
    current_app.logger.error(
        f"API Internal Server Error (500): Endpoint: {request.endpoint}, User: {session.get('username', 'anonymous')}, IP: {request.remote_addr}",
        exc_info=original_exception or error # Log traceback
    )
    # Do not expose internal error details to the client
    return jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred. Please try again later."}), 500

@app.errorhandler(503) # Service Unavailable
def handle_service_unavailable(error):
    """Handles 503 Service Unavailable errors."""
    description = getattr(error, 'description', "Service temporarily unavailable.")
    current_app.logger.error(f"API Service Unavailable (503): {description} - Endpoint: {request.endpoint}, IP: {request.remote_addr}")
    return jsonify({"error": "Service Unavailable", "message": description}), 503

# --- API Authentication Routes ---
@app.route('/api/login', methods=['POST'])
def api_login():
    """
    API Endpoint: POST /api/login
    Authenticates a user via username and password. Sets session cookies on success.
    """
    username_for_log = 'unknown' # Initialize for logging in case of early failure
    try:
        if not user_manager:
            current_app.logger.error("API Login attempt failed: User manager not initialized.")
            abort(503, description="Authentication service unavailable.")

        data = request.get_json()
        if not data:
             abort(400, description="Request body must be valid JSON.")
        if not data.get('username') or not data.get('password'):            
            abort(400, description="Username and password are required.")

        username = data['username'].strip()
        username_for_log = username # Update for logging
        password = data['password']

        current_app.logger.debug(f"API Login attempt for username: '{username}'")

        user = user_manager.login_user(username, password)

        if user:
            # Regenerate session ID upon login to prevent session fixation
            session.permanent = True # Make session persistent (e.g., browser close)
            # app.permanent_session_lifetime is set globally in app config now
            session.clear() # Clear old session data before setting new
            session['user_id'] = user.user_id
            session['username'] = user.username
            session['user_role'] = user.role
            current_app.logger.info(f"API Login Successful: User '{username}' (Role: {user.role}) logged in from IP {request.remote_addr}.")
            # Audit log handled by user_manager
            return jsonify({"message": "Login successful!", "user": {"id": user.id, "username": user.username, "role": user.role}}), 200
        else:
            # User not found or invalid password (already logged by user_manager)
            current_app.logger.warning(f"API Login Failed for username '{username}' from IP {request.remote_addr}.")
            abort(401, description="Invalid username or password.")

    except HTTPException as http_ex:
        # Re-raise HTTP exceptions (like abort(400), abort(401), abort(503))
        raise http_ex
    except Exception as e:
        # Catch *other* unexpected errors during login process
        current_app.logger.exception(f"API Login Error: Unexpected error during login for username '{username_for_log}'.")
        log_audit(AUDIT_LOG_FILE, username_for_log, 'api_login', f'unexpected error: {e}')
        abort(500) # Let the 500 handler provide generic message


@app.route('/api/register', methods=['POST'])
def api_register():
    """
    API Endpoint: POST /api/register
    Registers a new user with a 'basic' role.
    """
    username_for_log = 'unknown'
    try:
        if not user_manager:
            current_app.logger.error("API Register attempt failed: User manager not initialized.")
            abort(503, description="Registration service unavailable.")

        data = request.get_json()
        if not data:
             abort(400, description="Request body must be valid JSON.")
        if not data.get('username') or not data.get('password'):
            abort(400, description="Username and password are required.")

        username = data['username'].strip()
        username_for_log = username
        password = data['password']

        if not username: abort(400, description="Username cannot be empty.")
        if not password: abort(400, description="Password cannot be empty.") # Add password complexity checks here if desired

        current_app.logger.debug(f"API Register attempt for username: '{username}'")

        # Check if username exists (case-insensitive)
        if user_manager.find_user_by_username(username):
            current_app.logger.warning(f"API Register Failed: Username '{username}' already taken.")
            log_audit(AUDIT_LOG_FILE, username, 'api_register_attempt', 'failure - username exists')
            # Use 409 Conflict for existing resource
            return jsonify({"error": f"Username '{username}' is already taken."}), 409
        
        user = user_manager.register_user(username, password) # Default role 'basic'

        if user:
            current_app.logger.info(f"API Registration Successful: User '{username}' (Role: {user.role}) registered from IP {request.remote_addr}.")           
            # Audit log handled by user_manager
            return jsonify({"message": "Registration successful!", "user": {"id": user.user_id, "username": user.username, "role": user.role}}), 201 # 201 Created
        else:
            # Registration failed for other reasons (logged within user_manager)
            current_app.logger.error(f"API Registration Failed: Unexpected error during registration for username '{username}'. Check user_manager logs.")
            log_audit(AUDIT_LOG_FILE, username, 'api_register', 'failure - unexpected error in user_manager')
            abort(500, description="Registration failed due to an internal error.")

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        current_app.logger.exception(f"API Register Error: Unexpected error during registration for username '{username_for_log}'.")
        log_audit(AUDIT_LOG_FILE, username_for_log, 'api_register', f'unexpected error: {e}')
        abort(500)

@app.route('/api/logout', methods=['POST'])
@api_login_required
def api_logout():
    """
    API Endpoint: POST /api/logout
    Logs out the current user and clears the server-side session.
    """
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
        # Less likely to have errors here, but catch just in case
        current_app.logger.exception(f"API Logout Error: Unexpected error during logout for user '{username}'.")
        log_audit(AUDIT_LOG_FILE, username, 'api_logout', f'unexpected error: {e}')
        abort(500)


@app.route('/api/session', methods=['GET'])
def api_get_session():
    """
    API Endpoint: GET /api/session
    Retrieves the current authentication status and user information if logged in.
    """
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
    """
    API Endpoint: POST /api/request-password-reset
    Initiates the password reset process by sending an email with a reset link.
    """
    email_for_log = 'unknown'
    try:
        if not user_manager:
            current_app.logger.error("API Password Reset Request failed: User manager not initialized.")
            abort(503, description="Password reset service unavailable.")

        data = request.get_json()
        if not data:
             abort(400, description="Request body must be valid JSON.")
        if 'email' not in data:
            abort(400, description="Email address is required.")

        email = data['email'].strip()
        email_for_log = email
        if not email: # Basic validation
             abort(400, description="Email address cannot be empty.")

        current_app.logger.info(f"API Password Reset Request received for email: {email}")

        # Call the combined request/send logic in user_manager
        # This function now handles logging internally and always returns True to the caller
        # unless there's a critical internal error (like token generation failure).
        success = user_manager.request_password_reset(email)

        if not success:
             # This indicates an internal error occurred (logged by user_manager)
             abort(500, description="Could not process password reset request due to an internal error.")

        # Always return a generic success message to prevent email enumeration
        log_audit(AUDIT_LOG_FILE, email, 'request_password_reset', f'processed (outcome hidden from user)')
        return jsonify({"message": "If an account exists for this email, a password reset link has been sent."}), 200

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        current_app.logger.exception(f"API Request Password Reset Error: Unexpected error for email '{email_for_log}'.")
        log_audit(AUDIT_LOG_FILE, email_for_log, 'request_password_reset', f'unexpected internal error: {e}')
        abort(500)


@app.route('/api/reset-password/<token>', methods=['POST'])
def api_reset_password(token):
    """
    API Endpoint: POST /api/reset-password/<token>
    Resets the user's password using a valid, non-expired token.
    """
    token_for_log = token[:8] + '...' if token else 'none'
    try:
        if not user_manager:
            current_app.logger.error("API Password Reset failed: User manager not initialized.")
            abort(503, description="Password reset service unavailable.")

        data = request.get_json()
        if not data:
             abort(400, description="Request body must be valid JSON.")
        if 'new_password' not in data:
            abort(400, description="New password is required.")

        new_password = data['new_password']
        # Add password complexity validation here
        if not new_password or len(new_password) < 8:
            abort(400, description="New password cannot be empty and must be at least 8 characters long.")

        current_app.logger.info(f"API Password Reset attempt with token: {token_for_log}")

        success = user_manager.reset_password(token, new_password)

        if success:
            current_app.logger.info(f"Password successfully reset using token: {token_for_log}")
            # Audit log handled by user_manager
            return jsonify({"message": "Password reset successfully."}), 200
        else:
            # Failure logged by user_manager (invalid token or internal error)
            current_app.logger.warning(f"Password reset failed for token: {token_for_log}")
            log_audit(AUDIT_LOG_FILE, f"token:{token_for_log}", 'reset_password', 'failure - invalid/expired token or internal error')
            abort(400, description="Invalid or expired password reset token, or password could not be reset.")

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        current_app.logger.exception(f"API Reset Password Error: Unexpected error for token '{token_for_log}'.")
        log_audit(AUDIT_LOG_FILE, f"token:{token_for_log}", 'reset_password', f'unexpected error: {e}')
        abort(500)


# --- Admin User Management API Endpoints ---

@app.route('/api/users', methods=['GET'])
@api_admin_required
def api_get_all_users():
    """
    API Endpoint: GET /api/users (Admin Only)
    Retrieves a list of all registered users (excluding sensitive info).
    """
    admin_username = session.get('username', 'admin_user')
    current_app.logger.info(f"API Get All Users requested by admin '{admin_username}'.")
    try:
        if not user_manager: abort(503, description="User management service unavailable.")

        all_users = user_manager.get_all_users()
        all_users_list = []        
        for user in all_users:
            user_data = {"id": user.user_id, "username": user.username, "role": user.role}
            all_users_list.append(user_data)

        return jsonify(all_users_list), 200
    except HTTPException as e:
        print(e)
        raise http_ex
    except Exception as e:
        current_app.logger.exception(f"API Get All Users Error: Failed for admin '{admin_username}'.")
        abort(500)


@app.route('/api/users/<user_id>', methods=['DELETE'])
@api_admin_required
def api_admin_delete_user(user_id):
    """
    API Endpoint: DELETE /api/users/<user_id> (Admin Only)
    Deletes the specified user.
    """
    admin_username = session.get('username', 'admin_user')
    current_app.logger.info(f"API Delete User attempt by admin '{admin_username}' for user ID: {user_id}.")

    try:
        if not user_manager: abort(503, description="User management service unavailable.")

        # Prevent admin from deleting themselves
        if session.get('user_id') == user_id:
            current_app.logger.warning(f"Admin '{admin_username}' attempted self-deletion (ID: {user_id}).")
            log_audit(AUDIT_LOG_FILE, admin_username, 'api_delete_user', f'failure - admin self-deletion attempt for {user_id}')
            abort(403, description="Administrators cannot delete their own account.")

        user_to_delete = db_session.query(User).filter(User.user_id == user_id).first()
        if not user_to_delete:
            current_app.logger.warning(f"API Delete User Failed: User ID '{user_id}' not found by admin '{admin_username}'.")
            abort(404, description="User not found.")

        deleted_username = user_to_delete.username # Get username for logging before deletion
        success = user_manager.delete_user(user_id, actor_username=admin_username)

        if success:
            current_app.logger.info(f"API Delete User Successful: User '{deleted_username}' (ID: {user_id}) deleted by admin '{admin_username}'.")
            # Audit log handled by user_manager.delete_user
            return '', 204 # No Content
        else:
            # Should not happen if user was found
            current_app.logger.error(f"API Delete User Failed: delete_user returned False for ID '{user_id}', admin '{admin_username}'.")
            abort(500, description="Failed to delete user due to an internal error.")

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        current_app.logger.exception(f"API Delete User Error: Unexpected error for admin '{admin_username}', user ID '{user_id}'.")
        log_audit(AUDIT_LOG_FILE, admin_username, 'api_delete_user', f'unexpected error for id {user_id}: {e}')
        abort(500)


@app.route('/api/users/<user_id>/role', methods=['PUT'])
@api_admin_required
def api_admin_set_user_role(user_id):
    """
    API Endpoint: PUT /api/users/<user_id>/role (Admin Only)
    Changes the role of the specified user. Expects {"role": "new_role"} in the body.
    """
    admin_username = session.get('username', 'admin_user')
    current_app.logger.info(f"API Set User Role attempt by admin '{admin_username}' for user ID: {user_id}.")

    try:
        if not user_manager: abort(503, description="User management service unavailable.")

        data = request.get_json()
        if not data: abort(400, description="Request body must be valid JSON.")
        if 'role' not in data: abort(400, description="New role is required in request body.")

        new_role = data['role'].strip()
        if new_role not in VALID_ROLES:
            abort(400, description=f"Invalid role '{new_role}'. Valid roles are: {', '.join(VALID_ROLES)}")

        user_to_modify = db_session.query(User).filter(User.user_id == user_id).first()
        if not user_to_modify:
            current_app.logger.warning(f"API Set Role Failed: User ID '{user_id}' not found by admin '{admin_username}'.")
            abort(404, description="User not found.")
        # Optional: Prevent changing own role?

        # if session.get('user_id') == user_id:
        #     abort(403, description="Administrators cannot change their own role via this endpoint.")

        original_role = user_to_modify.role # Get role before change
        success = user_manager.set_user_role(user_id, new_role, actor_username=admin_username)

        if success:
            # Fetch user again to confirm change and return updated info         
            updated_user = user_manager.find_user_by_id(user_id)
            current_app.logger.info(f"API Set Role Successful: Role for user '{user_to_modify.username}' (ID: {user_id}) changed from '{original_role}' to '{new_role}' by admin '{admin_username}'.")
            # Audit log handled by user_manager.set_user_role
            return jsonify({"user_id": user_id, "username": updated_user.username, "role": updated_user.role}), 200
        else:
            # Failure logged within user_manager (e.g., save error)
            # Check if role was already the target role (set_user_role now returns True in this case)
            # This else block might only be reached on internal errors now.
            current_app.logger.error(f"API Set Role Failed: set_user_role returned False for ID '{user_id}', admin '{admin_username}'.")
            abort(500, description="Failed to set user role due to an internal error.")

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        current_app.logger.exception(f"API Set Role Error: Unexpected error for admin '{admin_username}', user ID '{user_id}'.")
        log_audit(AUDIT_LOG_FILE, admin_username, 'api_set_user_role', f'unexpected error for id {user_id}: {e}')
        abort(500)


# --- API Family Tree Data Routes ---
@app.route('/api/people', methods=['GET'])
@api_login_required
def get_all_people():
    """API endpoint to get a list of all people."""
    username = session.get('username', 'api_user')
    current_app.logger.debug(f"API Get All People requested by '{username}'.")
    if not family_tree: abort(503, description="Family tree service unavailable.")
    try:
        # Get all people from the database
        people = db_session.query(Person).all()
        # Convert people to a list of dictionaries
        people_list = []
        for person in people:
            person_dict = {"id": person.person_id, "first_name": person.first_name, "last_name":person.last_name, "birth_date": str(person.birth_date), "death_date": str(person.death_date), "notes": person.notes}
            people_list.append(person_dict)

        current_app.logger.info(f"API Get All People: Retrieved {len(people_list)} people for user '{username}'.")

        return jsonify(people_list)
    except Exception as e:
        current_app.logger.exception(f"API Get All People Error: Failed to retrieve people data for user '{username}'.")
        abort(500)
        
@app.route('/api/people/<person_id>', methods=['GET'])
@api_login_required
def get_person(person_id):
    """API endpoint to get details for a specific person."""
    username = session.get('username', 'api_user')
    current_app.logger.debug(f"API Get Person requested by '{username}' for ID: {person_id}.")
    if not family_tree: abort(503, description="Family tree service unavailable.")
    try:
        # Get person from the database
        person = db_session.query(Person).filter(Person.person_id == person_id).first()

        if person:
            current_app.logger.info(f"API Get Person: Retrieved person (ID: {person_id}) for user '{username}'.")
            person_dict = {
                "id": person.person_id,
                "first_name": person.first_name,
                "last_name": person.last_name,
                "birth_date": str(person.birth_date) if person.birth_date else None,
                "death_date": str(person.death_date) if person.death_date else None,
                "notes": person.notes}
            return jsonify(person_dict)
        else:
            current_app.logger.warning(f"API Get Person Failed: Person ID '{person_id}' not found for user '{username}'.")
            abort(404, description="Person not found.")
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        current_app.logger.exception(f"API Get Person Error: Failed to retrieve person data for ID '{person_id}', user '{username}'.")
        abort(500)

@app.route('/api/people', methods=['POST'])
@api_login_required
def api_add_person():
    """API endpoint to add a new person."""
    username = session.get('username', 'api_user')
    current_app.logger.debug(f"API Add Person attempt by '{username}'.")
    if not family_tree: abort(503, description="Family tree service unavailable.")
    try:
        data = request.get_json()
        if not data: abort(400, description="Request body must be valid JSON.")

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

        try:
            # Create a new Person object
            new_person = Person(first_name=first_name, last_name=last_name, nickname=nickname, birth_date=dob, death_date=dod, gender=gender, place_of_birth=pob, place_of_death=pod, notes=notes, user_id=session.get('user_id'))
            # Add the new Person to the session
            db_session.add(new_person)
            db_session.commit()
            current_app.logger.info(f"API Add Person Successful: Person (ID: {new_person.person_id}) added by '{username}'.")
            log_audit(AUDIT_LOG_FILE, username, 'api_add_person', f'success - id: {new_person.person_id}, name: {new_person.first_name}')

            # Return the added person data as JSON
            return jsonify({"id": new_person.person_id, "first_name": new_person.first_name, "last_name": new_person.last_name, "birth_date": str(new_person.birth_date), "death_date": str(new_person.death_date), "notes": new_person.notes}), 201
        except IntegrityError as e:
            db_session.rollback()
            current_app.logger.error(f"API Add Person Failed: Integrity error while adding person: {e}.")
            abort(409, description="Failed to add person due to a database integrity error.")
        except Exception as e:
            abort(500, description="Failed to add person due to an internal error after validation.")

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        current_app.logger.exception(f"API Add Person Error: Unexpected error for user '{username}'.")
        log_audit(AUDIT_LOG_FILE, username, 'api_add_person', f'unexpected error: {e}')
        abort(500)

@app.route('/api/people/<person_id>', methods=['PUT'])
@api_login_required
def api_edit_person(person_id):
    """API endpoint to edit an existing person."""
    username = session.get('username', 'api_user')
    current_app.logger.debug(f"API Edit Person attempt by '{username}' for ID: {person_id}.")
    if not family_tree: abort(503, description="Family tree service unavailable.")
    try:
        data = request.get_json()
        if not data: abort(400, description="Request body must be valid JSON.")

        person = db_session.query(Person).filter(Person.person_id == person_id).first()
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

        # Update fields from updated_data
        for key, value in updated_data.items():
            if hasattr(person, key):
                setattr(person, key, value)

        try:
            db_session.commit()

            current_app.logger.info(f"API Edit Person Successful: Person (ID: {person_id}) updated by '{username}'.")
            # Return the updated person data as JSON
            person_dict = {
                "id": person.person_id,
                "first_name": person.first_name,
                "last_name": person.last_name,
                "birth_date": str(person.birth_date) if person.birth_date else None,
                "death_date": str(person.death_date) if person.death_date else None,
                "notes": person.notes}
            return jsonify(person_dict), 200
        except IntegrityError as e:
            db_session.rollback()
            current_app.logger.error(f"API Edit Person Failed: Integrity error while updating person: {e}.")
            return jsonify({"message": "No effective changes detected or update failed internally."}), 200

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        current_app.logger.exception(f"API Edit Person Error: Unexpected error for user '{username}', ID '{person_id}'.")
        log_audit(AUDIT_LOG_FILE, username, 'api_edit_person', f'unexpected error for id {person_id}: {e}')
        abort(500)

@app.route('/api/people/<person_id>', methods=['DELETE'])
@api_login_required
def api_delete_person(person_id):
    """API endpoint to delete a person."""
    username = session.get('username', 'api_user')
    current_app.logger.debug(f"API Delete Person attempt by '{username}' for ID: {person_id}.")
    if not family_tree: abort(503, description="Family tree service unavailable.")
    try:
        person = db_session.query(Person).filter(Person.person_id == person_id).first()
        if not person:
            current_app.logger.warning(f"API Delete Person Failed: Person ID '{person_id}' not found for user '{username}'.")
            abort(404, description="Person not found.")
        
        db_session.delete(person)
        db_session.commit()
        success = True

        person_name = person.first_name
        if success:
            current_app.logger.info(f"API Delete Person Successful: Person '{person_name}' (ID: {person_id}) deleted by '{username}'.")
            return '', 204
        else:
            current_app.logger.error(f"API Delete Person Failed: delete_person returned False for ID '{person_id}', user '{username}' after person was found.")
            abort(500, description="Failed to delete person due to an internal error.")

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        current_app.logger.exception(f"API Delete Person Error: Unexpected error for user '{username}', ID '{person_id}'.")
        log_audit(AUDIT_LOG_FILE, username, 'api_delete_person', f'unexpected error for id {person_id}: {e}')
        abort(500)


@app.route('/api/relationships', methods=['GET'])
@api_login_required
def get_all_relationships():
    """API endpoint to get a list of all relationships."""
    username = session.get('username', 'api_user')
    current_app.logger.debug(f"API Get All Relationships requested by '{username}'.")
    if not family_tree: abort(503, description="Family tree service unavailable.")
    try:
        # Get all relationships from the database
        relationships = db_session.query(RelationshipModel).all()
        # Convert relationships to a list of dictionaries
        relationships_list = []
        for rel in relationships:
            rel_dict = {"id": rel.rel_id, "person1_id": rel.person1_id, "person2_id": rel.person2_id, "relationship_type": rel.rel_type, "start_date": str(rel.start_date), "end_date": str(rel.end_date)}
            relationships_list.append(rel_dict)


        current_app.logger.info(f"API Get All Relationships: Retrieved {len(relationships_list)} relationships for user '{username}'.")
        return jsonify(relationships_list)
    except Exception as e:
        current_app.logger.exception(f"API Get All Relationships Error: Failed to retrieve relationships data for user '{username}'.")
        abort(500)

@app.route('/api/relationships', methods=['POST'])
@api_login_required
def api_add_relationship():
    """API endpoint to add a new relationship."""
    username = session.get('username', 'api_user')
    current_app.logger.debug(f"API Add Relationship attempt by '{username}'.")
    if not family_tree: abort(503, description="Family tree service unavailable.")
    try:
        data = request.get_json()
        if not data: abort(400, description="Request body must be valid JSON.")

        # Map frontend keys to backend expected keys
        person1_id = data.get('person1')
        person2_id = data.get('person2')
        rel_type = data.get('relationshipType')
        attributes = data.get('attributes', {})

        errors = {}
        if not person1_id: errors['person1'] = 'Person 1 ID is required.'
        if not person2_id: errors['person2'] = 'Person 2 ID is required.'
        if not rel_type: errors['relationshipType'] = 'Relationship type is required.'
        if person1_id and person1_id == person2_id:
            errors['person2'] = 'Cannot add relationship to the same person.'
        if rel_type and rel_type not in VALID_RELATIONSHIP_TYPES:
            current_app.logger.warning(f"API Add Relationship: Received potentially non-standard relationship type '{rel_type}' from user '{username}'.")
            # Decide if this is an error or just a warning
            # errors['relationshipType'] = f"Invalid relationship type '{rel_type}'. Valid types: {', '.join(VALID_RELATIONSHIP_TYPES)}"

        person1, person2 = None, None
        if person1_id and 'person1' not in errors:
            person1 = family_tree.find_person(person_id=person1_id)
            person1 = db_session.query(Person).filter(Person.person_id == person1_id).first()
            if not person1: errors['person1'] = f"Person with ID {person1_id} not found."
        if person2_id and 'person2' not in errors:
            person2 = family_tree.find_person(person_id=person2_id)
            person2 = db_session.query(Person).filter(Person.person_id == person2_id).first()
            if not person2: errors['person2'] = f"Person with ID {person2_id} not found."
        if errors:
            current_app.logger.warning(f"API Add Relationship Validation Failed for user '{username}': {errors}")
            abort(400, description=errors)

        relationship = family_tree.add_relationship(
            person1_id=person1_id, person2_id=person2_id,
            relationship_type=rel_type, attributes=attributes, added_by=username
        )    

        try:
            new_relationship = RelationshipModel(person1_id=person1_id, person2_id=person2_id, rel_type=rel_type)
            db_session.add(new_relationship)
            db_session.commit()
            p1_name = person1.first_name if person1 else person1_id
            p2_name = person2.first_name if person2 else person2_id
            current_app.logger.info(f"API Add Relationship Successful: Relationship '{rel_type}' (ID: {new_relationship.rel_id}) added between '{p1_name}' and '{p2_name}' by '{username}'.")
            # Return the added relationship data as JSON
            return jsonify({"id": new_relationship.rel_id, "person1_id": new_relationship.person1_id, "person2_id": new_relationship.person2_id, "relationship_type": new_relationship.rel_type, "start_date": str(new_relationship.start_date), "end_date": str(new_relationship.end_date)}), 201

        except IntegrityError as e:
            db_session.rollback()
            current_app.logger.error(f"API Add Relationship Failed: Integrity error while adding relationship: {e}.")
            abort(409, description="Failed to add relationship due to a database integrity error.")

        else:
            current_app.logger.error(f"API Add Relationship Failed: family_tree.add_relationship returned None for user '{username}' after validation.")
            abort(409, description="Failed to add relationship. It might already exist or an internal error occurred.")

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        current_app.logger.exception(f"API Add Relationship Error: Unexpected error for user '{username}'.")
        log_audit(AUDIT_LOG_FILE, username, 'api_add_relationship', f'unexpected error: {e}')
        abort(500)

@app.route('/api/relationships/<relationship_id>', methods=['PUT'])
@api_login_required
def api_edit_relationship(relationship_id):
    """API endpoint to edit an existing relationship."""
    username = session.get('username', 'api_user')
    current_app.logger.debug(f"API Edit Relationship attempt by '{username}' for ID: {relationship_id}.")
    if not family_tree: abort(503, description="Family tree service unavailable.")
    try:
        data = request.get_json()
        if not data: abort(400, description="Request body must be valid JSON.")


        rel = db_session.query(RelationshipModel).filter(RelationshipModel.rel_id == relationship_id).first()
        if not rel:
            current_app.logger.warning(f"API Edit Relationship Failed: Relationship ID '{relationship_id}' not found for user '{username}'.")
            abort(404, description="Relationship not found.")

        errors = {}
        # Map frontend keys to backend expected keys for validation
        new_type = data.get('relationshipType')
        new_p1_id = data.get('person1')
        new_p2_id = data.get('person2')
        new_attributes = data.get('attributes')

        if 'relationshipType' in data:
            if not new_type or not str(new_type).strip():
                errors['relationshipType'] = 'Relationship type cannot be empty.'
            elif new_type not in VALID_RELATIONSHIP_TYPES:
                 current_app.logger.warning(f"API Edit Relationship: Received potentially non-standard relationship type '{new_type}' from user '{username}' for rel ID {relationship_id}.")
                 # errors['relationshipType'] = f"Invalid relationship type '{new_type}'. Valid types: {', '.join(VALID_RELATIONSHIP_TYPES)}"

        if 'attributes' in data and not isinstance(new_attributes, dict):
            errors['attributes'] = 'Attributes must be a valid JSON object (dictionary).'

        # Validate person IDs if they are being changed
        if 'person1' in data:
             if not family_tree.find_person(person_id=new_p1_id): errors['person1'] = f"Person with ID {new_p1_id} not found."
        if 'person2' in data:
             if not family_tree.find_person(person_id=new_p2_id): errors['person2'] = f"Person with ID {new_p2_id} not found."

        # Check for self-relationship if both persons are being potentially updated
        check_p1 = new_p1_id if 'person1' in data else rel.person1_id
        check_p2 = new_p2_id if 'person2' in data else rel.person2_id
        if check_p1 == check_p2:
             errors['person2'] = 'Cannot set relationship to the same person.'


        if errors:
            current_app.logger.warning(f"API Edit Relationship Validation Failed for user '{username}', ID '{relationship_id}': {errors}")
            abort(400, description=errors)

        # Prepare update data dict using backend keys
        updated_data = {}
        if 'relationshipType' in data: updated_data['rel_type'] = str(new_type).strip()
        if 'attributes' in data: updated_data['attributes'] = new_attributes
        if 'person1' in data: updated_data['person1_id'] = new_p1_id
        if 'person2' in data: updated_data['person2_id'] = new_p2_id

        if not updated_data:
            current_app.logger.info(f"API Edit Relationship: No update data provided by '{username}' for ID '{relationship_id}'.")
            return jsonify({"message": "No update data provided, no changes made."}), 200

        original_type = rel.rel_type
        original_p1 = rel.person1_id
        original_p2 = rel.person2_id
        success = family_tree.edit_relationship(relationship_id, updated_data, edited_by=username)
        if updated_data:
            # Update fields from updated_data
            for key, value in updated_data.items():
                if hasattr(rel, key):
                    setattr(rel, key, value)

        try:
            db_session.commit()
            current_app.logger.info(f"API Edit Relationship Successful: Relationship (ID: {relationship_id}) updated by '{username}'.")
             # Return the updated relationship data as JSON
            return jsonify({"id": rel.rel_id, "person1_id": rel.person1_id, "person2_id": rel.person2_id, "relationship_type": rel.rel_type, "start_date": str(rel.start_date), "end_date": str(rel.end_date)}), 200

        except IntegrityError as e:
            db_session.rollback()
            current_app.logger.error(f"API Edit Relationship Failed: Integrity error while updating relationship: {e}.")
            return jsonify({"message": "Failed to update relationship due to a database integrity error."}), 409
        except Exception as e:
            return jsonify({"message": "No effective changes detected or update failed internally."}), 200

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        current_app.logger.exception(f"API Edit Relationship Error: Unexpected error for user '{username}', ID '{relationship_id}'.")
        log_audit(AUDIT_LOG_FILE, username, 'api_edit_relationship', f'unexpected error for id {relationship_id}: {e}')
        abort(500)


@app.route('/api/relationships/<relationship_id>', methods=['DELETE'])
@api_login_required
def api_delete_relationship(relationship_id):
    """API endpoint to delete a relationship."""
    username = session.get('username', 'api_user')
    current_app.logger.debug(f"API Delete Relationship attempt by '{username}' for ID: {relationship_id}.")
    if not family_tree: abort(503, description="Family tree service unavailable.")
    try:
        rel = db_session.query(RelationshipModel).filter(RelationshipModel.rel_id == relationship_id).first()
        if not rel:
            current_app.logger.warning(f"API Delete Relationship Failed: Relationship ID '{relationship_id}' not found for user '{username}'.")
            abort(404, description="Relationship not found.")

        rel_type = rel.rel_type
        p1_id = rel.person1_id
        p2_id = rel.person2_id

        db_session.delete(rel)
        db_session.commit()
        success = family_tree.delete_relationship(relationship_id, deleted_by=username)

        if success:
            current_app.logger.info(f"API Delete Relationship Successful: Relationship '{rel_type}' (ID: {relationship_id}) between '{p1_id}' and '{p2_id}' deleted by '{username}'.")
            return '', 204
        else:
            current_app.logger.error(f"API Delete Relationship Failed: delete_relationship returned False for ID '{relationship_id}', user '{username}'.")
            abort(500, description="Failed to delete relationship due to an internal error.")

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        current_app.logger.exception(f"API Delete Relationship Error: Unexpected error for user '{username}', ID '{relationship_id}'.")
        log_audit(AUDIT_LOG_FILE, username, 'api_delete_relationship', f'unexpected error for id {relationship_id}: {e}')
        abort(500)

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

    if not family_tree: abort(503, description="Family tree service unavailable.")

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
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        current_app.logger.exception(f"API Tree Data Error: Failed to generate tree data for user '{username}'. Params: {log_params}.")
        log_audit(AUDIT_LOG_FILE, username, 'get_tree_data', f'error generating data: {e}')
        abort(500)

        

# --- Main Execution ---
if __name__ == '__main__':
   # Check for admin user only if user_manager initialized successfully
   if user_manager:
       # check if there are initial users
       try:            
           # Check if ANY admin user exists
           has_admin = any(isinstance(user, object) and getattr(user, 'role', None) == 'admin'
                           for user in user_manager.users.values())

           if user_manager.users and not has_admin:
               first_user_id = next(iter(user_manager.users)) # Get the first user ID
               user = user_manager.users[first_user_id]                
                if isinstance(user, object):
                    first_username = getattr(user, 'username', 'unknown')                    
                    # user_manager.set_user_role(first_user_id, 'admin', actor_username='system_startup')
                    app.logger.warning(f"No admin user found. The first user is '{first_username}' (ID: {first_user_id}).")                                           
            elif not user_manager.users:
                app.logger.info("No users found in user file. First registered user may need manual promotion to admin if required.")
            else:
                app.logger.info("Admin user(s) found.")
             
            with db_session_factory() as session:
                populate_database(session)                
                


        except StopIteration:
            app.logger.info("User file exists but contains no users.")
        except Exception as admin_err:
            app.logger.error(f"Error during initial admin check/promotion: {admin_err}", exc_info=True)
   else:
       app.logger.error("User manager failed to initialize. Cannot perform admin check or run application correctly.")
       # Consider exiting if core components fail
       # exit(1)

    
    port = int(os.environ.get('PORT', 8090))
    # Read FLASK_DEBUG from environment variable for consistency
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    flask_app.logger.info(f"Starting Flask server on host 0.0.0.0, port {port}, Debug: {debug_mode}")

    # Use app.run for development only
    # For production, use a WSGI server like Gunicorn or Waitress
    #app.run(debug=debug_mode, host='0.0.0.0', port=port)
    
@app.get("/api/users")
def get_users():
    """Get all users."""
    db = get_db_session(db_session_factory)
    users = get_all_users(db)
    return users

@app.get("/api/users/{id}")
def get_user(id: int):
    """Get a specific user."""
    db = get_db_session(db_session_factory)
    user = get_user_by_id(db, id)
    return user

@app.post("/api/users")
def create_user():
    """Create a new user."""
    db = get_db_session(db_session_factory)
    user = create_user(db, request.get_json())
    return user

@app.get("/api/people")
def get_people():
    """Get all people."""
    db = get_db_session(db_session_factory)
    return get_all_people_db(db)

@app.get("/api/people/{id}")
def get_person_api(id: int):
    """Get a specific person."""
    db = get_db_session(db_session_factory)
    return get_person_by_id_db(db, id)

@app.post("/api/people")
def create_person_api():
    db = get_db_session(db_session_factory)
    return create_person_db(db, request.get_json())

@app.get("/api/person_attributes")
def get_person_attributes_api():
    """Get all person attributes."""
    db = get_db_session(db_session_factory)
    return get_all_person_attributes(db)

@app.get("/api/person_attributes/{id}")
def get_person_attribute_api(id: int):
    """Get a specific person attribute."""
    db = get_db_session(db_session_factory)
    return get_person_attribute_by_id(db, id)

@app.post("/api/person_attributes")
def create_person_attribute_api():
    """Create a new person attribute."""
    db = get_db_session(db_session_factory)
    return create_person_attribute(db, request.get_json())

@app.put("/api/person_attributes/{id}")
def update_person_attribute_api(id: int):
    """Update an existing person attribute."""
    db = get_db_session(db_session_factory)
    return update_person_attribute(db, id, request.get_json())

@app.delete("/api/person_attributes/{id}")
def delete_person_attribute_api(id: int):
    """Delete a person attribute."""
    db = get_db_session(db_session_factory)
    return delete_person_attribute(db, id)

@app.get("/api/relationships")
def get_relationships_api():
    """Get all relationships."""
    db = get_db_session(db_session_factory)
    return get_all_relationships(db)

@app.get("/api/relationships/{id}")
def get_relationship_api(id: int):
    """Get a specific relationship."""
    db = get_db_session(db_session_factory)
    return get_relationship_by_id(db, id)

@app.post("/api/relationships")
def create_relationship_api():
    """Create a new relationship."""
    db = get_db_session(db_session_factory)
    return create_relationship(db, request.get_json())

@app.put("/api/relationships/{id}")
def update_relationship_api(id: int):
    """Update an existing relationship."""
    db = get_db_session(db_session_factory)
    return update_relationship(db, id, request.get_json())

@app.delete("/api/relationships/{id}")
def delete_relationship_api(id: int):
    """Delete a relationship."""
    db = get_db_session(db_session_factory)
    return delete_relationship(db, id)

@app.get("/api/relationship_attributes")
def get_relationship_attributes_api():
    """Get all relationship attributes."""
    db = get_db_session(db_session_factory)
    return get_all_relationship_attributes(db)

@app.get("/api/relationship_attributes/{id}")
def get_relationship_attribute_api(id: int):
    """Get a specific relationship attribute."""
    db = get_db_session(db_session_factory)
    return get_relationship_attribute_by_id(db, id)

@app.post("/api/relationship_attributes")
def create_relationship_attribute_api():
    """Create a new relationship attribute."""
    db = get_db_session(db_session_factory)
    return create_relationship_attribute(db, request.get_json())

@app.put("/api/relationship_attributes/{id}")
def update_relationship_attribute_api(id: int):
    """Update an existing relationship attribute."""
    db = get_db_session(db_session_factory)
    return update_relationship_attribute(db, id, request.get_json())

@app.delete("/api/relationship_attributes/{id}")
def delete_relationship_attribute_api(id: int):
    """Delete a relationship attribute."""
    db = get_db_session(db_session_factory)
    return delete_relationship_attribute(db, id)

@app.get("/api/media")
def get_media_api():
    """Get all media."""
    db = get_db_session(db_session_factory)
    return get_all_media(db)

@app.get("/api/media/{id}")
def get_media_attribute_api(id: int):
    """Get a specific media."""
    db = get_db_session(db_session_factory)
    return get_media_by_id(db, id)

@app.post("/api/media")
def create_media_api():
    """Create a new media."""
    db = get_db_session(db_session_factory)
    return create_media(db, request.get_json())

@app.put("/api/media/{id}")
def update_media_api(id: int):
    """Update an existing media."""
    db = get_db_session(db_session_factory)
    return update_media(db, id, request.get_json())
@app.delete("/api/media/{id}")
def delete_media_api(id: int):
    """Delete a media."""
    db = get_db_session(db_session_factory)
    return delete_media(db, id)

@app.get("/api/events")
def get_events_api():
    """Get all events."""
    db = get_db_session(db_session_factory)
    return get_all_events(db)

@app.get("/api/events/{id}")
def get_event_api(id: int):
    """Get a specific event."""
    db = get_db_session(db_session_factory)
    return get_event_by_id(db, id)

@app.post("/api/events")
def create_event_api():
    """Create a new event."""
    db = get_db_session(db_session_factory)
    return create_event(db, request.get_json())

@app.put("/api/events/{id}")
def update_event_api(id: int):
    """Update an existing event."""
    db = get_db_session(db_session_factory)
    return update_event(db, id, request.get_json())

@app.delete("/api/events/{id}")
def delete_event_api(id: int):
    """Delete an event."""
    db = get_db_session(db_session_factory)
    return delete_event(db, id)

@app.get("/api/sources")
def get_sources_api():
    """Get all sources."""
    db = get_db_session(db_session_factory)
    return get_all_sources(db)

@app.get("/api/sources/{id}")
def get_source_api(id: int):
    """Get a specific source."""
    db = get_db_session(db_session_factory)
    return get_source_by_id(db, id)

@app.post("/api/sources")
def create_source_api():
    """Create a new source."""
    db = get_db_session(db_session_factory)
    return create_source(db, request.get_json())

@app.put("/api/sources/{id}")
def update_source_api(id: int):
    """Update an existing source."""
    db = get_db_session(db_session_factory)
    return update_source(db, id, request.get_json())
@app.delete("/api/sources/{id}")
def delete_source_api(id: int):
    """Delete a source."""
    db = get_db_session(db_session_factory)
    return delete_source(db, id) 

@app.get("/api/citations")
def get_citations_api():
    """Get all citations."""
    db = get_db_session(db_session_factory)
    return get_all_citations(db)

@app.get("/api/citations/{id}")
def get_citation_api(id: int):
    """Get a specific citation."""
    db = get_db_session(db_session_factory)
    return get_citation_by_id(db, id)

@app.post("/api/citations")
def create_citation_api():
    """Create a new citation."""
    db = get_db_session(db_session_factory)
    return create_citation(db, request.get_json())

@app.put("/api/citations/{id}")
def update_citation_api(id: int):
    """Update an existing citation."""
    db = get_db_session(db_session_factory)
    return update_citation(db, id, request.get_json())
@app.delete("/api/citations/{id}")
def delete_citation_api(id: int):
    """Delete a citation."""
    db = get_db_session(db_session_factory)
    return delete_citation(db, id)
