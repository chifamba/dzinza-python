# backend/main.py
import logging
import bcrypt
import os
import json
import uuid
import time
import re # Import regex for password validation
import secrets # For generating secure tokens
from flask import Flask, abort, request, g, session, jsonify # Import jsonify
from sqlalchemy import create_engine
from urllib.parse import urljoin
from sqlalchemy.orm import Session, load_only, sessionmaker, joinedload, selectinload
from sqlalchemy.exc import SQLAlchemyError, NoResultFound, IntegrityError
from sqlalchemy import (
    or_, and_, desc, asc, Enum as SQLAlchemyEnum, TypeDecorator, String, Text, func, inspect, text,
    Column, Integer, Boolean, DateTime, Date, ForeignKey, JSON, LargeBinary, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB # Ensure UUID and JSONB are imported
from sqlalchemy.ext.declarative import declarative_base
from cryptography.fernet import Fernet, InvalidToken, InvalidSignature
from cryptography.exceptions import InvalidSignature
from typing import Optional, List, Dict, Any, Set
from datetime import date, datetime, timedelta, timezone
from werkzeug.exceptions import HTTPException
from collections import deque
import enum
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps # Import wraps for decorators

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
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

# --- Load Environment Variables ---
load_dotenv()

# --- Flask App Setup ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY", "your_default_secret_key")
app.config.update(
    SESSION_COOKIE_SECURE=os.environ.get('FLASK_ENV') == 'production',
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(days=7)
)

# --- Rate Limiter Setup ---
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
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
        structlog.processors.dict_tracebacks,
        structlog.contextvars.merge_contextvars,
        structlog.processors.CallsiteParameterAdder(
            parameters={
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.LINENO,
            },
        ),
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
logger = structlog.get_logger()

# --- OpenTelemetry Setup (Conceptual) ---
resource = Resource(attributes={ "service.name": os.getenv("OTEL_SERVICE_NAME", "family-tree-backend") })
# Configure Tracer Provider
trace.set_tracer_provider(TracerProvider(resource=resource))
otlp_exporter_trace = OTLPSpanExporter() # Assuming default endpoint or configured via OTEL_EXPORTER_OTLP_ENDPOINT
# span_processor = BatchSpanProcessor(otlp_exporter_trace)
span_processor = BatchSpanProcessor(
    otlp_exporter_trace,
    max_export_batch_size=512,
    max_queue_size=2048,
    export_timeout_millis=30000,
)
trace.get_tracer_provider().add_span_processor(span_processor)

# Configure Meter Provider
otlp_exporter_metric = OTLPMetricExporter()  # Assuming default endpoint
metric_reader = PeriodicExportingMetricReader(otlp_exporter_metric)

metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[metric_reader]))

# Instrument Flask and SQLAlchemy
FlaskInstrumentor().instrument_app(app)
# SQLAlchemyInstrumentor().instrument(engine=db.engine) # This needs to be called after engine is created

LoggingInstrumentor().instrument(set_logging_format=True)

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
auth_failure_counter = meter.create_counter(
    name="app.auth.failures",
    description="Counts authentication failures",
    unit="1"
)
role_change_counter = meter.create_counter(
    name="app.auth.role_changes",
    description="Counts user role changes",
    unit="1"
)
# --- End OpenTelemetry Setup ---

# --- Encryption Setup ---
ENCRYPTION_KEY_ENV_VAR = "ENCRYPTION_KEY"
ENCRYPTION_KEY_FILE = "/backend/data/encryption_key.json" # Assuming this path is correct within the container

def load_encryption_key():
    """Load encryption key from environment variable or file."""
    key = os.getenv(ENCRYPTION_KEY_ENV_VAR)
    if key:
        logger.info("Encryption key loaded from environment variable.")
        return key

    # Construct the absolute path to the key file
    # Assuming the script is run from the backend/app directory within the container
    # and the data directory is mounted at /backend/data
    key_file_abs_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'encryption_key.json')
    logger.info(f"Attempting to load encryption key from file: {key_file_abs_path}")

    try:
        with open(key_file_abs_path, 'r') as f:
            data = json.load(f)
            key_b64 = data.get('key_b64')
            if key_b64:
                logger.info(f"Key [***{key_b64[:6]}] found in JSON file.")
                return key_b64
            else:
                logger.error("Key not found in JSON file.")
                return None
    except FileNotFoundError:
        logger.warning(f"Encryption key file not found at {key_file_abs_path}.")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode encryption key JSON file: {e}")
        return None
    except KeyError:
        logger.error("Encryption key file is missing 'key_b64'.")
        return None
    except Exception as e:
        logger.error(f"Unexpected error loading encryption key from file: {e}")
        return None


try:
    _encryption_key = load_encryption_key()
    if _encryption_key:
        fernet_suite = Fernet(_encryption_key)
        logger.info("Fernet initialized successfully.")
    else:
        logger.critical("Encryption key is missing. Fernet cannot be initialized.")
        fernet_suite = None
except Exception as e:
    logger.critical(f"Failed to init Fernet: {e}", exc_info=True)
    fernet_suite = None

if fernet_suite is None:
    logger.critical("ENCRYPTION DISABLED.")

class EncryptedString(TypeDecorator):
    """SQLAlchemy type for encrypted strings"""
    impl = String

    def process_bind_param(self, value, dialect):
        if value is not None and fernet_suite:
            try:
                # Ensure value is a string before encoding
                encoded_value = str(value).encode('utf-8')
                return fernet_suite.encrypt(encoded_value).decode('utf-8')
            except Exception as e:
                logger.error("Encryption failed for value.", error=str(e), exc_info=True)
                # Depending on policy, you might want to raise an error or store unencrypted
                # For now, return original value as a fallback (log error!)
                return value
        return value

    def process_result_value(self, value, dialect):
        if value is not None and fernet_suite:
            try:
                # Ensure value is a string before encoding
                encoded_value = str(value).encode('utf-8')
                return fernet_suite.decrypt(encoded_value).decode('utf-8')
            except (InvalidToken, InvalidSignature) as e:
                logger.error("Decryption failed for value.", error=str(e), exc_info=True)
                # Depending on policy, return placeholder, original value, or raise error
                return value # Return original value if decryption fails
            except Exception as e:
                 logger.error("Unexpected error during decryption.", error=str(e), exc_info=True)
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
    role = Column(SQLAlchemyEnum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    preferences = Column(JSONB, default=dict)
    profile_image_path = Column(String(255))
    # Added for password reset functionality
    password_reset_token = Column(String(255), unique=True)
    password_reset_expires = Column(DateTime)


    def to_dict(self, include_sensitive=False):
        """Converts User object to dictionary, excluding sensitive info by default."""
        data = {
            "id": str(self.id), # Convert UUID to string
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role.value, # Convert Enum to string value
            "is_active": self.is_active,
            "email_verified": self.email_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "preferences": self.preferences,
            "profile_image_path": self.profile_image_path,
        }
        if include_sensitive:
             data['password_hash'] = self.password_hash
             data['password_reset_token'] = self.password_reset_token
             data['password_reset_expires'] = self.password_reset_expires.isoformat() if self.password_reset_expires else None
        return data


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

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "created_by": str(self.created_by),
            "is_public": self.is_public,
            "default_privacy_level": self.default_privacy_level.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class TreeAccess(Base):
    __tablename__ = "tree_access"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_id = Column(UUID(as_uuid=True), ForeignKey("trees.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    access_level = Column(String(50), nullable=False, default="view") # Consider an Enum here too
    granted_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    granted_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("tree_id", "user_id", name="tree_user_unique"),)

    def to_dict(self):
        return {
            "id": str(self.id),
            "tree_id": str(self.tree_id),
            "user_id": str(self.user_id),
            "access_level": self.access_level,
            "granted_by": str(self.granted_by) if self.granted_by else None,
            "granted_at": self.granted_at.isoformat() if self.granted_at else None,
        }


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
    # slug = Column(String(255), GENERATED ALWAYS AS (...), STORED) # Add slug if needed
    # CONSTRAINT valid_gender CHECK (gender IN ('male', 'female', 'other', 'unknown')), # Add check constraints
    # CONSTRAINT valid_privacy_level CHECK (privacy_level IN (...)) # Add check constraints

    def to_dict(self):
        return {
            "id": str(self.id),
            "tree_id": str(self.tree_id),
            "first_name": self.first_name,
            "middle_names": self.middle_names,
            "last_name": self.last_name,
            "maiden_name": self.maiden_name,
            "nickname": self.nickname,
            "gender": self.gender,
            "birth_date": self.birth_date.isoformat() if self.birth_date else None,
            "birth_date_approx": self.birth_date_approx,
            "birth_place": self.birth_place,
            "death_date": self.death_date.isoformat() if self.death_date else None,
            "death_date_approx": self.death_date_approx,
            "death_place": self.death_place,
            "burial_place": self.burial_place,
            "privacy_level": self.privacy_level.value,
            "is_living": self.is_living,
            "notes": self.notes,
            "custom_attributes": self.custom_attributes,
            "created_by": str(self.created_by),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


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
    # CONSTRAINT different_people CHECK (person1_id != person2_id) # Add check constraints
    # Add unique constraint on (tree_id, LEAST(person1_id, person2_id), GREATEST(person1_id, person2_id), relationship_type) if needed

    def to_dict(self):
        return {
            "id": str(self.id),
            "tree_id": str(self.tree_id),
            "person1_id": str(self.person1_id),
            "person2_id": str(self.person2_id),
            "relationship_type": self.relationship_type.value,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "certainty_level": self.certainty_level,
            "custom_attributes": self.custom_attributes,
            "notes": self.notes,
            "created_by": str(self.created_by),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


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
    # place_coordinates = Column(POINT) # Add if PostGIS is used
    description = Column(Text)
    custom_attributes = Column(JSONB, default=dict)
    privacy_level = Column(SQLAlchemyEnum(PrivacyLevelEnum), default=PrivacyLevelEnum.inherit)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    # def to_dict(self): ... # Add to_dict method


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
    # location_coordinates = Column(POINT) # Add if PostGIS is used
    media_metadata = Column(JSONB, default=dict)
    privacy_level = Column(SQLAlchemyEnum(PrivacyLevelEnum), default=PrivacyLevelEnum.inherit)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    # def to_dict(self): ... # Add to_dict method

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

    # def to_dict(self): ... # Add to_dict method


class ActivityLog(Base):
    __tablename__ = "activity_log"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_id = Column(UUID(as_uuid=True), ForeignKey("trees.id", ondelete="SET NULL")) # Optional tree link, SET NULL on tree delete
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")) # Optional user link, SET NULL on user delete
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False) # Index this maybe?
    action_type = Column(String(50), nullable=False) # Consider Enum
    previous_state = Column(JSONB)
    new_state = Column(JSONB)
    ip_address = Column(String(50)) # Consider using INET type if PostGIS is available
    user_agent = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # def to_dict(self): ... # Add to_dict method


# --- Utility Functions ---
def _handle_sqlalchemy_error(e: SQLAlchemyError, context: str, db: Session):
    """Handles SQLAlchemy errors and aborts with appropriate HTTP status."""
    db.rollback() # Always rollback on error
    if isinstance(e, IntegrityError):
        # Attempt to extract more specific error details if available
        detail = getattr(e.orig, 'diag', None) # PostgreSQL specific detail
        constraint_name = detail.constraint_name if detail else None

        if constraint_name == 'users_username_key':
            logger.warning(f"Integrity Error: Duplicate username during {context}", exc_info=False)
            abort(409, description="Username already exists.")
        elif constraint_name == 'users_email_key':
            logger.warning(f"Integrity Error: Duplicate email during {context}", exc_info=False)
            abort(409, description="Email already exists.")
        elif constraint_name == 'tree_user_unique':
             logger.warning(f"Integrity Error: Duplicate tree access entry during {context}", exc_info=False)
             abort(409, description="User already has access to this tree.")
        elif 'foreign key constraint' in str(e.orig).lower():
             logger.warning(f"Integrity Error: Foreign key violation during {context}", exc_info=False)
             abort(409, description=f"Cannot complete action due to related data.")
        elif "NOT NULL constraint failed" in str(e) or "null value in column" in str(e.orig):
            logger.warning(f"Integrity Error: Not null constraint failed during {context}", exc_info=False)
            abort(400, description=f"Missing required field during {context}.")
        else:
            logger.error(f"Unhandled Integrity Error during {context}", exc_info=True)
            abort(409, description=f"Database conflict during {context}.")
    elif isinstance(e, NoResultFound):
        logger.warning(f"No Result Found during {context}", exc_info=False)
        abort(404, description="Resource not found.")
    else:
        logger.error(f"Unhandled SQLAlchemy Error during {context}", exc_info=True)
        abort(500, description=f"Database error during {context}.")

def _get_or_404(db: Session, model: Any, model_id: uuid.UUID, tree_id: Optional[uuid.UUID] = None) -> Any:
    """Retrieves an object by ID, optionally filtered by tree_id, or aborts with 404."""
    with tracer.start_as_current_span(f"db.get.{model.__name__}") as span:
        span.set_attribute("db.system", "postgresql")
        span.set_attribute(f"{model.__name__}.id", str(model_id))
        if tree_id:
             span.set_attribute("tree.id", str(tree_id))

        try:
            start_time = time.monotonic()
            query = db.query(model)
            if tree_id and hasattr(model, 'tree_id'):
                 query = query.filter(model.tree_id == tree_id)

            obj = query.filter(model.id == model_id).one_or_none()

            duration = (time.monotonic() - start_time) * 1000
            db_operation_duration_histogram.record(duration, {"db.operation": f"get.{model.__name__}", "db.status": "success"})

            if obj is None:
                logger.warning("Resource not found", model_name=model.__name__, model_id=model_id, tree_id=tree_id)
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
            logger.error(f"Unexpected error fetching {model.__name__} ID {model_id}", exc_info=True)
            abort(500, "An unexpected error occurred.")


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
    # Allow a broader range of special characters
    if not re.search(r'[!@#$%^&*()_+=\-[\]{};\':"\\|,.<>/?`~]', password):
        raise ValueError("Password must contain at least one special character.")

def _hash_password(password: str) -> str:
    """Hashes a password using bcrypt."""
    # Use a strong, standard rounds value (e.g., 12)
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')

def _verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    # Handle potential hashing errors or invalid hash format gracefully
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception as e:
        logger.error("Error during password verification", exc_info=True)
        return False # Assume failure if verification process errors


# --- Authentication/Authorization Decorators ---

def require_auth(f):
    """Decorator to protect endpoints requiring authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            logger.warning("Authentication required, session not found.")
            abort(401, description="Authentication required.")
        # Optional: Load user object into g context here if needed frequently
        # g.user = g.db.query(User).filter(User.id == uuid.UUID(session['user_id'])).one_or_none()
        # if g.user is None:
        #     session.clear() # Clear invalid session
        #     abort(401, description="Invalid session.")
        return f(*args, **kwargs)
    return decorated_function

def require_admin(f):
    """Decorator to protect endpoints requiring admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != UserRole.ADMIN.value:
            logger.warning("Admin access required, but user is not admin.", user_id=session.get('user_id'), role=session.get('role'))
            abort(403, description="Admin access required.")
        return f(*args, **kwargs)
    return decorated_function

def require_tree_access(level: str = 'view'):
    """Decorator to protect endpoints requiring specific tree access level."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                logger.warning("Tree access required, but user not authenticated.")
                abort(401, description="Authentication required.")

            user_id = uuid.UUID(session['user_id'])
            tree_id_str = session.get('active_tree_id')

            if not tree_id_str:
                 logger.warning("Tree access required, but no active tree set in session.", user_id=user_id)
                 abort(400, description="No active tree selected.")

            try:
                tree_id = uuid.UUID(tree_id_str)
            except ValueError:
                 logger.warning("Tree access required, but active_tree_id in session is invalid UUID.", user_id=user_id, active_tree_id=tree_id_str)
                 session.pop('active_tree_id', None) # Clear invalid state
                 abort(400, description="Invalid active tree ID in session.")

            db = g.db
            # Check if user is the creator of the tree or has explicit access
            tree = db.query(Tree).filter(Tree.id == tree_id).one_or_none()

            if not tree:
                logger.warning("Tree access check failed: Tree not found.", user_id=user_id, tree_id=tree_id)
                session.pop('active_tree_id', None) # Clear session state for non-existent tree
                abort(404, description="Active tree not found.")

            has_access = False
            access_level = None

            if tree.created_by == user_id:
                 has_access = True
                 access_level = 'admin' # Creator has full control
            elif tree.is_public and level == 'view':
                 has_access = True
                 access_level = 'view' # Public tree allows view access
            else:
                tree_access = db.query(TreeAccess).filter(
                    TreeAccess.tree_id == tree_id,
                    TreeAccess.user_id == user_id
                ).one_or_none()

                if tree_access:
                    access_level = tree_access.access_level
                    # Check if granted access level meets the required level
                    # Simple hierarchy: admin > edit > view
                    if level == 'view' and access_level in ['view', 'edit', 'admin']:
                        has_access = True
                    elif level == 'edit' and access_level in ['edit', 'admin']:
                        has_access = True
                    elif level == 'admin' and access_level == 'admin':
                        has_access = True

            if not has_access:
                logger.warning("Tree access denied.", user_id=user_id, tree_id=tree_id, required_level=level, granted_level=access_level)
                abort(403, description=f"Access denied to tree {tree_id}.")

            # Store tree and access level in g context for easy access in the route handler
            g.active_tree = tree
            g.tree_access_level = access_level
            g.active_tree_id = tree_id # Store UUID directly

            return f(*args, **kwargs)
        return decorated_function
    return decorator


# --- User Services (Extended) ---

# register_user_db, authenticate_user_db, update_user_role_db, delete_user_db remain the same

def get_all_users_db(db: Session) -> List[Dict[str, Any]]:
    """Retrieves all users (admin only)."""
    with tracer.start_as_current_span("service.get_all_users") as span:
        logger.info("Fetching all users from DB.")
        try:
            users = db.query(User).all()
            # Return list of user dictionaries, excluding sensitive data
            return [u.to_dict() for u in users]
        except SQLAlchemyError as e:
            logger.error("Database error fetching all users", exc_info=True)
            _handle_sqlalchemy_error(e, "fetching all users", db)
        except Exception as e:
            logger.error("Unexpected error fetching all users", exc_info=True)
            abort(500, "An unexpected error occurred while fetching users.")

def request_password_reset_db(db: Session, email_or_username: str) -> bool:
    """Initiates password reset, generates token, and sends email."""
    with tracer.start_as_current_span("service.request_password_reset") as span:
        span.set_attribute("app.user.identifier", email_or_username)
        logger.info("Password reset request received", identifier=email_or_username)

        # Find user by email or username
        user = db.query(User).filter(
            or_(User.username == email_or_username, User.email == email_or_username)
        ).one_or_none()

        # Prevent user enumeration: always return success message even if user not found
        if not user:
            logger.warning("Password reset request for non-existent user.", identifier=email_or_username)
            span.set_attribute("app.user.found", False)
            # Still return True to the caller to indicate the request was processed
            return True

        span.set_attribute("app.user.found", True)
        span.set_attribute("app.user.id", str(user.id))

        # Generate a secure, time-limited token
        # Using Fernet for token generation and validation
        if not fernet_suite:
             logger.error("Password reset failed: Encryption suite not initialized.")
             abort(503, description="Password reset service unavailable.")

        try:
            # Token payload could be user ID, timestamp, etc.
            # For simplicity, just encrypt the user ID and add expiry time
            user_id_bytes = str(user.id).encode('utf-8')
            token = fernet_suite.encrypt(user_id_bytes).decode('utf-8')
            expires_at = datetime.utcnow() + timedelta(hours=1) # Token valid for 1 hour

            user.password_reset_token = token
            user.password_reset_expires = expires_at
            user.updated_at = datetime.utcnow() # Update user timestamp
            db.commit()

            # --- Email Sending (Placeholder) ---
            # This requires a configured email server.
            # Get app URL from environment variables for the reset link
            app_url = os.getenv("APP_URL", "http://localhost:5173") # Default frontend URL
            reset_link = f"{app_url}/reset-password/{token}"

            email_user = os.getenv("EMAIL_USER")
            email_password = os.getenv("EMAIL_PASSWORD")
            email_server = os.getenv("EMAIL_SERVER")
            email_port = os.getenv("EMAIL_PORT")
            mail_sender = os.getenv("MAIL_SENDER", email_user) # Default sender to user if not set

            if email_user and email_password and email_server and email_port:
                 try:
                     # --- Implement actual email sending logic here ---
                     # Example using smtplib (requires proper setup and error handling)
                     # import smtplib
                     # from email.mime.text import MIMEText

                     # msg = MIMEText(f"Click the link to reset your password: {reset_link}")
                     # msg['Subject'] = "Password Reset Request"
                     # msg['From'] = mail_sender
                     # msg['To'] = user.email

                     # with smtplib.SMTP(email_server, int(email_port)) as server:
                     #     server.starttls() # Secure the connection
                     #     server.login(email_user, email_password)
                     #     server.sendmail(mail_sender, [user.email], msg.as_string())

                     logger.info("Password reset email sent (simulated/placeholder).", user_id=user.id, email=user.email)
                     span.set_attribute("app.email.sent", True)

                 except Exception as email_err:
                     logger.error("Failed to send password reset email.", user_id=user.id, email=user.email, exc_info=True)
                     span.set_attribute("app.email.sent", False)
                     span.record_exception(email_err)
                     # Decide if email failure should prevent the token from being saved.
                     # For now, we save the token but log the email error.

            else:
                logger.warning("Email sending is not configured. Password reset link generated but not sent.", user_id=user.id, reset_link=reset_link)
                span.set_attribute("app.email.sent", False)
                # In a real app, you might want to store the link for admin retrieval or user notification in UI

            logger.info("Password reset token generated and saved.", user_id=user.id, event_type="PASSWORD_RESET_REQUEST")
            return True

        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Database error during password reset request.", user_id=user.id, exc_info=True)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "DB Error"))
            _handle_sqlalchemy_error(e, "requesting password reset", db)
        except Exception as e:
            db.rollback()
            logger.error("Unexpected error during password reset request.", user_id=user.id, exc_info=True)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Unknown Error"))
            abort(500, description="An unexpected error occurred during password reset.")


def reset_password_db(db: Session, token: str, new_password: str) -> bool:
    """Resets user password using a valid token."""
    with tracer.start_as_current_span("service.reset_password") as span:
        span.set_attribute("app.password_reset.token_provided", bool(token))

        if not fernet_suite:
             logger.error("Password reset failed: Encryption suite not initialized.")
             abort(503, description="Password reset service unavailable.")

        try:
            # Find user by token and check expiry
            user = db.query(User).filter(
                User.password_reset_token == token,
                User.password_reset_expires > datetime.utcnow()
            ).one_or_none()

            if not user:
                logger.warning("Password reset failed: Invalid or expired token provided.")
                span.set_attribute("app.password_reset.token_valid", False)
                abort(400, description="Invalid or expired password reset token.")

            span.set_attribute("app.password_reset.token_valid", True)
            span.set_attribute("app.user.id", str(user.id))

            # Validate new password complexity
            try:
                _validate_password_complexity(new_password)
            except ValueError as e:
                logger.warning("Password reset failed: New password complexity requirements not met.", user_id=user.id, reason=str(e))
                abort(400, description=str(e))

            # Hash and update password
            user.password_hash = _hash_password(new_password)
            user.password_reset_token = None # Clear token after use
            user.password_reset_expires = None
            user.updated_at = datetime.utcnow()
            db.commit()

            logger.info("Password reset successful.", user_id=user.id, username=user.username, event_type="PASSWORD_RESET_SUCCESS")
            return True

        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Database error during password reset.", exc_info=True)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "DB Error"))
            _handle_sqlalchemy_error(e, "resetting password", db)
        except HTTPException as e:
             raise e # Re-raise specific HTTP exceptions (e.g., from password validation)
        except Exception as e:
            db.rollback()
            logger.error("Unexpected error during password reset.", exc_info=True)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Unknown Error"))
            abort(500, description="An unexpected error occurred during password reset.")


# --- Tree Services ---

def create_tree_db(db: Session, user_id: uuid.UUID, tree_data: Dict[str, Any]) -> Dict[str, Any]:
    """Creates a new tree for a user."""
    with tracer.start_as_current_span("service.create_tree") as span:
        span.set_attribute("app.user.id", str(user_id))
        tree_name = tree_data.get('name', '[Unnamed Tree]')
        span.set_attribute("tree.name", tree_name)
        logger.info("Attempting to create new tree", user_id=user_id, tree_name=tree_name)

        if not tree_data or not tree_data.get('name'):
            logger.warning("Tree creation failed: Missing tree name.")
            abort(400, description="Tree name is required.")

        try:
            new_tree = Tree(
                name=tree_data['name'],
                description=tree_data.get('description'),
                created_by=user_id,
                is_public=tree_data.get('is_public', False),
                default_privacy_level=PrivacyLevelEnum(tree_data.get('default_privacy_level', PrivacyLevelEnum.private.value)),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(new_tree)
            db.commit()
            db.refresh(new_tree)

            # Grant creator admin access to the tree
            tree_access = TreeAccess(
                 tree_id=new_tree.id,
                 user_id=user_id,
                 access_level='admin',
                 granted_by=user_id,
                 granted_at=datetime.utcnow()
            )
            db.add(tree_access)
            db.commit() # Commit again to save access

            logger.info("Tree created successfully", tree_id=new_tree.id, tree_name=new_tree.name, created_by=user_id, event_type="TREE_CREATED")
            span.set_attribute("tree.id", str(new_tree.id))
            return new_tree.to_dict()

        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Database error during tree creation.", user_id=user_id, tree_name=tree_name, exc_info=True)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "DB Error"))
            _handle_sqlalchemy_error(e, "creating tree", db)
        except ValueError as e: # Handle invalid enum values
             db.rollback()
             logger.warning("Invalid privacy level during tree creation.", user_id=user_id, tree_name=tree_name, error=str(e))
             abort(400, description=f"Invalid privacy level: {e}")
        except Exception as e:
            db.rollback()
            logger.error("Unexpected error during tree creation.", user_id=user_id, tree_name=tree_name, exc_info=True)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Unknown Error"))
            abort(500, description="An unexpected error occurred during tree creation.")


def get_user_trees_db(db: Session, user_id: uuid.UUID) -> List[Dict[str, Any]]:
    """Retrieves all trees a user has access to."""
    with tracer.start_as_current_span("service.get_user_trees") as span:
        span.set_attribute("app.user.id", str(user_id))
        logger.info("Fetching trees for user", user_id=user_id)
        try:
            # Get trees created by the user OR trees the user has access to
            trees = db.query(Tree).join(TreeAccess, Tree.id == TreeAccess.tree_id).filter(
                 or_(Tree.created_by == user_id, TreeAccess.user_id == user_id)
            ).distinct().all() # Use distinct to avoid duplicates if user created and has access

            return [tree.to_dict() for tree in trees]

        except SQLAlchemyError as e:
            logger.error("Database error fetching user trees.", user_id=user_id, exc_info=True)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "DB Error"))
            _handle_sqlalchemy_error(e, "fetching user trees", db)
        except Exception as e:
            logger.error("Unexpected error fetching user trees.", user_id=user_id, exc_info=True)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Unknown Error"))
            abort(500, description="An unexpected error occurred while fetching trees.")


# --- Person Services ---

def get_all_people_db(db: Session, tree_id: uuid.UUID) -> List[Dict[str, Any]]:
    """Retrieves all people in a specific tree."""
    with tracer.start_as_current_span("service.get_all_people") as span:
        span.set_attribute("tree.id", str(tree_id))
        logger.info("Fetching all people for tree", tree_id=tree_id)
        try:
            people = db.query(Person).filter(Person.tree_id == tree_id).all()
            return [p.to_dict() for p in people]
        except SQLAlchemyError as e:
            logger.error("Database error fetching all people for tree.", tree_id=tree_id, exc_info=True)
            _handle_sqlalchemy_error(e, f"fetching all people for tree {tree_id}", db)
        except Exception as e:
            logger.error("Unexpected error fetching all people for tree.", tree_id=tree_id, exc_info=True)
            abort(500, "An unexpected error occurred while fetching people.")


def get_person_db(db: Session, person_id: uuid.UUID, tree_id: uuid.UUID) -> Dict[str, Any]:
    """Retrieves a specific person by ID within a tree."""
    with tracer.start_as_current_span("service.get_person") as span:
        span.set_attribute("person.id", str(person_id))
        span.set_attribute("tree.id", str(tree_id))
        logger.info("Fetching person details", person_id=person_id, tree_id=tree_id)
        person = _get_or_404(db, Person, person_id, tree_id)
        return person.to_dict()


def create_person_db(db: Session, user_id: uuid.UUID, tree_id: uuid.UUID, person_data: Dict[str, Any]) -> Dict[str, Any]:
    """Creates a new person in a specific tree."""
    with tracer.start_as_current_span("service.create_person") as span:
        span.set_attribute("app.user.id", str(user_id))
        span.set_attribute("tree.id", str(tree_id))
        person_name = f"{person_data.get('first_name', '')} {person_data.get('last_name', '')}".strip()
        span.set_attribute("person.name", person_name)
        logger.info("Attempting to create new person", user_id=user_id, tree_id=tree_id, person_name=person_name)

        # Basic validation (more detailed validation should be in a separate layer/model)
        if not person_data or not person_data.get('first_name'):
            logger.warning("Person creation failed: Missing first name.")
            abort(400, description={"details": {"first_name": "First name is required."}})

        # Validate dates if provided
        birth_date_str = person_data.get('birth_date')
        death_date_str = person_data.get('death_date')
        birth_date = None
        death_date = None

        if birth_date_str:
            try:
                birth_date = date.fromisoformat(birth_date_str)
            except ValueError:
                logger.warning("Person creation failed: Invalid birth date format.", birth_date=birth_date_str)
                abort(400, description={"details": {"birth_date": "Invalid date format (YYYY-MM-DD)."}})

        if death_date_str:
            try:
                death_date = date.fromisoformat(death_date_str)
            except ValueError:
                logger.warning("Person creation failed: Invalid death date format.", death_date=death_date_str)
                abort(400, description={"details": {"death_date": "Invalid date format (YYYY-MM-DD)."}})

        # Validate death date is not before birth date
        if birth_date and death_date and death_date < birth_date:
            logger.warning("Person creation failed: Death date before birth date.")
            abort(400, description={"details": {"date_comparison": "Death date cannot be before birth date."}})

        # Validate gender if provided
        gender = person_data.get('gender')
        if gender and gender.lower() not in ['male', 'female', 'other', 'unknown']:
             logger.warning("Person creation failed: Invalid gender value.", gender=gender)
             abort(400, description={"details": {"gender": "Invalid gender value."}})


        try:
            new_person = Person(
                tree_id=tree_id,
                first_name=person_data['first_name'],
                middle_names=person_data.get('middle_names'),
                last_name=person_data.get('last_name'),
                maiden_name=person_data.get('maiden_name'),
                nickname=person_data.get('nickname'),
                gender=gender, # Use validated gender
                birth_date=birth_date, # Use validated date objects
                birth_date_approx=person_data.get('birth_date_approx', False),
                birth_place=person_data.get('birth_place'),
                death_date=death_date, # Use validated date objects
                death_date_approx=person_data.get('death_date_approx', False),
                death_place=person_data.get('death_place'),
                burial_place=person_data.get('burial_place'),
                privacy_level=PrivacyLevelEnum(person_data.get('privacy_level', PrivacyLevelEnum.inherit.value)),
                is_living=person_data.get('is_living'), # Needs logic to determine if not provided
                notes=person_data.get('notes'),
                custom_attributes=person_data.get('custom_attributes', {}),
                created_by=user_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            # Determine is_living if not explicitly provided
            if new_person.is_living is None:
                 new_person.is_living = new_person.death_date is None

            db.add(new_person)
            db.commit()
            db.refresh(new_person)

            logger.info("Person created successfully", person_id=new_person.id, tree_id=tree_id, created_by=user_id, event_type="PERSON_CREATED")
            span.set_attribute("person.id", str(new_person.id))
            return new_person.to_dict()

        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Database error during person creation.", user_id=user_id, tree_id=tree_id, person_name=person_name, exc_info=True)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "DB Error"))
            _handle_sqlalchemy_error(e, "creating person", db)
        except ValueError as e: # Handle invalid enum values for privacy_level
             db.rollback()
             logger.warning("Invalid privacy level during person creation.", user_id=user_id, tree_id=tree_id, person_name=person_name, error=str(e))
             abort(400, description=f"Invalid privacy level: {e}")
        except Exception as e:
            db.rollback()
            logger.error("Unexpected error during person creation.", user_id=user_id, tree_id=tree_id, person_name=person_name, exc_info=True)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Unknown Error"))
            abort(500, description="An unexpected error occurred during person creation.")


def update_person_db(db: Session, person_id: uuid.UUID, tree_id: uuid.UUID, person_data: Dict[str, Any]) -> Dict[str, Any]:
    """Updates an existing person's details in a specific tree."""
    with tracer.start_as_current_span("service.update_person") as span:
        span.set_attribute("person.id", str(person_id))
        span.set_attribute("tree.id", str(tree_id))
        logger.info("Attempting to update person", person_id=person_id, tree_id=tree_id)

        person = _get_or_404(db, Person, person_id, tree_id)

        # Validate and update fields from person_data
        update_fields = {}
        validation_errors = {}

        # List of fields allowed to be updated and their validation/conversion
        allowed_fields = [
            'first_name', 'middle_names', 'last_name', 'maiden_name',
            'nickname', 'gender', 'birth_date', 'birth_date_approx',
            'birth_place', 'death_date', 'death_date_approx', 'death_place',
            'burial_place', 'privacy_level', 'is_living', 'notes', 'custom_attributes'
        ]

        for field in allowed_fields:
            if field in person_data:
                value = person_data[field]
                try:
                    if field in ['birth_date', 'death_date']:
                        # Convert date strings to date objects, allow None/empty string
                        update_fields[field] = date.fromisoformat(value) if value else None
                    elif field == 'gender':
                         # Validate gender value
                         if value and value.lower() not in ['male', 'female', 'other', 'unknown']:
                              validation_errors[field] = "Invalid gender value."
                         else:
                              update_fields[field] = value
                    elif field == 'privacy_level':
                         # Validate privacy level enum
                         try:
                              update_fields[field] = PrivacyLevelEnum(value)
                         except ValueError:
                              validation_errors[field] = "Invalid privacy level value."
                    elif field == 'custom_attributes':
                         # Ensure it's a dictionary
                         if not isinstance(value, dict):
                             validation_errors[field] = "Custom attributes must be a dictionary."
                         else:
                             update_fields[field] = value
                    else:
                        # For other fields, just assign the value
                        update_fields[field] = value
                except ValueError as e:
                    validation_errors[field] = f"Invalid value: {e}"
                except Exception as e:
                     logger.error(f"Unexpected error validating field {field} during person update.", exc_info=True)
                     validation_errors[field] = "An unexpected error occurred validating this field."


        if validation_errors:
             logger.warning("Person update failed: Validation errors.", person_id=person_id, errors=validation_errors)
             abort(400, description={"error": "Validation failed", "details": validation_errors})

        # Apply updates
        for field, value in update_fields.items():
            setattr(person, field, value)

        # Re-validate death date vs birth date after updates
        if person.birth_date and person.death_date and person.death_date < person.birth_date:
            validation_errors['date_comparison'] = "Death date cannot be before birth date."
            logger.warning("Person update failed: Death date before birth date after updates.", person_id=person_id, errors=validation_errors)
            abort(400, description={"error": "Validation failed", "details": validation_errors})

        # Update is_living if not explicitly provided in update_fields
        if 'is_living' not in update_fields:
             person.is_living = person.death_date is None


        person.updated_at = datetime.utcnow() # Update timestamp

        try:
            db.commit()
            db.refresh(person)
            logger.info("Person updated successfully", person_id=person.id, tree_id=tree_id, event_type="PERSON_UPDATED")
            return person.to_dict()

        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Database error during person update.", person_id=person_id, tree_id=tree_id, exc_info=True)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "DB Error"))
            _handle_sqlalchemy_error(e, f"updating person ID {person_id}", db)
        except Exception as e:
            db.rollback()
            logger.error("Unexpected error during person update.", person_id=person_id, tree_id=tree_id, exc_info=True)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Unknown Error"))
            abort(500, description="An unexpected error occurred during person update.")


def delete_person_db(db: Session, person_id: uuid.UUID, tree_id: uuid.UUID) -> bool:
    """Deletes a person and their associated data from a specific tree."""
    with tracer.start_as_current_span("service.delete_person") as span:
        span.set_attribute("person.id", str(person_id))
        span.set_attribute("tree.id", str(tree_id))
        logger.info("Attempting to delete person", person_id=person_id, tree_id=tree_id)

        # _get_or_404 handles not found and logs internally
        person = _get_or_404(db, Person, person_id, tree_id)
        person_name_for_log = f"{person.first_name} {person.last_name}".strip()

        try:
            # SQLAlchemy's CASCADE should handle related relationships, events, etc.
            db.delete(person)
            db.commit()
            logger.info("Person deleted successfully", person_id=person_id, person_name=person_name_for_log, tree_id=tree_id, event_type="PERSON_DELETED")
            return True
        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Database error during person deletion.", person_id=person_id, tree_id=tree_id, exc_info=True)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "DB Error"))
            _handle_sqlalchemy_error(e, f"deleting person ID {person_id}", db)
        except Exception as e:
            db.rollback()
            logger.error("Unexpected error during person deletion.", person_id=person_id, tree_id=tree_id, exc_info=True)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Unknown Error"))
            abort(500, description="An unexpected error occurred during person deletion.")


# --- Relationship Services ---

def get_all_relationships_db(db: Session, tree_id: uuid.UUID) -> List[Dict[str, Any]]:
    """Retrieves all relationships in a specific tree."""
    with tracer.start_as_current_span("service.get_all_relationships") as span:
        span.set_attribute("tree.id", str(tree_id))
        logger.info("Fetching all relationships for tree", tree_id=tree_id)
        try:
            relationships = db.query(Relationship).filter(Relationship.tree_id == tree_id).all()
            return [r.to_dict() for r in relationships]
        except SQLAlchemyError as e:
            logger.error("Database error fetching all relationships for tree.", tree_id=tree_id, exc_info=True)
            _handle_sqlalchemy_error(e, f"fetching all relationships for tree {tree_id}", db)
        except Exception as e:
            logger.error("Unexpected error fetching all relationships for tree.", tree_id=tree_id, exc_info=True)
            abort(500, "An unexpected error occurred while fetching relationships.")


def create_relationship_db(db: Session, user_id: uuid.UUID, tree_id: uuid.UUID, relationship_data: Dict[str, Any]) -> Dict[str, Any]:
    """Creates a new relationship in a specific tree."""
    with tracer.start_as_current_span("service.create_relationship") as span:
        span.set_attribute("app.user.id", str(user_id))
        span.set_attribute("tree.id", str(tree_id))
        p1_id_str = relationship_data.get('person1')
        p2_id_str = relationship_data.get('person2')
        rel_type_str = relationship_data.get('relationshipType')
        span.set_attribute("relationship.type", rel_type_str)
        span.set_attribute("relationship.person1_id", p1_id_str)
        span.set_attribute("relationship.person2_id", p2_id_str)
        logger.info("Attempting to create new relationship", user_id=user_id, tree_id=tree_id, p1=p1_id_str, p2=p2_id_str, type=rel_type_str)

        # Basic validation
        if not p1_id_str or not p2_id_str or not rel_type_str:
            logger.warning("Relationship creation failed: Missing required fields.")
            abort(400, description="person1, person2, and relationshipType are required.")

        if p1_id_str == p2_id_str:
            logger.warning("Relationship creation failed: Cannot create relationship with the same person.")
            abort(400, description="Cannot create a relationship between the same person.")

        try:
            person1_id = uuid.UUID(p1_id_str)
            person2_id = uuid.UUID(p2_id_str)
        except ValueError:
            logger.warning("Relationship creation failed: Invalid UUID format for person IDs.")
            abort(400, description="Invalid UUID format for person IDs.")

        # Validate relationship type enum
        try:
            relationship_type = RelationshipTypeEnum(rel_type_str)
        except ValueError:
            logger.warning("Relationship creation failed: Invalid relationship type.", rel_type=rel_type_str)
            abort(400, description=f"Invalid relationship type: {rel_type_str}")

        # Check if persons exist and belong to the same tree
        person1 = db.query(Person).filter(Person.id == person1_id, Person.tree_id == tree_id).one_or_none()
        person2 = db.query(Person).filter(Person.id == person2_id, Person.tree_id == tree_id).one_or_none()

        if not person1:
            logger.warning("Relationship creation failed: Person 1 not found in tree.", person_id=person1_id, tree_id=tree_id)
            abort(404, description=f"Person 1 with ID {person1_id} not found in the active tree.")
        if not person2:
            logger.warning("Relationship creation failed: Person 2 not found in tree.", person_id=person2_id, tree_id=tree_id)
            abort(404, description=f"Person 2 with ID {person2_id} not found in the active tree.")

        # Check for duplicate relationships (optional, depends on desired behavior)
        # Example: prevent multiple 'spouse_current' relationships between the same pair
        # existing_rel = db.query(Relationship).filter(
        #     Relationship.tree_id == tree_id,
        #     or_(
        #         and_(Relationship.person1_id == person1_id, Relationship.person2_id == person2_id),
        #         and_(Relationship.person1_id == person2_id, Relationship.person2_id == person1_id)
        #     ),
        #     Relationship.relationship_type == relationship_type # Or check for specific types like spouse
        # ).one_or_none()
        # if existing_rel:
        #      abort(409, description=f"A {relationship_type.value} relationship already exists between these people.")


        try:
            new_relationship = Relationship(
                tree_id=tree_id,
                person1_id=person1_id,
                person2_id=person2_id,
                relationship_type=relationship_type,
                start_date=relationship_data.get('start_date'), # Needs date validation
                end_date=relationship_data.get('end_date'),     # Needs date validation
                certainty_level=relationship_data.get('certainty_level'), # Needs int validation/range check
                custom_attributes=relationship_data.get('custom_attributes', {}),
                notes=relationship_data.get('notes'),
                created_by=user_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            # Basic date validation for start/end dates
            if new_relationship.start_date and not isinstance(new_relationship.start_date, date):
                 try: new_relationship.start_date = date.fromisoformat(new_relationship.start_date) if new_relationship.start_date else None
                 except ValueError: abort(400, description={"details": {"start_date": "Invalid date format (YYYY-MM-DD)."}})
            if new_relationship.end_date and not isinstance(new_relationship.end_date, date):
                 try: new_relationship.end_date = date.fromisoformat(new_relationship.end_date) if new_relationship.end_date else None
                 except ValueError: abort(400, description={"details": {"end_date": "Invalid date format (YYYY-MM-DD)."}})

            # Validate end date is not before start date
            if new_relationship.start_date and new_relationship.end_date and new_relationship.end_date < new_relationship.start_date:
                 abort(400, description={"details": {"date_comparison": "End date cannot be before start date."}})


            db.add(new_relationship)
            db.commit()
            db.refresh(new_relationship)

            logger.info("Relationship created successfully", rel_id=new_relationship.id, tree_id=tree_id, created_by=user_id, event_type="RELATIONSHIP_CREATED")
            span.set_attribute("relationship.id", str(new_relationship.id))
            return new_relationship.to_dict()

        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Database error during relationship creation.", user_id=user_id, tree_id=tree_id, exc_info=True)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "DB Error"))
            _handle_sqlalchemy_error(e, "creating relationship", db)
        except Exception as e:
            db.rollback()
            logger.error("Unexpected error during relationship creation.", user_id=user_id, tree_id=tree_id, exc_info=True)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Unknown Error"))
            abort(500, description="An unexpected error occurred during relationship creation.")


def update_relationship_db(db: Session, relationship_id: uuid.UUID, tree_id: uuid.UUID, relationship_data: Dict[str, Any]) -> Dict[str, Any]:
    """Updates an existing relationship in a specific tree."""
    with tracer.start_as_current_span("service.update_relationship") as span:
        span.set_attribute("relationship.id", str(relationship_id))
        span.set_attribute("tree.id", str(tree_id))
        logger.info("Attempting to update relationship", rel_id=relationship_id, tree_id=tree_id)

        relationship = _get_or_404(db, Relationship, relationship_id, tree_id)

        update_fields = {}
        validation_errors = {}

        allowed_fields = [
            'person1', 'person2', 'relationshipType', 'start_date',
            'end_date', 'certainty_level', 'custom_attributes', 'notes'
        ]

        for field in allowed_fields:
            if field in relationship_data:
                value = relationship_data[field]
                try:
                    if field in ['person1', 'person2']:
                        # Validate and convert person IDs
                        try:
                            update_fields[f'{field}_id'] = uuid.UUID(value) if value else None
                        except ValueError:
                            validation_errors[field] = "Invalid UUID format."
                    elif field == 'relationshipType':
                         # Validate relationship type enum
                         try:
                              update_fields['relationship_type'] = RelationshipTypeEnum(value)
                         except ValueError:
                              validation_errors[field] = "Invalid relationship type value."
                    elif field in ['start_date', 'end_date']:
                        # Convert date strings to date objects, allow None/empty string
                        update_fields[field] = date.fromisoformat(value) if value else None
                    elif field == 'certainty_level':
                         # Validate certainty level
                         if value is not None and (not isinstance(value, int) or not (1 <= value <= 5)):
                             validation_errors[field] = "Certainty level must be an integer between 1 and 5."
                         else:
                             update_fields[field] = value
                    elif field == 'custom_attributes':
                         # Ensure it's a dictionary
                         if not isinstance(value, dict):
                             validation_errors[field] = "Custom attributes must be a dictionary."
                         else:
                             update_fields[field] = value
                    else:
                        update_fields[field] = value
                except Exception as e:
                     logger.error(f"Unexpected error validating field {field} during relationship update.", exc_info=True)
                     validation_errors[field] = "An unexpected error occurred validating this field."

        if validation_errors:
             logger.warning("Relationship update failed: Validation errors.", rel_id=relationship_id, errors=validation_errors)
             abort(400, description={"error": "Validation failed", "details": validation_errors})

        # Apply updates
        for field, value in update_fields.items():
            setattr(relationship, field, value)

        # Re-validate person IDs are different if they were changed
        if 'person1_id' in update_fields or 'person2_id' in update_fields:
             if relationship.person1_id == relationship.person2_id:
                  validation_errors['person_ids'] = "Cannot create a relationship between the same person."
                  logger.warning("Relationship update failed: Persons are the same after update.", rel_id=relationship_id, errors=validation_errors)
                  abort(400, description={"error": "Validation failed", "details": validation_errors})

             # Check if new person IDs exist and are in the same tree
             if 'person1_id' in update_fields:
                 person1 = db.query(Person).filter(Person.id == relationship.person1_id, Person.tree_id == tree_id).one_or_none()
                 if not person1:
                      abort(404, description=f"New Person 1 with ID {relationship.person1_id} not found in the active tree.")
             if 'person2_id' in update_fields:
                 person2 = db.query(Person).filter(Person.id == relationship.person2_id, Person.tree_id == tree_id).one_or_none()
                 if not person2:
                      abort(404, description=f"New Person 2 with ID {relationship.person2_id} not found in the active tree.")


        # Re-validate end date vs start date after updates
        if relationship.start_date and relationship.end_date and relationship.end_date < relationship.start_date:
            validation_errors['date_comparison'] = "End date cannot be before start date."
            logger.warning("Relationship update failed: End date before start date after updates.", rel_id=relationship_id, errors=validation_errors)
            abort(400, description={"error": "Validation failed", "details": validation_errors})


        relationship.updated_at = datetime.utcnow() # Update timestamp

        try:
            db.commit()
            db.refresh(relationship)
            logger.info("Relationship updated successfully", rel_id=relationship.id, tree_id=tree_id, event_type="RELATIONSHIP_UPDATED")
            return relationship.to_dict()

        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Database error during relationship update.", rel_id=relationship_id, tree_id=tree_id, exc_info=True)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "DB Error"))
            _handle_sqlalchemy_error(e, f"updating relationship ID {relationship_id}", db)
        except HTTPException as e:
             raise e # Re-raise specific HTTP exceptions (e.g., from validation)
        except Exception as e:
            db.rollback()
            logger.error("Unexpected error during relationship update.", rel_id=relationship_id, tree_id=tree_id, exc_info=True)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Unknown Error"))
            abort(500, description="An unexpected error occurred during relationship update.")


def delete_relationship_db(db: Session, relationship_id: uuid.UUID, tree_id: uuid.UUID) -> bool:
    """Deletes a relationship from a specific tree."""
    with tracer.start_as_current_span("service.delete_relationship") as span:
        span.set_attribute("relationship.id", str(relationship_id))
        span.set_attribute("tree.id", str(tree_id))
        logger.info("Attempting to delete relationship", rel_id=relationship_id, tree_id=tree_id)

        # _get_or_404 handles not found and logs internally
        relationship = _get_or_404(db, Relationship, relationship_id, tree_id)

        try:
            db.delete(relationship)
            db.commit()
            logger.info("Relationship deleted successfully", rel_id=relationship_id, tree_id=tree_id, event_type="RELATIONSHIP_DELETED")
            return True
        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Database error during relationship deletion.", rel_id=relationship_id, tree_id=tree_id, exc_info=True)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "DB Error"))
            _handle_sqlalchemy_error(e, f"deleting relationship ID {relationship_id}", db)
        except Exception as e:
            db.rollback()
            logger.error("Unexpected error during relationship deletion.", rel_id=relationship_id, tree_id=tree_id, exc_info=True)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Unknown Error"))
            abort(500, description="An unexpected error occurred during relationship deletion.")


# --- Tree Data Service ---

def get_tree_data_db(db: Session, tree_id: uuid.UUID) -> Dict[str, Any]:
    """Retrieves all person and relationship data for a tree, formatted for visualization."""
    with tracer.start_as_current_span("service.get_tree_data") as span:
        span.set_attribute("tree.id", str(tree_id))
        logger.info("Fetching full tree data for visualization", tree_id=tree_id)

        try:
            # Fetch all people and relationships for the tree
            people = db.query(Person).filter(Person.tree_id == tree_id).all()
            relationships = db.query(Relationship).filter(Relationship.tree_id == tree_id).all()

            # Format data as nodes and links
            nodes = []
            for person in people:
                label = f"{person.first_name or ''} {person.last_name or ''}".strip()
                if person.nickname:
                    label += f" ({person.nickname})"
                if not label:
                    label = str(person.id)[:8]  # Fallback label

                nodes.append({
                    "id": str(person.id),
                    "type": "personNode",
                    "position": {"x": 0, "y": 0},
                    "data": {
                        "id": str(person.id),
                        "label": label,
                        "full_name": f"{person.first_name or ''} {person.last_name or ''}".strip(),
                        "gender": person.gender,
                        "dob": person.birth_date.isoformat() if person.birth_date else None,
                        "dod": person.death_date.isoformat() if person.death_date else None,
                        "birth_place": person.birth_place,
                        "death_place": person.death_place,
                        "is_living": person.is_living,
                    },
                    "person_id": str(person.id)
                })

            links = []
            for relationship in relationships:
                links.append({
                    "id": str(relationship.id),
                    "source": str(relationship.person1_id),
                    "target": str(relationship.person2_id),
                    "type": "default",
                    "animated": False,
                    "label": relationship.relationship_type.value,
                    "data": relationship.to_dict()
                })

            logger.info("Full tree data fetched and formatted successfully", tree_id=tree_id, num_nodes=len(nodes), num_links=len(links))
            return {"nodes": nodes, "links": links}

        except SQLAlchemyError as e:
            logger.error("Database error fetching tree data for visualization.", exc_info=True, tree_id=tree_id)
            _handle_sqlalchemy_error(e, f"fetching tree data for tree {tree_id}", db)
        except Exception as e:
            logger.error("Unexpected error fetching tree data for visualization.", exc_info=True, tree_id=tree_id)
            abort(500, description="An unexpected error occurred while fetching tree data.")


# --- Database Setup ---
DATABASE_URL = os.environ.get('DATABASE_URL')
logger.info(f"Database URL: {'<set>' if DATABASE_URL else '<not set>'}")
if not DATABASE_URL:
    logger.critical("DATABASE_URL environment variable is not set. Exiting.")
    exit(1)

# Create the SQLAlchemy engine and session factory
try:
    engine = create_engine(DATABASE_URL, pool_size=32, echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    # Instrument SQLAlchemy after engine is created
    SQLAlchemyInstrumentor().instrument(engine=engine)
    logger.info("SQLAlchemy engine and session factory created.")
except Exception as e:
    logger.critical(f"Failed to create SQLAlchemy engine or session factory: {e}", exc_info=True)
    exit(1)


# --- Database Initialization Functions ---
def create_tables(engine_to_use):
    """Creates all tables defined in Base metadata."""
    logger.info("Attempting to create database tables if they don't exist...")
    try:
        # Check if tables exist before attempting creation
        inspector = inspect(engine_to_use)
        existing_tables = inspector.get_table_names()
        if not existing_tables:
             logger.info("No tables found. Creating all tables...")
             Base.metadata.create_all(bind=engine_to_use)
             logger.info("Database tables creation complete.")
        else:
             logger.info(f"Found {len(existing_tables)} existing tables. Skipping creation.")

    except Exception as e:
        logger.error(f"Error creating database tables: {e}", exc_info=True)
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
            admin_username = os.getenv("INITIAL_ADMIN_USERNAME", "admin")
            admin_email = os.getenv("INITIAL_ADMIN_EMAIL", "admin@example.com")
            admin_password = os.getenv("INITIAL_ADMIN_PASSWORD") # Require password from env

            if not admin_password:
                 logger.critical("INITIAL_ADMIN_PASSWORD environment variable is not set. Cannot create initial admin user.")
                 # Do not exit, but log critical error. User registration might still work.
                 return

            try:
                 # Attempt to validate password complexity for initial admin password
                 _validate_password_complexity(admin_password)
            except ValueError as e:
                 logger.critical(f"Initial admin password complexity requirements not met: {e}. Cannot create initial admin user.")
                 return # Do not create user if password is weak

            hashed_password = _hash_password(admin_password)

            admin_user = User(
                username=admin_username,
                email=admin_email,
                password_hash=hashed_password,
                role=UserRole.ADMIN,
                is_active=True,
                email_verified=True
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
        session.rollback()
    finally:
        session.close()

def initialize_database(engine_to_use, session_factory):
    """Checks table existence and initializes DB if needed."""
    logger.info("Initializing database...")
    try:
        create_tables(engine_to_use) # Create tables if they don't exist
        populate_initial_data(session_factory) # Populate initial data if needed
        logger.info("Database initialization complete.")
    except Exception as e:
        logger.critical(f"Database initialization failed: {e}", exc_info=True)
        # Decide if the application should exit or continue without a working DB
        # For now, we log and allow the app to potentially start, but it will fail on DB operations.
        # exit(1) # Uncomment to halt startup on DB init failure


# Call the database initialization logic during app startup
initialize_database(engine, SessionLocal)


# --- Flask Request Lifecycle Hooks ---
@app.before_request
def before_request_hook():
    """Initialize the database session and attach it to Flask's `g` object."""
    g.db = SessionLocal()
    # logger.debug("Database session opened for request.") # Enable for detailed request logging

@app.teardown_appcontext
def teardown_db_hook(exception=None):
    """Close the database session after the request is complete."""
    db = g.pop('db', None)
    if db is not None:
        try:
            # In web applications, it's common to let the request handling
            # commit successful transactions or rely on the ORM's default behavior.
            # Explicit commit/rollback here can be tricky with error handling.
            # A common pattern is to commit after successful operations in service functions
            # and rely on the rollback in _handle_sqlalchemy_error for errors.
            db.close()
            # logger.debug("Database session closed for request.") # Enable for detailed request logging
        except Exception as e:
             logger.error(f"Error closing database session: {e}", exc_info=True)
    # The exception parameter is the exception that occurred during request processing, if any.
    # It's already logged by Flask/Werkzeug and potentially by our span error handling.
    # No need to log it again here unless for specific teardown errors.


# --- API Endpoints ---

# Authentication Endpoints (Existing)
@limiter.limit("5 per minute")
@app.route('/api/login', methods=['POST'])
def login():
    """Authenticates a user and starts a session."""
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        abort(400, description="Username and password are required.")

    username_or_email = data['username']
    password = data['password']

    db = g.db
    user = authenticate_user_db(db, username_or_email, password)
    if not user:
        # Use a generic message for security, even if user exists but password is wrong
        abort(401, description="Incorrect username or password.")

    # Set session cookies
    session['user_id'] = str(user['id']) # Store UUID as string in session
    session['username'] = user['username']
    session['role'] = user['role']

    logger.info("User logged in successfully", user_id=user['id'], username=user['username'])
    return {
        "message": "Login successful!",
        "user": user
    }, 200

@limiter.limit("2 per minute") # Limit registration rate
@app.route('/api/register', methods=['POST'])
def register():
    """Registers a new user."""
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password') or not data.get('email'):
        abort(400, description="Username, email, and password are required.")

    db = g.db
    try:
        # Pass only necessary data to the service function
        user_data = {
            'username': data['username'],
            'email': data['email'],
            'password': data['password'], # Pass plain password for hashing in service
            'full_name': data.get('full_name'), # Optional fields
            'role': data.get('role', UserRole.USER.value) # Allow specifying role, but service should validate/restrict
        }
        # Ensure role is valid if provided, default to USER in service
        if 'role' in data:
             try: UserRole(data['role'])
             except ValueError: abort(400, description=f"Invalid role specified: {data['role']}")


        user = register_user_db(db, user_data)
        logger.info("User registered successfully", user_id=user['id'], username=user['username'])
        return {
            "message": "Registration successful!",
            "user": user # Return non-sensitive user data
        }, 201
    except HTTPException as e:
        raise e  # Re-raise known exceptions (like 400 from validation, 409 from integrity)
    except Exception as e:
        logger.error("Unexpected error during registration", exc_info=True)
        abort(500, description="An unexpected error occurred during registration.")

@app.route('/api/logout', methods=['POST'])
@require_auth
def logout():
    """Logs out the current user."""
    user_id = session.get('user_id')
    username = session.get('username')

    session.clear() # Clear all session data

    logger.info("User logged out successfully", user_id=user_id, username=username)
    return {
        "message": "Logout successful"
    }, 200

@app.route('/api/session', methods=['GET'])
def session_status():
    """Retrieves the current session status."""
    if 'user_id' not in session:
        return {
            "isAuthenticated": False,
            "user": None,
            "active_tree_id": None # Indicate no active tree
        }, 200

    user_id = session['user_id']
    username = session['username']
    role = session['role']
    active_tree_id = session.get('active_tree_id') # Get active tree from session

    # Optional: Verify user still exists in DB if session is old/stale
    # user_obj = g.db.query(User).filter(User.id == uuid.UUID(user_id)).one_or_none()
    # if not user_obj:
    #      session.clear()
    #      return {"isAuthenticated": False, "user": None, "active_tree_id": None}, 200


    logger.debug("Session status retrieved", user_id=user_id, username=username, active_tree_id=active_tree_id)
    return {
        "isAuthenticated": True,
        "user": {
            "id": user_id,
            "username": username,
            "role": role
        },
        "active_tree_id": active_tree_id # Include active tree ID
    }, 200

# Password Reset Endpoints (NEW)
@limiter.limit("3 per minute") # Limit password reset requests
@app.route('/api/request-password-reset', methods=['POST'])
def request_password_reset():
    """Initiates the password reset process."""
    data = request.get_json()
    if not data or not data.get('email'):
        abort(400, description="Email address is required.")

    email_or_username = data['email']
    db = g.db

    # The service function handles finding the user and sending the email (or logging failure)
    # It's designed to return success even if the user doesn't exist to prevent enumeration.
    request_password_reset_db(db, email_or_username)

    # Always return a generic success message for security
    return {
        "message": "If an account exists for this email, a password reset link has been sent."
    }, 200

@limiter.limit("3 per minute") # Limit password reset attempts with token
@app.route('/api/reset-password/<token>', methods=['POST'])
def reset_password(token):
    """Resets user password using a valid token."""
    data = request.get_json()
    if not data or not data.get('new_password'):
        abort(400, description="New password is required.")

    new_password = data['new_password']
    db = g.db

    # The service function handles token validation, password complexity, and updating the password
    reset_password_db(db, token, new_password)

    return {
        "message": "Password reset successfully."
    }, 200

# Tree Management Endpoints (NEW)
@app.route('/api/trees', methods=['POST'])
@require_auth
def create_tree():
    """Creates a new tree for the logged-in user."""
    data = request.get_json()
    if not data or not data.get('name'):
        abort(400, description="Tree name is required.")

    user_id = uuid.UUID(session['user_id'])
    db = g.db

    try:
        new_tree = create_tree_db(db, user_id, data)
        # Automatically set the newly created tree as the active tree
        session['active_tree_id'] = new_tree['id']
        return new_tree, 201
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error("Unexpected error in create_tree endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while creating the tree.")

@app.route('/api/trees', methods=['GET'])
@require_auth
def get_user_trees():
    """Retrieves all trees the logged-in user has access to."""
    user_id = uuid.UUID(session['user_id'])
    db = g.db

    try:
        trees = get_user_trees_db(db, user_id)
        return jsonify(trees), 200
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error("Unexpected error in get_user_trees endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while fetching user trees.")

@app.route('/api/session/active_tree', methods=['PUT'])
@require_auth
def set_active_tree():
    """Sets the active tree ID in the user's session."""
    data = request.get_json()
    if not data or not data.get('tree_id'):
        abort(400, description="tree_id is required.")

    tree_id_str = data['tree_id']
    user_id = uuid.UUID(session['user_id'])
    db = g.db

    try:
        tree_id = uuid.UUID(tree_id_str)
    except ValueError:
        abort(400, description="Invalid UUID format for tree_id.")

    # Verify user has access to this tree before setting it as active
    tree = db.query(Tree).filter(Tree.id == tree_id).one_or_none()
    if not tree:
         abort(404, description=f"Tree with ID {tree_id} not found.")

    # Check access level (even 'view' access is sufficient to set as active)
    has_access = False
    if tree.created_by == user_id:
         has_access = True
         access_level = 'admin' # Creator has full control
    elif tree.is_public:
         has_access = True
         access_level = 'view' # Public tree allows view access
    else:
        tree_access = db.query(TreeAccess).filter(
            TreeAccess.tree_id == tree_id,
            TreeAccess.user_id == user_id
        ).one_or_none()

        if tree_access:
            access_level = tree_access.access_level
            # Check if granted access level meets the required level
            # Simple hierarchy: admin > edit > view
            if access_level in ['edit', 'admin']:
                has_access = True

    if not has_access:
        abort(403, description=f"Access denied to tree {tree_id}.")


    session['active_tree_id'] = tree_id_str
    logger.info("Active tree set in session.", user_id=user_id, tree_id=tree_id)

    return {
        "message": "Active tree set successfully.",
        "active_tree_id": tree_id_str
    }, 200


# People Endpoints (NEW)
@app.route('/api/people', methods=['GET'])
@require_tree_access('view') # Require view access to the active tree
def get_all_people():
    """Retrieves all people in the active tree."""
    db = g.db
    tree_id = g.active_tree_id # Get active tree ID from g context

    try:
        people = get_all_people_db(db, tree_id)
        return jsonify(people), 200
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error("Unexpected error in get_all_people endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while fetching people.")

@app.route('/api/people/<uuid:person_id>', methods=['GET'])
@require_tree_access('view') # Require view access to the active tree
def get_person(person_id):
    """Retrieves a specific person by ID within the active tree."""
    db = g.db
    tree_id = g.active_tree_id

    try:
        person = get_person_db(db, person_id, tree_id)
        return jsonify(person), 200
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error("Unexpected error in get_person endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while fetching the person.")

@app.route('/api/people', methods=['POST'])
@require_tree_access('edit') # Require edit access to the active tree to add a person
def create_person():
    """Adds a new person to the active tree."""
    data = request.get_json()
    if not data:
        abort(400, description="Request body is required.")

    user_id = uuid.UUID(session['user_id'])
    tree_id = g.active_tree_id
    db = g.db

    try:
        new_person = create_person_db(db, user_id, tree_id, data)
        return new_person, 201
    except HTTPException as e:
        raise e # Re-raise specific HTTP exceptions (e.g., 400, 404)
    except Exception as e:
        logger.error("Unexpected error in create_person endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while creating the person.")

@app.route('/api/people/<uuid:person_id>', methods=['PUT'])
@require_tree_access('edit') # Require edit access to the active tree to update a person
def update_person(person_id):
    """Updates an existing person's details within the active tree."""
    data = request.get_json()
    if not data:
        abort(400, description="Request body is required.")

    tree_id = g.active_tree_id
    db = g.db

    try:
        updated_person = update_person_db(db, person_id, tree_id, data)
        return jsonify(updated_person), 200
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error("Unexpected error in update_person endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while updating the person.")

@app.route('/api/people/<uuid:person_id>', methods=['DELETE'])
@require_tree_access('edit') # Require edit access to the active tree to delete a person
def delete_person(person_id):
    """Deletes a person and their associated data from the active tree."""
    tree_id = g.active_tree_id
    db = g.db

    try:
        delete_person_db(db, person_id, tree_id)
        return '', 204 # No content response for successful deletion
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error("Unexpected error in delete_person endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while deleting the person.")

# Relationships Endpoints (NEW)
@app.route('/api/relationships', methods=['GET'])
@require_tree_access('view') # Require view access to the active tree
def get_all_relationships():
    """Retrieves all relationships in the active tree."""
    db = g.db
    tree_id = g.active_tree_id

    try:
        relationships = get_all_relationships_db(db, tree_id)
        return jsonify(relationships), 200
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error("Unexpected error in get_all_relationships endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while fetching relationships.")

@app.route('/api/relationships/<uuid:relationship_id>', methods=['GET'])
@require_tree_access('view') # Require view access to the active tree
def get_relationship(relationship_id):
    """Retrieves a specific relationship by ID within the active tree."""
    # Note: api_docs.md did not explicitly list GET /relationships/{id}, but it's a standard CRUD endpoint.
    # Implementing based on common REST patterns.
    with tracer.start_as_current_span("endpoint.get_relationship") as span:
        span.set_attribute("relationship.id", str(relationship_id))
        db = g.db
        tree_id = g.active_tree_id
        span.set_attribute("tree.id", str(tree_id))

        try:
            relationship = _get_or_404(db, Relationship, relationship_id, tree_id)
            return jsonify(relationship.to_dict()), 200
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error("Unexpected error in get_relationship endpoint.", exc_info=True)
            abort(500, description="An unexpected error occurred while fetching the relationship.")


@app.route('/api/relationships', methods=['POST'])
@require_tree_access('edit') # Require edit access to the active tree to add a relationship
def create_relationship():
    """Adds a new relationship to the active tree."""
    data = request.get_json()
    if not data:
        abort(400, description="Request body is required.")

    user_id = uuid.UUID(session['user_id'])
    tree_id = g.active_tree_id
    db = g.db

    try:
        new_relationship = create_relationship_db(db, user_id, tree_id, data)
        return new_relationship, 201
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error("Unexpected error in create_relationship endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while creating the relationship.")

@app.route('/api/relationships/<uuid:relationship_id>', methods=['PUT'])
@require_tree_access('edit') # Require edit access to the active tree to update a relationship
def update_relationship(relationship_id):
    """Updates an existing relationship within the active tree."""
    data = request.get_json()
    if not data:
        abort(400, description="Request body is required.")

    tree_id = g.active_tree_id
    db = g.db

    try:
        updated_relationship = update_relationship_db(db, relationship_id, tree_id, data)
        return jsonify(updated_relationship), 200
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error("Unexpected error in update_relationship endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while updating the relationship.")


@app.route('/api/relationships/<uuid:relationship_id>', methods=['DELETE'])
@require_tree_access('edit') # Require edit access to the active tree to delete a relationship
def delete_relationship(relationship_id):
    """Deletes a relationship from the active tree."""
    tree_id = g.active_tree_id
    db = g.db

    try:
        delete_relationship_db(db, relationship_id, tree_id)
        return '', 204 # No content response for successful deletion
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error("Unexpected error in delete_relationship endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while deleting the relationship.")


# --- Tree Data Endpoint (NEW)
@app.route('/api/tree_data', methods=['GET'])
@require_tree_access('view') # Require view access to the active tree
def get_tree_data():
    """Retrieves node and link data for the active tree, formatted for visualization."""
    # Note: This currently returns the full tree. Query parameters for start_node/depth are not yet implemented.
    db = g.db
    tree_id = g.active_tree_id

    # Ignore start_node and depth query parameters for now, as per current backend capability note in api_docs.md
    # start_node_id = request.args.get('start_node')
    # depth_str = request.args.get('depth')

    try:
        tree_data = get_tree_data_db(db, tree_id)
        return jsonify(tree_data), 200
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error("Unexpected error in get_tree_data endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while fetching tree data.")


# Admin User Management Endpoints (NEW)
@app.route('/api/users', methods=['GET'])
@require_admin # Require admin role
def get_all_users():
    """Retrieves a list of all registered users (Admin only)."""
    db = g.db
    try:
        users = get_all_users_db(db)
        return jsonify(users), 200
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error("Unexpected error in get_all_users endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while fetching users.")

@app.route('/api/users/<uuid:user_id>', methods=['DELETE'])
@require_admin # Require admin role
def delete_user(user_id):
    """Deletes a specified user (Admin only)."""
    # Prevent admin from deleting themselves
    current_user_id = uuid.UUID(session['user_id'])
    if user_id == current_user_id:
        logger.warning("Admin attempted to delete their own account.", user_id=current_user_id)
        abort(403, description="Admins cannot delete their own account via this endpoint.")

    db = g.db
    try:
        delete_user_db(db, user_id)
        return '', 204 # No content response for successful deletion
    except HTTPException as e:
        raise e # Re-raise 404 or 409 from service function
    except Exception as e:
        logger.error("Unexpected error in delete_user endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while deleting the user.")


@app.route('/api/users/<uuid:user_id>/role', methods=['PUT'])
@require_admin # Require admin role
def set_user_role(user_id):
    """Changes the role of a specified user (Admin only)."""
    data = request.get_json()
    if not data or not data.get('role'):
        abort(400, description="role is required.")

    new_role = data['role']

    # Prevent admin from changing their own role
    current_user_id = uuid.UUID(session['user_id'])
    if user_id == current_user_id:
        logger.warning("Admin attempted to change their own role.", user_id=current_user_id)
        abort(403, description="Admins cannot change their own role via this endpoint.")

    db = g.db
    try:
        # The service function handles role validation
        updated_user = update_user_role_db(db, user_id, new_role)
        # Return non-sensitive updated user data
        return jsonify(updated_user), 200
    except HTTPException as e:
        raise e # Re-raise 400 or 404 from service function
    except Exception as e:
        logger.error("Unexpected error in set_user_role endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while setting the user role.")


# --- Health Check Endpoint (Existing) ---
@limiter.limit("60 per minute")
@app.route('/health', methods=['GET'])
def health_check():
    """Performs health checks on the application and its dependencies."""

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
        service_status = "unhealthy"  # If DB is critical, service is unhealthy
        logger.error(f"Database health check failed: {e}", exc_info=False)  # Don't need full trace usually
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

    # Add rate limit information
    rate_limit_info = {}
    try:
        # Get rate limit information for the current endpoint
        limit = limiter.current_limit
        if limit:
            rate_limit_info = {
                "limit": str(limit.limit), # Convert to string for JSON
                "remaining": limit.remaining,
                "reset_time": limit.reset_at.isoformat() if limit.reset_at else None
            }
    except Exception as e:
        logger.error(f"Failed to retrieve rate limit information: {e}", exc_info=True)

    response_data = {
        "status": service_status,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "dependencies": dependencies,
        "rate_limit": rate_limit_info  # Include rate limit information
    }

    # Return 503 if unhealthy, 200 if healthy
    http_status = 200 if service_status == "healthy" else 503
    logger.info(
        "===> Health check. Status: %s, DB Status: %s, Latency: %.2f ms, Dependencies: %s, Rate Limit: %s",
        service_status, db_status, db_latency_ms, dependencies, rate_limit_info
    )
    return jsonify(response_data), http_status # Use jsonify for consistent response


# --- Main Execution Guard ---
if __name__ == '__main__':
    # Use environment variables for host and port, provide defaults
    host = os.environ.get('FLASK_RUN_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_RUN_PORT', 8090)) # Use 8090 as per docker-compose/api.js
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() in ['true', '1', 't']

    logger.info(f"Starting Flask server on {host}:{port} (Debug: {debug_mode})")
    # Use Flask's built-in server for development, Gunicorn/uWSGI for production
    # debug=True enables reloader and debugger, useful for development
    app.run(host=host, port=port, debug=debug_mode)

