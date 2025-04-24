# backend/app.py
import os
import logging
from functools import wraps
from flask import Flask, request, session, jsonify, abort # Removed current_app
from flask_cors import CORS
from datetime import date, timedelta # Removed datetime
from logging.handlers import RotatingFileHandler
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, NoResultFound
from sqlalchemy.orm import sessionmaker, Session as DbSession
from sqlalchemy import create_engine, desc, asc # Removed Column, Integer, String, Date, ForeignKey
# Removed declarative_base, relationship, load_only
from werkzeug.exceptions import HTTPException, Unauthorized, InternalServerError, NotFound, BadRequest, Forbidden
# Removed Optional, List, Any

# Assuming these are correctly implemented in services and models
# Adjust imports based on actual project structure if different
try:
    # Import only services used directly in these routes
    from .services import (
        get_all_users, get_user_by_id,
        get_all_people_db, get_person_by_id_db, create_person_db,
        get_all_events, # Assuming get_events_api uses this
        get_all_sources, # Assuming get_sources_api uses this
        get_all_citations, # Assuming get_citations_api uses this
        search_people, get_person_relationships_and_attributes,
        get_all_person_attributes, get_person_attribute as get_person_attribute_by_id,
        get_all_relationships,
        get_all_relationship_attributes,
        get_all_media, # Assuming get_media_api uses this
        get_partial_tree
        # Removed unused service imports based on previous app.py version
    )
    from .models import Base # Assuming models define Base
    # Removed unused model imports: User, Person, RelationshipModel
    from .db_init import populate_database
    from .user_management import UserManagement # Removed VALID_ROLES
    # Removed FamilyTree
    # Removed VALID_RELATIONSHIP_TYPES
    from .audit_log import log_audit
except ImportError as e:
    logging.critical(f"Failed to import necessary modules: {e}", exc_info=True)
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
flask_app = Flask(__name__)
flask_app.secret_key = SECRET_KEY
flask_app.config.update(
    SESSION_COOKIE_SECURE=os.environ.get('FLASK_ENV') == 'production',
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(days=7)
)

app = flask_app # Using Flask app instance

# --- Configure CORS ---
CORS(app, supports_credentials=True, origins=["http://localhost:5173", "http://127.0.0.1:5173"])
logging.info("CORS configured for development origins.")

# --- Configure Logging ---
os.makedirs(LOG_DIR, exist_ok=True)
log_formatter = logging.Formatter('%(asctime)s %(levelname)-8s [%(name)s] %(message)s [in %(pathname)s:%(lineno)d]')
file_handler = RotatingFileHandler(APP_LOG_FILE, maxBytes=1024*1024*5, backupCount=5, encoding='utf-8')
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.DEBUG if os.environ.get('FLASK_DEBUG') == '1' else logging.INFO)

root_logger = logging.getLogger()
if root_logger.handlers: root_logger.handlers.clear()
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)
root_logger.setLevel(logging.DEBUG if os.environ.get('FLASK_DEBUG') == '1' else logging.INFO)

logging.info("Application starting up...")

# --- Database Engine & Session ---
db_engine = None
db_session_factory = None
try:
    db_engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=db_engine)
    db_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    logging.info("Database engine and session factory created successfully.")
except SQLAlchemyError as e:
    logging.critical(f"CRITICAL ERROR: Database engine creation failed: {e}", exc_info=True)
    exit(1)
except NameError as e:
    logging.critical(f"CRITICAL ERROR: Database Base model not defined or imported correctly: {e}", exc_info=True)
    exit(1)

# --- Dependency Injection Helper (Manual Session Management) ---
# Define get_db_session if it's not imported elsewhere
def get_db_session(session_factory):
    """Helper to get a DB session."""
    if not session_factory:
        logging.error("Database session factory not initialized.")
        raise HTTPException(status_code=503, detail="Database connection not available.")
    return session_factory()

# --- Initialize Core Components ---
# UserManagement might be needed for login/register if not using services directly
# user_manager = UserManagement(db_session_factory, AUDIT_LOG_FILE) # Instantiate if needed

# --- Initial data population ---
try:
    # Use context manager for session
    with get_db_session(db_session_factory) as initial_session:
        populate_database(initial_session)
except Exception as e:
    logging.error(f"Error during initial database population: {e}", exc_info=True)


# --- Decorators ---
def api_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            logging.warning(f"API Authentication Required: Endpoint '{request.endpoint}' accessed without login (IP: {request.remote_addr}).")
            log_audit(AUDIT_LOG_FILE, 'anonymous', 'api_access_denied', f'login required for API endpoint {request.endpoint}')
            abort(401, description="Authentication required.")
        if not db_session_factory:
             logging.error(f"API Service Unavailable: Endpoint '{request.endpoint}' accessed but DB session factory not initialized.")
             abort(503, description="Service temporarily unavailable. Please try again later.")
        return f(*args, **kwargs)
    return decorated_function

def api_admin_required(f):
    @wraps(f)
    @api_login_required
    def decorated_function(*args, **kwargs):
        user_role = session.get("user_role")
        username = session.get('username', 'unknown_user')
        if user_role != 'admin':
            logging.warning(f"API Authorization Failed: User '{username}' (Role: {user_role}) attempted to access admin endpoint '{request.endpoint}'.")
            log_audit(AUDIT_LOG_FILE, username, 'api_access_denied', f'admin required (role: {user_role}) for API endpoint {request.endpoint}')
            abort(403, description="Administrator privileges required.")
        return f(*args, **kwargs)
    return decorated_function

# --- Validation Helper ---
def validate_person_data(data: dict, is_edit: bool = False) -> dict:
    """Validates incoming person data."""
    errors = {}
    first_name = data.get('first_name')
    dob_str = data.get('birth_date')
    dod_str = data.get('death_date')
    gender = data.get('gender')

    if not is_edit and (first_name is None or not str(first_name).strip()):
        errors['first_name'] = 'First name is required.'
    elif 'first_name' in data and (first_name is None or not str(first_name).strip()):
        errors['first_name'] = 'First name cannot be empty.'

    dob, dod = None, None
    if dob_str:
        try:
            dob = date.fromisoformat(dob_str)
        except (ValueError, TypeError):
            errors['birth_date'] = 'Invalid date format (YYYY-MM-DD).'
    if dod_str:
        try:
            dod = date.fromisoformat(dod_str)
        except (ValueError, TypeError):
            errors['death_date'] = 'Invalid date format (YYYY-MM-DD).'

    if dob and dod and 'birth_date' not in errors and 'death_date' not in errors:
        if dod < dob:
            errors['date_comparison'] = 'Date of Death cannot be before Date of Birth.'

    if gender and gender not in ['Male', 'Female', 'Other']:
        errors['gender'] = 'Invalid gender. Use Male, Female, or Other.'

    return errors

# --- Custom Error Handlers ---
@app.errorhandler(400)
def handle_bad_request(error: BadRequest):
    description = getattr(error, 'description', "Invalid request format or data.")
    logging.warning(f"API Bad Request (400): {description} - Endpoint: {request.endpoint}, IP: {request.remote_addr}")
    response_data = {"error": "Bad Request", "message": description}
    if isinstance(description, dict):
        response_data = {"error": "Validation failed", "details": description}
    return jsonify(response_data), 400

@app.errorhandler(401)
def handle_unauthorized(error: Unauthorized):
    description = getattr(error, 'description', "Authentication required.")
    logging.warning(f"API Unauthorized (401): {description} - Endpoint: {request.endpoint}, IP: {request.remote_addr}")
    return jsonify({"error": "Unauthorized", "message": description}), 401

@app.errorhandler(403)
def handle_forbidden(error: Forbidden):
    description = getattr(error, 'description', "Permission denied.")
    logging.warning(f"API Forbidden (403): {description} - Endpoint: {request.endpoint}, User: {session.get('username', 'anonymous')}, IP: {request.remote_addr}")
    return jsonify({"error": "Forbidden", "message": description}), 403

@app.errorhandler(404)
def handle_not_found(error: NotFound):
    logging.warning(f"API Not Found (404): Path '{request.path}' - IP: {request.remote_addr}, Referrer: {request.referrer}")
    return jsonify({"error": "Not Found", "message": f"The requested URL '{request.path}' was not found on this server."}), 404

@app.errorhandler(500)
def handle_internal_server_error(error: InternalServerError):
    original_exception = getattr(error, 'original_exception', error)
    logging.error(
        f"API Internal Server Error (500): Endpoint: {request.endpoint}, User: {session.get('username', 'anonymous')}, IP: {request.remote_addr}",
        exc_info=original_exception
    )
    return jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred."}), 500

@app.errorhandler(503)
def handle_service_unavailable(error):
    description = getattr(error, 'description', "Service temporarily unavailable.")
    logging.error(f"API Service Unavailable (503): {description} - Endpoint: {request.endpoint}, IP: {request.remote_addr}")
    return jsonify({"error": "Service Unavailable", "message": description}), 503


# --- API Routes ---

@app.route('/api/login', methods=['POST'])
def api_login():
    db = None # Initialize db to None
    try:
        db = get_db_session(db_session_factory) # Get session
        user_manager = UserManagement(db, AUDIT_LOG_FILE) # Instantiate with session
        data = request.get_json()
        if not data or not data.get('username') or not data.get('password'):
            abort(400, description="Username and password required.")
        user_obj = user_manager.login_user(data['username'], data['password']) # Use user_obj consistently
        if user_obj:
            session.permanent = True
            session['user_id'] = user_obj.id # Assuming user model has 'id'
            session['username'] = user_obj.username
            session['user_role'] = user_obj.role
            return jsonify({"message": "Login successful!", "user": {"id": user_obj.id, "username": user_obj.username, "role": user_obj.role}}), 200
        else:
            abort(401, description="Invalid credentials.")
    except HTTPException as he:
        # If db session was obtained, rollback on handled errors too
        if db: db.rollback()
        raise he
    except Exception as e:
        if db: db.rollback()
        logging.exception("Error during login")
        abort(500)
    finally:
        if db: db.close() # Ensure session is closed


@app.route('/api/users', methods=['GET'])
@api_admin_required
def get_users():
    """Get all users."""
    db = None
    try:
        db = get_db_session(db_session_factory)
        users = get_all_users(db)
        # Convert User objects to dicts for JSON response
        return jsonify([u.to_dict() for u in users]) # Assuming User model has to_dict
    except Exception as e:
        logging.exception("Error getting all users")
        abort(500)
    finally:
        if db: db.close()

@app.route('/api/users/<int:user_id>', methods=['GET'])
@api_admin_required
def get_user(user_id: int):
    """Get a specific user."""
    db = None
    try:
        db = get_db_session(db_session_factory)
        user_obj = get_user_by_id(db, user_id) # Use user_obj
        if not user_obj:
            abort(404, "User not found")
        return jsonify(user_obj.to_dict()) # Assuming User model has to_dict
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.exception(f"Error getting user {user_id}")
        abort(500)
    finally:
        if db: db.close()

# ... (Implement POST /users, PUT /users/{id}/role, DELETE /users/{id} similarly, ensuring db closure) ...

# --- People Endpoints ---
@app.route('/api/people', methods=['GET'])
@api_login_required
def get_people():
    """Get all people with pagination."""
    db = None
    try:
        db = get_db_session(db_session_factory)
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        order_by = request.args.get('order_by', 'id', type=str)
        order_direction = request.args.get('order_direction', 'asc', type=str)
        name = request.args.get('name', type=str)
        gender = request.args.get('gender', type=str)
        birth_date_str = request.args.get('birth_date')
        death_date_str = request.args.get('death_date')
        fields_str = request.args.get('fields')

        birth_date = date.fromisoformat(birth_date_str) if birth_date_str else None
        death_date = date.fromisoformat(death_date_str) if death_date_str else None
        fields = fields_str.split(',') if fields_str else None

        if page < 1 or page_size < 1:
            abort(400, description="Page and page_size must be positive integers.")
        if order_direction not in ('asc', 'desc'):
            abort(400, description="order_direction must be 'asc' or 'desc'.")

        result = get_all_people_db(
            db, page=page, page_size=page_size, order_by=order_by,
            order_direction=order_direction, name=name, gender=gender,
            birth_date=birth_date, death_date=death_date, fields=fields
        )
        return jsonify(result) # Service now returns dict
    except ValueError as ve:
        abort(400, description=f"Invalid parameter format: {ve}")
    except Exception as e:
        logging.exception("Error getting people")
        abort(500)
    finally:
        if db: db.close()

@app.route('/api/people/<int:person_id>', methods=['GET'])
@api_login_required
def get_person_api(person_id: int):
    """Get a specific person."""
    db = None
    try:
        db = get_db_session(db_session_factory)
        fields_str = request.args.get('fields')
        fields = fields_str.split(',') if fields_str else None
        person_data = get_person_by_id_db(db, person_id, fields=fields)
        if not person_data:
            abort(404, "Person not found")
        return jsonify(person_data) # Service function already returns dict
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.exception(f"Error getting person {person_id}")
        abort(500)
    finally:
        if db: db.close()

@app.route('/api/people', methods=['POST'])
@api_login_required
def create_person_api():
    """Create a new person."""
    db = None
    try:
        db = get_db_session(db_session_factory)
        data = request.get_json()
        if not data:
            abort(400, description="Request body must be valid JSON.")

        validation_errors = validate_person_data(data)
        if validation_errors:
            abort(400, description=validation_errors)

        data['created_by'] = session.get('user_id')

        new_person = create_person_db(db, data)
        log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'create_person', f'success - id: {new_person.id}')
        return jsonify(new_person.to_dict()), 201
    except HTTPException as he:
        if db: db.rollback()
        raise he
    except IntegrityError as ie:
         if db: db.rollback()
         logging.error(f"Integrity error creating person: {ie}")
         abort(409, description="Failed to create person due to data conflict.")
    except Exception as e:
        if db: db.rollback()
        logging.exception("Error creating person")
        abort(500)
    finally:
        if db: db.close()

# --- Add PUT and DELETE for /people/{id} similarly ---

# --- Person Attributes Endpoints ---
@app.route("/api/person_attributes", methods=['GET'])
@api_login_required
def get_all_person_attributes_api():
    """Get all person attributes with pagination and filtering."""
    db = None
    try:
        db = get_db_session(db_session_factory)
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        order_by = request.args.get('order_by', 'id', type=str)
        order_direction = request.args.get('order_direction', 'asc', type=str)
        key = request.args.get('key')
        value = request.args.get('value')
        fields_str = request.args.get('fields')
        fields = fields_str.split(',') if fields_str else None
        include_person_str = request.args.get('include_person', 'false')
        include_person = include_person_str.lower() == 'true'

        if page < 1 or page_size < 1:
            abort(400, description="Page and page_size must be positive integers.")
        if order_direction not in ('asc', 'desc'):
            abort(400, description="order_direction must be 'asc' or 'desc'.")

        result = get_all_person_attributes(
            db, page=page, page_size=page_size, order_by=order_by,
            order_direction=order_direction, key=key, value=value,
            fields=fields, include_person=include_person
        )
        return jsonify(result)
    except Exception as e:
        logging.exception("Error getting person attributes")
        abort(500)
    finally:
        if db: db.close()

@app.route("/api/person_attributes/<int:person_attribute_id>", methods=['GET'])
@api_login_required
def get_person_attribute_api(person_attribute_id: int):
    """Get a specific person attribute by ID."""
    db = None
    try:
        db = get_db_session(db_session_factory)
        fields_str = request.args.get('fields')
        fields = fields_str.split(',') if fields_str else None
        include_person_str = request.args.get('include_person', 'false')
        include_person = include_person_str.lower() == 'true'

        result = get_person_attribute_by_id(
            db, person_attribute_id=person_attribute_id,
            fields=fields, include_person=include_person
        )
        if result is None:
            abort(404, description="Person attribute not found.")
        return jsonify(result)
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.exception(f"Error getting person attribute {person_attribute_id}")
        abort(500)
    finally:
        if db: db.close()

# --- Add POST, PUT, DELETE for /person_attributes similarly ---

# --- Relationship Endpoints ---
@app.route("/api/relationships", methods=['GET'])
@api_login_required
def get_relationships_api():
    """Get all relationships with pagination and filtering."""
    db = None
    try:
        db = get_db_session(db_session_factory)
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        order_by = request.args.get('order_by', 'id', type=str)
        order_direction = request.args.get('order_direction', 'asc', type=str)
        rel_type = request.args.get('type')
        person1_id = request.args.get('person1_id', type=int)
        person2_id = request.args.get('person2_id', type=int)
        fields_str = request.args.get('fields')
        fields = fields_str.split(',') if fields_str else None
        include_person1 = request.args.get('include_person1', 'false').lower() == 'true'
        include_person2 = request.args.get('include_person2', 'false').lower() == 'true'

        if page < 1 or page_size < 1:
            abort(400, description="Page and page_size must be positive integers.")
        if order_direction not in ('asc', 'desc'):
            abort(400, description="order_direction must be 'asc' or 'desc'.")

        result = get_all_relationships(
            db, request, page=page, page_size=page_size, order_by=order_by,
            order_direction=order_direction, type=rel_type,
            person1_id=person1_id, person2_id=person2_id, fields=fields,
            include_person1=include_person1, include_person2=include_person2
        )
        return jsonify(result)
    except Exception as e:
        logging.exception("Error getting relationships")
        abort(500)
    finally:
        if db: db.close()

# --- Add GET /relationships/{id}, POST, PUT, DELETE similarly ---

# --- Relationship Attributes Endpoints ---
@app.route("/api/relationship_attributes", methods=['GET'])
@api_login_required
def get_relationship_attributes_api():
    """Get all relationship attributes with pagination and filtering."""
    db = None
    try:
        db = get_db_session(db_session_factory)
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        order_by = request.args.get('order_by', 'id', type=str)
        order_direction = request.args.get('order_direction', 'asc', type=str)
        key = request.args.get('key')
        value = request.args.get('value')
        relationship_id = request.args.get('relationship_id', type=int)
        fields_str = request.args.get('fields')
        fields = fields_str.split(',') if fields_str else None
        include_relationship = request.args.get('include_relationship', 'false').lower() == 'true'

        if page < 1 or page_size < 1:
            abort(400, description="Page and page_size must be positive integers.")
        if order_direction not in ('asc', 'desc'):
            abort(400, description="order_direction must be 'asc' or 'desc'.")

        result = get_all_relationship_attributes(
            db, page=page, page_size=page_size, order_by=order_by,
            order_direction=order_direction, key=key, value=value,
            relationship_id=relationship_id, fields=fields,
            include_relationship=include_relationship
        )
        return jsonify(result)
    except Exception as e:
        logging.exception("Error getting relationship attributes")
        abort(500)
    finally:
        if db: db.close()

# --- Add GET /relationship_attributes/{id}, POST, PUT, DELETE similarly ---

# --- Media Endpoints ---
@app.route("/api/media", methods=['GET'])
@api_login_required
def get_media_api():
    """Get all media with pagination and filtering."""
    db = None
    try:
        db = get_db_session(db_session_factory)
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        order_by = request.args.get('order_by', 'id', type=str)
        order_direction = request.args.get('order_direction', 'asc', type=str)
        file_name = request.args.get('file_name')
        file_type = request.args.get('file_type')
        description = request.args.get('description')
        fields_str = request.args.get('fields')
        fields = fields_str.split(',') if fields_str else None

        if page < 1 or page_size < 1:
            abort(400, description="Page and page_size must be positive integers.")
        if order_direction not in ('asc', 'desc'):
            abort(400, description="order_direction must be 'asc' or 'desc'.")

        result = get_all_media(
            db, page=page, page_size=page_size, order_by=order_by,
            order_direction=order_direction, file_name=file_name,
            file_type=file_type, description=description, fields=fields
        )
        return jsonify(result)
    except Exception as e:
        logging.exception("Error getting media")
        abort(500)
    finally:
        if db: db.close()

# --- Add GET /media/{id}, POST, PUT, DELETE similarly ---

# --- Event Endpoints ---
@app.route("/api/events", methods=['GET'])
@api_login_required
def get_events_api():
    """Get all events with pagination and filtering."""
    db = None
    try:
        db = get_db_session(db_session_factory)
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        order_by = request.args.get('order_by', 'id', type=str)
        order_direction = request.args.get('order_direction', 'asc', type=str)
        event_type = request.args.get('type')
        place = request.args.get('place')
        description = request.args.get('description')
        fields_str = request.args.get('fields')
        fields = fields_str.split(',') if fields_str else None

        if page < 1 or page_size < 1:
            abort(400, description="Page and page_size must be positive integers.")
        if order_direction not in ('asc', 'desc'):
            abort(400, description="order_direction must be 'asc' or 'desc'.")

        result = get_all_events(
            db, page=page, page_size=page_size, order_by=order_by,
            order_direction=order_direction, type=event_type, place=place,
            description=description, fields=fields
        )
        return jsonify(result)
    except Exception as e:
        logging.exception("Error getting events")
        abort(500)
    finally:
        if db: db.close()

# --- Add GET /events/{id}, POST, PUT, DELETE similarly ---

# --- Source Endpoints ---
@app.route("/api/sources", methods=['GET'])
@api_login_required
def get_sources_api():
    """Get all sources with pagination and filtering."""
    db = None
    try:
        db = get_db_session(db_session_factory)
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        order_by = request.args.get('order_by', 'id', type=str)
        order_direction = request.args.get('order_direction', 'asc', type=str)
        title = request.args.get('title')
        author = request.args.get('author')
        fields_str = request.args.get('fields')
        fields = fields_str.split(',') if fields_str else None

        if page < 1 or page_size < 1:
            abort(400, description="Page and page_size must be positive integers.")
        if order_direction not in ('asc', 'desc'):
            abort(400, description="order_direction must be 'asc' or 'desc'.")

        result = get_all_sources(
            db, page=page, page_size=page_size, order_by=order_by,
            order_direction=order_direction, title=title, author=author,
            fields=fields
        )
        return jsonify(result)
    except Exception as e:
        logging.exception("Error getting sources")
        abort(500)
    finally:
        if db: db.close()

# --- Add GET /sources/{id}, POST, PUT, DELETE similarly ---

# --- Citation Endpoints ---
@app.route("/api/citations", methods=['GET'])
@api_login_required
def get_citations_api():
    """Get all citations with pagination and filtering."""
    db = None
    try:
        db = get_db_session(db_session_factory)
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        order_by = request.args.get('order_by', 'id', type=str)
        order_direction = request.args.get('order_direction', 'asc', type=str)
        source_id = request.args.get('source_id', type=int)
        person_id = request.args.get('person_id', type=int)
        description = request.args.get('description')
        fields_str = request.args.get('fields')
        fields = fields_str.split(',') if fields_str else None
        include_source = request.args.get('include_source', 'false').lower() == 'true'
        include_person = request.args.get('include_person', 'false').lower() == 'true'

        if page < 1 or page_size < 1:
            abort(400, description="Page and page_size must be positive integers.")
        if order_direction not in ('asc', 'desc'):
            abort(400, description="order_direction must be 'asc' or 'desc'.")

        result = get_all_citations(
            db, request, page=page, page_size=page_size, order_by=order_by,
            order_direction=order_direction, source_id=source_id,
            person_id=person_id, description=description, fields=fields,
            include_source=include_source, include_person=include_person
        )
        return jsonify(result)
    except Exception as e:
        logging.exception("Error getting citations")
        abort(500)
    finally:
        if db: db.close()

# --- Add GET /citations/{id}, POST, PUT, DELETE similarly ---

# --- Tree Traversal & Search Endpoints ---
@app.route('/api/people/<int:person_id>/partial_tree', methods=['GET'])
@api_login_required
def get_partial_tree_api(person_id: int):
    """API endpoint to get a partial tree of a person."""
    db = None
    try:
        db = get_db_session(db_session_factory)
        depth_str = request.args.get('depth')
        depth = int(depth_str) if depth_str else 5
        only_ancestors = request.args.get('only_ancestors', 'false').lower() == 'true'
        only_descendants = request.args.get('only_descendants', 'false').lower() == 'true'

        if depth < 0:
            abort(400, description="Depth must be a non-negative integer.")

        logging.info(f"Getting partial tree for person {person_id} with depth {depth}, only_ancestors={only_ancestors}, only_descendants={only_descendants}")
        partial_tree = get_partial_tree(db, person_id, depth, only_ancestors, only_descendants)

        # Convert Person objects within the structure to dicts
        if partial_tree.get('center'): partial_tree['center'] = partial_tree['center'].to_dict()
        if partial_tree.get('ancestors'): partial_tree['ancestors'] = [p.to_dict() for p in partial_tree['ancestors']]
        if partial_tree.get('descendants'): partial_tree['descendants'] = [p.to_dict() for p in partial_tree['descendants']]

        return jsonify(partial_tree)
    except HTTPException as he:
        raise he
    except NoResultFound:
        abort(404, description=f"Person with ID {person_id} not found.")
    except ValueError:
         abort(400, description="Invalid depth parameter. Must be an integer.")
    except Exception as e:
        logging.exception(f"Error getting partial tree for person {person_id}")
        abort(500)
    finally:
        if db: db.close()

# --- Add other traversal endpoints similarly (ancestors, descendants, etc.) ---

@app.route('/api/people/search', methods=['GET'])
@api_login_required
def search_people_api():
    """API endpoint to search for people."""
    db = None
    try:
        db = get_db_session(db_session_factory)
        name = request.args.get('name')
        birth_date_str = request.args.get('birth_date')
        death_date_str = request.args.get('death_date')
        gender = request.args.get('gender')
        place_of_birth = request.args.get('place_of_birth')
        place_of_death = request.args.get('place_of_death')
        notes = request.args.get('notes')
        attribute_key = request.args.get('attribute_key')
        attribute_value = request.args.get('attribute_value')

        birth_date = date.fromisoformat(birth_date_str) if birth_date_str else None
        death_date = date.fromisoformat(death_date_str) if death_date_str else None

        results = search_people(
            db, name=name, birth_date=birth_date, death_date=death_date,
            gender=gender, place_of_birth=place_of_birth,
            place_of_death=place_of_death, notes=notes,
            attribute_key=attribute_key, attribute_value=attribute_value
        )
        return jsonify([p.to_dict() for p in results])
    except ValueError:
         abort(400, description="Invalid date format provided for search.")
    except Exception as e:
        logging.exception("Error searching people")
        abort(500)
    finally:
        if db: db.close()

@app.route('/api/people/<int:person_id>/relationships_and_attributes', methods=['GET'])
@api_login_required
def get_person_relationships_and_attributes_api(person_id: int):
    """API endpoint to get all relationships and attributes of a person."""
    db = None
    try:
        db = get_db_session(db_session_factory)
        logging.info(f"Getting relationships and attributes for person {person_id}")
        data = get_person_relationships_and_attributes(db, person_id)
        return jsonify(data)
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.exception(f"Error getting relationships and attributes for person {person_id}")
        abort(500)
    finally:
        if db: db.close()

# --- Main Execution Guard ---
if __name__ == '__main__':
    logging.warning("Running Flask development server directly. Use a WSGI server (like uvicorn or gunicorn) for production.")
    port = int(os.environ.get('PORT', 8090))
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(debug=debug_mode, host='0.0.0.0', port=port)

