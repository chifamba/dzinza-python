# backend/main.py
import logging
import bcrypt
import os
import json
import uuid
import time
import re  # Import regex for password validation
import secrets # For generating secure tokens
from flask import Flask, abort, request, g, session, jsonify, make_response
from sqlalchemy import (
    or_, and_, desc, asc, Enum as SQLAlchemyEnum, TypeDecorator, String, Text, func, inspect, text,
    Column, Integer, Boolean, DateTime, Date, ForeignKey, JSON, LargeBinary, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from cryptography.fernet import Fernet, InvalidToken, InvalidSignature
from cryptography.exceptions import InvalidSignature
from datetime import date, datetime, timedelta, timezone
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps
from dotenv import load_dotenv
import structlog
from typing import Optional, List, Dict, Any, Set
from sqlalchemy.exc import IntegrityError, NoResultFound, SQLAlchemyError
from sqlalchemy.orm import Session as DBSession # Aliased to avoid conflict with Flask-Session
from sqlalchemy.types import TypeDecorator, String, Text
import enum
from werkzeug.exceptions import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker # Ensure sessionmaker is imported from sqlalchemy.orm
from urllib.parse import urljoin
from collections import deque

# OpenTelemetry and SQLAlchemy-related types
from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

# Import for Redis session management
import redis
from flask_session import Session as ServerSession # Using ServerSession to avoid name clash

# --- Load Environment Variables ---
load_dotenv()

# --- Flask App Setup ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY", "your_default_secret_key_for_session_signing")

# Define redis_url early as it's needed for session config
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Flask-Session configuration for Redis
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_PERMANENT'] = False # Sessions are not permanent by default, rely on Redis TTL
app.config['SESSION_USE_SIGNER'] = True  # Encrypts the session cookie
app.config['SESSION_KEY_PREFIX'] = 'session:' # Recommended prefix for Redis keys
app.config['SESSION_REDIS'] = redis.from_url(redis_url)

# Standard Flask app configurations (some might be defaults for Flask-Session or handled differently)
app.config.update(
    SESSION_COOKIE_SECURE=False, # is important for production with HTTPS
    # SESSION_COOKIE_SECURE=os.environ.get('FLASK_ENV') != 'development', # True in prod if FLASK_ENV is not 'development'
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax', # Consider 'Strict' or 'None' (with Secure=True) for production needs
    PERMANENT_SESSION_LIFETIME=timedelta(days=7) # Used if SESSION_PERMANENT is True
)

# Initialize Flask-Session
server_side_session = ServerSession()
server_side_session.init_app(app)


# Enable CORS for the Flask app
CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}}, supports_credentials=True)


# --- Rate Limiter Setup ---
limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri=redis_url,  # Use Redis as the storage backend for limiter as well
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

# --- OpenTelemetry Setup ---
resource = Resource(attributes={ "service.name": os.getenv("OTEL_SERVICE_NAME", "family-tree-backend") })
# Configure Tracer Provider
trace.set_tracer_provider(TracerProvider(resource=resource))
otlp_exporter_trace = OTLPSpanExporter()
span_processor = BatchSpanProcessor(
    otlp_exporter_trace,
    max_export_batch_size=64,
    max_queue_size=128,
    export_timeout_millis=300,
)
trace.get_tracer_provider().add_span_processor(span_processor)
tracer = trace.get_tracer(__name__)

# Configure Meter Provider
otlp_exporter_metric = OTLPMetricExporter()
metric_reader = PeriodicExportingMetricReader(otlp_exporter_metric)
meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)
meter = metrics.get_meter(__name__)

FlaskInstrumentor().instrument_app(app)
LoggingInstrumentor().instrument(set_logging_format=True)


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
ENCRYPTION_KEY_FILE = "/backend/data/encryption_key.json"

def load_encryption_key():
    """Load encryption key from environment variable or file."""
    key = os.getenv(ENCRYPTION_KEY_ENV_VAR)
    if key:
        logger.info("Encryption key loaded from environment variable.")
        return key
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
                encoded_value = str(value).encode('utf-8')
                return fernet_suite.encrypt(encoded_value).decode('utf-8')
            except Exception as e:
                logger.error("Encryption failed for value.", error=str(e), exc_info=True)
                return value
        return value
    def process_result_value(self, value, dialect):
        if value is not None and fernet_suite:
            try:
                encoded_value = str(value).encode('utf-8')
                return fernet_suite.decrypt(encoded_value).decode('utf-8')
            except (InvalidToken, InvalidSignature) as e:
                logger.error("Decryption failed for value.", error=str(e), exc_info=True)
                return value
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
    password_reset_token = Column(String(255), unique=True)
    password_reset_expires = Column(DateTime)
    def to_dict(self, include_sensitive=False):
        data = {
            "id": str(self.id), "username": self.username, "email": self.email,
            "full_name": self.full_name, "role": self.role.value, "is_active": self.is_active,
            "email_verified": self.email_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "preferences": self.preferences, "profile_image_path": self.profile_image_path,
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
            "id": str(self.id), "name": self.name, "description": self.description,
            "created_by": str(self.created_by), "is_public": self.is_public,
            "default_privacy_level": self.default_privacy_level.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class TreeAccess(Base):
    __tablename__ = "tree_access"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_id = Column(UUID(as_uuid=True), ForeignKey("trees.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    access_level = Column(String(50), nullable=False, default="view")
    granted_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    granted_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("tree_id", "user_id", name="tree_user_unique"),)
    def to_dict(self):
        return {
            "id": str(self.id), "tree_id": str(self.tree_id), "user_id": str(self.user_id),
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
    gender = Column(String(20))
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
    def to_dict(self):
        return {
            "id": str(self.id), "tree_id": str(self.tree_id), "first_name": self.first_name,
            "middle_names": self.middle_names, "last_name": self.last_name, "maiden_name": self.maiden_name,
            "nickname": self.nickname, "gender": self.gender,
            "birth_date": self.birth_date.isoformat() if self.birth_date else None,
            "birth_date_approx": self.birth_date_approx, "birth_place": self.birth_place,
            "death_date": self.death_date.isoformat() if self.death_date else None,
            "death_date_approx": self.death_date_approx, "death_place": self.death_place,
            "burial_place": self.burial_place, "privacy_level": self.privacy_level.value,
            "is_living": self.is_living, "notes": self.notes, "custom_attributes": self.custom_attributes,
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
    certainty_level = Column(Integer)
    custom_attributes = Column(JSONB, default=dict)
    notes = Column(Text)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    def to_dict(self):
        return {
            "id": str(self.id), "tree_id": str(self.tree_id),
            "person1_id": str(self.person1_id), "person2_id": str(self.person2_id),
            "relationship_type": self.relationship_type.value,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "certainty_level": self.certainty_level, "custom_attributes": self.custom_attributes,
            "notes": self.notes, "created_by": str(self.created_by),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class Event(Base):
    __tablename__ = "events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_id = Column(UUID(as_uuid=True), ForeignKey("trees.id", ondelete="CASCADE"), nullable=False)
    person_id = Column(UUID(as_uuid=True), ForeignKey("people.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(100), nullable=False)
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
    source_id = Column(UUID(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"), nullable=False)
    citation_text = Column(Text, nullable=False)
    page_number = Column(String(50))
    confidence_level = Column(Integer)
    notes = Column(Text)
    custom_attributes = Column(JSONB, default=dict)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class ActivityLog(Base):
    __tablename__ = "activity_log"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_id = Column(UUID(as_uuid=True), ForeignKey("trees.id", ondelete="SET NULL"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    action_type = Column(String(50), nullable=False)
    previous_state = Column(JSONB)
    new_state = Column(JSONB)
    ip_address = Column(String(50))
    user_agent = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    def to_dict(self):
        return {
            "id": str(self.id),
            "tree_id": str(self.tree_id) if self.tree_id else None,
            "user_id": str(self.user_id) if self.user_id else None,
            "entity_type": self.entity_type, "entity_id": str(self.entity_id),
            "action_type": self.action_type, "previous_state": self.previous_state,
            "new_state": self.new_state, "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

# --- Utility Functions ---
def _handle_sqlalchemy_error(e: SQLAlchemyError, context: str, db: DBSession): # Use DBSession alias
    db.rollback()
    if isinstance(e, IntegrityError):
        detail = getattr(e.orig, 'diag', None)
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

def _get_or_404(db: DBSession, model: Any, model_id: uuid.UUID, tree_id: Optional[uuid.UUID] = None) -> Any: # Use DBSession alias
    with tracer.start_as_current_span(f"db.get.{model.__name__}") as span:
        span.set_attribute("db.system", "postgresql")
        span.set_attribute(f"{model.__name__}.id", str(model_id))
        if tree_id: span.set_attribute("tree.id", str(tree_id))
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
            if 'start_time' in locals():
                duration = (time.monotonic() - start_time) * 1000
                db_operation_duration_histogram.record(duration, {"db.operation": f"get.{model.__name__}", "db.status": "error"})
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Non-DB Error"))
            logger.error(f"Unexpected error fetching {model.__name__} ID {model_id}", exc_info=True)
            abort(500, "An unexpected error occurred.")

def _validate_password_complexity(password: str) -> None:
    if len(password) < 8: raise ValueError("Password must be at least 8 characters long.")
    if not re.search(r'[A-Z]', password): raise ValueError("Password must contain at least one uppercase letter.")
    if not re.search(r'[a-z]', password): raise ValueError("Password must contain at least one lowercase letter.")
    if not re.search(r'[0-9]', password): raise ValueError("Password must contain at least one digit.")
    if not re.search(r'[!@#$%^&*()_+=\-[\]{};\':"\\|,.<>/?`~]', password): raise ValueError("Password must contain at least one special character.")

def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')

def _verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception as e:
        logger.error("Error during password verification", exc_info=True)
        return False

# --- Authentication/Authorization Decorators ---
def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            logger.warning("Authentication required, session not found.", session_contents=session)
            abort(401, description="Authentication required.")
        return f(*args, **kwargs)
    return decorated_function

def require_admin(f):
    @wraps(f)
    @require_auth
    def decorated_function(*args, **kwargs):
        if session.get('role') != UserRole.ADMIN.value:
            logger.warning("Admin access required, but user is not admin.", user_id=session.get('user_id'), role=session.get('role'))
            abort(403, description="Admin access required.")
        return f(*args, **kwargs)
    return decorated_function

def require_tree_access(level: str = 'view'):
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            user_id = uuid.UUID(session['user_id'])
            tree_id_str = session.get('active_tree_id')
            if not tree_id_str:
                 logger.warning("Tree access required, but no active tree set in session.", user_id=user_id)
                 abort(400, description="No active tree selected.")
            try:
                tree_id = uuid.UUID(tree_id_str)
            except ValueError:
                 logger.warning("Tree access required, but active_tree_id in session is invalid UUID.", user_id=user_id, active_tree_id=tree_id_str)
                 session.pop('active_tree_id', None)
                 abort(400, description="Invalid active tree ID in session.")
            db = g.db
            tree = db.query(Tree).filter(Tree.id == tree_id).one_or_none()
            if not tree:
                logger.warning("Tree access check failed: Tree not found.", user_id=user_id, tree_id=tree_id)
                session.pop('active_tree_id', None)
                abort(404, description="Active tree not found.")
            has_access = False
            current_access_level = None
            if tree.created_by == user_id:
                 has_access = True
                 current_access_level = 'admin'
            elif tree.is_public and level == 'view':
                 has_access = True
                 current_access_level = 'view'
            else:
                tree_access_obj = db.query(TreeAccess).filter(
                    TreeAccess.tree_id == tree_id, TreeAccess.user_id == user_id
                ).one_or_none()
                if tree_access_obj:
                    current_access_level = tree_access_obj.access_level
                    if level == 'view' and current_access_level in ['view', 'edit', 'admin']: has_access = True
                    elif level == 'edit' and current_access_level in ['edit', 'admin']: has_access = True
                    elif level == 'admin' and current_access_level == 'admin': has_access = True
            if not has_access:
                logger.warning("Tree access denied.", user_id=user_id, tree_id=tree_id, required_level=level, granted_level=current_access_level)
                abort(403, description=f"Access denied to tree {tree_id}.")
            g.active_tree = tree
            g.tree_access_level = current_access_level
            g.active_tree_id = tree_id
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- User Services (Extended) ---
def get_activity_log_db(db: DBSession, tree_id: Optional[uuid.UUID] = None, user_id: Optional[uuid.UUID] = None) -> List[Dict[str, Any]]:
    with tracer.start_as_current_span("service.get_activity_log") as span:
        logger.info("Fetching activity logs", tree_id=tree_id, user_id=user_id)
        try:
            query = db.query(ActivityLog)
            if tree_id: query = query.filter(ActivityLog.tree_id == tree_id)
            if user_id: query = query.filter(ActivityLog.user_id == user_id)
            logs = query.order_by(ActivityLog.created_at.desc()).all()
            return [log.to_dict() for log in logs]
        except SQLAlchemyError as e:
            logger.error("Database error fetching activity logs.", exc_info=True)
            _handle_sqlalchemy_error(e, "fetching activity logs", db)
        except Exception as e:
            logger.error("Unexpected error fetching activity logs.", exc_info=True)
            abort(500, description="An unexpected error occurred while fetching activity logs.")

def delete_tree_db(db: DBSession, tree_id: uuid.UUID) -> None:
    with tracer.start_as_current_span("service.delete_tree") as span:
        span.set_attribute("tree.id", str(tree_id))
        logger.info("Deleting tree", tree_id=tree_id)
        tree = _get_or_404(db, Tree, tree_id)
        try:
            db.delete(tree)
            db.commit()
            logger.info("Tree deleted successfully", tree_id=tree_id)
        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Database error during tree deletion.", tree_id=tree_id, exc_info=True)
            _handle_sqlalchemy_error(e, "deleting tree", db)
        except Exception as e:
            db.rollback()
            logger.error("Unexpected error during tree deletion.", tree_id=tree_id, exc_info=True)
            abort(500, description="An unexpected error occurred while deleting the tree.")

def update_tree_db(db: DBSession, tree_id: uuid.UUID, tree_data: Dict[str, Any]) -> Dict[str, Any]:
    with tracer.start_as_current_span("service.update_tree") as span:
        span.set_attribute("tree.id", str(tree_id))
        logger.info("Updating tree", tree_id=tree_id)
        tree = _get_or_404(db, Tree, tree_id)
        try:
            for key, value in tree_data.items():
                if hasattr(tree, key): setattr(tree, key, value)
            tree.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(tree)
            logger.info("Tree updated successfully", tree_id=tree.id)
            return tree.to_dict()
        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Database error during tree update.", tree_id=tree_id, exc_info=True)
            _handle_sqlalchemy_error(e, "updating tree", db)
        except Exception as e:
            db.rollback()
            logger.error("Unexpected error during tree update.", tree_id=tree_id, exc_info=True)
            abort(500, description="An unexpected error occurred while updating the tree.")

def delete_user_db(db: DBSession, user_id: uuid.UUID) -> None:
    with tracer.start_as_current_span("service.delete_user") as span:
        span.set_attribute("app.user.id", str(user_id))
        logger.info("Deleting user", user_id=user_id)
        user = _get_or_404(db, User, user_id)
        try:
            db.delete(user)
            db.commit()
            logger.info("User deleted successfully", user_id=user_id)
        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Database error during user deletion.", user_id=user_id, exc_info=True)
            _handle_sqlalchemy_error(e, "deleting user", db)
        except Exception as e:
            db.rollback()
            logger.error("Unexpected error during user deletion.", user_id=user_id, exc_info=True)
            abort(500, description="An unexpected error occurred while deleting the user.")

def update_user_role_db(db: DBSession, user_id: uuid.UUID, new_role: str) -> Dict[str, Any]:
    with tracer.start_as_current_span("service.update_user_role") as span:
        span.set_attribute("app.user.id", str(user_id))
        span.set_attribute("app.user.new_role", new_role)
        logger.info("Updating user role", user_id=user_id, new_role=new_role)
        try:
            user = _get_or_404(db, User, user_id)
            user.role = UserRole(new_role)
            # user.updated_at = datetime.utcnow() # Assuming User model has updated_at, if not, add it or remove this line.
            db.commit()
            db.refresh(user)
            logger.info("User role updated successfully", user_id=user.id, new_role=user.role.value)
            return user.to_dict()
        except ValueError:
            logger.warning("Invalid role specified.", user_id=user_id, new_role=new_role)
            abort(400, description=f"Invalid role specified: {new_role}")
        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Database error during user role update.", user_id=user_id, exc_info=True)
            _handle_sqlalchemy_error(e, "updating user role", db)
        except Exception as e:
            db.rollback()
            logger.error("Unexpected error during user role update.", user_id=user_id, exc_info=True)
            abort(500, description="An unexpected error occurred while updating the user role.")

def register_user_db(db: DBSession, user_data: Dict[str, Any]) -> Dict[str, Any]:
    with tracer.start_as_current_span("service.register_user") as span:
        span.set_attribute("app.user.username", user_data['username'])
        logger.info("Registering new user", username=user_data['username'])
        try: _validate_password_complexity(user_data['password'])
        except ValueError as e:
            logger.warning("User registration failed: Password complexity requirements not met.", username=user_data['username'], reason=str(e))
            abort(400, description=str(e))
        hashed_password = _hash_password(user_data['password'])
        try:
            new_user = User(
                username=user_data['username'], email=user_data['email'], password_hash=hashed_password,
                full_name=user_data.get('full_name'), role=UserRole(user_data.get('role', UserRole.USER.value)),
                is_active=True, email_verified=False, created_at=datetime.utcnow()
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            logger.info("User registered successfully", user_id=new_user.id, username=new_user.username)
            return new_user.to_dict()
        except IntegrityError as e:
            db.rollback()
            logger.warning("User registration failed: Integrity error.", username=user_data['username'], exc_info=True)
            _handle_sqlalchemy_error(e, "registering user", db)
        except ValueError as e:
            db.rollback()
            logger.warning(f"User registration failed: Invalid role value '{user_data.get('role')}'.", username=user_data['username'], error=str(e))
            abort(400, description=f"Invalid role specified: {user_data.get('role')}")
        except Exception as e:
            db.rollback()
            logger.error("Unexpected error during user registration.", username=user_data['username'], exc_info=True)
            abort(500, description="An unexpected error occurred during registration.")

def authenticate_user_db(db: DBSession, username_or_email: str, password: str) -> Optional[Dict[str, Any]]:
    with tracer.start_as_current_span("service.authenticate_user") as span:
        span.set_attribute("app.user.identifier", username_or_email)
        logger.info("Authenticating user", identifier=username_or_email)
        try:
            normalized_identifier = username_or_email.lower()
            user = db.query(User).filter(or_(func.lower(User.username) == normalized_identifier, func.lower(User.email) == normalized_identifier)).one_or_none()
            if not user:
                logger.warning("Authentication failed: User not found", identifier=username_or_email)
                span.set_attribute("app.user.found", False)
                return None
            span.set_attribute("app.user.found", True)
            span.set_attribute("app.user.id", str(user.id))
            if not _verify_password(password, user.password_hash):
                logger.warning("Authentication failed: Incorrect password", user_id=user.id, username=user.username)
                span.set_attribute("app.auth.success", False)
                return None
            span.set_attribute("app.auth.success", True)
            logger.info("Authentication successful", user_id=user.id, username=user.username)
            return user.to_dict(include_sensitive=False)
        except SQLAlchemyError as e:
            logger.error("Database error during user authentication", identifier=username_or_email, exc_info=True)
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, "DB Error")
            raise
        except Exception as e:
            logger.error("Unexpected error during user authentication", identifier=username_or_email, exc_info=True)
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, "Unknown Error")
            raise

def get_all_users_db(db: DBSession) -> List[Dict[str, Any]]:
    with tracer.start_as_current_span("service.get_all_users") as span:
        logger.info("Fetching all users from DB.")
        try:
            users = db.query(User).all()
            return [u.to_dict() for u in users]
        except SQLAlchemyError as e:
            logger.error("Database error fetching all users", exc_info=True)
            _handle_sqlalchemy_error(e, "fetching all users", db)
        except Exception as e:
            logger.error("Unexpected error fetching all users", exc_info=True)
            abort(500, "An unexpected error occurred while fetching users.")

def request_password_reset_db(db: DBSession, email_or_username: str) -> bool:
    with tracer.start_as_current_span("service.request_password_reset") as span:
        span.set_attribute("app.user.identifier", email_or_username)
        logger.info("Password reset request received", identifier=email_or_username)
        user = db.query(User).filter(or_(User.username == email_or_username, User.email == email_or_username)).one_or_none()
        if not user:
            logger.warning("Password reset request for non-existent user.", identifier=email_or_username)
            span.set_attribute("app.user.found", False)
            return True
        span.set_attribute("app.user.found", True)
        span.set_attribute("app.user.id", str(user.id))
        if not fernet_suite:
             logger.error("Password reset failed: Encryption suite not initialized.")
             abort(503, description="Password reset service unavailable.")
        try:
            user_id_bytes = str(user.id).encode('utf-8')
            token = fernet_suite.encrypt(user_id_bytes).decode('utf-8')
            expires_at = datetime.utcnow() + timedelta(hours=1)
            user.password_reset_token = token
            user.password_reset_expires = expires_at
            user.updated_at = datetime.utcnow()
            db.commit()
            app_url = os.getenv("FRONTEND_APP_URL", "http://frontend:5173")
            reset_link = f"{app_url}/reset-password/{token}"
            email_user_env = os.getenv("EMAIL_USER") # Renamed to avoid conflict
            email_password_env = os.getenv("EMAIL_PASSWORD")
            email_server_env = os.getenv("EMAIL_SERVER")
            email_port_env = os.getenv("EMAIL_PORT")
            mail_sender_env = os.getenv("MAIL_SENDER", email_user_env)
            if email_user_env and email_password_env and email_server_env and email_port_env:
                 try:
                     logger.info("Password reset email sent (simulated/placeholder).", user_id=user.id, email=user.email)
                     span.set_attribute("app.email.sent", True)
                 except Exception as email_err:
                     logger.error("Failed to send password reset email.", user_id=user.id, email=user.email, exc_info=True)
                     span.set_attribute("app.email.sent", False)
                     span.record_exception(email_err)
            else:
                logger.warning("Email sending is not configured. Password reset link generated but not sent.", user_id=user.id, reset_link=reset_link)
                span.set_attribute("app.email.sent", False)
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

def reset_password_db(db: DBSession, token: str, new_password: str) -> bool:
    with tracer.start_as_current_span("service.reset_password") as span:
        span.set_attribute("app.password_reset.token_provided", bool(token))
        if not fernet_suite:
             logger.error("Password reset failed: Encryption suite not initialized.")
             abort(503, description="Password reset service unavailable.")
        try:
            user = db.query(User).filter(User.password_reset_token == token, User.password_reset_expires > datetime.utcnow()).one_or_none()
            if not user:
                logger.warning("Password reset failed: Invalid or expired token provided.")
                span.set_attribute("app.password_reset.token_valid", False)
                abort(400, description="Invalid or expired password reset token.")
            span.set_attribute("app.password_reset.token_valid", True)
            span.set_attribute("app.user.id", str(user.id))
            try: _validate_password_complexity(new_password)
            except ValueError as e:
                logger.warning("Password reset failed: New password complexity requirements not met.", user_id=user.id, reason=str(e))
                abort(400, description=str(e))
            user.password_hash = _hash_password(new_password)
            user.password_reset_token = None
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
        except HTTPException as e: raise e
        except Exception as e:
            db.rollback()
            logger.error("Unexpected error during password reset.", exc_info=True)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Unknown Error"))
            abort(500, description="An unexpected error occurred during password reset.")

# --- Tree Services ---
def create_tree_db(db: DBSession, user_id: uuid.UUID, tree_data: Dict[str, Any]) -> Dict[str, Any]:
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
                name=tree_data['name'], description=tree_data.get('description'), created_by=user_id,
                is_public=tree_data.get('is_public', False),
                default_privacy_level=PrivacyLevelEnum(tree_data.get('default_privacy_level', PrivacyLevelEnum.private.value)),
                created_at=datetime.utcnow(), updated_at=datetime.utcnow()
            )
            db.add(new_tree)
            db.commit()
            db.refresh(new_tree)
            tree_access = TreeAccess(
                 tree_id=new_tree.id, user_id=user_id, access_level='admin',
                 granted_by=user_id, granted_at=datetime.utcnow()
            )
            db.add(tree_access)
            db.commit()
            logger.info("Tree created successfully", tree_id=new_tree.id, tree_name=new_tree.name, created_by=user_id, event_type="TREE_CREATED")
            span.set_attribute("tree.id", str(new_tree.id))
            return new_tree.to_dict()
        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Database error during tree creation.", user_id=user_id, tree_name=tree_name, exc_info=True)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "DB Error"))
            _handle_sqlalchemy_error(e, "creating tree", db)
        except ValueError as e:
             db.rollback()
             logger.warning("Invalid privacy level during tree creation.", user_id=user_id, tree_name=tree_name, error=str(e))
             abort(400, description=f"Invalid privacy level: {e}")
        except Exception as e:
            db.rollback()
            logger.error("Unexpected error during tree creation.", user_id=user_id, tree_name=tree_name, exc_info=True)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Unknown Error"))
            abort(500, description="An unexpected error occurred during tree creation.")

def get_user_trees_db(db: DBSession, user_id: uuid.UUID) -> List[Dict[str, Any]]:
    with tracer.start_as_current_span("service.get_user_trees") as span:
        span.set_attribute("app.user.id", str(user_id))
        logger.info("Fetching trees for user", user_id=user_id)
        try:
            trees = db.query(Tree).join(TreeAccess, Tree.id == TreeAccess.tree_id).filter(or_(Tree.created_by == user_id, TreeAccess.user_id == user_id)).distinct().all()
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
def get_all_people_db(db: DBSession, tree_id: uuid.UUID) -> List[Dict[str, Any]]:
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

def get_person_db(db: DBSession, person_id: uuid.UUID, tree_id: uuid.UUID) -> Dict[str, Any]:
    with tracer.start_as_current_span("service.get_person") as span:
        span.set_attribute("person.id", str(person_id))
        span.set_attribute("tree.id", str(tree_id))
        logger.info("Fetching person details", person_id=person_id, tree_id=tree_id)
        person = _get_or_404(db, Person, person_id, tree_id)
        return person.to_dict()

def create_person_db(db: DBSession, user_id: uuid.UUID, tree_id: uuid.UUID, person_data: Dict[str, Any]) -> Dict[str, Any]:
    with tracer.start_as_current_span("service.create_person") as span:
        span.set_attribute("app.user.id", str(user_id))
        span.set_attribute("tree.id", str(tree_id))
        person_name = f"{person_data.get('first_name', '')} {person_data.get('last_name', '')}".strip()
        span.set_attribute("person.name", person_name)
        logger.info("Attempting to create new person", user_id=user_id, tree_id=tree_id, person_name=person_name)
        if not person_data or not person_data.get('first_name'):
            logger.warning("Person creation failed: Missing first name.")
            abort(400, description={"details": {"first_name": "First name is required."}})
        birth_date_str = person_data.get('birth_date')
        death_date_str = person_data.get('death_date')
        birth_date = None
        death_date = None
        if birth_date_str:
            try: birth_date = date.fromisoformat(birth_date_str) if birth_date_str else None
            except ValueError:
                logger.warning("Person creation failed: Invalid birth date format.", birth_date=birth_date_str)
                abort(400, description={"details": {"birth_date": "Invalid date format (YYYY-MM-DD)."}})
        if death_date_str:
            try: death_date = date.fromisoformat(death_date_str) if death_date_str else None
            except ValueError:
                logger.warning("Person creation failed: Invalid death date format.", death_date=death_date_str)
                abort(400, description={"details": {"death_date": "Invalid date format (YYYY-MM-DD)."}})
        if birth_date and death_date and death_date < birth_date:
            logger.warning("Person creation failed: Death date before birth date.")
            abort(400, description={"details": {"date_comparison": "Death date cannot be before birth date."}})
        gender = person_data.get('gender')
        if gender and gender.lower() not in ['male', 'female', 'other', 'unknown']:
             logger.warning("Person creation failed: Invalid gender value.", gender=gender)
             abort(400, description={"details": {"gender": "Invalid gender value."}})
        try:
            new_person = Person(
                tree_id=tree_id, first_name=person_data['first_name'], middle_names=person_data.get('middle_names'),
                last_name=person_data.get('last_name'), maiden_name=person_data.get('maiden_name'),
                nickname=person_data.get('nickname'), gender=gender, birth_date=birth_date,
                birth_date_approx=person_data.get('birth_date_approx', False), birth_place=person_data.get('birth_place'),
                death_date=death_date, death_date_approx=person_data.get('death_date_approx', False),
                death_place=person_data.get('death_place'), burial_place=person_data.get('burial_place'),
                privacy_level=PrivacyLevelEnum(person_data.get('privacy_level', PrivacyLevelEnum.inherit.value)),
                is_living=person_data.get('is_living'), notes=person_data.get('notes'),
                custom_attributes=person_data.get('custom_attributes', {}), created_by=user_id,
                created_at=datetime.utcnow(), updated_at=datetime.utcnow()
            )
            if new_person.is_living is None: new_person.is_living = new_person.death_date is None
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
        except ValueError as e:
             db.rollback()
             logger.warning("Invalid privacy level during person creation.", user_id=user_id, tree_id=tree_id, person_name=person_name, error=str(e))
             abort(400, description=f"Invalid privacy level: {e}")
        except Exception as e:
            db.rollback()
            logger.error("Unexpected error during person creation.", user_id=user_id, tree_id=tree_id, person_name=person_name, exc_info=True)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Unknown Error"))
            abort(500, description="An unexpected error occurred during person creation.")

def update_person_db(db: DBSession, person_id: uuid.UUID, tree_id: uuid.UUID, person_data: Dict[str, Any]) -> Dict[str, Any]:
    with tracer.start_as_current_span("service.update_person") as span:
        span.set_attribute("person.id", str(person_id))
        span.set_attribute("tree.id", str(tree_id))
        logger.info("Attempting to update person", person_id=person_id, tree_id=tree_id)
        person = _get_or_404(db, Person, person_id, tree_id)
        update_fields = {}
        validation_errors = {}
        allowed_fields = [
            'first_name', 'middle_names', 'last_name', 'maiden_name', 'nickname', 'gender',
            'birth_date', 'birth_date_approx', 'birth_place', 'death_date', 'death_date_approx',
            'death_place', 'burial_place', 'privacy_level', 'is_living', 'notes', 'custom_attributes'
        ]
        for field in allowed_fields:
            if field in person_data:
                value = person_data[field]
                try:
                    if field in ['birth_date', 'death_date']:
                        update_fields[field] = date.fromisoformat(value) if value else None
                    elif field == 'gender':
                         if value and value.lower() not in ['male', 'female', 'other', 'unknown']: validation_errors[field] = "Invalid gender value."
                         else: update_fields[field] = value if value else None
                    elif field == 'privacy_level':
                         try: update_fields[field] = PrivacyLevelEnum(value) if value else None
                         except ValueError: validation_errors[field] = "Invalid privacy level value."
                    elif field == 'custom_attributes':
                         if not isinstance(value, dict): validation_errors[field] = "Custom attributes must be a dictionary."
                         else: update_fields[field] = value
                    else: update_fields[field] = value
                except ValueError as e: validation_errors[field] = f"Invalid value: {e}"
                except Exception as e:
                     logger.error(f"Unexpected error validating field {field} during person update.", exc_info=True)
                     validation_errors[field] = "An unexpected error occurred validating this field."
        if validation_errors:
             logger.warning("Person update failed: Validation errors.", person_id=person_id, errors=validation_errors)
             abort(400, description={"error": "Validation failed", "details": validation_errors})
        for field, value in update_fields.items(): setattr(person, field, value)
        if person.birth_date and person.death_date and person.death_date < person.birth_date:
            validation_errors['date_comparison'] = "Death date cannot be before birth date."
            logger.warning("Person update failed: Death date before birth date after updates.", person_id=person_id, errors=validation_errors)
            abort(400, description={"error": "Validation failed", "details": validation_errors})
        if 'is_living' not in update_fields and ('death_date' in update_fields or 'birth_date' in update_fields):
             person.is_living = person.death_date is None
        person.updated_at = datetime.utcnow()
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

def delete_person_db(db: DBSession, person_id: uuid.UUID, tree_id: uuid.UUID) -> bool:
    with tracer.start_as_current_span("service.delete_person") as span:
        span.set_attribute("person.id", str(person_id))
        span.set_attribute("tree.id", str(tree_id))
        logger.info("Attempting to delete person", person_id=person_id, tree_id=tree_id)
        person = _get_or_404(db, Person, person_id, tree_id)
        person_name_for_log = f"{person.first_name} {person.last_name}".strip()
        try:
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
def get_all_relationships_db(db: DBSession, tree_id: uuid.UUID) -> List[Dict[str, Any]]:
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

def create_relationship_db(db: DBSession, user_id: uuid.UUID, tree_id: uuid.UUID, relationship_data: Dict[str, Any]) -> Dict[str, Any]:
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
        if not p1_id_str or not p2_id_str or not rel_type_str:
            logger.warning("Relationship creation failed: Missing required fields.")
            abort(400, description="person1, person2, and relationshipType are required.")
        if p1_id_str == p2_id_str:
            logger.warning("Relationship creation failed: Cannot create relationship with the same person.")
            abort(400, description="Cannot create a relationship between the same person.")
        try:
            person1_id_uuid = uuid.UUID(p1_id_str) # Renamed to avoid conflict
            person2_id_uuid = uuid.UUID(p2_id_str)
        except ValueError:
            logger.warning("Relationship creation failed: Invalid UUID format for person IDs.")
            abort(400, description="Invalid UUID format for person IDs.")
        try: relationship_type_enum = RelationshipTypeEnum(rel_type_str) # Renamed
        except ValueError:
            logger.warning("Relationship creation failed: Invalid relationship type.", rel_type=rel_type_str)
            abort(400, description=f"Invalid relationship type: {rel_type_str}")
        _get_or_404(db, Person, person1_id_uuid, tree_id)
        _get_or_404(db, Person, person2_id_uuid, tree_id)
        try:
            new_relationship = Relationship(
                tree_id=tree_id, person1_id=person1_id_uuid, person2_id=person2_id_uuid,
                relationship_type=relationship_type_enum, start_date=relationship_data.get('start_date'),
                end_date=relationship_data.get('end_date'), certainty_level=relationship_data.get('certainty_level'),
                custom_attributes=relationship_data.get('custom_attributes', {}), notes=relationship_data.get('notes'),
                created_by=user_id, created_at=datetime.utcnow(), updated_at=datetime.utcnow()
            )
            if new_relationship.start_date and not isinstance(new_relationship.start_date, date):
                 try: new_relationship.start_date = date.fromisoformat(str(new_relationship.start_date)) if new_relationship.start_date else None
                 except ValueError: abort(400, description={"details": {"start_date": "Invalid date format (YYYY-MM-DD)."}})
            if new_relationship.end_date and not isinstance(new_relationship.end_date, date):
                 try: new_relationship.end_date = date.fromisoformat(str(new_relationship.end_date)) if new_relationship.end_date else None
                 except ValueError: abort(400, description={"details": {"end_date": "Invalid date format (YYYY-MM-DD)."}})
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
        except HTTPException as e: raise e
        except Exception as e:
            db.rollback()
            logger.error("Unexpected error during relationship creation.", user_id=user_id, tree_id=tree_id, exc_info=True)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Unknown Error"))
            abort(500, description="An unexpected error occurred during relationship creation.")

def update_relationship_db(db: DBSession, relationship_id: uuid.UUID, tree_id: uuid.UUID, relationship_data: Dict[str, Any]) -> Dict[str, Any]:
    with tracer.start_as_current_span("service.update_relationship") as span:
        span.set_attribute("relationship.id", str(relationship_id))
        span.set_attribute("tree.id", str(tree_id))
        logger.info("Attempting to update relationship", rel_id=relationship_id, tree_id=tree_id)
        relationship = _get_or_404(db, Relationship, relationship_id, tree_id)
        update_fields = {}
        validation_errors = {}
        field_map = {'person1': 'person1_id', 'person2': 'person2_id', 'relationshipType': 'relationship_type'}
        allowed_fields_update = [
            'person1', 'person2', 'relationshipType', 'start_date', 'end_date',
            'certainty_level', 'custom_attributes', 'notes'
        ] # Renamed to avoid conflict
        for key_from_data in allowed_fields_update:
            if key_from_data in relationship_data:
                value = relationship_data[key_from_data]
                model_field_name = field_map.get(key_from_data, key_from_data)
                try:
                    if model_field_name in ['person1_id', 'person2_id']:
                        try: update_fields[model_field_name] = uuid.UUID(value) if value else None
                        except ValueError: validation_errors[key_from_data] = "Invalid UUID format."
                    elif model_field_name == 'relationship_type':
                         try: update_fields[model_field_name] = RelationshipTypeEnum(value) if value else None
                         except ValueError: validation_errors[key_from_data] = "Invalid relationship type value."
                    elif model_field_name in ['start_date', 'end_date']:
                        update_fields[model_field_name] = date.fromisoformat(str(value)) if value else None
                    elif model_field_name == 'certainty_level':
                         if value is not None and (not isinstance(value, int) or not (1 <= value <= 5)):
                             validation_errors[key_from_data] = "Certainty level must be an integer between 1 and 5."
                         else: update_fields[model_field_name] = value
                    elif model_field_name == 'custom_attributes':
                         if not isinstance(value, dict): validation_errors[key_from_data] = "Custom attributes must be a dictionary."
                         else: update_fields[model_field_name] = value
                    else: update_fields[model_field_name] = value
                except ValueError as e: validation_errors[key_from_data] = f"Invalid value: {e}"
                except Exception as e:
                     logger.error(f"Unexpected error validating field {key_from_data} for model field {model_field_name} during relationship update.", exc_info=True)
                     validation_errors[key_from_data] = "An unexpected error occurred validating this field."
        if validation_errors:
             logger.warning("Relationship update failed: Validation errors.", rel_id=relationship_id, errors=validation_errors)
             abort(400, description={"error": "Validation failed", "details": validation_errors})
        for field, value in update_fields.items(): setattr(relationship, field, value)
        if relationship.person1_id == relationship.person2_id:
              validation_errors['person_ids'] = "Cannot create a relationship between the same person."
              abort(400, description={"error": "Validation failed", "details": validation_errors})
        if 'person1_id' in update_fields and update_fields['person1_id']: _get_or_404(db, Person, update_fields['person1_id'], tree_id)
        if 'person2_id' in update_fields and update_fields['person2_id']: _get_or_404(db, Person, update_fields['person2_id'], tree_id)
        if relationship.start_date and relationship.end_date and relationship.end_date < relationship.start_date:
            validation_errors['date_comparison'] = "End date cannot be before start date."
            abort(400, description={"error": "Validation failed", "details": validation_errors})
        relationship.updated_at = datetime.utcnow()
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
        except HTTPException as e: raise e
        except Exception as e:
            db.rollback()
            logger.error("Unexpected error during relationship update.", rel_id=relationship_id, tree_id=tree_id, exc_info=True)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Unknown Error"))
            abort(500, description="An unexpected error occurred during relationship update.")

def delete_relationship_db(db: DBSession, relationship_id: uuid.UUID, tree_id: uuid.UUID) -> bool:
    with tracer.start_as_current_span("service.delete_relationship") as span:
        span.set_attribute("relationship.id", str(relationship_id))
        span.set_attribute("tree.id", str(tree_id))
        logger.info("Attempting to delete relationship", rel_id=relationship_id, tree_id=tree_id)
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
def get_tree_data_db(db: DBSession, tree_id: uuid.UUID) -> Dict[str, Any]:
    with tracer.start_as_current_span("service.get_tree_data") as span:
        span.set_attribute("tree.id", str(tree_id))
        logger.info("Fetching full tree data for visualization", tree_id=tree_id)
        try:
            people = db.query(Person).filter(Person.tree_id == tree_id).all()
            relationships = db.query(Relationship).filter(Relationship.tree_id == tree_id).all()
            nodes = []
            for person_obj in people: # Renamed to avoid conflict
                label = f"{person_obj.first_name or ''} {person_obj.last_name or ''}".strip()
                if person_obj.nickname: label += f" ({person_obj.nickname})"
                if not label: label = str(person_obj.id)[:8]
                nodes.append({
                    "id": str(person_obj.id), "type": "personNode", "position": {"x": 0, "y": 0},
                    "data": {
                        "id": str(person_obj.id), "label": label,
                        "full_name": f"{person_obj.first_name or ''} {person_obj.last_name or ''}".strip(),
                        "gender": person_obj.gender,
                        "dob": person_obj.birth_date.isoformat() if person_obj.birth_date else None,
                        "dod": person_obj.death_date.isoformat() if person_obj.death_date else None,
                        "birth_place": person_obj.birth_place, "death_place": person_obj.death_place,
                        "is_living": person_obj.is_living,
                    },
                    "person_id": str(person_obj.id)
                })
            links = []
            for rel_obj in relationships: # Renamed
                links.append({
                    "id": str(rel_obj.id), "source": str(rel_obj.person1_id), "target": str(rel_obj.person2_id),
                    "type": "default", "animated": False, "label": rel_obj.relationship_type.value,
                    "data": rel_obj.to_dict()
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
try:
    engine = create_engine(DATABASE_URL, pool_size=32, echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) # Use DBSession alias if needed elsewhere
    SQLAlchemyInstrumentor().instrument(engine=engine)
    logger.info("SQLAlchemy engine and session factory created.")
except Exception as e:
    logger.critical(f"Failed to create SQLAlchemy engine or session factory: {e}", exc_info=True)
    exit(1)

# --- Database Initialization Functions ---
def create_tables(engine_to_use):
    logger.info("Attempting to create database tables if they don't exist...")
    try:
        inspector = inspect(engine_to_use)
        existing_tables = inspector.get_table_names()
        if not existing_tables:
             logger.info("No tables found. Creating all tables...")
             Base.metadata.create_all(bind=engine_to_use)
             logger.info("Database tables creation attempt complete.")
        else:
             logger.info(f"Found {len(existing_tables)} existing tables. Skipping creation.")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}", exc_info=True)
        raise

def populate_initial_data(session_factory):
    logger.info("Checking if initial data population is needed...")
    db_session_init = session_factory() # Renamed
    try:
        user_count = db_session_init.query(func.count(User.id)).scalar()
        if user_count == 0:
            logger.info("No users found. Populating initial admin data...")
            admin_username = os.getenv("INITIAL_ADMIN_USERNAME", "admin")
            admin_email = os.getenv("INITIAL_ADMIN_EMAIL", "admin@example.com")
            admin_password = os.getenv("INITIAL_ADMIN_PASSWORD")
            if not admin_password:
                 logger.critical("INITIAL_ADMIN_PASSWORD environment variable is not set. Cannot create initial admin user.")
                 return
            try: _validate_password_complexity(admin_password)
            except ValueError as e:
                 logger.critical(f"Initial admin password complexity requirements not met: {e}. Cannot create initial admin user.")
                 return
            hashed_password = _hash_password(admin_password)
            admin_user = User(
                username=admin_username, email=admin_email, password_hash=hashed_password,
                role=UserRole.ADMIN, is_active=True, email_verified=True
            )
            db_session_init.add(admin_user)
            db_session_init.commit()
            logger.info(f"Initial admin user '{admin_user.username}' created successfully.")
        else:
            logger.info(f"Database already contains {user_count} users. Skipping initial data population.")
    except SQLAlchemyError as e:
        logger.error(f"Database error during initial data population: {e}", exc_info=True)
        db_session_init.rollback()
    except Exception as e:
        logger.error(f"Unexpected error during initial data population: {e}", exc_info=True)
        db_session_init.rollback()
    finally:
        db_session_init.close()

def initialize_database(engine_to_use, session_factory):
    logger.info("Initializing database...")
    try:
        create_tables(engine_to_use)
        populate_initial_data(session_factory)
        logger.info("Database initialization complete.")
    except Exception as e:
        logger.critical(f"Database initialization failed: {e}", exc_info=True)

initialize_database(engine, SessionLocal)

@app.errorhandler(Exception)
def handle_global_exception(e):
    if isinstance(e, HTTPException):
        logger.warning("HTTP exception occurred", status_code=e.code, description=e.description, path=request.path, method=request.method)
        response = jsonify({"error": e.description, "details": getattr(e, "details", None)})
        response.status_code = e.code
        return response
    logger.error("Unexpected exception occurred", exc_info=True, path=request.path, method=request.method)
    return jsonify({"error": "An unexpected error occurred. Please try again later."}), 500

# --- Flask Request Lifecycle Hooks ---
@app.before_request
def before_request_hook():
    g.db = SessionLocal() # Use SessionLocal directly, which is a factory for DBSession instances

@app.teardown_appcontext
def teardown_db_hook(exception=None):
    db = g.pop('db', None)
    if db is not None:
        try: db.close()
        except Exception as e: logger.error(f"Error closing database session: {e}", exc_info=True)

# --- API Endpoints ---
@limiter.limit("5 per minute")
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        abort(400, description="Username and password are required.")
    username_or_email = data['username']
    password = data['password']
    db = g.db
    user = authenticate_user_db(db, username_or_email, password)
    if not user:
        auth_failure_counter.add(1, {"reason": "invalid_credentials", "identifier": username_or_email[:30]})
        abort(401, description="Incorrect username or password.")
    session['user_id'] = str(user['id'])
    session['username'] = user['username']
    session['role'] = user['role']
    logger.info("User logged in successfully", user_id=user['id'], username=user['username'])
    return jsonify({"message": "Login successful!", "user": user}), 200

@limiter.limit("2 per minute")
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password') or not data.get('email'):
        abort(400, description="Username, email, and password are required.")
    db = g.db
    try:
        user_data = {
            'username': data['username'], 'email': data['email'], 'password': data['password'],
            'full_name': data.get('full_name'), 'role': data.get('role', UserRole.USER.value)
        }
        if 'role' in data:
             try: UserRole(data['role'])
             except ValueError: abort(400, description=f"Invalid role specified: {data['role']}")
        user = register_user_db(db, user_data)
        user_registration_counter.add(1, {"status": "success"})
        logger.info("User registered successfully", user_id=user['id'], username=user['username'])
        return jsonify({"message": "Registration successful!", "user": user}), 201
    except HTTPException as e:
        user_registration_counter.add(1, {"status": "failure", "reason": "http_exception"})
        raise e
    except Exception as e:
        user_registration_counter.add(1, {"status": "failure", "reason": "unknown_error"})
        logger.error("Unexpected error during registration", exc_info=True)
        abort(500, description="An unexpected error occurred during registration.")

@app.route('/api/logout', methods=['POST'])
@require_auth
def logout():
    user_id = session.get('user_id')
    username = session.get('username')
    session.clear()
    logger.info("User logged out successfully", user_id=user_id, username=username)
    return jsonify({"message": "Logout successful"}), 200

@app.route('/api/session', methods=['GET'])
def session_status():
    if 'user_id' not in session:
        return jsonify({"isAuthenticated": False, "user": None, "active_tree_id": None}), 200
    user_id = session['user_id']
    username = session['username']
    role = session['role']
    active_tree_id = session.get('active_tree_id')
    logger.debug("Session status retrieved", user_id=user_id, username=username, active_tree_id=active_tree_id)
    return jsonify({
        "isAuthenticated": True, "user": {"id": user_id, "username": username, "role": role},
        "active_tree_id": active_tree_id
    }), 200

@limiter.limit("3 per minute")
@app.route('/api/request-password-reset', methods=['POST'])
def request_password_reset():
    data = request.get_json()
    if not data or not data.get('email'):
        abort(400, description="Email or username is required.")
    email_or_username = data['email']
    db = g.db
    request_password_reset_db(db, email_or_username)
    return jsonify({"message": "If an account exists for this identifier, a password reset link has been sent."}), 200

@limiter.limit("3 per minute")
@app.route('/api/reset-password/<token>', methods=['POST'])
def reset_password(token: str): # Added type hint
    data = request.get_json()
    if not data or not data.get('new_password'):
        abort(400, description="New password is required.")
    new_password = data['new_password']
    db = g.db
    reset_password_db(db, token, new_password)
    return jsonify({"message": "Password reset successfully."}), 200

@app.route('/api/trees', methods=['POST'])
@require_auth
def create_tree():
    data = request.get_json()
    if not data or not data.get('name'): abort(400, description="Tree name is required.")
    user_id = uuid.UUID(session['user_id'])
    db = g.db
    try:
        new_tree = create_tree_db(db, user_id, data)
        session['active_tree_id'] = new_tree['id']
        return jsonify(new_tree), 201
    except HTTPException as e: raise e
    except Exception as e:
        logger.error("Unexpected error in create_tree endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while creating the tree.")

@app.route('/api/trees', methods=['GET'])
@require_auth
def get_user_trees():
    user_id = uuid.UUID(session['user_id'])
    db = g.db
    try:
        trees = get_user_trees_db(db, user_id)
        return jsonify(trees), 200
    except HTTPException as e: raise e
    except Exception as e:
        logger.error("Unexpected error in get_user_trees endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while fetching user trees.")

@app.route('/api/session/active_tree', methods=['PUT'])
@require_auth
def set_active_tree():
    data = request.get_json()
    if not data or not data.get('tree_id'): abort(400, description="tree_id is required.")
    tree_id_str = data['tree_id']
    user_id = uuid.UUID(session['user_id'])
    db = g.db
    try: tree_id_uuid = uuid.UUID(tree_id_str)
    except ValueError: abort(400, description="Invalid UUID format for tree_id.")
    tree = db.query(Tree).filter(Tree.id == tree_id_uuid).one_or_none()
    if not tree: abort(404, description=f"Tree with ID {tree_id_str} not found.")
    can_set_active = False
    if tree.created_by == user_id or tree.is_public: can_set_active = True
    else:
        tree_access_obj = db.query(TreeAccess).filter(TreeAccess.tree_id == tree_id_uuid, TreeAccess.user_id == user_id).one_or_none()
        if tree_access_obj: can_set_active = True
    if not can_set_active: abort(403, description=f"Access denied to tree {tree_id_str}.")
    session['active_tree_id'] = tree_id_str
    logger.info("Active tree set in session.", user_id=user_id, tree_id=tree_id_str)
    return jsonify({"message": "Active tree set successfully.", "active_tree_id": tree_id_str}), 200

@app.route('/api/people', methods=['GET'])
@require_tree_access('view')
def get_all_people():
    db = g.db
    tree_id = g.active_tree_id
    try:
        people_list = get_all_people_db(db, tree_id) # Renamed
        return jsonify(people_list), 200
    except HTTPException as e: raise e
    except Exception as e:
        logger.error("Unexpected error in get_all_people endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while fetching people.")

@app.route('/api/people/<uuid:person_id>', methods=['GET'])
@require_tree_access('view')
def get_person(person_id: uuid.UUID):
    db = g.db
    tree_id = g.active_tree_id
    try:
        person_details = get_person_db(db, person_id, tree_id) # Renamed
        return jsonify(person_details), 200
    except HTTPException as e: raise e
    except Exception as e:
        logger.error("Unexpected error in get_person endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while fetching the person.")

@app.route('/api/people', methods=['POST'])
@require_tree_access('edit')
def create_person():
    data = request.get_json()
    if not data: abort(400, description="Request body is required and cannot be empty.")
    user_id = uuid.UUID(session['user_id'])
    tree_id = g.active_tree_id
    db = g.db
    try:
        new_person_obj = create_person_db(db, user_id, tree_id, data) # Renamed
        return jsonify(new_person_obj), 201
    except HTTPException as e: raise e
    except Exception as e:
        logger.error("Unexpected error in create_person endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while creating the person.")

@app.route('/api/people/<uuid:person_id>', methods=['PUT'])
@require_tree_access('edit')
def update_person(person_id: uuid.UUID):
    data = request.get_json()
    if not data: abort(400, description="Request body is required and cannot be empty.")
    tree_id = g.active_tree_id
    db = g.db
    try:
        updated_person_obj = update_person_db(db, person_id, tree_id, data) # Renamed
        return jsonify(updated_person_obj), 200
    except HTTPException as e: raise e
    except Exception as e:
        logger.error("Unexpected error in update_person endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while updating the person.")

@app.route('/api/people/<uuid:person_id>', methods=['DELETE'])
@require_tree_access('edit')
def delete_person(person_id: uuid.UUID):
    tree_id = g.active_tree_id
    db = g.db
    try:
        delete_person_db(db, person_id, tree_id)
        return '', 204
    except HTTPException as e: raise e
    except Exception as e:
        logger.error("Unexpected error in delete_person endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while deleting the person.")

@app.route('/api/relationships', methods=['GET'])
@require_tree_access('view')
def get_all_relationships():
    db = g.db
    tree_id = g.active_tree_id
    try:
        relationships_list = get_all_relationships_db(db, tree_id) # Renamed
        return jsonify(relationships_list), 200
    except HTTPException as e: raise e
    except Exception as e:
        logger.error("Unexpected error in get_all_relationships endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while fetching relationships.")

@app.route('/api/relationships/<uuid:relationship_id>', methods=['GET'])
@require_tree_access('view')
def get_relationship(relationship_id: uuid.UUID):
    with tracer.start_as_current_span("endpoint.get_relationship") as span:
        span.set_attribute("relationship.id", str(relationship_id))
        db = g.db
        tree_id = g.active_tree_id
        span.set_attribute("tree.id", str(tree_id))
        try:
            relationship_details = _get_or_404(db, Relationship, relationship_id, tree_id) # Renamed
            return jsonify(relationship_details.to_dict()), 200
        except HTTPException as e: raise e
        except Exception as e:
            logger.error("Unexpected error in get_relationship endpoint.", exc_info=True)
            abort(500, description="An unexpected error occurred while fetching the relationship.")

@app.route('/api/relationships', methods=['POST'])
@require_tree_access('edit')
def create_relationship():
    data = request.get_json()
    if not data: abort(400, description="Request body is required and cannot be empty.")
    user_id = uuid.UUID(session['user_id'])
    tree_id = g.active_tree_id
    db = g.db
    try:
        new_relationship_obj = create_relationship_db(db, user_id, tree_id, data) # Renamed
        return jsonify(new_relationship_obj), 201
    except HTTPException as e: raise e
    except Exception as e:
        logger.error("Unexpected error in create_relationship endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while creating the relationship.")

@app.route('/api/relationships/<uuid:relationship_id>', methods=['PUT'])
@require_tree_access('edit')
def update_relationship(relationship_id: uuid.UUID):
    data = request.get_json()
    if not data: abort(400, description="Request body is required and cannot be empty.")
    tree_id = g.active_tree_id
    db = g.db
    try:
        updated_relationship_obj = update_relationship_db(db, relationship_id, tree_id, data) # Renamed
        return jsonify(updated_relationship_obj), 200
    except HTTPException as e: raise e
    except Exception as e:
        logger.error("Unexpected error in update_relationship endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while updating the relationship.")

@app.route('/api/relationships/<uuid:relationship_id>', methods=['DELETE'])
@require_tree_access('edit')
def delete_relationship(relationship_id: uuid.UUID):
    tree_id = g.active_tree_id
    db = g.db
    try:
        delete_relationship_db(db, relationship_id, tree_id)
        return '', 204
    except HTTPException as e: raise e
    except Exception as e:
        logger.error("Unexpected error in delete_relationship endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while deleting the relationship.")

@app.route('/api/tree_data', methods=['GET'])
@require_tree_access('view')
def get_tree_data():
    db = g.db
    tree_id = g.active_tree_id
    try:
        tree_data_result = get_tree_data_db(db, tree_id)
        return jsonify(tree_data_result), 200
    except HTTPException as e: raise e
    except Exception as e:
        logger.error("Unexpected error in get_tree_data endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while fetching tree data.")

@app.route('/api/users', methods=['GET'])
@require_admin
def get_all_users():
    db = g.db
    try:
        users_list = get_all_users_db(db) # Renamed
        return jsonify(users_list), 200
    except HTTPException as e: raise e
    except Exception as e:
        logger.error("Unexpected error in get_all_users endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while fetching users.")

@app.route('/api/users/<uuid:user_id>', methods=['DELETE'])
@require_admin
def delete_user(user_id: uuid.UUID):
    current_user_id_str = session.get('user_id')
    if current_user_id_str and uuid.UUID(current_user_id_str) == user_id:
        logger.warning("Admin attempted to delete their own account.", user_id=current_user_id_str)
        abort(403, description="Admins cannot delete their own account via this endpoint.")
    db = g.db
    try:
        delete_user_db(db, user_id)
        return '', 204
    except HTTPException as e: raise e
    except Exception as e:
        logger.error("Unexpected error in delete_user endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while deleting the user.")

@app.route('/api/users/<uuid:user_id>/role', methods=['PUT'])
@require_admin
def set_user_role(user_id: uuid.UUID):
    data = request.get_json()
    if not data or not data.get('role'):
        abort(400, description="The 'role' field is required in the request body.")
    new_role_str = data['role']
    current_user_id_str = session.get('user_id')
    if current_user_id_str and uuid.UUID(current_user_id_str) == user_id:
        logger.warning("Admin attempted to change their own role.", user_id=current_user_id_str)
        abort(403, description="Admins cannot change their own role via this endpoint.")
    db = g.db
    try:
        updated_user_obj = update_user_role_db(db, user_id, new_role_str) # Renamed
        role_change_counter.add(1, {"admin_user_id": current_user_id_str, "target_user_id": str(user_id), "new_role": new_role_str})
        return jsonify(updated_user_obj), 200
    except HTTPException as e: raise e
    except Exception as e:
        logger.error("Unexpected error in set_user_role endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while setting the user role.")

@limiter.limit("60 per minute")
@app.route('/health', methods=['GET'])
def health_check():
    service_status = "healthy"
    db_status_check = "unknown" # Renamed
    db_latency_ms_check = None # Renamed
    dependencies_check = {} # Renamed
    start_time = time.monotonic()
    try:
        with SessionLocal() as health_db:
            health_db.execute(text("SELECT 1"))
            db_status_check = "healthy"
    except SQLAlchemyError as e:
        db_status_check = "unhealthy"; service_status = "unhealthy"
        logger.error(f"Database health check failed: {e}", exc_info=False)
    except Exception as e:
        db_status_check = "error"; service_status = "unhealthy"
        logger.error(f"Unexpected error during DB health check: {e}", exc_info=True)
    finally:
        end_time = time.monotonic()
        db_latency_ms_check = (end_time - start_time) * 1000
    dependencies_check["database"] = {"status": db_status_check, "latency_ms": round(db_latency_ms_check, 2) if db_latency_ms_check is not None else None}
    response_data = {"status": service_status, "timestamp": datetime.utcnow().isoformat() + "Z", "dependencies": dependencies_check}
    http_status = 200 if service_status == "healthy" else 503
    if service_status != "healthy": logger.warning("Health check. Status: %s, DB Status: %s, Latency: %.2f ms, Dependencies: %s", service_status, db_status_check, db_latency_ms_check or 0.0, dependencies_check)
    else: logger.debug("Health check. Status: %s, DB Status: %s, Latency: %.2f ms", service_status, db_status_check, db_latency_ms_check or 0.0)
    return jsonify(response_data), http_status

@limiter.limit("60 per minute")
@app.route('/metrics', methods=['GET'])
def metrics_endpoint():
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    try:
        prometheus_response = make_response(generate_latest()) # Renamed
        prometheus_response.headers['Content-Type'] = CONTENT_TYPE_LATEST
        return prometheus_response
    except Exception as e:
        logger.error(f"Error generating metrics: {e}", exc_info=True)
        abort(500, "Error generating metrics.")

if __name__ == '__main__':
    host = os.environ.get('FLASK_RUN_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_RUN_PORT', 8090))
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() in ['true', '1', 't']
    logger.info(f"Starting Flask server on {host}:{port} (Debug: {debug_mode})")
    app.run(host=host, port=port, debug=debug_mode)
