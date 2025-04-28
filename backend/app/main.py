# backend/main.py
import logging
import bcrypt
import os
import json
import uuid
import time # Added for manual timing example
from flask import Flask, abort, request, g
from sqlalchemy import create_engine
from urllib.parse import urljoin
from sqlalchemy.orm import Session, load_only, sessionmaker, joinedload, selectinload
from sqlalchemy.exc import SQLAlchemyError, NoResultFound, IntegrityError
from sqlalchemy import (
    or_, and_, desc, asc, Enum as SQLAlchemyEnum, TypeDecorator, String, Text, func, inspect, text,
    Column, Integer, Boolean, DateTime, Date, ForeignKey, JSON, LargeBinary, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from cryptography.fernet import Fernet, InvalidToken, InvalidSignature
from cryptography.exceptions import InvalidSignature
from typing import Optional, List, Dict, Any, Set
from datetime import date, datetime, timedelta, timezone
from werkzeug.exceptions import HTTPException # Assuming Flask context for abort
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

# --- Flask App Setup ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY", "your_default_secret_key")
# FlaskInstrumentor().instrument_app(app) # Call during app startup
# SQLAlchemyInstrumentor().instrument(engine=db.engine) # Call during app startup
app.config.update(
    SESSION_COOKIE_SECURE=os.environ.get('FLASK_ENV') == 'production',
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(days=7)
)

# --- Logging Setup (Using Structlog) ---
logging.basicConfig(level=logging.INFO, format='%(message)s', handlers=[logging.StreamHandler()])
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.dict_tracebacks, # Render tracebacks better
        # --- OpenTelemetry Log Correlation ---
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
    processor=structlog.processors.JSONRenderer(),
    foreign_pre_chain=[]
)
handler = logging.getLogger().handlers[0]; handler.setFormatter(formatter)
logger = structlog.get_logger() # Use this logger

# --- OpenTelemetry Setup (Conceptual) ---
resource = Resource(attributes={ "service.name": os.getenv("OTEL_SERVICE_NAME", "family-tree-backend") })
def configure_tracer_provider():
    """Configure the tracer provider for OpenTelemetry."""
    pass  # Implement the tracer provider configuration here

def configure_meter_provider():
    """Configure the meter provider for OpenTelemetry."""
    pass  # Implement the meter provider configuration here

# configure_tracer_provider() # Call during app startup
# configure_meter_provider() # Call during app startup
# LoggingInstrumentor().instrument(set_logging_format=True) # Call during app startup
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)
user_registration_counter = meter.create_counter(
    name="app.user.registration",
    description="Counts user registration attempts and successes",
    unit="1"
)
db_operation_duration_histogram = meter.create_histogram(
    name="db.operation.duration",
    description="Records the duration of database operations",
    unit="ms"
)
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
ENCRYPTION_KEY_ENV_VAR = "ENCRYPTION_KEY"
ENCRYPTION_KEY_FILE = "/backend/data/encryption_key.json"

def load_encryption_key():
    """Load encryption key from environment variable or file."""
    key = os.getenv(ENCRYPTION_KEY_ENV_VAR)
    if key:
        return key

    try:
        with open(ENCRYPTION_KEY_FILE, 'r') as f:
            data = json.load(f)
            key_b64 = data.get('key_b64')
            if key_b64:
                logger.info(f"Key [***{key_b64[:6]}] found in JSON file.")
                return key_b64
            else:
                logger.error("Key not found in JSON file.")
                return None
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        logger.error(f"Failed to load encryption key from file: {e}")
        return None

try:
    _encryption_key = load_encryption_key()
    if _encryption_key:
        fernet_suite = Fernet(_encryption_key)
    else:
        logger.critical("Encryption key is missing. Fernet cannot be initialized.")
        fernet_suite = None
except Exception as e:
    logger.critical(f"Failed to init Fernet: {e}")
    fernet_suite = None

if fernet_suite is None:
    logger.critical("ENCRYPTION DISABLED.")

class EncryptedString(TypeDecorator):
    """SQLAlchemy type for encrypted strings"""
    impl = String

    def process_bind_param(self, value, dialect):
        if value is not None and fernet_suite:
            try:
                return fernet_suite.encrypt(value.encode()).decode()
            except Exception as e:
                logger.error("Encryption failed for value.", error=str(e))
                return value
        return value

    def process_result_value(self, value, dialect):
        if value is not None and fernet_suite:
            try:
                return fernet_suite.decrypt(value.encode()).decode()
            except InvalidToken:
                logger.error("Decryption failed for value.")
                return value
        return value

# --- Enums & Models ---
Base = declarative_base()

class RoleEnum(str, enum.Enum):
    user = "user"
    admin = "admin"
    researcher = "researcher"
    guest = "guest"

class RelationshipTypeEnum(str, enum.Enum):
    biological_parent = "biological_parent"
    adoptive_parent = "adoptive_parent"
    step_parent = "step_parent"
    foster_parent = "foster_parent"
    guardian = "guardian"
    spouse_current = "spouse_current"
    spouse_former = "spouse_former"
    partner = "partner"
    biological_child = "biological_child"
    adoptive_child = "adoptive_child"
    step_child = "step_child"
    foster_child = "foster_child"
    sibling_full = "sibling_full"
    sibling_half = "sibling_half"
    sibling_step = "sibling_step"
    sibling_adoptive = "sibling_adoptive"
    other = "other"

class PrivacyLevelEnum(str, enum.Enum):
    inherit = "inherit"
    private = "private"
    public = "public"
    connections = "connections"
    researchers = "researchers"

class MediaTypeEnum(str, enum.Enum):
    photo = "photo"
    document = "document"
    audio = "audio"
    video = "video"
    other = "other"

# Reusing UserRole enum defined earlier for consistency
class UserRole(enum.Enum):
    USER = "user"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    # Use RoleEnum for consistency if possible, otherwise keep UserRole
    # Assuming UserRole from above is the intended one for the service logic
    role = Column(SQLAlchemyEnum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    preferences = Column(JSONB, default=dict)
    profile_image_path = Column(String(255))

    def to_dict(self): # Example method, needs to be defined in the actual model
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class Tree(Base):
    __tablename__ = "trees"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    is_public = Column(Boolean, default=False)
    default_privacy_level = Column(SQLAlchemyEnum(PrivacyLevelEnum), default=PrivacyLevelEnum.private)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class TreeAccess(Base):
    __tablename__ = "tree_access"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_id = Column(UUID(as_uuid=True), ForeignKey("trees.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    access_level = Column(String(50), nullable=False, default="view") # Consider an Enum here too
    granted_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    granted_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("tree_id", "user_id", name="tree_user_unique"),)

class Person(Base):
    __tablename__ = "people"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_id = Column(UUID(as_uuid=True), ForeignKey("trees.id", ondelete="CASCADE"), nullable=False)
    first_name = Column(String(100))
    middle_names = Column(String(255))
    last_name = Column(String(100))
    maiden_name = Column(String(100))
    nickname = Column(String(100))
    gender = Column(String(20)) # Consider Enum
    birth_date = Column(Date)
    birth_date_approx = Column(Boolean, default=False)
    birth_place = Column(String(255))
    death_date = Column(Date)
    death_date_approx = Column(Boolean, default=False)
    death_place = Column(String(255))
    burial_place = Column(String(255))
    privacy_level = Column(SQLAlchemyEnum(PrivacyLevelEnum), default=PrivacyLevelEnum.inherit)
    is_living = Column(Boolean)
    notes = Column(Text)
    custom_attributes = Column(JSONB, default=dict)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Relationship(Base):
    __tablename__ = "relationships"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_id = Column(UUID(as_uuid=True), ForeignKey("trees.id", ondelete="CASCADE"), nullable=False)
    person1_id = Column(UUID(as_uuid=True), ForeignKey("people.id", ondelete="CASCADE"), nullable=False)
    person2_id = Column(UUID(as_uuid=True), ForeignKey("people.id", ondelete="CASCADE"), nullable=False)
    relationship_type = Column(SQLAlchemyEnum(RelationshipTypeEnum), nullable=False)
    start_date = Column(Date)
    end_date = Column(Date)
    certainty_level = Column(Integer) # Consider range/enum
    custom_attributes = Column(JSONB, default=dict)
    notes = Column(Text)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Event(Base):
    __tablename__ = "events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_id = Column(UUID(as_uuid=True), ForeignKey("trees.id", ondelete="CASCADE"), nullable=False)
    person_id = Column(UUID(as_uuid=True), ForeignKey("people.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(100), nullable=False) # Consider Enum
    date = Column(Date)
    date_approx = Column(Boolean, default=False)
    date_range_start = Column(Date)
    date_range_end = Column(Date)
    place = Column(String(255))
    description = Column(Text)
    custom_attributes = Column(JSONB, default=dict)
    privacy_level = Column(SQLAlchemyEnum(PrivacyLevelEnum), default=PrivacyLevelEnum.inherit)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Media(Base):
    __tablename__ = "media"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_id = Column(UUID(as_uuid=True), ForeignKey("trees.id", ondelete="CASCADE"), nullable=False)
    file_path = Column(String(512), nullable=False)
    storage_bucket = Column(String(255), nullable=False)
    media_type = Column(SQLAlchemyEnum(MediaTypeEnum), nullable=False)
    original_filename = Column(String(255))
    file_size = Column(Integer)
    mime_type = Column(String(100))
    title = Column(String(255))
    description = Column(Text)
    date_taken = Column(Date)
    location = Column(String(255))
    media_metadata = Column(JSONB, default=dict)
    privacy_level = Column(SQLAlchemyEnum(PrivacyLevelEnum), default=PrivacyLevelEnum.inherit)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Citation(Base):
    __tablename__ = "citations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_id = Column(UUID(as_uuid=True), ForeignKey("trees.id", ondelete="CASCADE"), nullable=False)
    source_id = Column(UUID(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"), nullable=False) # Assuming link to Media table
    citation_text = Column(Text, nullable=False)
    page_number = Column(String(50))
    confidence_level = Column(Integer) # Consider range/enum
    notes = Column(Text)
    custom_attributes = Column(JSONB, default=dict)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class ActivityLog(Base):
    __tablename__ = "activity_log"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_id = Column(UUID(as_uuid=True), ForeignKey("trees.id")) # Optional tree link
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id")) # Optional user link
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False) # Index this maybe?
    action_type = Column(String(50), nullable=False) # Consider Enum
    previous_state = Column(JSONB)
    new_state = Column(JSONB)
    ip_address = Column(String(50))
    user_agent = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


# --- Placeholder Model Definitions from app.models ---
# These were originally imported from 'app.models'. Ensure they are defined correctly
# (either here or in the actual app.models) and consistent with the services.
# We'll assume the Base and Enum definitions above cover the needs, but verify this.


# --- Utility Functions ---
def _handle_sqlalchemy_error(e: SQLAlchemyError, context: str, db: Session):
    if isinstance(e, IntegrityError):
        if hasattr(e.orig, 'pgcode') and e.orig.pgcode == '23505':  # Unique violation (PostgreSQL-specific)
            if 'users_username_key' in str(e.orig): abort(409, description="Username already exists.")
            elif 'users_email_key' in str(e.orig): abort(409, description="Email already exists.")
            else: abort(409, description=f"Database conflict {context}.")
        elif "NOT NULL constraint failed" in str(e) or "null value in column" in str(e):
            abort(400, description=f"Missing required field during {context}: {e}")
        else:
            abort(409, description=f"Integrity error during {context}.")
    elif isinstance(e, NoResultFound):
        abort(404, description="Resource not found.")
    else:
        abort(500, description=f"Database error {context}.")

def _get_or_404(db: Session, model: Any, model_id: int) -> Any:
    with tracer.start_as_current_span(f"db.get.{model.__name__}") as span:
        span.set_attribute("db.system", "postgresql")
        span.set_attribute(f"{model.__name__}.id", model_id)
        try:
            start_time = time.monotonic()
            query = db.query(model)
            obj = query.filter(model.id == model_id).one_or_none()
            duration = (time.monotonic() - start_time) * 1000
            db_operation_duration_histogram.record(duration, {"db.operation": f"get.{model.__name__}", "db.status": "success"})
            if obj is None:
                logger.warning("Resource not found", model_name=model.__name__, model_id=model_id)
                span.set_attribute("db.found", False)
                abort(404, description=f"{model.__name__} not found")
            span.set_attribute("db.found", True)
            return obj
        except SQLAlchemyError as e:
            duration = (time.monotonic() - start_time) * 1000
            db_operation_duration_histogram.record(duration, {"db.operation": f"get.{model.__name__}", "db.status": "error"})
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, f"DB Error: {e}"))
            _handle_sqlalchemy_error(e, f"fetching {model.__name__} ID {model_id}", db)
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Non-DB Error"))
            raise e

import re

def _validate_password_complexity(password: str) -> None:
    """Validates the complexity of a password."""
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if not re.search(r'[A-Z]', password):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not re.search(r'[a-z]', password):
        raise ValueError("Password must contain at least one lowercase letter.")
    if not re.search(r'[0-9]', password):
        raise ValueError("Password must contain at least one digit.")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValueError("Password must contain at least one special character.")

def _hash_password(password: str) -> str:
    """Hashes a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def _verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

# --- User Services ---

def register_user_db(db: Session, user_data: dict) -> Dict[str, Any]:
    """Registers a new user, hashing the password."""
    with tracer.start_as_current_span("service.register_user") as span:
        username = user_data.get('username', '[unknown]')
        email = user_data.get('email', '[unknown]')
        logger.info("User registration attempt", username=username, email=email)

        plain_password = user_data.get('password')
        if not plain_password:
            logger.warning("Registration failed: Missing password", username=username, email=email)
            abort(400, description="Password is required.")

        try:
            _validate_password_complexity(plain_password)
        except ValueError as e:
            logger.warning("Registration failed: Password complexity requirements not met", reason=str(e), username=username)
            abort(400, description=str(e))

        hashed_password = _hash_password(plain_password)
        create_data = user_data.copy()
        create_data.pop('password', None)
        create_data['password_hash'] = hashed_password
        create_data['created_at'] = datetime.utcnow()
        create_data['updated_at'] = datetime.utcnow() # Add updated_at on creation
        create_data['is_active'] = True
        create_data.setdefault('role', UserRole.USER)

        try:
            # Ensure role is the correct Enum type
            create_data['role'] = UserRole(create_data['role'])
        except ValueError:
            logger.error("Registration failed: Invalid role specified", role=create_data['role'])
            abort(400, description=f"Invalid role: {create_data['role']}")

        try:
            new_user = User(**create_data)
            db.add(new_user)
            db.commit()
            db.refresh(new_user)

            logger.info(
                "User registration successful",
                user_id=new_user.id,
                username=username,
                email=email,
                assigned_role=new_user.role.value,
                event_type="USER_REGISTRATION_SUCCESS"
            )
            span.set_attribute("app.user.id", new_user.id)
            user_registration_counter.add(1, {"registration.type": "success"})

            user_dict = new_user.to_dict()
            user_dict.pop('password_hash', None)
            return user_dict
        except SQLAlchemyError as e:
            logger.error(
                "User registration failed due to database error",
                username=username, email=email, event_type="USER_REGISTRATION_FAILURE",
                reason="database_error", exc_info=False
            )
            user_registration_counter.add(1, {"registration.type": "failure", "reason": "db_error"})
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "DB Error"))
            _handle_sqlalchemy_error(e, f"registering user {username}", db)
        except Exception as e:
            logger.error(
                "User registration failed due to unexpected error",
                username=username, email=email, event_type="USER_REGISTRATION_FAILURE",
                reason="unknown", exc_info=True
            )
            user_registration_counter.add(1, {"registration.type": "failure", "reason": "unknown"})
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Unknown Error"))
            abort(500, "An unexpected error occurred during registration.")

def authenticate_user_db(db: Session, identifier: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticates a user by username or email and password."""
    with tracer.start_as_current_span("service.authenticate_user") as span:
        span.set_attribute("app.user.identifier", identifier)
        logger.info("User authentication attempt", identifier=identifier, event_type="USER_AUTHENTICATION_ATTEMPT")

        try:
            # Load only necessary fields for auth check
            user_obj = db.query(User).options(
                load_only(User.id, User.username, User.password_hash, User.is_active, User.last_login) # Added last_login
            ).filter(
                or_(User.username == identifier, User.email == identifier)
            ).first()

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
                logger.info("User authentication successful", user_id=user_obj.id, username=user_obj.username, event_type="USER_AUTHENTICATION_SUCCESS")
                span.set_attribute("app.user.id", user_obj.id)
                span.set_attribute("app.auth.success", True)
                # Update last login time
                user_obj.last_login = datetime.utcnow()
                db.commit()
                db.refresh(user_obj) # Refresh to get the updated last_login if needed in the returned dict
                # Fetch full user details after successful auth
                full_user = db.query(User).filter(User.id == user_obj.id).one()
                user_dict = full_user.to_dict()
                user_dict.pop('password_hash', None)
                return user_dict
            else:
                logger.warning("User authentication failed", identifier=identifier, reason=failure_reason, event_type="USER_AUTHENTICATION_FAILURE")
                auth_failure_counter.add(1, {"reason": failure_reason})
                span.set_attribute("app.auth.success", False)
                span.set_attribute("app.auth.failure_reason", failure_reason)
                return None
        except SQLAlchemyError as e:
            logger.error("Database error during authentication", identifier=identifier, event_type="USER_AUTHENTICATION_FAILURE", reason="database_error", exc_info=True)
            auth_failure_counter.add(1, {"reason": "database_error"})
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "DB Error"))
            abort(500, "An error occurred during authentication.")
        except Exception as e:
            logger.error("Unknown error during authentication", identifier=identifier, event_type="USER_AUTHENTICATION_FAILURE", reason="unknown", exc_info=True)
            auth_failure_counter.add(1, {"reason": "unknown"})
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Unknown Error"))
            abort(500, "An unexpected error occurred during authentication.")


def update_user_role_db(db: Session, user_id: int, new_role: str) -> Dict[str, Any]:
    """Updates only the role of a specific user."""
    with tracer.start_as_current_span("service.update_user_role") as span:
        span.set_attribute("app.user.id", user_id)
        span.set_attribute("app.user.new_role", new_role)

        calling_user_id = getattr(g, 'user_id', '[unknown]') # Example of getting caller context

        try:
            # Get the user first using the utility function
            user_obj = _get_or_404(db, User, user_id)
            original_role = user_obj.role.value # Assuming role is an enum

            span.set_attribute("app.user.original_role", original_role)
            logger.info(
                "Attempting role update",
                target_user_id=user_id, new_role=new_role, original_role=original_role,
                performed_by_user_id=calling_user_id, event_type="USER_ROLE_CHANGE_ATTEMPT"
            )

            try:
                # Convert string role to Enum
                role_enum = UserRole(new_role)
            except ValueError:
                logger.error("Role update failed: Invalid role specified", invalid_role=new_role)
                abort(400, description=f"Invalid role specified: {new_role}")

            if user_obj.role != role_enum:
                user_obj.role = role_enum
                user_obj.updated_at = datetime.utcnow() # Update timestamp
                db.commit()
                db.refresh(user_obj)

                logger.info(
                    "User role updated successfully",
                    target_user_id=user_id, username=user_obj.username,
                    original_role=original_role, new_role=new_role,
                    performed_by_user_id=calling_user_id, event_type="USER_ROLE_CHANGE_SUCCESS"
                )
                role_change_counter.add(1, {"status": "success", "role": new_role})
            else:
                logger.info(
                    "User role update skipped: User already has the specified role",
                    target_user_id=user_id, role=new_role, event_type="USER_ROLE_CHANGE_NOOP"
                )
                role_change_counter.add(1, {"status": "noop", "role": new_role})

            user_dict = user_obj.to_dict()
            user_dict.pop('password_hash', None)
            return user_dict

        except SQLAlchemyError as e:
            logger.error(
                "User role update failed due to database error",
                target_user_id=user_id, new_role=new_role, performed_by_user_id=calling_user_id,
                event_type="USER_ROLE_CHANGE_FAILURE", reason="database_error", exc_info=False
            )
            role_change_counter.add(1, {"status": "failure", "role": new_role, "reason": "db_error"})
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "DB Error"))
            _handle_sqlalchemy_error(e, f"updating role for user ID {user_id}", db)
        except Exception as e:
            # Check for specific exceptions like HTTPException from _get_or_404 if needed
            if isinstance(e, HTTPException) and e.code == 404:
                 # Already handled by _get_or_404, just re-raise or log differently
                 logger.warning(f"Role update failed: User {user_id} not found.")
                 raise e # Re-raise the abort
            logger.error(
                "User role update failed due to unexpected error",
                target_user_id=user_id, new_role=new_role, performed_by_user_id=calling_user_id,
                event_type="USER_ROLE_CHANGE_FAILURE", reason="unknown", exc_info=True
            )
            role_change_counter.add(1, {"status": "failure", "role": new_role, "reason": "unknown"})
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Unknown Error"))
            abort(500, "An unexpected error occurred during role update.")


def delete_user_db(db: Session, user_id: int) -> bool:
    """Deletes a user."""
    with tracer.start_as_current_span("service.delete_user") as span:
        span.set_attribute("app.user.id", user_id)
        calling_user_id = getattr(g, 'user_id', '[unknown]')
        logger.info("Attempting user deletion", target_user_id=user_id, performed_by_user_id=calling_user_id, event_type="USER_DELETE_ATTEMPT")

        # Use _get_or_404 to handle not found case and log internally
        user_obj = _get_or_404(db, User, user_id)
        username_for_log = user_obj.username # Get username before potential deletion

        try:
            db.delete(user_obj)
            db.commit()
            logger.info("User deleted successfully", target_user_id=user_id, username=username_for_log, performed_by_user_id=calling_user_id, event_type="USER_DELETE_SUCCESS")
            return True
        except SQLAlchemyError as e:
            db.rollback() # Rollback on error
            logger.error(
                "User deletion failed due to database error", target_user_id=user_id, username=username_for_log,
                performed_by_user_id=calling_user_id, event_type="USER_DELETE_FAILURE", reason="database_error", exc_info=False
            )
            if isinstance(e, IntegrityError):
                # More specific check for FK violation if possible based on DB dialect
                if 'foreign key constraint' in str(e.orig).lower():
                    logger.warning(f"Cannot delete User {user_id} ({username_for_log}) due to foreign key constraints.")
                    abort(409, "Cannot delete user: related data exists.")
                else:
                    logger.warning(f"Cannot delete User {user_id} ({username_for_log}) due to database integrity issues.")
                    abort(409, "Cannot delete user: integrity issues.")
            else:
                _handle_sqlalchemy_error(e, f"deleting user {user_id} ({username_for_log})", db)
        except Exception as e:
            db.rollback() # Rollback on unexpected error
            # Check for specific exceptions like HTTPException from _get_or_404
            if isinstance(e, HTTPException) and e.code == 404:
                logger.warning(f"User deletion failed: User {user_id} not found.")
                raise e # Re-raise the abort
            logger.error(
                "User deletion failed due to unexpected error", target_user_id=user_id, username=username_for_log,
                performed_by_user_id=calling_user_id, event_type="USER_DELETE_FAILURE", reason="unknown", exc_info=True
            )
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Unknown Error"))
            abort(500, "An unexpected error occurred during user deletion.")


# Example comment for web vulns/rate limiting (remains relevant)
# --- Security Note: API Layer Responsibilities ---

# --- (Rest of service functions template) ---
def example_service_function(db: Session, example_param: str) -> Dict[str, Any]:
    """Example service function template."""
    with tracer.start_as_current_span("service.example_function") as span:
        span.set_attribute("example.param", example_param)
        logger.info("Example service function called", example_param=example_param)
        try:
            # Perform database operations or business logic here
            result = {"example_key": "example_value"}
            return result
        except SQLAlchemyError as e:
            logger.error("Database error in example service function", exc_info=True)
            _handle_sqlalchemy_error(e, "example_service_function", db)
        except Exception as e:
            logger.error("Unexpected error in example service function", exc_info=True)
            abort(500, "An unexpected error occurred in the example service function.")

# --- Database Setup ---
DATABASE_URL = os.environ.get('DATABASE_URL')
logger.info(f"Database URL: {'<set>' if DATABASE_URL else '<not set>'}") # Avoid logging full URL potentially
if not DATABASE_URL:
    logger.critical("DATABASE_URL environment variable is not set. Exiting.")
    exit(1)

# Create the SQLAlchemy engine and session factory
engine = create_engine(DATABASE_URL, pool_size=32, echo=False) # echo=False is common for production
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- Database Initialization Functions ---
def create_tables(engine_to_use):
    """Creates all tables defined in Base metadata."""
    logger.info("Attempting to create database tables if they don't exist...")
    try:
        Base.metadata.create_all(bind=engine_to_use)
        logger.info("Database tables check/creation complete.")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}", exc_info=True)
        # Decide if the application should exit or continue without tables
        raise # Re-raise the exception to potentially halt startup if critical

def populate_initial_data(session_factory):
    """Populates the database with initial data if necessary."""
    logger.info("Checking if initial data population is needed...")
    session = session_factory()
    try:
        # Check if any user exists
        user_count = session.query(func.count(User.id)).scalar()
        if user_count == 0:
            logger.info("No users found. Populating initial admin data...")
            # **SECURITY WARNING:** Never hardcode passwords. Use environment variables or a secure config system.
            # Hash the password securely.
            admin_password = os.getenv("INITIAL_ADMIN_PASSWORD", "default_unsafe_password")
            if admin_password == "default_unsafe_password":
                 logger.warning("Using default unsafe password for initial admin user. SET INITIAL_ADMIN_PASSWORD env var.")
            hashed_password = _hash_password(admin_password)

            admin_user = User(
                username=os.getenv("INITIAL_ADMIN_USERNAME", "admin"),
                email=os.getenv("INITIAL_ADMIN_EMAIL", "admin@example.com"),
                password_hash=hashed_password,
                # Use the correct Enum based on model definition (UserRole or RoleEnum)
                role=UserRole.ADMIN, # Or RoleEnum.admin if that's the model's enum
                is_active=True,
                email_verified=True # Assume admin email is verified initially
            )
            session.add(admin_user)
            session.commit()
            logger.info(f"Initial admin user '{admin_user.username}' created successfully.")
        else:
            logger.info(f"Database already contains {user_count} users. Skipping initial data population.")
    except SQLAlchemyError as e:
        logger.error(f"Database error during initial data population: {e}", exc_info=True)
        session.rollback()
    except Exception as e:
        logger.error(f"Unexpected error during initial data population: {e}", exc_info=True)
        session.rollback() # Rollback on any error
    finally:
        session.close()

def initialize_database(engine_to_use, session_factory):
    """Checks table existence and initializes DB if needed."""
    logger.info("Initializing database...")
    try:
        inspector = inspect(engine_to_use)
        required_tables = Base.metadata.tables.keys() # Get tables defined in models
        existing_tables = inspector.get_table_names()

        missing_tables = set(required_tables) - set(existing_tables)

        if not existing_tables or missing_tables:
            if not existing_tables:
                 logger.info("No tables found in the database.")
            else:
                 logger.warning(f"Missing required tables: {missing_tables}. Attempting creation.")
            create_tables(engine_to_use) # Create tables
            populate_initial_data(session_factory) # Populate data *after* tables are created
        else:
            logger.info("Database tables already exist. Skipping creation and initial data population.")
        logger.info("Database initialization complete.")
    except Exception as e:
        logger.critical(f"Database initialization failed: {e}", exc_info=True)
        # Depending on severity, might want to exit
        # exit(1)

# Call the database initialization logic during app startup
# Ensure this runs *after* models are defined and engine/session are created
initialize_database(engine, SessionLocal)


# --- Flask Request Lifecycle Hooks ---
@app.before_request
def before_request_hook(): # Renamed slightly to avoid conflict if imported elsewhere
    """Initialize the database session and attach it to Flask's `g` object."""
    g.db = SessionLocal()
    logger.debug("Database session opened for request.") # Example debug log

@app.teardown_appcontext
def teardown_db_hook(exception=None): # Renamed slightly
    """Close the database session after the request is complete."""
    db = g.pop('db', None)
    if db is not None:
        try:
            # Optionally commit or rollback based on exception
            # if exception is None:
            #     db.commit() # Be careful with auto-commit
            # else:
            #     db.rollback()
            db.close()
            logger.debug("Database session closed for request.")
        except Exception as e:
             logger.error(f"Error closing database session: {e}", exc_info=True)
    if exception:
        # Log the exception that occurred during the request teardown if desired
        logger.error(f"Exception during request teardown: {exception}", exc_info=True)


# --- Health Check Endpoint ---
@app.route('/health', methods=['GET'])
def health_check(): # Renamed slightly
    """Performs health checks on the application and its dependencies."""
    logger.info("Health check requested.")
    service_status = "healthy"
    db_status = "unknown"
    db_latency_ms = None
    dependencies = {}

    # Check Database Connection and Latency
    start_time = time.monotonic()
    try:
        with engine.connect() as connection:
            # Simple query to check connectivity and basic function
            connection.execute(text("SELECT 1"))
            db_status = "healthy"
    except SQLAlchemyError as e:
        db_status = "unhealthy"
        service_status = "unhealthy" # If DB is critical, service is unhealthy
        logger.error(f"Database health check failed: {e}", exc_info=False) # Don't need full trace usually
    except Exception as e:
        db_status = "error"
        service_status = "unhealthy"
        logger.error(f"Unexpected error during DB health check: {e}", exc_info=True)
    finally:
        end_time = time.monotonic()
        db_latency_ms = (end_time - start_time) * 1000

    dependencies["database"] = {
        "status": db_status,
        "latency_ms": round(db_latency_ms, 2) if db_latency_ms is not None else None
    }

    # Add checks for other critical dependencies (e.g., external APIs, message queues) here

    response_data = {
        "status": service_status,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "dependencies": dependencies
    }

    # Return 503 if unhealthy, 200 if healthy
    http_status = 200 if service_status == "healthy" else 503
    return response_data, http_status

# --- Main Execution Guard ---
if __name__ == '__main__':
    # Use environment variables for host and port, provide defaults
    host = os.environ.get('FLASK_RUN_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_RUN_PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() in ['true', '1', 't']

    logger.info(f"Starting Flask server on {host}:{port} (Debug: {debug_mode})")
    # Use Flask's built-in server for development, Gunicorn/uWSGI for production
    app.run(host=host, port=port, debug=debug_mode)