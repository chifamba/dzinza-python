# backend/main.py
import logging
import bcrypt
import os
import json
import uuid
import time # Added for manual timing example
from urllib.parse import urljoin
from sqlalchemy.orm import Session, load_only, joinedload, selectinload
from sqlalchemy.exc import SQLAlchemyError, NoResultFound, IntegrityError
from sqlalchemy import or_, and_, desc, asc, Enum as SQLAlchemyEnum, TypeDecorator, String, Text, func, inspect
from cryptography.fernet import Fernet, InvalidToken
from cryptography.exceptions import InvalidSignature
from typing import Optional, List, Dict, Any, Set
from datetime import date, datetime

# Assuming Flask context for abort, adjust if using a different framework
try:
    from flask import abort, request, g
    from werkzeug.exceptions import HTTPException
except ImportError:
    class HTTPException(Exception):
        def __init__(self, code=500, description="Server Error"): self.code = code; self.description = description; super().__init__(description)
    def abort(code, description): raise HTTPException(code=code, description=description)
    class G: pass
    g = G() # Simple fallback for 'g'

from collections import deque
import enum
from dotenv import load_dotenv

# --- Enhanced Logging & Tracing Imports ---
import structlog
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
# from opentelemetry.instrumentation.flask import FlaskInstrumentor
# from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
# from opentelemetry.instrumentation.logging import LoggingInstrumentor

# --- Load Environment Variables ---
load_dotenv()

# --- Logging Setup (Using Structlog) ---
logging.basicConfig(level=logging.INFO, format='%(message)s', handlers=[logging.StreamHandler()])
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        # Add trace/span IDs to logs if OTEL is configured
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.dict_tracebacks, # Render tracebacks better
        # --- OpenTelemetry Log Correlation ---
        # This processor adds span_id and trace_id to log records
        # Requires LoggingInstrumentor().instrument() to be called
        structlog.contextvars.merge_contextvars,
        structlog.processors.CallsiteParameterAdder(
            parameters={
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.LINENO,
            },
        ),
        # --- End OpenTelemetry ---
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
formatter = structlog.stdlib.ProcessorFormatter(
    # Render as JSON
    processor=structlog.processors.JSONRenderer(),
    # These run JUST before rendering
    foreign_pre_chain=[
        # structlog.stdlib.add_logger_name, # Already added above
        # structlog.stdlib.add_log_level, # Already added above
        # structlog.processors.TimeStamper(fmt="iso"), # Already added above
    ]
)
handler = logging.getLogger().handlers[0]; handler.setFormatter(formatter)
logger = structlog.get_logger() # Use this logger

# --- OpenTelemetry Setup (Conceptual) ---
resource = Resource(attributes={ "service.name": os.getenv("OTEL_SERVICE_NAME", "family-tree-backend"), /* ... */ })
def configure_tracer_provider(): /* ... */
def configure_meter_provider(): /* ... */
# configure_tracer_provider() # Call during app startup
# configure_meter_provider() # Call during app startup
# LoggingInstrumentor().instrument(set_logging_format=True) # Call during app startup
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)
user_registration_counter = meter.create_counter(/* ... */)
db_operation_duration_histogram = meter.create_histogram(/* ... */)
auth_failure_counter = meter.create_counter( # New metric for auth failures
    name="app.auth.failures",
    description="Counts authentication failures",
    unit="1"
)
role_change_counter = meter.create_counter( # New metric for role changes
    name="app.auth.role_changes",
    description="Counts user role changes",
    unit="1"
)
# --- End OpenTelemetry Setup ---

# --- Encryption Setup ---
ENCRYPTION_KEY_ENV_VAR = "ENCRYPTION_KEY"; ENCRYPTION_KEY_FILE = "backend/data/encryption_key.json"
def load_encryption_key(): /* ... */
try: _encryption_key = load_encryption_key(); fernet_suite = Fernet(_encryption_key) if _encryption_key else None
except Exception as e: logger.critical(f"Failed to init Fernet: {e}"); fernet_suite = None
if fernet_suite is None: logger.critical("ENCRYPTION DISABLED.")
class EncryptedString(TypeDecorator): /* ... */

# --- Enums ---
class UserRole(enum.Enum): USER = "user"; ADMIN = "admin"

# --- Placeholder Model Definitions ---
class Base: /* ... */
class User(Base): /* ... */
class Person(Base): /* ... */
class RelationshipModel(Base): /* ... */
class PersonAttribute(Base): /* ... */
class RelationshipAttribute(Base): /* ... */
class Media(Base): /* ... */
class Event(Base): /* ... */
class Source(Base): /* ... */
class Citation(Base): /* ... */

# --- Relationship Type Constants ---
REL_PARENT = 'parent'; REL_CHILD = 'child'; REL_SPOUSE = 'spouse'

# --- Utility Functions ---
def _handle_sqlalchemy_error(e: SQLAlchemyError, context: str, db: Session):
    db.rollback()
    # Log detailed error info for debugging/audit
    logger.error("Database operation failed", context=context, db_error=str(e), exc_info=True)
    if isinstance(e, IntegrityError):
        if 'users_username_key' in str(e.orig): abort(409, description="Username already exists.")
        elif 'users_email_key' in str(e.orig): abort(409, description="Email already exists.")
        else: abort(409, description=f"Database conflict {context}.")
    elif isinstance(e, NoResultFound): abort(404, description="Resource not found.")
    elif "NOT NULL constraint failed" in str(e) or "null value in column" in str(e): abort(400, description=f"Missing required field during {context}: {e}")
    else: abort(500, description=f"Database error {context}.")

def _get_or_404(db: Session, model: Any, model_id: int) -> Any:
    # --- Security Note: Access Control ---
    # This function retrieves any object by ID. In a real application,
    # access control checks (e.g., can the current user view this specific object?)
    # should be performed *before* or *after* calling this function, typically
    # in the API layer based on the authenticated user's permissions.
    with tracer.start_as_current_span(f"db.get.{model.__name__}") as span:
        span.set_attribute("db.system", "postgresql"); span.set_attribute(f"{model.__name__}.id", model_id)
        try:
            start_time = time.monotonic()
            query = db.query(model); obj = query.filter(model.id == model_id).one_or_none()
            duration = (time.monotonic() - start_time) * 1000
            db_operation_duration_histogram.record(duration, {"db.operation": f"get.{model.__name__}", "db.status": "success"})
            if obj is None:
                logger.warning("Resource not found", model_name=model.__name__, model_id=model_id)
                span.set_attribute("db.found", False); abort(404, description=f"{model.__name__} not found")
            span.set_attribute("db.found", True); return obj
        except SQLAlchemyError as e:
            duration = (time.monotonic() - start_time) * 1000
            db_operation_duration_histogram.record(duration, {"db.operation": f"get.{model.__name__}", "db.status": "error"})
            span.record_exception(e); span.set_status(trace.Status(trace.StatusCode.ERROR, f"DB Error: {e}"))
            _handle_sqlalchemy_error(e, f"fetching {model.__name__} ID {model_id}", db)
        except Exception as e: span.record_exception(e); span.set_status(trace.Status(trace.StatusCode.ERROR, "Non-DB Error")); raise e

def _hash_password(password: str) -> str: /* ... */
def _verify_password(plain_password: str, hashed_password: str) -> bool: /* ... */

# --- User Services ---

def register_user_db(db: Session, user_data: dict) -> Dict[str, Any]:
    """Registers a new user, hashing the password."""
    # --- Security Note: Input Validation ---
    # Robust validation (e.g., username format, email format, password complexity)
    # should be performed in the API layer before calling this service.
    with tracer.start_as_current_span("service.register_user") as span:
        username = user_data.get('username', '[unknown]')
        email = user_data.get('email', '[unknown]')
        span.set_attribute("app.user.username", username)
        user_registration_counter.add(1, {"registration.type": "attempt"})
        # Audit Log: Registration attempt
        log = logger.bind(username=username, email=email, event_type="USER_REGISTRATION_ATTEMPT")
        log.info("User registration attempt")

        plain_password = user_data.get('password')
        if not plain_password:
            log.warning("Registration failed: Missing password")
            abort(400, description="Password is required.")

        hashed_password = _hash_password(plain_password)
        create_data = user_data.copy(); create_data.pop('password', None); create_data['password_hash'] = hashed_password
        create_data['created_at'] = datetime.utcnow(); create_data['updated_at'] = datetime.utcnow(); create_data['is_active'] = True
        create_data.setdefault('role', UserRole.USER)
        try: create_data['role'] = UserRole(create_data['role'])
        except ValueError:
             log.error("Registration failed: Invalid role specified", role=create_data['role'])
             abort(400, description=f"Invalid role: {create_data['role']}")

        try:
            new_user = User(**create_data); db.add(new_user); db.commit(); db.refresh(new_user)
            # Audit Log: Registration success
            logger.info("User registration successful", user_id=new_user.id, username=username, email=email, assigned_role=new_user.role.value, event_type="USER_REGISTRATION_SUCCESS")
            span.set_attribute("app.user.id", new_user.id)
            user_registration_counter.add(1, {"registration.type": "success"})
            user_dict = new_user.to_dict(); user_dict.pop('password_hash', None); return user_dict
        except SQLAlchemyError as e:
            # Audit Log: Registration failure (DB)
            logger.error("User registration failed due to database error", username=username, email=email, event_type="USER_REGISTRATION_FAILURE", reason="database_error", exc_info=False) # exc_info handled by _handle_sqlalchemy_error
            user_registration_counter.add(1, {"registration.type": "failure", "reason": "db_error"})
            span.record_exception(e); span.set_status(trace.Status(trace.StatusCode.ERROR, "DB Error"))
            _handle_sqlalchemy_error(e, f"registering user {username}", db)
        except Exception as e:
             logger.error("User registration failed due to unexpected error", username=username, email=email, event_type="USER_REGISTRATION_FAILURE", reason="unknown", exc_info=True)
             user_registration_counter.add(1, {"registration.type": "failure", "reason": "unknown"})
             span.record_exception(e); span.set_status(trace.Status(trace.StatusCode.ERROR, "Unknown Error"))
             abort(500, "An unexpected error occurred during registration.")


def authenticate_user_db(db: Session, identifier: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticates a user by username or email and password."""
    # --- Security Note: JWT ---
    # This function only verifies credentials. JWT generation (creating access/refresh tokens)
    # should happen in the API layer *after* this function returns a valid user object.
    # The API layer would then set the HttpOnly cookie containing the token.
    with tracer.start_as_current_span("service.authenticate_user") as span:
        span.set_attribute("app.user.identifier", identifier)
        # Audit Log: Authentication attempt
        log = logger.bind(identifier=identifier, event_type="USER_AUTHENTICATION_ATTEMPT")
        log.info("User authentication attempt")
        try:
            user_obj = db.query(User).filter(or_(User.username == identifier, User.email == identifier)).first()
            auth_success = False
            failure_reason = "unknown"
            if user_obj:
                if not user_obj.is_active:
                    failure_reason = "inactive_account"
                elif _verify_password(password, user_obj.password_hash):
                    auth_success = True
                else:
                    failure_reason = "invalid_credentials"
            else:
                failure_reason = "user_not_found"

            if auth_success:
                # Audit Log: Authentication success
                logger.info("User authentication successful", user_id=user_obj.id, username=user_obj.username, event_type="USER_AUTHENTICATION_SUCCESS")
                span.set_attribute("app.user.id", user_obj.id); span.set_attribute("app.auth.success", True)
                user_obj.last_login = datetime.utcnow(); db.commit(); db.refresh(user_obj)
                user_dict = user_obj.to_dict(); user_dict.pop('password_hash', None); return user_dict
            else:
                # Audit Log: Authentication failure
                logger.warning("User authentication failed", identifier=identifier, reason=failure_reason, event_type="USER_AUTHENTICATION_FAILURE")
                auth_failure_counter.add(1, {"reason": failure_reason}) # Increment failure metric
                span.set_attribute("app.auth.success", False); span.set_attribute("app.auth.failure_reason", failure_reason)
                return None
        except SQLAlchemyError as e:
            logger.error("Database error during authentication", identifier=identifier, event_type="USER_AUTHENTICATION_FAILURE", reason="database_error", exc_info=True)
            auth_failure_counter.add(1, {"reason": "database_error"})
            span.record_exception(e); span.set_status(trace.Status(trace.StatusCode.ERROR, "DB Error"))
            abort(500, "An error occurred during authentication.")
        except Exception as e:
             logger.error("Unknown error during authentication", identifier=identifier, event_type="USER_AUTHENTICATION_FAILURE", reason="unknown", exc_info=True)
             auth_failure_counter.add(1, {"reason": "unknown"})
             span.record_exception(e); span.set_status(trace.Status(trace.StatusCode.ERROR, "Unknown Error"))
             abort(500, "An unexpected error occurred during authentication.")


def update_user_role_db(db: Session, user_id: int, new_role: str) -> Dict[str, Any]:
    """Updates only the role of a specific user."""
    # --- Security Note: Authorization ---
    # This function changes a user's role. The check to ensure the *calling* user
    # has permission (e.g., is an admin) to perform this action must happen
    # in the API layer before calling this service function.
    with tracer.start_as_current_span("service.update_user_role") as span:
        span.set_attribute("app.user.id", user_id)
        span.set_attribute("app.user.new_role", new_role)
        # Assuming the calling user ID is available (e.g., from JWT in API layer)
        # calling_user_id = g.user.id # Example if stored in Flask 'g'
        calling_user_id = getattr(g, 'user_id', '[unknown]') # Safer fallback
        log = logger.bind(target_user_id=user_id, new_role=new_role, performed_by_user_id=calling_user_id, event_type="USER_ROLE_CHANGE_ATTEMPT")
        log.info("Attempting user role update")

        user_obj = _get_or_404(db, User, user_id) # Logged internally if fails
        original_role = user_obj.role.value
        span.set_attribute("app.user.original_role", original_role)

        try: role_enum = UserRole(new_role)
        except ValueError:
            log.error("Role update failed: Invalid role specified", invalid_role=new_role)
            abort(400, description=f"Invalid role specified: {new_role}")

        try:
            if user_obj.role != role_enum:
                user_obj.role = role_enum; user_obj.updated_at = datetime.utcnow(); db.commit(); db.refresh(user_obj)
                # Audit Log: Role change success
                logger.info("User role updated successfully", target_user_id=user_id, username=user_obj.username, original_role=original_role, new_role=new_role, performed_by_user_id=calling_user_id, event_type="USER_ROLE_CHANGE_SUCCESS")
                role_change_counter.add(1, {"status": "success", "role": new_role})
            else:
                logger.info("User role update skipped: User already has the specified role", target_user_id=user_id, role=new_role, event_type="USER_ROLE_CHANGE_NOOP")
                role_change_counter.add(1, {"status": "noop", "role": new_role})

            user_dict = user_obj.to_dict(); user_dict.pop('password_hash', None); return user_dict
        except SQLAlchemyError as e:
            # Audit Log: Role change failure (DB)
            logger.error("User role update failed due to database error", target_user_id=user_id, new_role=new_role, performed_by_user_id=calling_user_id, event_type="USER_ROLE_CHANGE_FAILURE", reason="database_error", exc_info=False)
            role_change_counter.add(1, {"status": "failure", "role": new_role, "reason": "db_error"})
            span.record_exception(e); span.set_status(trace.Status(trace.StatusCode.ERROR, "DB Error"))
            _handle_sqlalchemy_error(e, f"updating role for user ID {user_id}", db)
        except Exception as e:
             logger.error("User role update failed due to unexpected error", target_user_id=user_id, new_role=new_role, performed_by_user_id=calling_user_id, event_type="USER_ROLE_CHANGE_FAILURE", reason="unknown", exc_info=True)
             role_change_counter.add(1, {"status": "failure", "role": new_role, "reason": "unknown"})
             span.record_exception(e); span.set_status(trace.Status(trace.StatusCode.ERROR, "Unknown Error"))
             abort(500, "An unexpected error occurred during role update.")


def delete_user_db(db: Session, user_id: int) -> bool:
    """Deletes a user."""
    # --- Security Note: Authorization ---
    # Check if the calling user has permission to delete this user in the API layer.
    with tracer.start_as_current_span("service.delete_user") as span:
        span.set_attribute("app.user.id", user_id)
        calling_user_id = getattr(g, 'user_id', '[unknown]')
        log = logger.bind(target_user_id=user_id, performed_by_user_id=calling_user_id, event_type="USER_DELETE_ATTEMPT")
        log.info("Attempting user deletion")

        user_obj = _get_or_404(db, User, user_id) # Logged internally if fails
        username_for_log = user_obj.username # Get username before potential deletion

        try:
            db.delete(user_obj); db.commit()
            # Audit Log: Deletion success
            logger.info("User deleted successfully", target_user_id=user_id, username=username_for_log, performed_by_user_id=calling_user_id, event_type="USER_DELETE_SUCCESS")
            return True
        except SQLAlchemyError as e:
             # Audit Log: Deletion failure (DB)
            logger.error("User deletion failed due to database error", target_user_id=user_id, username=username_for_log, performed_by_user_id=calling_user_id, event_type="USER_DELETE_FAILURE", reason="database_error", exc_info=False)
            span.record_exception(e); span.set_status(trace.Status(trace.StatusCode.ERROR, "DB Error"))
            if isinstance(e, IntegrityError):
                 db.rollback(); logger.warning(f"Cannot delete User {user_id} due to refs."); abort(409, "Cannot delete user: refs exist.")
            else: _handle_sqlalchemy_error(e, f"deleting user {user_id}", db)
        except Exception as e:
             logger.error("User deletion failed due to unexpected error", target_user_id=user_id, username=username_for_log, performed_by_user_id=calling_user_id, event_type="USER_DELETE_FAILURE", reason="unknown", exc_info=True)
             span.record_exception(e); span.set_status(trace.Status(trace.StatusCode.ERROR, "Unknown Error"))
             abort(500, "An unexpected error occurred during user deletion.")


# --- (Rest of service functions) ---
# ... Add similar structured logging, tracing, and metrics where appropriate ...
# ... Remember that input validation, XSS/CSRF protection, rate limiting are typically handled outside this service layer ...

# Example comment for web vulns/rate limiting
# --- Security Note: API Layer Responsibilities ---
# Protection against common web vulnerabilities (e.g., Cross-Site Scripting - XSS,
# Cross-Site Request Forgery - CSRF) and implementation of Rate Limiting
# are typically handled in the web framework layer (e.g., Flask/FastAPI)
# using middleware, specific extensions (like Flask-Limiter, Flask-WTF/Starlette CSRF middleware),
# and appropriate security headers (Content-Security-Policy, X-Frame-Options, etc.).
# Input validation should also be strictly enforced at the API boundary before
# data is passed to these service functions.

# ... (Person, Relationship, Attribute, Media, Event, Source, Citation, Tree Traversal services) ...

# --- End of main.py content ---
