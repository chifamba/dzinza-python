# backend/app/main.py
import os
import logging
from functools import wraps
from flask import Flask, request, session, jsonify, abort, g, current_app # Use Flask's g for request context
from flask_cors import CORS
from datetime import date, timedelta, datetime
from logging.handlers import RotatingFileHandler
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, NoResultFound
from sqlalchemy.orm import sessionmaker, Session as DbSession
from sqlalchemy import create_engine
from werkzeug.exceptions import HTTPException, Unauthorized, InternalServerError, NotFound, BadRequest, Forbidden
from typing import Optional, List, Any

# --- Service Imports ---
# Import functions from services using their actual names
# Assuming these are correctly implemented in services.py
try:
    from app.services import (
        get_all_users, get_user_by_id, create_user, # User services
        get_all_people_db, get_person_by_id_db, create_person_db, # Person services (add update/delete if available)
        # update_person_db, delete_person_db, # Uncomment if implemented in services.py
        get_all_events, get_event_by_id, create_event, update_event, delete_event, # Event services
        get_all_sources, get_source_by_id, create_source, update_source, delete_source, # Source services
        get_all_citations, get_citation_by_id, create_citation, update_citation, delete_citation, # Citation services
        search_people, get_person_relationships_and_attributes, # Search/Detail services
        get_descendants, get_ancestors, # Tree traversal services (ensure these exist in services.py)
        get_partial_tree, # Keep if implemented in services.py
        # get_extended_family, get_related, get_branch # Removed - Not found in services.py previously
        get_all_person_attributes, get_person_attribute as get_person_attribute_by_id, # Person Attribute services
        create_person_attribute, update_person_attribute, delete_person_attribute,
        get_all_relationships, get_relationship_by_id, create_relationship, update_relationship, delete_relationship, # Relationship services
        get_all_relationship_attributes, get_relationship_attribute as get_relationship_attribute_by_id, # Relationship Attribute services
        create_relationship_attribute, update_relationship_attribute, delete_relationship_attribute,
        get_all_media, get_media_by_id, create_media, update_media, delete_media # Media services
    )
except ImportError as e:
    # Log which specific import failed if possible
    logging.critical(f"Failed to import function(s) from app.services: {e}. Ensure all listed functions exist in services.py.", exc_info=True)
    raise # Re-raise to prevent app from starting incorrectly

# --- Model Imports ---
try:
    from app.models.base import Base # Import shared Base
    from app.models.user import User
    from app.models.person import Person
    from app.models.relationship import Relationship as RelationshipModel # Alias is good
    # Import other models if needed directly (though usually accessed via services)
except ImportError as e:
    logging.critical(f"Failed to import models: {e}", exc_info=True)
    raise

# --- Other Imports ---
try:
    from app.db_init import populate_database
    # Import from src (Assuming these exist and are needed, e.g., for UserManagement in login)
    from src.user_management import UserManagement, VALID_ROLES # Keep if UserManagement is used in login
    # from src.family_tree import FamilyTree # Remove if FamilyTree logic is fully within services.py
    from src.relationship import VALID_RELATIONSHIP_TYPES # Keep if used for validation constants
    from src.audit_log import log_audit # Keep for auditing
except ImportError as e:
    logging.critical(f"Failed to import from db_init or src: {e}", exc_info=True)
    raise

# --- Configuration & Constants ---
SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'a_very_strong_dev_secret_key_39$@5_v2')
if SECRET_KEY == 'a_very_strong_dev_secret_key_39$@5_v2':
    logging.warning("SECURITY WARNING: Using default Flask secret key. Set FLASK_SECRET_KEY environment variable for production.")

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(APP_ROOT)
LOG_DIR = os.path.join(PROJECT_ROOT, 'logs', 'backend')
AUDIT_LOG_FILE = os.path.join(LOG_DIR, 'audit.log')
APP_LOG_FILE = os.path.join(LOG_DIR, 'app.log')
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    logging.critical("DATABASE_URL environment variable not set. Exiting.")
    exit(1)

# --- Application Setup ---
app = Flask(__name__) # Use Flask app instance
app.secret_key = SECRET_KEY
app.config.update(
    SESSION_COOKIE_SECURE=os.environ.get('FLASK_ENV') == 'production',
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax', # Use 'Strict' if possible, 'Lax' is a good default
    PERMANENT_SESSION_LIFETIME=timedelta(days=7)
)

# --- Configure CORS ---
# Allow requests from the typical Vite dev server port
CORS(app, supports_credentials=True, origins=["http://localhost:5173", "http://127.0.0.1:5173"])
logging.info("CORS configured for development origins.")

# --- Configure Logging ---
os.makedirs(LOG_DIR, exist_ok=True)
log_formatter = logging.Formatter('%(asctime)s %(levelname)-8s [%(name)s] %(message)s [in %(pathname)s:%(lineno)d]')
# App Log (File)
file_handler = RotatingFileHandler(APP_LOG_FILE, maxBytes=1024*1024*5, backupCount=5, encoding='utf-8')
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)
# Console Log
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.DEBUG if os.environ.get('FLASK_DEBUG') == '1' else logging.INFO)

# Configure Flask's logger
app.logger.handlers.clear() # Clear default handlers if any
app.logger.addHandler(file_handler)
app.logger.addHandler(console_handler)
app.logger.setLevel(logging.DEBUG if os.environ.get('FLASK_DEBUG') == '1' else logging.INFO)

# Redirect root logger output (used by SQLAlchemy etc.) to Flask's logger handlers
# root_logger = logging.getLogger()
# if root_logger.handlers: root_logger.handlers.clear()
# root_logger.addHandler(file_handler)
# root_logger.addHandler(console_handler)
# root_logger.setLevel(logging.DEBUG if os.environ.get('FLASK_DEBUG') == '1' else logging.INFO)
# OR more simply:
logging.basicConfig(level=logging.DEBUG if os.environ.get('FLASK_DEBUG') == '1' else logging.INFO, handlers=[file_handler, console_handler])


app.logger.info("Application starting up...")

# --- Database Engine & Session ---
db_engine = None
db_session_factory = None
try:
    db_engine = create_engine(DATABASE_URL)
    # Create tables if they don't exist
    Base.metadata.create_all(bind=db_engine)
    # Create a configured "Session" class
    db_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    app.logger.info("Database engine and session factory created successfully.")
except SQLAlchemyError as e:
    app.logger.critical(f"CRITICAL ERROR: Database engine creation failed: {e}", exc_info=True)
    exit(1)
except NameError as e:
    app.logger.critical(f"CRITICAL ERROR: Database Base model not defined or imported correctly: {e}", exc_info=True)
    exit(1)

# --- Flask DB Session Management ---
@app.before_request
def create_session():
    """Create a database session for the current request context."""
    if not db_session_factory:
        app.logger.error("Database session factory not initialized before request.")
        # Abort might be too early here, consider how to handle startup failure
        abort(503, description="Database connection not available.")
    g.db = db_session_factory() # Store the session in Flask's 'g' object
    app.logger.debug(f"DB Session created for request {request.path}")

@app.teardown_request
def close_session(exception=None):
    """Close the database session at the end of the request."""
    db = g.pop('db', None) # Get session from g, removing it
    if db is not None:
        if exception:
            # Rollback on error before closing
            app.logger.warning(f"Rolling back DB session due to exception: {exception}")
            try:
                db.rollback()
            except Exception as rb_exc:
                app.logger.error(f"Error during session rollback: {rb_exc}", exc_info=True)
        # Always close the session
        try:
            db.close()
            app.logger.debug(f"DB Session closed for request {request.path}")
        except Exception as close_exc:
            app.logger.error(f"Error closing DB session: {close_exc}", exc_info=True)
    elif exception:
         # Log the exception even if no db session was found in g
         app.logger.error(f"Request ended with exception but no DB session found in g: {exception}", exc_info=True)


# --- Initial data population ---
# Use a context manager to ensure the session is closed after population
try:
    with db_session_factory() as initial_session:
        populate_database(initial_session) # Use the imported function
except Exception as e:
    app.logger.error(f"Error during initial database population: {e}", exc_info=True)

# --- Decorators ---
def api_login_required(f):
    """Decorator to ensure user is logged in via Flask session."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            app.logger.warning(f"API Authentication Required: Endpoint '{request.endpoint}' accessed without login (IP: {request.remote_addr}).")
            # Use the imported log_audit function
            log_audit(AUDIT_LOG_FILE, 'anonymous', 'api_access_denied', f'login required for API endpoint {request.endpoint}')
            abort(401, description="Authentication required.")
        # Check if db session is available via g (should be due to before_request)
        if 'db' not in g or g.db is None:
             app.logger.error(f"API Service Unavailable: Endpoint '{request.endpoint}' accessed but DB session not found in g.")
             abort(503, description="Service temporarily unavailable. Please try again later.")
        return f(*args, **kwargs)
    return decorated_function

def api_admin_required(f):
    """Decorator to ensure user is logged in and has 'admin' role."""
    @wraps(f)
    @api_login_required # Ensures login and db checks first
    def decorated_function(*args, **kwargs):
        user_role = session.get("user_role")
        username = session.get('username', 'unknown_user')
        if user_role != 'admin':
            app.logger.warning(f"API Authorization Failed: User '{username}' (Role: {user_role}) attempted to access admin endpoint '{request.endpoint}'.")
            # Use the imported log_audit function
            log_audit(AUDIT_LOG_FILE, username, 'api_access_denied', f'admin required (role: {user_role}) for API endpoint {request.endpoint}')
            abort(403, description="Administrator privileges required.")
        return f(*args, **kwargs)
    return decorated_function

# --- Validation Helper ---
def validate_person_data(data: dict, is_edit: bool = False) -> dict:
    """Validates incoming person data. Returns a dict of errors if any."""
    errors = {}
    first_name = data.get('first_name')
    dob_str = data.get('birth_date')
    dod_str = data.get('death_date')
    gender = data.get('gender')

    # Validate required fields on create
    if not is_edit and (first_name is None or not str(first_name).strip()):
        errors['first_name'] = 'First name is required.'
    # Validate non-empty if provided on edit
    elif 'first_name' in data and (first_name is None or not str(first_name).strip()):
        errors['first_name'] = 'First name cannot be empty if provided.'

    # Validate dates
    dob, dod = None, None
    if dob_str:
        try:
            # Handle empty string explicitly
            if dob_str == "": dob = None
            else: dob = date.fromisoformat(dob_str)
        except (ValueError, TypeError):
            errors['birth_date'] = 'Invalid date format (YYYY-MM-DD).'
    if dod_str:
        try:
             # Handle empty string explicitly
            if dod_str == "": dod = None
            else: dod = date.fromisoformat(dod_str)
        except (ValueError, TypeError):
            errors['death_date'] = 'Invalid date format (YYYY-MM-DD).'

    # Validate date logic if both are valid dates
    if dob and dod and 'birth_date' not in errors and 'death_date' not in errors:
        if dod < dob:
            errors['date_comparison'] = 'Date of Death cannot be before Date of Birth.'

    # Validate gender if provided
    if gender and gender not in ['Male', 'Female', 'Other']:
        errors['gender'] = 'Invalid gender. Use Male, Female, or Other.'

    # Add more validation as needed (e.g., length limits)

    return errors

# --- Custom Error Handlers (Flask Style) ---
@app.errorhandler(BadRequest) # Catch specific Werkzeug exception
@app.errorhandler(400)
def handle_bad_request(error):
    # Extract description safely
    description = getattr(error, 'description', "Invalid request format or data.")
    app.logger.warning(f"API Bad Request (400): {description} - Endpoint: {request.endpoint}, IP: {request.remote_addr}")
    # Prepare JSON response
    response_data = {"error": "Bad Request", "message": description}
    if isinstance(description, dict): # Handle validation error dicts
        response_data = {"error": "Validation failed", "details": description}
    response = jsonify(response_data)
    response.status_code = 400
    return response

@app.errorhandler(Unauthorized)
@app.errorhandler(401)
def handle_unauthorized(error):
    description = getattr(error, 'description', "Authentication required.")
    app.logger.warning(f"API Unauthorized (401): {description} - Endpoint: {request.endpoint}, IP: {request.remote_addr}")
    response = jsonify({"error": "Unauthorized", "message": description})
    response.status_code = 401
    return response

@app.errorhandler(Forbidden)
@app.errorhandler(403)
def handle_forbidden(error):
    description = getattr(error, 'description', "Permission denied.")
    app.logger.warning(f"API Forbidden (403): {description} - Endpoint: {request.endpoint}, User: {session.get('username', 'anonymous')}, IP: {request.remote_addr}")
    response = jsonify({"error": "Forbidden", "message": description})
    response.status_code = 403
    return response

@app.errorhandler(NotFound)
@app.errorhandler(404)
def handle_not_found(error):
    app.logger.warning(f"API Not Found (404): Path '{request.path}' - IP: {request.remote_addr}, Referrer: {request.referrer}")
    response = jsonify({"error": "Not Found", "message": f"The requested URL '{request.path}' was not found on this server."})
    response.status_code = 404
    return response

@app.errorhandler(SQLAlchemyError) # Catch database errors specifically
def handle_database_error(error):
    app.logger.error(
        f"API Database Error: Endpoint: {request.endpoint}, User: {session.get('username', 'anonymous')}, IP: {request.remote_addr}",
        exc_info=error # Log the specific SQLAlchemy error
    )
    # Avoid exposing detailed DB errors to the client
    response = jsonify({"error": "Database Error", "message": "A database error occurred."})
    response.status_code = 500
    # Rollback might have already happened in teardown, but ensure it happens if teardown fails
    db = g.get('db', None)
    if db:
        try:
            db.rollback()
            db.close() # Ensure closed if teardown fails
            g.pop('db', None) # Remove from g
        except Exception as rb_exc:
            app.logger.error(f"Error during rollback/close in SQLAlchemy error handler: {rb_exc}")
    return response

@app.errorhandler(InternalServerError) # Catch generic 500s
@app.errorhandler(500)
def handle_internal_server_error(error):
    # Log the original exception if available
    original_exception = getattr(error, 'original_exception', error)
    app.logger.error(
        f"API Internal Server Error (500): Endpoint: {request.endpoint}, User: {session.get('username', 'anonymous')}, IP: {request.remote_addr}",
        exc_info=original_exception
    )
    response = jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred."})
    response.status_code = 500
    return response

@app.errorhandler(503)
def handle_service_unavailable(error):
    description = getattr(error, 'description', "Service temporarily unavailable.")
    app.logger.error(f"API Service Unavailable (503): {description} - Endpoint: {request.endpoint}, IP: {request.remote_addr}")
    response = jsonify({"error": "Service Unavailable", "message": description})
    response.status_code = 503
    return response


# --- Health Check Endpoint ---
@app.route('/health', methods=['GET'])
def health_check():
    """Basic health check endpoint including database connection status and version."""
    db_session = None
    try:
        # Attempt to get a database session
        if not db_session_factory:
            app.logger.error("Health check: Database session factory not initialized.")
            return jsonify({"status": "error", "database": "Database session factory not initialized"}), 503

        db_session = db_session_factory()

        # Execute a simple query to check connection and get DB version
        # For PostgreSQL, SELECT version(); is common
        db_version_result = db_session.execute(text("SELECT version();")).scalar()

        # If we reach here, the database connection and basic query were successful
        return jsonify({
            "status": "ok",
            "database": "connected",
            "database_version": db_version_result
        }), 200

    except Exception as e:
        # Catch any exception during database connection or query
        app.logger.error(f"Health check failed: Database connection or query failed: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "database": "connection_failed",
            "message": f"Database connection or query failed: {e}"
        }), 503 # Use 503 Service Unavailable for dependency issues

    finally:
        # Ensure the database session is closed
        if db_session:
            try:
                db_session.close()
                app.logger.debug("Health check: Database session closed.")
            except Exception as close_exc:
                app.logger.error(f"Health check: Error closing DB session: {close_exc}", exc_info=True)



# --- API Routes (Flask Style) ---

@app.route('/api/login', methods=['POST'])
def api_login():
    """Handles user login using Flask session."""
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        abort(400, description="Username and password required.")

    username = data['username']
    password = data['password']

    # Instantiate UserManagement here, passing the request's DB session
    # Ensure UserManagement is adapted to accept a session or works stateless
    try:
        # Assuming UserManagement needs audit log file path
        user_manager = UserManagement(g.db, AUDIT_LOG_FILE) # Pass session from g
        user = user_manager.login_user(username, password)

        if user:
            session.permanent = True # Make session last longer than browser session
            session['user_id'] = user.id # Use the correct attribute name (id from Base)
            session['username'] = user.username
            session['user_role'] = user.role
            # Log successful login audit
            log_audit(AUDIT_LOG_FILE, username, 'login_success', f'User {username} logged in successfully.')
            app.logger.info(f"User '{username}' logged in successfully.")
            # Return user info (without password hash)
            return jsonify({
                "message": "Login successful!",
                "user": user.to_dict() # Use to_dict method if available
            }), 200
        else:
            # Log failed login attempt audit
            log_audit(AUDIT_LOG_FILE, username, 'login_failed', f'Invalid credentials for user {username}.')
            app.logger.warning(f"Invalid login attempt for user '{username}'.")
            abort(401, description="Invalid credentials.")
    except Exception as e:
        # Catch potential errors during login process (e.g., DB error handled by generic handler)
        app.logger.error(f"Error during login process for user {username}: {e}", exc_info=True)
        abort(500, description="An error occurred during login.")


@app.route('/api/logout', methods=['POST'])
@api_login_required # Ensure user is logged in to log out
def api_logout():
    """Handles user logout by clearing the Flask session."""
    username = session.get('username', 'unknown_user')
    user_id = session.get('user_id')

    # Clear the session
    session.clear()

    # Log logout audit
    log_audit(AUDIT_LOG_FILE, username, 'logout_success', f'User {username} (ID: {user_id}) logged out.')
    app.logger.info(f"User '{username}' (ID: {user_id}) logged out.")
    return jsonify({"message": "Logout successful!"}), 200

@app.route('/api/session', methods=['GET'])
def api_check_session():
    """Checks if a user session is active."""
    if 'user_id' in session:
        # Optionally refresh session lifetime on activity
        session.permanent = True
        # Return user info if logged in
        user_info = {
            "id": session['user_id'],
            "username": session.get('username'),
            "role": session.get('user_role')
        }
        return jsonify({"logged_in": True, "user": user_info}), 200
    else:
        return jsonify({"logged_in": False}), 200


# --- User Management Endpoints (Admin Only) ---

@app.route('/api/users', methods=['GET'])
@api_admin_required
def get_users():
    """Get all users (Admin only)."""
    try:
        users = get_all_users(g.db) # Use session from g
        # Convert User objects to dicts for JSON response
        return jsonify([u.to_dict() for u in users]) # Use to_dict method
    except Exception as e:
        # Error handled by generic handlers, logging happens there
        # Re-raise or let it propagate
        raise e # Let the error handlers catch it

@app.route('/api/users/<int:user_id>', methods=['GET'])
@api_admin_required
def get_user(user_id: int):
    """Get a specific user (Admin only)."""
    try:
        user = get_user_by_id(g.db, user_id) # Use session from g
        if not user:
            abort(404, "User not found")
        return jsonify(user.to_dict()) # Use to_dict method
    except HTTPException: # Re-raise HTTP exceptions like 404
        raise
    except Exception as e:
        raise e # Let the error handlers catch it

# --- Implement POST /users, PUT /users/{id}/role, DELETE /users/{id} similarly ---
# Remember to use g.db for the session

# --- People Endpoints ---
@app.route('/api/people', methods=['GET'])
@api_login_required
def get_people():
    """Get all people with pagination, filtering, sorting, and field selection."""
    try:
        # Extract and validate query parameters
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        order_by = request.args.get('order_by', 'id', type=str)
        order_direction = request.args.get('order_direction', 'asc', type=str)
        name = request.args.get('name', type=str)
        gender = request.args.get('gender', type=str)
        birth_date_str = request.args.get('birth_date')
        death_date_str = request.args.get('death_date')
        fields_str = request.args.get('fields')

        if page < 1 or page_size < 1:
            abort(400, description="Page and page_size must be positive integers.")
        if order_direction not in ('asc', 'desc'):
            abort(400, description="order_direction must be 'asc' or 'desc'.")

        # Validate date formats
        birth_date, death_date = None, None
        if birth_date_str:
            try: birth_date = date.fromisoformat(birth_date_str)
            except ValueError: abort(400, description="Invalid birth_date format (YYYY-MM-DD).")
        if death_date_str:
            try: death_date = date.fromisoformat(death_date_str)
            except ValueError: abort(400, description="Invalid death_date format (YYYY-MM-DD).")

        # Parse fields
        fields = fields_str.split(',') if fields_str else None

        # Call the service function with the request's DB session
        result = get_all_people_db(
            db=g.db, # Use session from g
            page=page, page_size=page_size, order_by=order_by,
            order_direction=order_direction, name=name, gender=gender,
            birth_date=birth_date, death_date=death_date, fields=fields
        )
        # Service function should return a serializable dict
        return jsonify(result)
    except HTTPException: # Re-raise HTTP exceptions like 400, 404
        raise
    except Exception as e:
        # Logged and handled by generic error handlers
        raise e

@app.route('/api/people/<int:person_id>', methods=['GET'])
@api_login_required
def get_person_api(person_id: int):
    """Get a specific person by ID."""
    try:
        fields_str = request.args.get('fields')
        fields = fields_str.split(',') if fields_str else None

        person_data = get_person_by_id_db(g.db, person_id, fields=fields) # Use session from g
        if not person_data:
            # Service function might raise HTTPException(404) or return None
            abort(404, "Person not found")
        # Service function should return a serializable dict
        return jsonify(person_data)
    except HTTPException:
        raise
    except Exception as e:
        raise e

@app.route('/api/people', methods=['POST'])
@api_login_required
def create_person_api():
    """Create a new person."""
    data = request.get_json()
    if not data:
        abort(400, description="Request body must be valid JSON.")

    # Validate incoming data
    validation_errors = validate_person_data(data, is_edit=False)
    if validation_errors:
        # Abort with validation details
        abort(400, description=validation_errors)

    # Add creator user_id from session
    data['created_by'] = session.get('user_id')
    username = session.get('username', 'unknown')

    try:
        new_person = create_person_db(g.db, data) # Use session from g
        # Log audit trail
        log_audit(AUDIT_LOG_FILE, username, 'create_person', f'success - id: {new_person.id}')
        app.logger.info(f"User '{username}' created person ID {new_person.id}")
        # Return the created person data using to_dict
        return jsonify(new_person.to_dict()), 201
    except HTTPException as he: # Catch potential 409 Conflict from service
         db = g.get('db')
         if db: db.rollback() # Ensure rollback on handled HTTP errors during creation
         raise he
    except IntegrityError as ie: # Catch potential DB integrity errors
         db = g.get('db')
         if db: db.rollback()
         app.logger.error(f"Integrity error creating person: {ie}", exc_info=True)
         abort(409, description="Failed to create person due to data conflict (e.g., unique constraint).")
    except Exception as e:
        # Rollback should happen in teardown_request or SQLAlchemyError handler
        app.logger.error(f"Unexpected error creating person: {e}", exc_info=True)
        abort(500) # Let generic handler manage response


# --- Implement PUT /people/{id} and DELETE /people/{id} similarly ---
# Remember to use g.db, handle validation, logging, auditing, and exceptions

# --- Person Attributes Endpoints ---
@app.route("/api/person_attributes", methods=['GET'])
@api_login_required
def get_all_person_attributes_api():
    """Get all person attributes with pagination and filtering."""
    try:
        # Extract and validate query parameters
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        order_by = request.args.get('order_by', 'id', type=str)
        order_direction = request.args.get('order_direction', 'asc', type=str)
        key = request.args.get('key')
        value = request.args.get('value')
        person_id_str = request.args.get('person_id') # Get as string first
        fields_str = request.args.get('fields')
        include_person_str = request.args.get('include_person', 'false')

        if page < 1 or page_size < 1:
            abort(400, description="Page and page_size must be positive integers.")
        if order_direction not in ('asc', 'desc'):
            abort(400, description="order_direction must be 'asc' or 'desc'.")

        # Validate person_id if provided
        person_id = None
        if person_id_str:
            try: person_id = int(person_id_str)
            except ValueError: abort(400, description="Invalid person_id format.")

        fields = fields_str.split(',') if fields_str else None
        include_person = include_person_str.lower() == 'true'

        result = get_all_person_attributes(
            db=g.db, page=page, page_size=page_size, order_by=order_by,
            order_direction=order_direction, key=key, value=value,
            person_id=person_id, fields=fields, include_person=include_person
        )
        return jsonify(result)
    except HTTPException:
        raise
    except Exception as e:
        raise e

@app.route("/api/person_attributes/<int:person_attribute_id>", methods=['GET'])
@api_login_required
def get_person_attribute_api(person_attribute_id: int):
    """Get a specific person attribute by ID."""
    try:
        fields_str = request.args.get('fields')
        fields = fields_str.split(',') if fields_str else None
        include_person_str = request.args.get('include_person', 'false')
        include_person = include_person_str.lower() == 'true'

        result = get_person_attribute_by_id(
            db=g.db, person_attribute_id=person_attribute_id,
            fields=fields, include_person=include_person
        )
        if result is None:
            abort(404, description="Person attribute not found.")
        return jsonify(result) # Service returns dict or ORM object converted by service
    except HTTPException:
        raise
    except Exception as e:
        raise e

# --- Implement POST, PUT, DELETE for /person_attributes similarly ---

# --- Relationship Endpoints ---
@app.route("/api/relationships", methods=['GET'])
@api_login_required
def get_relationships_api():
    """Get all relationships with pagination and filtering."""
    try:
        # Extract and validate query parameters
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        order_by = request.args.get('order_by', 'id', type=str)
        order_direction = request.args.get('order_direction', 'asc', type=str)
        rel_type = request.args.get('type') # Use 'type' as query param name
        person1_id_str = request.args.get('person1_id')
        person2_id_str = request.args.get('person2_id')
        fields_str = request.args.get('fields')
        include_person1 = request.args.get('include_person1', 'false').lower() == 'true'
        include_person2 = request.args.get('include_person2', 'false').lower() == 'true'

        if page < 1 or page_size < 1:
            abort(400, description="Page and page_size must be positive integers.")
        if order_direction not in ('asc', 'desc'):
            abort(400, description="order_direction must be 'asc' or 'desc'.")

        # Validate IDs if provided
        person1_id = None
        if person1_id_str:
            try: person1_id = int(person1_id_str)
            except ValueError: abort(400, description="Invalid person1_id format.")
        person2_id = None
        if person2_id_str:
            try: person2_id = int(person2_id_str)
            except ValueError: abort(400, description="Invalid person2_id format.")

        fields = fields_str.split(',') if fields_str else None

        # Remove 'request' argument from service call, Flask request is global
        result = get_all_relationships(
            db=g.db, page=page, page_size=page_size, order_by=order_by,
            order_direction=order_direction, type=rel_type, # Pass rel_type as 'type'
            person1_id=person1_id, person2_id=person2_id, fields=fields,
            include_person1=include_person1, include_person2=include_person2
        )
        return jsonify(result)
    except HTTPException:
        raise
    except Exception as e:
        raise e

# --- Implement GET /relationships/{id}, POST, PUT, DELETE similarly ---

# --- Relationship Attributes Endpoints ---
@app.route("/api/relationship_attributes", methods=['GET'])
@api_login_required
def get_relationship_attributes_api():
    """Get all relationship attributes with pagination and filtering."""
    try:
        # Extract and validate query parameters
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        order_by = request.args.get('order_by', 'id', type=str)
        order_direction = request.args.get('order_direction', 'asc', type=str)
        key = request.args.get('key')
        value = request.args.get('value')
        relationship_id_str = request.args.get('relationship_id')
        fields_str = request.args.get('fields')
        include_relationship = request.args.get('include_relationship', 'false').lower() == 'true'

        if page < 1 or page_size < 1:
            abort(400, description="Page and page_size must be positive integers.")
        if order_direction not in ('asc', 'desc'):
            abort(400, description="order_direction must be 'asc' or 'desc'.")

        # Validate ID if provided
        relationship_id = None
        if relationship_id_str:
            try: relationship_id = int(relationship_id_str)
            except ValueError: abort(400, description="Invalid relationship_id format.")

        fields = fields_str.split(',') if fields_str else None

        result = get_all_relationship_attributes(
            db=g.db, page=page, page_size=page_size, order_by=order_by,
            order_direction=order_direction, key=key, value=value,
            relationship_id=relationship_id, fields=fields,
            include_relationship=include_relationship
        )
        return jsonify(result)
    except HTTPException:
        raise
    except Exception as e:
        raise e

# --- Implement GET /relationship_attributes/{id}, POST, PUT, DELETE similarly ---

# --- Media Endpoints ---
@app.route("/api/media", methods=['GET'])
@api_login_required
def get_media_api():
    """Get all media with pagination and filtering."""
    try:
        # Extract and validate query parameters
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        order_by = request.args.get('order_by', 'id', type=str)
        order_direction = request.args.get('order_direction', 'asc', type=str)
        file_name = request.args.get('file_name')
        file_type = request.args.get('file_type')
        description = request.args.get('description')
        fields_str = request.args.get('fields')

        if page < 1 or page_size < 1:
            abort(400, description="Page and page_size must be positive integers.")
        if order_direction not in ('asc', 'desc'):
            abort(400, description="order_direction must be 'asc' or 'desc'.")

        fields = fields_str.split(',') if fields_str else None

        result = get_all_media(
            db=g.db, page=page, page_size=page_size, order_by=order_by,
            order_direction=order_direction, file_name=file_name,
            file_type=file_type, description=description, fields=fields
        )
        return jsonify(result)
    except HTTPException:
        raise
    except Exception as e:
        raise e

# --- Implement GET /media/{id}, POST, PUT, DELETE similarly ---

# --- Event Endpoints ---
@app.route("/api/events", methods=['GET'])
@api_login_required
def get_events_api():
    """Get all events with pagination and filtering."""
    try:
        # Extract and validate query parameters
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        order_by = request.args.get('order_by', 'id', type=str)
        order_direction = request.args.get('order_direction', 'asc', type=str)
        event_type = request.args.get('type') # Use 'type' as query param
        place = request.args.get('place')
        description = request.args.get('description')
        fields_str = request.args.get('fields')

        if page < 1 or page_size < 1:
            abort(400, description="Page and page_size must be positive integers.")
        if order_direction not in ('asc', 'desc'):
            abort(400, description="order_direction must be 'asc' or 'desc'.")

        fields = fields_str.split(',') if fields_str else None

        result = get_all_events(
            db=g.db, page=page, page_size=page_size, order_by=order_by,
            order_direction=order_direction, type=event_type, place=place,
            description=description, fields=fields
        )
        return jsonify(result)
    except HTTPException:
        raise
    except Exception as e:
        raise e

# --- Implement GET /events/{id}, POST, PUT, DELETE similarly ---

# --- Source Endpoints ---
@app.route("/api/sources", methods=['GET'])
@api_login_required
def get_sources_api():
    """Get all sources with pagination and filtering."""
    try:
        # Extract and validate query parameters
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        order_by = request.args.get('order_by', 'id', type=str)
        order_direction = request.args.get('order_direction', 'asc', type=str)
        title = request.args.get('title')
        author = request.args.get('author')
        fields_str = request.args.get('fields')

        if page < 1 or page_size < 1:
            abort(400, description="Page and page_size must be positive integers.")
        if order_direction not in ('asc', 'desc'):
            abort(400, description="order_direction must be 'asc' or 'desc'.")

        fields = fields_str.split(',') if fields_str else None

        result = get_all_sources(
            db=g.db, page=page, page_size=page_size, order_by=order_by,
            order_direction=order_direction, title=title, author=author,
            fields=fields
        )
        return jsonify(result)
    except HTTPException:
        raise
    except Exception as e:
        raise e

# --- Implement GET /sources/{id}, POST, PUT, DELETE similarly ---

# --- Citation Endpoints ---
@app.route("/api/citations", methods=['GET'])
@api_login_required
def get_citations_api():
    """Get all citations with pagination and filtering."""
    try:
        # Extract and validate query parameters
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        order_by = request.args.get('order_by', 'id', type=str)
        order_direction = request.args.get('order_direction', 'asc', type=str)
        source_id_str = request.args.get('source_id')
        person_id_str = request.args.get('person_id')
        event_id_str = request.args.get('event_id')
        description = request.args.get('description') # Assuming maps to citation_text
        fields_str = request.args.get('fields')
        include_source = request.args.get('include_source', 'false').lower() == 'true'
        include_person = request.args.get('include_person', 'false').lower() == 'true'
        include_event = request.args.get('include_event', 'false').lower() == 'true' # Add include for event

        if page < 1 or page_size < 1:
            abort(400, description="Page and page_size must be positive integers.")
        if order_direction not in ('asc', 'desc'):
            abort(400, description="order_direction must be 'asc' or 'desc'.")

        # Validate IDs if provided
        source_id = None
        if source_id_str:
            try: source_id = int(source_id_str)
            except ValueError: abort(400, description="Invalid source_id format.")
        person_id = None
        if person_id_str:
            try: person_id = int(person_id_str)
            except ValueError: abort(400, description="Invalid person_id format.")
        event_id = None
        if event_id_str:
            try: event_id = int(event_id_str)
            except ValueError: abort(400, description="Invalid event_id format.")

        fields = fields_str.split(',') if fields_str else None

        # Remove 'request' argument from service call
        result = get_all_citations(
            db=g.db, page=page, page_size=page_size, order_by=order_by,
            order_direction=order_direction, source_id=source_id,
            person_id=person_id, event_id=event_id, # Add event_id filter
            description=description, fields=fields,
            include_source=include_source, include_person=include_person,
            include_event=include_event # Pass include_event flag
        )
        return jsonify(result)
    except HTTPException:
        raise
    except Exception as e:
        raise e

# --- Implement GET /citations/{id}, POST, PUT, DELETE similarly ---

# --- Tree Traversal & Search Endpoints ---
@app.route('/api/people/<int:person_id>/ancestors', methods=['GET'])
@api_login_required
def get_ancestors_api(person_id: int):
    """API endpoint to get ancestors of a person."""
    try:
        depth_str = request.args.get('depth', default='5') # Default depth
        try:
            depth = int(depth_str)
            if depth < 0: raise ValueError("Depth cannot be negative")
        except ValueError:
            abort(400, description="Invalid depth parameter. Must be a non-negative integer.")

        app.logger.info(f"Getting ancestors for person {person_id} with depth {depth}")
        ancestor_list = get_ancestors(g.db, person_id, depth)
        # Convert Person objects to dicts
        return jsonify([p.to_dict() for p in ancestor_list])
    except NoResultFound: # Catch if the initial person_id is not found
        abort(404, description=f"Person with ID {person_id} not found.")
    except HTTPException:
        raise
    except Exception as e:
        raise e

@app.route('/api/people/<int:person_id>/descendants', methods=['GET'])
@api_login_required
def get_descendants_api(person_id: int):
    """API endpoint to get descendants of a person."""
    try:
        depth_str = request.args.get('depth', default='5') # Default depth
        try:
            depth = int(depth_str)
            if depth < 0: raise ValueError("Depth cannot be negative")
        except ValueError:
            abort(400, description="Invalid depth parameter. Must be a non-negative integer.")

        app.logger.info(f"Getting descendants for person {person_id} with depth {depth}")
        descendant_list = get_descendants(g.db, person_id, depth)
        # Convert Person objects to dicts
        return jsonify([p.to_dict() for p in descendant_list])
    except NoResultFound: # Catch if the initial person_id is not found
        abort(404, description=f"Person with ID {person_id} not found.")
    except HTTPException:
        raise
    except Exception as e:
        raise e

# --- Add other traversal endpoints similarly (partial_tree, etc.) if implemented in services ---
# Example for partial_tree (if implemented in services.py)
# @app.route('/api/people/<int:person_id>/partial_tree', methods=['GET'])
# @api_login_required
# def get_partial_tree_api(person_id: int):
#     """API endpoint to get a partial tree (ancestors and descendants)."""
#     try:
#         depth_str = request.args.get('depth', default='3') # Default depth
#         try:
#             depth = int(depth_str)
#             if depth < 0: raise ValueError("Depth cannot be negative")
#         except ValueError:
#             abort(400, description="Invalid depth parameter. Must be a non-negative integer.")
#
#         # Assuming get_partial_tree exists in services.py
#         # from app.services import get_partial_tree
#         partial_tree_data = get_partial_tree(g.db, person_id, depth)
#         # Ensure service returns serializable data (dicts)
#         return jsonify(partial_tree_data)
#     except NoResultFound:
#         abort(404, description=f"Person with ID {person_id} not found.")
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise e


@app.route('/api/people/search', methods=['GET'])
@api_login_required
def search_people_api():
    """API endpoint to search for people based on various criteria."""
    try:
        # Extract search parameters from query string
        name = request.args.get('name')
        birth_date_str = request.args.get('birth_date')
        death_date_str = request.args.get('death_date')
        gender = request.args.get('gender')
        place_of_birth = request.args.get('place_of_birth')
        place_of_death = request.args.get('place_of_death')
        notes = request.args.get('notes')
        attribute_key = request.args.get('attribute_key')
        attribute_value = request.args.get('attribute_value')

        # Validate date formats
        birth_date, death_date = None, None
        if birth_date_str:
            try: birth_date = date.fromisoformat(birth_date_str)
            except ValueError: abort(400, description="Invalid birth_date format (YYYY-MM-DD).")
        if death_date_str:
            try: death_date = date.fromisoformat(death_date_str)
            except ValueError: abort(400, description="Invalid death_date format (YYYY-MM-DD).")

        # Call the service function
        results = search_people(
            db=g.db, name=name, birth_date=birth_date, death_date=death_date,
            gender=gender, place_of_birth=place_of_birth,
            place_of_death=place_of_death, notes=notes,
            attribute_key=attribute_key, attribute_value=attribute_value
        )
        # Convert results (Person objects) to dicts
        return jsonify([p.to_dict() for p in results])
    except HTTPException:
        raise
    except Exception as e:
        raise e

@app.route('/api/people/<int:person_id>/relationships_and_attributes', methods=['GET'])
@api_login_required
def get_person_relationships_and_attributes_api(person_id: int):
    """API endpoint to get all relationships and attributes of a specific person."""
    try:
        app.logger.info(f"Getting relationships and attributes for person {person_id}")
        # Service function should handle fetching and structuring the data
        data = get_person_relationships_and_attributes(g.db, person_id)
        # Service should return a serializable dict
        return jsonify(data)
    except HTTPException as he: # Catch 404 from service if person not found
        raise he
    except Exception as e:
        raise e


# --- Main Execution Guard ---
if __name__ == '__main__':
    # Suitable for direct execution (`python backend/app/main.py`)
    # For production, use a WSGI server like Gunicorn or Waitress
    app.logger.warning("Running Flask development server directly. Use a WSGI server (like Gunicorn) for production.")
    port = int(os.environ.get('PORT', 8090)) # Use PORT env var or default
    # Debug mode is automatically enabled if FLASK_DEBUG=1 env var is set
    # app.run(debug=True) handles this.
    app.run(host='0.0.0.0', port=port) # Debug determined by FLASK_DEBUG env var

