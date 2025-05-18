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
from cryptography.fernet import Fernet, InvalidToken
# cryptography.exceptions.InvalidSignature is a more specific exception if needed,
# but InvalidToken often covers it for Fernet.
from datetime import date, datetime, timedelta, timezone
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps
from dotenv import load_dotenv
import structlog
from typing import Optional, List, Dict, Any, Set, Tuple, TypeVar, Generic
from sqlalchemy.exc import IntegrityError, NoResultFound, SQLAlchemyError
from sqlalchemy.orm import Session as DBSession, Query # Aliased to avoid conflict with Flask-Session
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

# --- Constants ---
DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
PAGINATION_DEFAULTS = {
    "page": DEFAULT_PAGE,
    "per_page": DEFAULT_PAGE_SIZE,
    "max_per_page": MAX_PAGE_SIZE,
}

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

# Standard Flask app configurations
app.config.update(
    SESSION_COOKIE_SECURE=os.getenv('FLASK_ENV', 'development') == 'production', # True in prod
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax', # Consider 'Strict' or 'None' (with Secure=True) for production needs
    PERMANENT_SESSION_LIFETIME=timedelta(days=7) # Used if SESSION_PERMANENT is True
)

# Initialize Flask-Session
server_side_session = ServerSession()
server_side_session.init_app(app)


# Enable CORS for the Flask app
CORS(app, resources={r"/api/*": {"origins": os.getenv("CORS_ORIGINS", "http://localhost:5173").split(',')}}, supports_credentials=True)


# --- Rate Limiter Setup ---
limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri=redis_url,
    default_limits=["100 per second", "5000 per minute"] # Adjusted defaults
)

# --- Logging Setup (Using Structlog) ---
logging.basicConfig(level=logging.INFO, format='%(message)s', handlers=[logging.StreamHandler()])
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        # structlog.processors.add_log_level, # Redundant with stdlib.add_log_level
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.dict_tracebacks,
        # structlog.contextvars.merge_contextvars, # Already added
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
    foreign_pre_chain=[structlog.stdlib.add_log_level, structlog.stdlib.add_logger_name] # Add these here for foreign logs
)
handler = logging.getLogger().handlers[0]; handler.setFormatter(formatter)
logger = structlog.get_logger()

# --- OpenTelemetry Setup ---
otel_service_name = os.getenv("OTEL_SERVICE_NAME", "family-tree-backend")
otel_exporter_otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", None) # e.g. "http://localhost:4317"

resource = Resource(attributes={ "service.name": otel_service_name })
# Configure Tracer Provider
trace.set_tracer_provider(TracerProvider(resource=resource))
otlp_exporter_trace_args = {}
if otel_exporter_otlp_endpoint:
    otlp_exporter_trace_args["endpoint"] = urljoin(otel_exporter_otlp_endpoint, "v1/traces") # For HTTP
    # For gRPC, it would be just the endpoint without path, e.g., "localhost:4317"
    # Assuming gRPC exporter by default if OTLPSpanExporter is used directly.
    # If using OTLPSpanExporterHTTP, then the endpoint with /v1/traces is correct.
    # The default OTLPSpanExporter is gRPC.

otlp_exporter_trace = OTLPSpanExporter(**otlp_exporter_trace_args)
span_processor = BatchSpanProcessor(
    otlp_exporter_trace,
    max_export_batch_size=64,
    max_queue_size=128,
    export_timeout_millis=300,
)
trace.get_tracer_provider().add_span_processor(span_processor)
tracer = trace.get_tracer(__name__)

# Configure Meter Provider
otlp_exporter_metric_args = {}
if otel_exporter_otlp_endpoint:
    otlp_exporter_metric_args["endpoint"] = urljoin(otel_exporter_otlp_endpoint, "v1/metrics") # For HTTP

otlp_exporter_metric = OTLPMetricExporter(**otlp_exporter_metric_args)
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
# ENCRYPTION_KEY_FILE = "/backend/data/encryption_key.json" # Path seems specific, ensure it's correct if used

def load_encryption_key():
    """Load encryption key from environment variable or file."""
    key = os.getenv(ENCRYPTION_KEY_ENV_VAR)
    if key:
        logger.info("Encryption key loaded from environment variable.")
        return key.encode('utf-8') # Fernet expects bytes
    
    # Construct path relative to this file's directory for the key file
    base_dir = os.path.dirname(os.path.abspath(__file__))
    key_file_abs_path = os.path.join(base_dir, '..', 'data', 'encryption_key.json') # Assuming 'data' is sibling to 'backend'
    
    logger.info(f"Attempting to load encryption key from file: {key_file_abs_path}")
    try:
        with open(key_file_abs_path, 'r') as f:
            data = json.load(f)
            key_b64 = data.get('key_b64')
            if key_b64:
                logger.info(f"Key [***{key_b64[:6]}] found in JSON file.")
                return key_b64.encode('utf-8') # Fernet expects bytes
            else:
                logger.error("Key 'key_b64' not found in JSON file.")
                return None
    except FileNotFoundError:
        logger.warning(f"Encryption key file not found at {key_file_abs_path}.")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode encryption key JSON file: {e}")
        return None
    except KeyError: # Should be caught by data.get() returning None
        logger.error("Encryption key file is missing 'key_b64'.") # Redundant if using .get()
        return None
    except Exception as e:
        logger.error(f"Unexpected error loading encryption key from file: {e}")
        return None

try:
    _encryption_key_bytes = load_encryption_key()
    if _encryption_key_bytes:
        fernet_suite = Fernet(_encryption_key_bytes)
        logger.info("Fernet initialized successfully.")
    else:
        logger.critical("Encryption key is missing. Fernet cannot be initialized.")
        fernet_suite = None
except Exception as e:
    logger.critical(f"Failed to init Fernet: {e}", exc_info=True)
    fernet_suite = None

if fernet_suite is None:
    logger.critical("ENCRYPTION DISABLED. Sensitive data will be stored in plaintext if EncryptedString is used.")

class EncryptedString(TypeDecorator):
    """SQLAlchemy type for encrypted strings"""
    impl = Text # Using Text for potentially longer encrypted strings
    cache_ok = True # Safe to cache this type decorator

    def process_bind_param(self, value, dialect):
        if value is not None and fernet_suite:
            try:
                encoded_value = str(value).encode('utf-8')
                return fernet_suite.encrypt(encoded_value).decode('utf-8')
            except Exception as e:
                logger.error("Encryption failed for value.", error=str(e), exc_info=True)
                # Storing plaintext if encryption fails is a security risk.
                # Consider raising an error or returning a marker.
                # For now, matching original behavior but logging critical.
                logger.critical("Storing plaintext due to encryption failure.", field_value_start=str(value)[:20])
                return str(value) # Fallback to plaintext, but this is risky
        return value

    def process_result_value(self, value, dialect):
        if value is not None and fernet_suite:
            try:
                encrypted_bytes = str(value).encode('utf-8')
                return fernet_suite.decrypt(encrypted_bytes).decode('utf-8')
            except InvalidToken: # More specific Fernet exception
                logger.error("Decryption failed: Invalid token or signature.", field_value_start=str(value)[:20], exc_info=False)
                return None # Return None or a specific marker instead of encrypted data
            except Exception as e: # Catch other potential errors during decryption
                 logger.error("Unexpected error during decryption.", error=str(e), field_value_start=str(value)[:20], exc_info=True)
                 return None # Return None or a specific marker
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

class UserRole(enum.Enum): # This was already an enum.Enum
    USER = "user"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(SQLAlchemyEnum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) # Added updated_at
    last_login = Column(DateTime)
    preferences = Column(JSONB, default=dict)
    profile_image_path = Column(String(255))
    # Password reset token should ideally be stored hashed if it's long-lived or sensitive itself.
    # For short-lived tokens, this might be acceptable if the token is opaque.
    password_reset_token = Column(String(255), unique=True, index=True) # Added index
    password_reset_expires = Column(DateTime)

    def to_dict(self, include_sensitive=False):
        data = {
            "id": str(self.id), "username": self.username, "email": self.email,
            "full_name": self.full_name, "role": self.role.value, "is_active": self.is_active,
            "email_verified": self.email_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None, # Added
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "preferences": self.preferences, "profile_image_path": self.profile_image_path,
        }
        if include_sensitive:
             data['password_hash'] = self.password_hash # Be careful exposing this, even internally
             data['password_reset_token'] = self.password_reset_token
             data['password_reset_expires'] = self.password_reset_expires.isoformat() if self.password_reset_expires else None
        return data

class Tree(Base):
    __tablename__ = "trees"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    is_public = Column(Boolean, default=False)
    default_privacy_level = Column(SQLAlchemyEnum(PrivacyLevelEnum), default=PrivacyLevelEnum.private)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
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
    tree_id = Column(UUID(as_uuid=True), ForeignKey("trees.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    access_level = Column(String(50), nullable=False, default="view") # Consider Enum
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
    tree_id = Column(UUID(as_uuid=True), ForeignKey("trees.id", ondelete="CASCADE"), nullable=False, index=True)
    first_name = Column(String(100), index=True)
    middle_names = Column(String(255))
    last_name = Column(String(100), index=True)
    maiden_name = Column(String(100))
    nickname = Column(String(100))
    gender = Column(String(20)) # Consider Enum
    birth_date = Column(Date, index=True)
    birth_date_approx = Column(Boolean, default=False)
    birth_place = Column(String(255))
    death_date = Column(Date, index=True)
    death_date_approx = Column(Boolean, default=False)
    death_place = Column(String(255))
    burial_place = Column(String(255))
    privacy_level = Column(SQLAlchemyEnum(PrivacyLevelEnum), default=PrivacyLevelEnum.inherit)
    is_living = Column(Boolean, index=True)
    notes = Column(Text)
    custom_attributes = Column(JSONB, default=dict)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
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
    tree_id = Column(UUID(as_uuid=True), ForeignKey("trees.id", ondelete="CASCADE"), nullable=False, index=True)
    person1_id = Column(UUID(as_uuid=True), ForeignKey("people.id", ondelete="CASCADE"), nullable=False, index=True)
    person2_id = Column(UUID(as_uuid=True), ForeignKey("people.id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_type = Column(SQLAlchemyEnum(RelationshipTypeEnum), nullable=False)
    start_date = Column(Date)
    end_date = Column(Date)
    certainty_level = Column(Integer) # Consider a range or enum
    custom_attributes = Column(JSONB, default=dict)
    notes = Column(Text)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (
        UniqueConstraint("tree_id", "person1_id", "person2_id", "relationship_type", name="uq_relationship_key_fields"),
    ) # Example of a more specific unique constraint if needed
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

class Event(Base): # Add indexes as needed based on query patterns
    __tablename__ = "events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_id = Column(UUID(as_uuid=True), ForeignKey("trees.id", ondelete="CASCADE"), nullable=False, index=True)
    person_id = Column(UUID(as_uuid=True), ForeignKey("people.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    date = Column(Date, index=True)
    date_approx = Column(Boolean, default=False)
    date_range_start = Column(Date)
    date_range_end = Column(Date)
    place = Column(String(255))
    description = Column(Text)
    custom_attributes = Column(JSONB, default=dict)
    privacy_level = Column(SQLAlchemyEnum(PrivacyLevelEnum), default=PrivacyLevelEnum.inherit)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Add to_dict if this model will be directly returned by APIs

class Media(Base): # Add indexes as needed
    __tablename__ = "media"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_id = Column(UUID(as_uuid=True), ForeignKey("trees.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(String(512), nullable=False) # Potentially unique if not using storage_bucket for uniqueness
    storage_bucket = Column(String(255), nullable=False)
    media_type = Column(SQLAlchemyEnum(MediaTypeEnum), nullable=False)
    original_filename = Column(String(255))
    file_size = Column(Integer) # Use BigInteger for large files
    mime_type = Column(String(100))
    title = Column(String(255), index=True)
    description = Column(Text)
    date_taken = Column(Date)
    location = Column(String(255))
    media_metadata = Column(JSONB, default=dict)
    privacy_level = Column(SQLAlchemyEnum(PrivacyLevelEnum), default=PrivacyLevelEnum.inherit)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Add to_dict if this model will be directly returned by APIs

class Citation(Base): # Add indexes as needed
    __tablename__ = "citations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_id = Column(UUID(as_uuid=True), ForeignKey("trees.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = Column(UUID(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"), nullable=False, index=True) # Assuming media is the source
    # If source can be other entities, consider a polymorphic relationship or separate source table.
    citation_text = Column(Text, nullable=False)
    page_number = Column(String(50))
    confidence_level = Column(Integer) # Consider a range or enum
    notes = Column(Text)
    custom_attributes = Column(JSONB, default=dict)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Add to_dict if this model will be directly returned by APIs

class ActivityLog(Base):
    __tablename__ = "activity_log"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_id = Column(UUID(as_uuid=True), ForeignKey("trees.id", ondelete="SET NULL"), index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    action_type = Column(String(50), nullable=False, index=True)
    previous_state = Column(JSONB) # Can be large
    new_state = Column(JSONB) # Can be large
    ip_address = Column(String(50))
    user_agent = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
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

T = TypeVar('T', bound=Base) # Type variable for models

def apply_sorting(query: Query, model: T, sort_by: Optional[str], sort_order: Optional[str]) -> Query:
    """Applies sorting to a SQLAlchemy query."""
    if sort_by and hasattr(model, sort_by):
        column_to_sort = getattr(model, sort_by)
        if sort_order == "desc":
            query = query.order_by(desc(column_to_sort))
        else:
            query = query.order_by(asc(column_to_sort))
    elif not any(True for _ in query._order_by_clauses): # Apply default sort if none provided by user and none already on query
        if hasattr(model, "created_at"):
             query = query.order_by(desc(model.created_at)) # Default sort
        elif hasattr(model, "name"):
             query = query.order_by(asc(model.name))
    return query

def paginate_query(
    query: Query,
    model: T, # Pass the model for sorting and to_dict access
    page: int,
    per_page: int,
    max_per_page: int = MAX_PAGE_SIZE,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = "asc"
) -> Dict[str, Any]:
    """Paginates a SQLAlchemy query and returns a dictionary with pagination info."""
    per_page = min(abs(per_page), max_per_page)
    page = abs(page)

    # Apply sorting before counting and pagination
    query = apply_sorting(query, model, sort_by, sort_order)

    # Efficiently count total items without re-executing complex joins if possible
    # For simple queries, query.count() is fine. For complex ones, a separate count query might be needed.
    # The order_by(None) trick is to remove existing order_bys for count, if they make count slow.
    # However, if sorting was applied above, we might need to keep it or handle count carefully.
    # A common pattern:
    # count_query = query.order_by(None) if len(query._order_by_clauses) > 0 else query
    # total_items = count_query.count()
    # For simplicity here, assuming query.count() is acceptable after sorting.
    # If performance issues arise with count, optimize count query separately.
    try:
        total_items = query.count()
    except Exception as e: # Some DB drivers or query constructs might fail with .count() after certain operations.
        logger.warning(f"Could not execute efficient count on query, falling back to slower method or raising: {e}")
        # Fallback or re-raise depending on how critical precise count is vs. performance.
        # For now, let it raise if it's a fundamental issue.
        # A more robust way for complex queries is:
        # total_items = db_session.query(func.count()).select_from(query.order_by(None).subquery()).scalar()
        total_items = query.with_entities(func.count()).scalar()


    offset = (page - 1) * per_page
    items = query.limit(per_page).offset(offset).all()

    total_pages = (total_items + per_page - 1) // per_page if total_items > 0 else 0

    return {
        "items": [item.to_dict() for item in items if hasattr(item, 'to_dict')], # Ensure to_dict exists
        "page": page,
        "per_page": per_page,
        "total_items": total_items,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
        "sort_by": sort_by,
        "sort_order": sort_order
    }


def _handle_sqlalchemy_error(e: SQLAlchemyError, context: str, db: DBSession):
    db.rollback() # Ensure rollback on any SQLAlchemy error
    logger.error(f"SQLAlchemy Error during {context}", exc_info=True, error_type=type(e).__name__, orig_error=str(getattr(e, 'orig', None)))
    if isinstance(e, IntegrityError):
        detail = getattr(e.orig, 'diag', None) # For psycopg2
        constraint_name = detail.constraint_name if detail else None
        error_message = str(e.orig).lower()

        if constraint_name == 'users_username_key' or 'unique constraint "users_username_key"' in error_message:
            logger.warning(f"Integrity Error: Duplicate username during {context}", exc_info=False)
            abort(409, description="Username already exists.")
        elif constraint_name == 'users_email_key' or 'unique constraint "users_email_key"' in error_message:
            logger.warning(f"Integrity Error: Duplicate email during {context}", exc_info=False)
            abort(409, description="Email already exists.")
        elif constraint_name == 'tree_user_unique' or 'unique constraint "tree_user_unique"' in error_message:
             logger.warning(f"Integrity Error: Duplicate tree access entry during {context}", exc_info=False)
             abort(409, description="User already has access to this tree.")
        elif 'foreign key constraint' in error_message:
             logger.warning(f"Integrity Error: Foreign key violation during {context}", exc_info=False)
             abort(409, description=f"Cannot complete action due to related data dependencies.")
        elif "not null constraint failed" in error_message or "null value in column" in error_message:
            # Try to extract column name if possible (DB dependent)
            column_match = re.search(r"column \"(.*?)\"", error_message)
            column_name = column_match.group(1) if column_match else "a required field"
            logger.warning(f"Integrity Error: Not null constraint failed for {column_name} during {context}", exc_info=False)
            abort(400, description=f"Missing required field: {column_name}.")
        else:
            logger.error(f"Unhandled Integrity Error during {context}", exc_info=True)
            abort(409, description=f"Database conflict during {context}. Please check your input.")
    elif isinstance(e, NoResultFound):
        logger.warning(f"No Result Found during {context}", exc_info=False)
        abort(404, description="The requested resource was not found.")
    else: # Catch-all for other SQLAlchemyErrors
        logger.error(f"Unhandled SQLAlchemy Error during {context}", exc_info=True)
        abort(500, description=f"A database error occurred while {context}. Please try again later.")

def _get_or_404(db: DBSession, model: Any, model_id: uuid.UUID, tree_id: Optional[uuid.UUID] = None) -> Any:
    with tracer.start_as_current_span(f"db.get.{model.__name__}") as span:
        span.set_attribute("db.system", "postgresql") # Or your DB type
        span.set_attribute(f"{model.__name__}.id", str(model_id))
        if tree_id: span.set_attribute("tree.id", str(tree_id))
        
        start_time = time.monotonic()
        obj = None
        try:
            query = db.query(model)
            # Ensure tree_id check happens before ID check if model is tree-specific
            if tree_id and hasattr(model, 'tree_id'):
                 query = query.filter(model.tree_id == tree_id)
            
            # Now filter by primary ID
            obj = query.filter(model.id == model_id).one_or_none()
            
            duration = (time.monotonic() - start_time) * 1000
            db_operation_duration_histogram.record(duration, {"db.operation": f"get.{model.__name__}", "db.status": "success" if obj else "not_found"})

            if obj is None:
                logger.warning("Resource not found", model_name=model.__name__, model_id=model_id, tree_id=tree_id)
                span.set_attribute("db.found", False)
                # Construct a more specific message if tree_id was part of the query
                message = f"{model.__name__} with ID {model_id} not found"
                if tree_id and hasattr(model, 'tree_id'):
                    message += f" in tree {tree_id}"
                abort(404, description=message)
            
            span.set_attribute("db.found", True)
            return obj
        except SQLAlchemyError as e: # Catch SQLAlchemy errors specifically
            duration = (time.monotonic() - start_time) * 1000 # Recalculate duration up to error point
            db_operation_duration_histogram.record(duration, {"db.operation": f"get.{model.__name__}", "db.status": "error"})
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, f"DB Error: {e}"))
            _handle_sqlalchemy_error(e, f"fetching {model.__name__} ID {model_id}", db)
        except HTTPException: # Re-raise HTTPExceptions (like abort(404))
            raise
        except Exception as e: # Catch any other unexpected errors
            if 'start_time' in locals(): # Check if start_time was defined
                duration = (time.monotonic() - start_time) * 1000
                db_operation_duration_histogram.record(duration, {"db.operation": f"get.{model.__name__}", "db.status": "error"})
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Non-DB Error during fetch"))
            logger.error(f"Unexpected error fetching {model.__name__} ID {model_id}", exc_info=True)
            abort(500, "An unexpected error occurred while retrieving data.")


def _validate_password_complexity(password: str) -> None:
    if len(password) < 8: raise ValueError("Password must be at least 8 characters long.")
    if not re.search(r'[A-Z]', password): raise ValueError("Password must contain at least one uppercase letter.")
    if not re.search(r'[a-z]', password): raise ValueError("Password must contain at least one lowercase letter.")
    if not re.search(r'[0-9]', password): raise ValueError("Password must contain at least one digit.")
    if not re.search(r'[!@#$%^&*()_+=\-[\]{};\':"\\|,.<>/?`~]', password): raise ValueError("Password must contain at least one special character.")

def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')

def _verify_password(plain_password: str, hashed_password: str) -> bool:
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception as e: # Catch potential errors like malformed hash
        logger.error("Error during password verification (checkpw)", exc_info=True)
        return False

# --- Authentication/Authorization Decorators ---
def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            logger.warning("Authentication required, session not found.", session_contents=dict(session))
            abort(401, description="Authentication required. Please log in.")
        # Optionally, re-verify user from DB if session validity is short or needs active check
        # g.current_user = g.db.query(User).get(session['user_id'])
        # if not g.current_user or not g.current_user.is_active:
        #     session.clear()
        #     abort(401, description="User account is inactive or invalid.")
        return f(*args, **kwargs)
    return decorated_function

def require_admin(f):
    @wraps(f)
    @require_auth # Ensures user is logged in first
    def decorated_function(*args, **kwargs):
        # Ensure role is compared against the Enum member for type safety
        if session.get('role') != UserRole.ADMIN.value:
            logger.warning("Admin access required, but user is not admin.", user_id=session.get('user_id'), role=session.get('role'))
            abort(403, description="Administrator access is required for this action.")
        return f(*args, **kwargs)
    return decorated_function

def require_tree_access(level: str = 'view'): # level can be 'view', 'edit', 'admin'
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            user_id_str = session.get('user_id')
            if not user_id_str: # Should be caught by @require_auth, but defensive check
                 abort(401, description="Authentication required.")
            user_id = uuid.UUID(user_id_str)

            # Determine tree_id: from path parameter or active_tree_id in session
            tree_id_str = kwargs.get('tree_id_param') # If tree_id is part of the URL path
            if not tree_id_str:
                tree_id_str = session.get('active_tree_id')
                if not tree_id_str:
                    logger.warning("Tree access required, but no active tree set in session and not in path.", user_id=user_id)
                    abort(400, description={"message": "No active tree selected or tree ID provided.", "code": "NO_ACTIVE_TREE"})
            
            try:
                tree_id = uuid.UUID(tree_id_str)
            except ValueError:
                 logger.warning("Tree access required, but tree_id is invalid UUID.", user_id=user_id, tree_id_input=tree_id_str)
                 if tree_id_str == session.get('active_tree_id'): session.pop('active_tree_id', None) # Clear invalid session tree
                 abort(400, description={"message": "Invalid tree ID format.", "code": "INVALID_TREE_ID_FORMAT"})

            db = g.db # Assuming db session is on g
            tree = db.query(Tree).filter(Tree.id == tree_id).one_or_none()
            if not tree:
                logger.warning("Tree access check failed: Tree not found.", user_id=user_id, tree_id=tree_id)
                if tree_id_str == session.get('active_tree_id'): session.pop('active_tree_id', None)
                abort(404, description=f"Tree with ID {tree_id} not found.")

            has_access = False
            current_access_level = None # e.g., 'view', 'edit', 'admin'

            # Owner has admin access
            if tree.created_by == user_id:
                 has_access = True
                 current_access_level = 'admin' # Owner is admin
            # Public trees allow view access
            elif tree.is_public and level == 'view':
                 has_access = True
                 current_access_level = 'view'
            # Check TreeAccess table for explicit permissions
            else:
                tree_access_obj = db.query(TreeAccess).filter(
                    TreeAccess.tree_id == tree_id, TreeAccess.user_id == user_id
                ).one_or_none()

                if tree_access_obj:
                    current_access_level = tree_access_obj.access_level
                    # Define access hierarchy: admin > edit > view
                    access_hierarchy = {'view': 1, 'edit': 2, 'admin': 3}
                    required_level_val = access_hierarchy.get(level, 0)
                    granted_level_val = access_hierarchy.get(current_access_level, 0)
                    
                    if granted_level_val >= required_level_val:
                        has_access = True
            
            if not has_access:
                logger.warning("Tree access denied.", user_id=user_id, tree_id=tree_id, required_level=level, granted_level=current_access_level or "none")
                abort(403, description={"message": f"You do not have sufficient permissions ({level} required) for tree {tree_id}.", "code": "ACCESS_DENIED_TREE"})
            
            # Store tree and access level in g for use in the route
            g.active_tree = tree
            g.tree_access_level = current_access_level
            g.active_tree_id = tree_id # Ensure this is always the UUID object
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- User Services (Extended) ---
def get_activity_log_db(db: DBSession,
                        tree_id: Optional[uuid.UUID] = None,
                        user_id: Optional[uuid.UUID] = None,
                        page: int = DEFAULT_PAGE,
                        per_page: int = DEFAULT_PAGE_SIZE,
                        sort_by: str = "created_at",
                        sort_order: str = "desc"
                        ) -> Dict[str, Any]:
    with tracer.start_as_current_span("service.get_activity_log") as span:
        logger.info("Fetching activity logs", tree_id=tree_id, user_id=user_id, page=page, per_page=per_page)
        span.set_attributes({
            "tree.id": str(tree_id) if tree_id else "N/A",
            "user.id": str(user_id) if user_id else "N/A",
            "page": page, "per_page": per_page
        })
        try:
            query = db.query(ActivityLog)
            if tree_id: query = query.filter(ActivityLog.tree_id == tree_id)
            if user_id: query = query.filter(ActivityLog.user_id == user_id)
            
            return paginate_query(query, ActivityLog, page, per_page, PAGINATION_DEFAULTS["max_per_page"], sort_by, sort_order)
        except SQLAlchemyError as e:
            logger.error("Database error fetching activity logs.", exc_info=True)
            _handle_sqlalchemy_error(e, "fetching activity logs", db) # aborts
        except Exception as e: # Catch any other unexpected error
            logger.error("Unexpected error fetching activity logs.", exc_info=True)
            abort(500, description="An unexpected error occurred while fetching activity logs.")


def delete_tree_db(db: DBSession, tree_id: uuid.UUID) -> None:
    with tracer.start_as_current_span("service.delete_tree") as span:
        span.set_attribute("tree.id", str(tree_id))
        logger.info("Deleting tree", tree_id=tree_id)
        tree = _get_or_404(db, Tree, tree_id) # This already handles not found
        try:
            # Cascading deletes should handle related People, Relationships, etc. if set up in models
            db.delete(tree)
            db.commit()
            logger.info("Tree deleted successfully", tree_id=tree_id)
        except SQLAlchemyError as e:
            # db.rollback() is called by _handle_sqlalchemy_error
            logger.error("Database error during tree deletion.", tree_id=tree_id, exc_info=True)
            _handle_sqlalchemy_error(e, "deleting tree", db)
        except Exception as e:
            db.rollback() # Ensure rollback for non-SQLAlchemy errors before abort
            logger.error("Unexpected error during tree deletion.", tree_id=tree_id, exc_info=True)
            abort(500, description="An unexpected error occurred while deleting the tree.")

def update_tree_db(db: DBSession, tree_id: uuid.UUID, tree_data: Dict[str, Any]) -> Dict[str, Any]:
    with tracer.start_as_current_span("service.update_tree") as span:
        span.set_attribute("tree.id", str(tree_id))
        logger.info("Updating tree", tree_id=tree_id, data_keys=list(tree_data.keys()))
        tree = _get_or_404(db, Tree, tree_id)
        try:
            # Define allowed fields to update
            allowed_fields = ['name', 'description', 'is_public', 'default_privacy_level']
            for key, value in tree_data.items():
                if key in allowed_fields:
                    if key == 'default_privacy_level':
                        try:
                            setattr(tree, key, PrivacyLevelEnum(value))
                        except ValueError:
                            abort(400, description=f"Invalid value for default_privacy_level: {value}")
                    else:
                        setattr(tree, key, value)
            # tree.updated_at is handled by onupdate=datetime.utcnow in the model
            db.commit()
            db.refresh(tree) # Refresh to get updated values like updated_at
            logger.info("Tree updated successfully", tree_id=tree.id)
            return tree.to_dict()
        except SQLAlchemyError as e:
            logger.error("Database error during tree update.", tree_id=tree_id, exc_info=True)
            _handle_sqlalchemy_error(e, "updating tree", db)
        except HTTPException: # Re-raise HTTP exceptions (like abort from value validation)
            raise
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
            # Consider implications: what happens to trees created by this user?
            # Current ForeignKey("users.id") on Tree.created_by is nullable=False.
            # This means user deletion will fail if they own trees, unless ON DELETE SET NULL/CASCADE is used,
            # or trees are reassigned/deleted first.
            # For now, assuming DB constraints will prevent deletion if user owns critical data.
            db.delete(user)
            db.commit()
            logger.info("User deleted successfully", user_id=user_id)
        except IntegrityError as ie: # Catch foreign key violations specifically
            db.rollback()
            if "violates foreign key constraint" in str(ie.orig).lower():
                logger.warning(f"Cannot delete user {user_id} due to existing references (e.g., trees, data).", exc_info=False)
                abort(409, description="Cannot delete user: user owns data (e.g., trees). Please reassign or delete their data first.")
            _handle_sqlalchemy_error(ie, "deleting user due to integrity constraint", db)
        except SQLAlchemyError as e:
            logger.error("Database error during user deletion.", user_id=user_id, exc_info=True)
            _handle_sqlalchemy_error(e, "deleting user", db)
        except Exception as e:
            db.rollback()
            logger.error("Unexpected error during user deletion.", user_id=user_id, exc_info=True)
            abort(500, description="An unexpected error occurred while deleting the user.")


def update_user_role_db(db: DBSession, user_id: uuid.UUID, new_role_str: str) -> Dict[str, Any]:
    with tracer.start_as_current_span("service.update_user_role") as span:
        span.set_attribute("app.user.id", str(user_id))
        span.set_attribute("app.user.new_role", new_role_str)
        logger.info("Updating user role", user_id=user_id, new_role=new_role_str)
        
        try:
            new_role_enum = UserRole(new_role_str) # Validate role string
        except ValueError:
            logger.warning("Invalid role specified for update.", user_id=user_id, new_role=new_role_str)
            abort(400, description=f"Invalid role specified: {new_role_str}. Valid roles are: {[r.value for r in UserRole]}.")

        user = _get_or_404(db, User, user_id)
        try:
            if user.role == new_role_enum:
                logger.info("User role is already set to the target role. No update performed.", user_id=user.id, role=new_role_enum.value)
                return user.to_dict() # Return current state

            user.role = new_role_enum
            # user.updated_at is handled by onupdate in the model
            db.commit()
            db.refresh(user)
            logger.info("User role updated successfully", user_id=user.id, new_role=user.role.value)
            role_change_counter.add(1, {"target_user_id": str(user_id), "new_role": new_role_str})
            return user.to_dict()
        except SQLAlchemyError as e:
            logger.error("Database error during user role update.", user_id=user_id, exc_info=True)
            _handle_sqlalchemy_error(e, "updating user role", db)
        except Exception as e:
            db.rollback()
            logger.error("Unexpected error during user role update.", user_id=user_id, exc_info=True)
            abort(500, description="An unexpected error occurred while updating the user role.")


def register_user_db(db: DBSession, user_data: Dict[str, Any]) -> Dict[str, Any]:
    with tracer.start_as_current_span("service.register_user") as span:
        username = user_data.get('username')
        email = user_data.get('email')
        password = user_data.get('password')
        span.set_attribute("app.user.username", username)
        logger.info("Registering new user", username=username, email=email)

        if not username or not email or not password:
            abort(400, description="Username, email, and password are required.")

        try:
            _validate_password_complexity(password)
        except ValueError as e:
            logger.warning("User registration failed: Password complexity requirements not met.", username=username, reason=str(e))
            abort(400, description=str(e))
        
        hashed_password = _hash_password(password)
        
        try:
            role_value = user_data.get('role', UserRole.USER.value)
            try:
                user_role_enum = UserRole(role_value)
            except ValueError:
                logger.warning(f"User registration failed: Invalid role value '{role_value}'.", username=username)
                abort(400, description=f"Invalid role specified: {role_value}. Valid roles are: {[r.value for r in UserRole]}.")

            new_user = User(
                username=username,
                email=email.lower(), # Store emails in lowercase for consistency
                password_hash=hashed_password,
                full_name=user_data.get('full_name'),
                role=user_role_enum,
                is_active=True, # Or False, requiring email verification first
                email_verified=False,
                # created_at and updated_at have defaults
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            user_registration_counter.add(1, {"status": "success"})
            logger.info("User registered successfully", user_id=new_user.id, username=new_user.username)
            return new_user.to_dict()
        except IntegrityError as e: # Handles duplicate username/email
            # db.rollback() is called by _handle_sqlalchemy_error
            logger.warning("User registration failed: Integrity error (e.g., duplicate username/email).", username=username, exc_info=False) # Don't log full exc_info for common errors
            _handle_sqlalchemy_error(e, "registering user", db)
        except SQLAlchemyError as e: # Catch other DB errors
             logger.error("Database error during user registration.", username=username, exc_info=True)
             _handle_sqlalchemy_error(e, "registering user", db)
        except HTTPException: # Re-raise aborts
            raise
        except Exception as e:
            db.rollback()
            user_registration_counter.add(1, {"status": "failure", "reason": "unknown_error"})
            logger.error("Unexpected error during user registration.", username=username, exc_info=True)
            abort(500, description="An unexpected error occurred during registration.")


def authenticate_user_db(db: DBSession, username_or_email: str, password: str) -> Optional[Dict[str, Any]]:
    with tracer.start_as_current_span("service.authenticate_user") as span:
        span.set_attribute("app.user.identifier", username_or_email)
        logger.info("Authenticating user", identifier=username_or_email)
        
        if not username_or_email or not password:
            logger.warning("Authentication attempt with empty username/email or password.")
            return None # Or abort(400) depending on desired behavior

        try:
            normalized_identifier = username_or_email.lower()
            user = db.query(User).filter(
                or_(User.username == username_or_email, User.email == normalized_identifier) # Case-sensitive username, case-insensitive email
            ).one_or_none()

            if not user:
                logger.warning("Authentication failed: User not found", identifier=username_or_email)
                span.set_attribute("app.user.found", False)
                auth_failure_counter.add(1, {"reason": "user_not_found", "identifier_prefix": username_or_email[:5]})
                return None
            
            span.set_attribute("app.user.found", True)
            span.set_attribute("app.user.id", str(user.id))

            if not user.is_active:
                logger.warning("Authentication failed: User account is inactive", user_id=user.id, username=user.username)
                span.set_attribute("app.auth.success", False)
                span.set_attribute("app.auth.reason", "inactive_account")
                auth_failure_counter.add(1, {"reason": "inactive_account", "user_id": str(user.id)})
                # Return a specific error or a generic one
                abort(401, description="Account is inactive.")


            if not _verify_password(password, user.password_hash):
                logger.warning("Authentication failed: Incorrect password", user_id=user.id, username=user.username)
                span.set_attribute("app.auth.success", False)
                span.set_attribute("app.auth.reason", "incorrect_password")
                auth_failure_counter.add(1, {"reason": "incorrect_password", "user_id": str(user.id)})
                return None
            
            # Update last_login timestamp
            user.last_login = datetime.utcnow()
            # user.updated_at will also be updated by onupdate
            db.commit()
            db.refresh(user) # To get the updated last_login and updated_at in the returned dict

            span.set_attribute("app.auth.success", True)
            logger.info("Authentication successful", user_id=user.id, username=user.username)
            return user.to_dict(include_sensitive=False) # Ensure sensitive data is not returned
        except SQLAlchemyError as e:
            # db.rollback() is handled by _handle_sqlalchemy_error if it aborts, or by teardown if not
            logger.error("Database error during user authentication", identifier=username_or_email, exc_info=True)
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, "DB Error during authentication")
            # Let _handle_sqlalchemy_error decide to abort or if it's caught later
            _handle_sqlalchemy_error(e, "authenticating user", db)
            return None # Should not be reached if abort happens
        except HTTPException:
            raise
        except Exception as e:
            # db.rollback() if necessary
            logger.error("Unexpected error during user authentication", identifier=username_or_email, exc_info=True)
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, "Unknown Error during authentication")
            abort(500, "An unexpected error occurred during authentication.")
            return None # Should not be reached


def get_all_users_db(db: DBSession,
                     page: int = DEFAULT_PAGE,
                     per_page: int = DEFAULT_PAGE_SIZE,
                     sort_by: Optional[str] = "username", # Default sort for users
                     sort_order: Optional[str] = "asc"
                     ) -> Dict[str, Any]:
    with tracer.start_as_current_span("service.get_all_users") as span:
        logger.info("Fetching all users from DB", page=page, per_page=per_page, sort_by=sort_by, sort_order=sort_order)
        span.set_attributes({"page": page, "per_page": per_page, "sort_by": sort_by, "sort_order": sort_order})
        try:
            query = db.query(User)
            # Add filtering capabilities if needed, e.g., by role, is_active
            # query = query.filter(User.is_active == True)
            return paginate_query(query, User, page, per_page, PAGINATION_DEFAULTS["max_per_page"], sort_by, sort_order)
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

        if not fernet_suite:
             logger.error("Password reset failed: Encryption suite (Fernet) not initialized.")
             # This is a server configuration issue, so 503 is appropriate.
             abort(503, description="Password reset service is temporarily unavailable due to a configuration issue.")

        normalized_identifier = email_or_username.lower()
        user = db.query(User).filter(
            or_(User.username == email_or_username, User.email == normalized_identifier)
        ).one_or_none()

        if not user:
            # Do not reveal if user exists or not to prevent user enumeration.
            logger.warning("Password reset request for non-existent or non-matching user.", identifier_prefix=email_or_username[:5])
            span.set_attribute("app.user.found", False)
            return True # Pretend success

        span.set_attribute("app.user.found", True)
        span.set_attribute("app.user.id", str(user.id))
        
        if not user.is_active:
            logger.warning("Password reset requested for inactive user.", user_id=user.id)
            # Decide whether to send email or not. For security, often better not to.
            return True # Pretend success

        try:
            # Generate a secure, URL-safe token. secrets.token_urlsafe is good.
            raw_token = secrets.token_urlsafe(32)
            # Store a hash of the token in the DB, not the raw token.
            # This prevents an attacker with DB access from using the raw token.
            # bcrypt is for passwords; for tokens, SHA256 is common.
            # However, the original code used Fernet on user_id. Let's stick to a simpler random token.
            
            user.password_reset_token = raw_token # Store the raw token for simplicity in this version
                                                  # For higher security, store hash_of_raw_token
            user.password_reset_expires = datetime.utcnow() + timedelta(hours=1) # 1-hour expiry
            # user.updated_at handled by onupdate
            db.commit()

            # --- Email Sending Logic (Placeholder) ---
            # In a real app, use a proper email library (e.g., Flask-Mail) and background tasks.
            app_url = os.getenv("FRONTEND_APP_URL", "http://localhost:5173") # Ensure this is correct for your frontend
            reset_link = f"{app_url}/reset-password/{raw_token}" # Send raw_token in link

            # Simulate email sending
            email_configured = all([
                os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASSWORD"),
                os.getenv("EMAIL_SERVER"), os.getenv("EMAIL_PORT")
            ])

            if email_configured:
                 try:
                     # Placeholder for actual email sending:
                     # send_email(to=user.email, subject="Password Reset Request", body=f"Reset link: {reset_link}")
                     logger.info(f"Simulating password reset email to {user.email} with link: {reset_link}", user_id=user.id)
                     span.set_attribute("app.email.sent_simulated", True)
                 except Exception as email_err:
                     logger.error("Failed to send password reset email (simulated).", user_id=user.id, email=user.email, exc_info=True)
                     span.set_attribute("app.email.sent_simulated", False)
                     span.record_exception(email_err)
                     # Don't abort the whole process if email fails, user can try again.
            else:
                logger.warning("Email sending is not configured. Password reset link generated but not sent.", user_id=user.id, reset_link_for_log=reset_link)
                span.set_attribute("app.email.sent_simulated", False)
            
            logger.info("Password reset token generated and saved.", user_id=user.id, event_type="PASSWORD_RESET_REQUEST")
            return True
        except SQLAlchemyError as e:
            # db.rollback() handled by _handle_sqlalchemy_error
            logger.error("Database error during password reset request.", user_id=getattr(user, 'id', None), exc_info=True)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "DB Error in password reset request"))
            _handle_sqlalchemy_error(e, "requesting password reset", db)
        except Exception as e:
            db.rollback()
            logger.error("Unexpected error during password reset request.", user_id=getattr(user, 'id', None), exc_info=True)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Unknown Error in password reset request"))
            abort(500, description="An unexpected error occurred during the password reset process.")
        return False # Should be unreachable if aborts occur


def reset_password_db(db: DBSession, token: str, new_password: str) -> bool:
    with tracer.start_as_current_span("service.reset_password") as span:
        span.set_attribute("app.password_reset.token_provided", bool(token))
        
        if not token or not new_password:
            abort(400, description="Token and new password are required.")

        # No Fernet needed here if we store raw (or hashed) random token
        try:
            # Find user by the raw token and check expiry
            user = db.query(User).filter(
                User.password_reset_token == token,
                User.password_reset_expires > datetime.utcnow()
            ).one_or_none()

            if not user:
                logger.warning("Password reset failed: Invalid or expired token provided.", token_prefix=token[:8])
                span.set_attribute("app.password_reset.token_valid", False)
                # Generic message to prevent token probing
                abort(400, description="Invalid or expired password reset token. Please request a new one.")
            
            span.set_attribute("app.password_reset.token_valid", True)
            span.set_attribute("app.user.id", str(user.id))

            try:
                _validate_password_complexity(new_password)
            except ValueError as e:
                logger.warning("Password reset failed: New password complexity requirements not met.", user_id=user.id, reason=str(e))
                abort(400, description=str(e)) # Send complexity error to user

            user.password_hash = _hash_password(new_password)
            user.password_reset_token = None # Invalidate the token
            user.password_reset_expires = None
            user.email_verified = True # Optionally verify email on successful password reset
            # user.updated_at handled by onupdate
            db.commit()
            logger.info("Password reset successful.", user_id=user.id, username=user.username, event_type="PASSWORD_RESET_SUCCESS")
            return True
        except SQLAlchemyError as e:
            logger.error("Database error during password reset.", exc_info=True)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "DB Error in password reset"))
            _handle_sqlalchemy_error(e, "resetting password", db)
        except HTTPException: # Re-raise abort() calls
            raise
        except Exception as e:
            db.rollback()
            logger.error("Unexpected error during password reset.", exc_info=True)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Unknown Error in password reset"))
            abort(500, description="An unexpected error occurred while resetting the password.")
        return False # Should be unreachable

# --- Tree Services ---
def create_tree_db(db: DBSession, user_id: uuid.UUID, tree_data: Dict[str, Any]) -> Dict[str, Any]:
    with tracer.start_as_current_span("service.create_tree") as span:
        span.set_attribute("app.user.id", str(user_id))
        tree_name = tree_data.get('name')
        span.set_attribute("tree.name", tree_name or "[Unnamed Tree]")
        logger.info("Attempting to create new tree", user_id=user_id, tree_name=tree_name)

        if not tree_name: # Name is mandatory
            logger.warning("Tree creation failed: Missing tree name.")
            abort(400, description="Tree name is required.")
        
        try:
            default_privacy_str = tree_data.get('default_privacy_level', PrivacyLevelEnum.private.value)
            try:
                default_privacy_enum = PrivacyLevelEnum(default_privacy_str)
            except ValueError:
                abort(400, description=f"Invalid default_privacy_level: {default_privacy_str}. Valid values: {[p.value for p in PrivacyLevelEnum]}")

            new_tree = Tree(
                name=tree_name,
                description=tree_data.get('description'),
                created_by=user_id,
                is_public=tree_data.get('is_public', False), # Ensure boolean
                default_privacy_level=default_privacy_enum,
                # created_at, updated_at have defaults
            )
            db.add(new_tree)
            # We need to flush to get new_tree.id before creating TreeAccess if TreeAccess needs it immediately
            # However, if TreeAccess is created after commit, it's fine.
            # For safety, let's commit tree first, then access.
            db.commit() 
            db.refresh(new_tree) # Get the ID and other defaults

            # Grant owner admin access
            tree_access = TreeAccess(
                 tree_id=new_tree.id,
                 user_id=user_id,
                 access_level='admin', # Owner gets admin access
                 granted_by=user_id, # Granted by self (owner)
                 # granted_at has default
            )
            db.add(tree_access)
            db.commit() # Commit the access grant

            logger.info("Tree created successfully with owner access.", tree_id=new_tree.id, tree_name=new_tree.name, created_by=user_id, event_type="TREE_CREATED")
            span.set_attribute("tree.id", str(new_tree.id))
            return new_tree.to_dict()
        except SQLAlchemyError as e:
            logger.error("Database error during tree creation.", user_id=user_id, tree_name=tree_name, exc_info=True)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "DB Error in create_tree"))
            _handle_sqlalchemy_error(e, "creating tree", db)
        except HTTPException:
            raise
        except Exception as e:
            db.rollback() # Ensure rollback for non-SQLAlchemy errors
            logger.error("Unexpected error during tree creation.", user_id=user_id, tree_name=tree_name, exc_info=True)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Unknown Error in create_tree"))
            abort(500, description="An unexpected error occurred during tree creation.")

def get_user_trees_db(db: DBSession,
                        user_id: uuid.UUID,
                        page: int = DEFAULT_PAGE,
                        per_page: int = DEFAULT_PAGE_SIZE,
                        sort_by: Optional[str] = "name",
                        sort_order: Optional[str] = "asc"
                        ) -> Dict[str, Any]:
    with tracer.start_as_current_span("service.get_user_trees") as span:
        span.set_attributes({
            "app.user.id": str(user_id), "page": page, "per_page": per_page,
            "sort_by": sort_by, "sort_order": sort_order
        })
        logger.info("Fetching trees for user", user_id=user_id, page=page, per_page=per_page)
        try:
            # Query for trees directly owned by the user OR shared with the user via TreeAccess
            # This requires a careful query to handle distinct trees correctly with pagination.

            # Step 1: Get a subquery of distinct tree IDs the user has access to.
            # Trees created by the user
            owned_trees_sq = db.query(Tree.id.label("tree_id")).filter(Tree.created_by == user_id)
            # Trees shared with the user
            shared_trees_sq = db.query(TreeAccess.tree_id.label("tree_id")).filter(TreeAccess.user_id == user_id)
            
            # Union the two sets of tree IDs
            accessible_tree_ids_sq = owned_trees_sq.union(shared_trees_sq).distinct().subquery('accessible_tree_ids')

            # Step 2: Build the main query based on these accessible tree IDs
            query = db.query(Tree).join(accessible_tree_ids_sq, Tree.id == accessible_tree_ids_sq.c.tree_id)
            
            # The paginate_query helper will apply sorting and pagination
            paginated_result = paginate_query(query, Tree, page, per_page, PAGINATION_DEFAULTS["max_per_page"], sort_by, sort_order)
            
            logger.info(f"Found {paginated_result['total_items']} trees for user {user_id}")
            return paginated_result

        except SQLAlchemyError as e:
            logger.error("Database error fetching user trees.", user_id=user_id, exc_info=True)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "DB Error fetching user trees"))
            _handle_sqlalchemy_error(e, "fetching user trees", db)
        except Exception as e:
            logger.error("Unexpected error fetching user trees.", user_id=user_id, exc_info=True)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Unknown Error fetching user trees"))
            abort(500, description="An unexpected error occurred while fetching trees.")


# --- Person Services ---
def get_all_people_db(db: DBSession,
                        tree_id: uuid.UUID,
                        page: int = DEFAULT_PAGE,
                        per_page: int = DEFAULT_PAGE_SIZE,
                        sort_by: Optional[str] = "last_name", # Sensible default sort for people
                        sort_order: Optional[str] = "asc",
                        filters: Optional[Dict[str, Any]] = None # For future filter extension
                        ) -> Dict[str, Any]:
    with tracer.start_as_current_span("service.get_all_people") as span:
        span.set_attributes({
            "tree.id": str(tree_id), "page": page, "per_page": per_page,
            "sort_by": sort_by, "sort_order": sort_order
        })
        logger.info("Fetching all people for tree", tree_id=tree_id, page=page, per_page=per_page)
        try:
            query = db.query(Person).filter(Person.tree_id == tree_id)

            # Example basic filtering (can be expanded)
            if filters:
                if 'is_living' in filters and isinstance(filters['is_living'], bool):
                    query = query.filter(Person.is_living == filters['is_living'])
                if 'gender' in filters:
                    query = query.filter(func.lower(Person.gender) == str(filters['gender']).lower())
                # Add more filters as needed: name searches, date ranges etc.

            return paginate_query(query, Person, page, per_page, PAGINATION_DEFAULTS["max_per_page"], sort_by, sort_order)
        except SQLAlchemyError as e:
            logger.error("Database error fetching all people for tree.", tree_id=tree_id, exc_info=True)
            _handle_sqlalchemy_error(e, f"fetching all people for tree {tree_id}", db)
        except Exception as e:
            logger.error("Unexpected error fetching all people for tree.", tree_id=tree_id, exc_info=True)
            abort(500, "An unexpected error occurred while fetching people.")

def get_person_db(db: DBSession, person_id: uuid.UUID, tree_id: uuid.UUID) -> Dict[str, Any]:
    # This function already uses _get_or_404 which is good for single resource.
    with tracer.start_as_current_span("service.get_person") as span:
        span.set_attribute("person.id", str(person_id))
        span.set_attribute("tree.id", str(tree_id))
        logger.info("Fetching person details", person_id=person_id, tree_id=tree_id)
        # _get_or_404 will handle SQLAlchemyError and aborts if not found or error.
        person = _get_or_404(db, Person, person_id, tree_id=tree_id) # Pass tree_id for context
        return person.to_dict()


def create_person_db(db: DBSession, user_id: uuid.UUID, tree_id: uuid.UUID, person_data: Dict[str, Any]) -> Dict[str, Any]:
    with tracer.start_as_current_span("service.create_person") as span:
        # (Initial setup and logging from original code)
        span.set_attribute("app.user.id", str(user_id))
        span.set_attribute("tree.id", str(tree_id))
        person_name = f"{person_data.get('first_name', '')} {person_data.get('last_name', '')}".strip()
        span.set_attribute("person.name", person_name)
        logger.info("Attempting to create new person", user_id=user_id, tree_id=tree_id, person_name=person_name)

        if not person_data or not person_data.get('first_name'): # Basic validation
            logger.warning("Person creation failed: Missing first name.")
            abort(400, description={"message": "Validation failed", "details": {"first_name": "First name is required."}})

        birth_date_str = person_data.get('birth_date')
        death_date_str = person_data.get('death_date')
        birth_date, death_date = None, None
        errors = {}

        if birth_date_str:
            try: birth_date = date.fromisoformat(birth_date_str)
            except ValueError: errors['birth_date'] = "Invalid date format (YYYY-MM-DD)."
        if death_date_str:
            try: death_date = date.fromisoformat(death_date_str)
            except ValueError: errors['death_date'] = "Invalid date format (YYYY-MM-DD)."
        
        if birth_date and death_date and death_date < birth_date:
            errors['date_comparison'] = "Death date cannot be before birth date."

        gender = person_data.get('gender')
        if gender and str(gender).lower() not in ['male', 'female', 'other', 'unknown', '']: # Allow empty string for clearing
             errors['gender'] = "Invalid gender value. Allowed: male, female, other, unknown."
        
        privacy_level_str = person_data.get('privacy_level', PrivacyLevelEnum.inherit.value)
        try:
            privacy_level_enum = PrivacyLevelEnum(privacy_level_str)
        except ValueError:
            errors['privacy_level'] = f"Invalid privacy level: {privacy_level_str}. Valid: {[p.value for p in PrivacyLevelEnum]}"

        if errors:
            logger.warning("Person creation failed due to validation errors.", errors=errors)
            abort(400, description={"message": "Validation failed", "details": errors})

        try:
            new_person = Person(
                tree_id=tree_id,
                first_name=person_data['first_name'], # Already checked for presence
                middle_names=person_data.get('middle_names'),
                last_name=person_data.get('last_name'),
                maiden_name=person_data.get('maiden_name'),
                nickname=person_data.get('nickname'),
                gender=gender if gender else None, # Store None if empty string was provided
                birth_date=birth_date,
                birth_date_approx=person_data.get('birth_date_approx', False),
                birth_place=person_data.get('birth_place'),
                death_date=death_date,
                death_date_approx=person_data.get('death_date_approx', False),
                death_place=person_data.get('death_place'),
                burial_place=person_data.get('burial_place'),
                privacy_level=privacy_level_enum,
                is_living=person_data.get('is_living'), # Will be auto-set if None
                notes=person_data.get('notes'),
                custom_attributes=person_data.get('custom_attributes', {}),
                created_by=user_id,
                # created_at, updated_at have defaults
            )
            # If is_living is not explicitly provided, determine it based on death_date.
            if new_person.is_living is None:
                new_person.is_living = new_person.death_date is None

            db.add(new_person)
            db.commit()
            db.refresh(new_person)
            logger.info("Person created successfully", person_id=new_person.id, tree_id=tree_id, created_by=user_id, event_type="PERSON_CREATED")
            span.set_attribute("person.id", str(new_person.id))
            return new_person.to_dict()
        except SQLAlchemyError as e:
            logger.error("Database error during person creation.", user_id=user_id, tree_id=tree_id, person_name=person_name, exc_info=True)
            _handle_sqlalchemy_error(e, "creating person", db)
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error("Unexpected error during person creation.", user_id=user_id, tree_id=tree_id, person_name=person_name, exc_info=True)
            abort(500, description="An unexpected error occurred during person creation.")


def update_person_db(db: DBSession, person_id: uuid.UUID, tree_id: uuid.UUID, person_data: Dict[str, Any]) -> Dict[str, Any]:
    with tracer.start_as_current_span("service.update_person") as span:
        # (Initial setup and logging from original code)
        span.set_attribute("person.id", str(person_id))
        span.set_attribute("tree.id", str(tree_id))
        logger.info("Attempting to update person", person_id=person_id, tree_id=tree_id, data_keys=list(person_data.keys()))

        person = _get_or_404(db, Person, person_id, tree_id=tree_id)
        
        validation_errors = {}
        # Define fields that can be updated and their types/validation
        allowed_fields = {
            'first_name': str, 'middle_names': str, 'last_name': str, 'maiden_name': str, 'nickname': str,
            'gender': str, 'birth_date': date, 'birth_date_approx': bool, 'birth_place': str,
            'death_date': date, 'death_date_approx': bool, 'death_place': str, 'burial_place': str,
            'privacy_level': PrivacyLevelEnum, 'is_living': bool, 'notes': str, 'custom_attributes': dict
        }

        for field, value in person_data.items():
            if field not in allowed_fields:
                logger.warning(f"Attempt to update unallowed field '{field}' for person {person_id}.")
                continue # Skip unallowed fields

            try:
                if field in ['birth_date', 'death_date']:
                    setattr(person, field, date.fromisoformat(value) if value else None)
                elif field == 'gender':
                    if value is not None and str(value).lower() not in ['male', 'female', 'other', 'unknown', '']:
                         validation_errors[field] = "Invalid gender value. Allowed: male, female, other, unknown, or empty to clear."
                    else: setattr(person, field, value if value else None) # Store None if empty
                elif field == 'privacy_level':
                    setattr(person, field, PrivacyLevelEnum(value) if value else person.default_privacy_level) # Fallback or error?
                elif field == 'custom_attributes':
                    if not isinstance(value, dict): validation_errors[field] = "Custom attributes must be a dictionary."
                    else: setattr(person, field, value)
                elif field in ['is_living', 'birth_date_approx', 'death_date_approx']:
                    if not isinstance(value, bool): validation_errors[field] = f"{field} must be a boolean (true/false)."
                    else: setattr(person, field, value)
                else: # For other string fields
                    setattr(person, field, value)
            except ValueError as e: # Catches date format errors, enum errors
                validation_errors[field] = f"Invalid value or format for {field}: {e}"
            except Exception as e: # Catch-all for unexpected issues during field processing
                logger.error(f"Unexpected error processing field {field} for person update.", exc_info=True)
                validation_errors[field] = f"Unexpected error processing {field}."

        if validation_errors:
             logger.warning("Person update failed: Validation errors.", person_id=person_id, errors=validation_errors)
             abort(400, description={"message": "Validation failed", "details": validation_errors})

        # Date consistency check
        if person.birth_date and person.death_date and person.death_date < person.birth_date:
            logger.warning("Person update failed: Death date cannot be before birth date.", person_id=person_id)
            abort(400, description={"message": "Validation failed", "details": {"date_comparison": "Death date cannot be before birth date."}})
        
        # Auto-update is_living if not explicitly set and death_date changed
        if 'is_living' not in person_data and ('death_date' in person_data or 'birth_date' in person_data):
             person.is_living = person.death_date is None
        
        # person.updated_at is handled by onupdate
        try:
            db.commit()
            db.refresh(person)
            logger.info("Person updated successfully", person_id=person.id, tree_id=tree_id, event_type="PERSON_UPDATED")
            return person.to_dict()
        except SQLAlchemyError as e:
            logger.error("Database error during person update.", person_id=person_id, tree_id=tree_id, exc_info=True)
            _handle_sqlalchemy_error(e, f"updating person ID {person_id}", db)
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error("Unexpected error during person update.", person_id=person_id, tree_id=tree_id, exc_info=True)
            abort(500, description="An unexpected error occurred during person update.")


def delete_person_db(db: DBSession, person_id: uuid.UUID, tree_id: uuid.UUID) -> bool:
    with tracer.start_as_current_span("service.delete_person") as span:
        span.set_attribute("person.id", str(person_id))
        span.set_attribute("tree.id", str(tree_id))
        logger.info("Attempting to delete person", person_id=person_id, tree_id=tree_id)
        
        person = _get_or_404(db, Person, person_id, tree_id=tree_id)
        person_name_for_log = f"{person.first_name or ''} {person.last_name or ''}".strip()

        try:
            # Deleting a person might have cascading effects or be restricted by foreign keys
            # (e.g., if they are part of relationships). SQLAlchemy's ondelete="CASCADE" on
            # Relationship.person1_id/person2_id would handle this.
            # If not, IntegrityError will be raised.
            db.delete(person)
            db.commit()
            logger.info("Person deleted successfully", person_id=person_id, person_name=person_name_for_log, tree_id=tree_id, event_type="PERSON_DELETED")
            return True
        except IntegrityError as ie:
            db.rollback()
            if "foreign key constraint" in str(ie.orig).lower():
                logger.warning(f"Cannot delete person {person_id} due to existing relationships or other linked data.", exc_info=False)
                abort(409, description="Cannot delete person: they are part of existing relationships or other linked data. Please remove these links first.")
            _handle_sqlalchemy_error(ie, f"deleting person ID {person_id} due to integrity constraint", db)
        except SQLAlchemyError as e:
            logger.error("Database error during person deletion.", person_id=person_id, tree_id=tree_id, exc_info=True)
            _handle_sqlalchemy_error(e, f"deleting person ID {person_id}", db)
        except Exception as e:
            db.rollback()
            logger.error("Unexpected error during person deletion.", person_id=person_id, tree_id=tree_id, exc_info=True)
            abort(500, description="An unexpected error occurred during person deletion.")
        return False # Should be unreachable

# --- Relationship Services ---
def get_all_relationships_db(db: DBSession,
                               tree_id: uuid.UUID,
                               page: int = DEFAULT_PAGE,
                               per_page: int = DEFAULT_PAGE_SIZE,
                               sort_by: Optional[str] = "created_at",
                               sort_order: Optional[str] = "desc",
                               filters: Optional[Dict[str, Any]] = None
                               ) -> Dict[str, Any]:
    with tracer.start_as_current_span("service.get_all_relationships") as span:
        span.set_attributes({
            "tree.id": str(tree_id), "page": page, "per_page": per_page,
            "sort_by": sort_by, "sort_order": sort_order
        })
        logger.info("Fetching all relationships for tree", tree_id=tree_id, page=page, per_page=per_page)
        try:
            query = db.query(Relationship).filter(Relationship.tree_id == tree_id)
            
            if filters:
                if 'person_id' in filters: # Filter relationships involving a specific person
                    person_uuid = uuid.UUID(str(filters['person_id']))
                    query = query.filter(or_(Relationship.person1_id == person_uuid, Relationship.person2_id == person_uuid))
                if 'relationship_type' in filters:
                    try:
                        rel_type_enum = RelationshipTypeEnum(str(filters['relationship_type']))
                        query = query.filter(Relationship.relationship_type == rel_type_enum)
                    except ValueError:
                        logger.warning(f"Invalid relationship_type filter: {filters['relationship_type']}")
                        # Optionally abort or ignore invalid filter

            return paginate_query(query, Relationship, page, per_page, PAGINATION_DEFAULTS["max_per_page"], sort_by, sort_order)
        except SQLAlchemyError as e:
            logger.error("Database error fetching all relationships for tree.", tree_id=tree_id, exc_info=True)
            _handle_sqlalchemy_error(e, f"fetching all relationships for tree {tree_id}", db)
        except ValueError: # From uuid.UUID conversion if invalid person_id filter
            abort(400, description="Invalid person_id format for filtering relationships.")
        except Exception as e:
            logger.error("Unexpected error fetching all relationships for tree.", tree_id=tree_id, exc_info=True)
            abort(500, "An unexpected error occurred while fetching relationships.")


def create_relationship_db(db: DBSession, user_id: uuid.UUID, tree_id: uuid.UUID, relationship_data: Dict[str, Any]) -> Dict[str, Any]:
    with tracer.start_as_current_span("service.create_relationship") as span:
        # (Initial setup and logging from original code)
        span.set_attribute("app.user.id", str(user_id))
        span.set_attribute("tree.id", str(tree_id))
        p1_id_str = relationship_data.get('person1_id') # Changed from 'person1' for clarity
        p2_id_str = relationship_data.get('person2_id') # Changed from 'person2'
        rel_type_str = relationship_data.get('relationship_type') # Changed from 'relationshipType'
        span.set_attribute("relationship.type", rel_type_str)
        span.set_attribute("relationship.person1_id", p1_id_str)
        span.set_attribute("relationship.person2_id", p2_id_str)
        logger.info("Attempting to create new relationship", user_id=user_id, tree_id=tree_id, p1=p1_id_str, p2=p2_id_str, type=rel_type_str)

        errors = {}
        if not p1_id_str: errors['person1_id'] = "person1_id is required."
        if not p2_id_str: errors['person2_id'] = "person2_id is required."
        if not rel_type_str: errors['relationship_type'] = "relationship_type is required."

        if errors:
            logger.warning("Relationship creation failed: Missing required fields.", errors=errors)
            abort(400, description={"message": "Validation failed", "details": errors})

        if p1_id_str == p2_id_str:
            logger.warning("Relationship creation failed: Cannot create relationship with the same person.")
            abort(400, description="Cannot create a relationship between a person and themselves.")

        try:
            person1_id_uuid = uuid.UUID(p1_id_str)
            person2_id_uuid = uuid.UUID(p2_id_str)
        except ValueError:
            logger.warning("Relationship creation failed: Invalid UUID format for person IDs.")
            abort(400, description="Invalid UUID format for one or both person IDs.")
        
        try:
            relationship_type_enum = RelationshipTypeEnum(rel_type_str)
        except ValueError:
            logger.warning("Relationship creation failed: Invalid relationship type.", rel_type=rel_type_str)
            abort(400, description=f"Invalid relationship type: {rel_type_str}. Valid types: {[rt.value for rt in RelationshipTypeEnum]}")

        # Verify both persons exist in the given tree
        _get_or_404(db, Person, person1_id_uuid, tree_id=tree_id) # Ensures person1 is in this tree
        _get_or_404(db, Person, person2_id_uuid, tree_id=tree_id) # Ensures person2 is in this tree

        start_date_str = relationship_data.get('start_date')
        end_date_str = relationship_data.get('end_date')
        start_date, end_date = None, None
        date_errors = {}

        if start_date_str:
            try: start_date = date.fromisoformat(start_date_str)
            except ValueError: date_errors['start_date'] = "Invalid date format (YYYY-MM-DD)."
        if end_date_str:
            try: end_date = date.fromisoformat(end_date_str)
            except ValueError: date_errors['end_date'] = "Invalid date format (YYYY-MM-DD)."
        
        if start_date and end_date and end_date < start_date:
             date_errors['date_comparison'] = "End date cannot be before start date."
        
        if date_errors:
            abort(400, description={"message": "Date validation failed", "details": date_errors})
        
        try:
            new_relationship = Relationship(
                tree_id=tree_id,
                person1_id=person1_id_uuid,
                person2_id=person2_id_uuid,
                relationship_type=relationship_type_enum,
                start_date=start_date,
                end_date=end_date,
                certainty_level=relationship_data.get('certainty_level'), # Add validation if needed (e.g., range 1-5)
                custom_attributes=relationship_data.get('custom_attributes', {}),
                notes=relationship_data.get('notes'),
                created_by=user_id,
                # created_at, updated_at have defaults
            )
            db.add(new_relationship)
            db.commit()
            db.refresh(new_relationship)
            logger.info("Relationship created successfully", rel_id=new_relationship.id, tree_id=tree_id, created_by=user_id, event_type="RELATIONSHIP_CREATED")
            span.set_attribute("relationship.id", str(new_relationship.id))
            return new_relationship.to_dict()
        except IntegrityError as e: # Catch potential unique constraint violations if defined
            logger.warning("Relationship creation failed: Integrity constraint violation (e.g., duplicate relationship).", exc_info=False)
            _handle_sqlalchemy_error(e, "creating relationship due to integrity constraint", db)
        except SQLAlchemyError as e:
            logger.error("Database error during relationship creation.", user_id=user_id, tree_id=tree_id, exc_info=True)
            _handle_sqlalchemy_error(e, "creating relationship", db)
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error("Unexpected error during relationship creation.", user_id=user_id, tree_id=tree_id, exc_info=True)
            abort(500, description="An unexpected error occurred during relationship creation.")


def update_relationship_db(db: DBSession, relationship_id: uuid.UUID, tree_id: uuid.UUID, relationship_data: Dict[str, Any]) -> Dict[str, Any]:
    with tracer.start_as_current_span("service.update_relationship") as span:
        # (Initial setup and logging from original code)
        span.set_attribute("relationship.id", str(relationship_id))
        span.set_attribute("tree.id", str(tree_id))
        logger.info("Attempting to update relationship", rel_id=relationship_id, tree_id=tree_id, data_keys=list(relationship_data.keys()))

        relationship = _get_or_404(db, Relationship, relationship_id, tree_id=tree_id)
        
        validation_errors = {}
        # Define fields that can be updated
        allowed_fields = {
            'person1_id': uuid.UUID, 'person2_id': uuid.UUID, 'relationship_type': RelationshipTypeEnum,
            'start_date': date, 'end_date': date, 'certainty_level': int,
            'custom_attributes': dict, 'notes': str
        }

        for field, value in relationship_data.items():
            if field not in allowed_fields:
                logger.warning(f"Attempt to update unallowed field '{field}' for relationship {relationship_id}.")
                continue

            try:
                if field in ['person1_id', 'person2_id']:
                    new_person_id = uuid.UUID(str(value)) if value else None
                    if new_person_id: # Verify person exists in this tree
                        _get_or_404(db, Person, new_person_id, tree_id=tree_id)
                    setattr(relationship, field, new_person_id)
                elif field == 'relationship_type':
                    setattr(relationship, field, RelationshipTypeEnum(value) if value else None)
                elif field in ['start_date', 'end_date']:
                    setattr(relationship, field, date.fromisoformat(str(value)) if value else None)
                elif field == 'certainty_level':
                    if value is not None and (not isinstance(value, int) or not (0 <= value <= 5)): # Example range
                         validation_errors[field] = "Certainty level must be an integer between 0 and 5."
                    else: setattr(relationship, field, value)
                elif field == 'custom_attributes':
                    if not isinstance(value, dict): validation_errors[field] = "Custom attributes must be a dictionary."
                    else: setattr(relationship, field, value)
                else: # For notes (str)
                    setattr(relationship, field, value)
            except ValueError as e: # Catches UUID format, date format, enum errors
                validation_errors[field] = f"Invalid value or format for {field}: {e}"
            except HTTPException: # Re-raise 404 from _get_or_404 if person not found
                raise 
            except Exception as e:
                logger.error(f"Unexpected error processing field {field} for relationship update.", exc_info=True)
                validation_errors[field] = f"Unexpected error processing {field}."

        if validation_errors:
             logger.warning("Relationship update failed: Validation errors.", rel_id=relationship_id, errors=validation_errors)
             abort(400, description={"message": "Validation failed", "details": validation_errors})

        # Post-update validation
        if relationship.person1_id == relationship.person2_id:
              abort(400, description="Cannot have a relationship where person1 and person2 are the same.")
        if relationship.start_date and relationship.end_date and relationship.end_date < relationship.start_date:
            abort(400, description="End date cannot be before start date.")
        
        # relationship.updated_at handled by onupdate
        try:
            db.commit()
            db.refresh(relationship)
            logger.info("Relationship updated successfully", rel_id=relationship.id, tree_id=tree_id, event_type="RELATIONSHIP_UPDATED")
            return relationship.to_dict()
        except SQLAlchemyError as e:
            logger.error("Database error during relationship update.", rel_id=relationship_id, tree_id=tree_id, exc_info=True)
            _handle_sqlalchemy_error(e, f"updating relationship ID {relationship_id}", db)
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error("Unexpected error during relationship update.", rel_id=relationship_id, tree_id=tree_id, exc_info=True)
            abort(500, description="An unexpected error occurred during relationship update.")


def delete_relationship_db(db: DBSession, relationship_id: uuid.UUID, tree_id: uuid.UUID) -> bool:
    with tracer.start_as_current_span("service.delete_relationship") as span:
        span.set_attribute("relationship.id", str(relationship_id))
        span.set_attribute("tree.id", str(tree_id))
        logger.info("Attempting to delete relationship", rel_id=relationship_id, tree_id=tree_id)
        
        relationship = _get_or_404(db, Relationship, relationship_id, tree_id=tree_id)
        try:
            db.delete(relationship)
            db.commit()
            logger.info("Relationship deleted successfully", rel_id=relationship_id, tree_id=tree_id, event_type="RELATIONSHIP_DELETED")
            return True
        except SQLAlchemyError as e: # Should not hit IntegrityError if relationship is correctly identified and deleted.
            logger.error("Database error during relationship deletion.", rel_id=relationship_id, tree_id=tree_id, exc_info=True)
            _handle_sqlalchemy_error(e, f"deleting relationship ID {relationship_id}", db)
        except Exception as e:
            db.rollback()
            logger.error("Unexpected error during relationship deletion.", rel_id=relationship_id, tree_id=tree_id, exc_info=True)
            abort(500, description="An unexpected error occurred during relationship deletion.")
        return False # Should be unreachable

# --- Tree Data Service ---
def get_tree_data_db(db: DBSession, tree_id: uuid.UUID) -> Dict[str, Any]:
    # This endpoint is inherently data-intensive for large trees.
    # Consider alternatives like GraphQL, paginated graph traversal, or server-side pre-aggregation
    # if performance becomes an issue for very large trees.
    with tracer.start_as_current_span("service.get_tree_data") as span:
        span.set_attribute("tree.id", str(tree_id))
        logger.info("Fetching full tree data for visualization", tree_id=tree_id)
        
        # Check tree existence first (implicitly done by require_tree_access decorator usually)
        # tree = _get_or_404(db, Tree, tree_id) # Not strictly needed if decorator handles it

        try:
            # Fetch all people and relationships for the tree.
            # For extremely large trees, this can be memory intensive.
            # WARNING: This does not use pagination and is intended to fetch the entire tree.
            people_list = db.query(Person).filter(Person.tree_id == tree_id).all()
            relationships_list = db.query(Relationship).filter(Relationship.tree_id == tree_id).all()

            num_people = len(people_list)
            num_relationships = len(relationships_list)
            span.set_attributes({"tree.nodes_count": num_people, "tree.edges_count": num_relationships})

            if num_people > 1000 or num_relationships > 2000: # Arbitrary thresholds for logging
                logger.warning(f"Fetching very large tree data for visualization: {num_people} people, {num_relationships} relationships for tree {tree_id}. This might be slow or memory intensive.")

            nodes = []
            for person_obj in people_list:
                label_parts = []
                if person_obj.first_name: label_parts.append(person_obj.first_name)
                if person_obj.last_name: label_parts.append(person_obj.last_name)
                label = " ".join(label_parts)
                
                if person_obj.nickname: label += f" ({person_obj.nickname})"
                if not label.strip(): label = f"Person (ID: {str(person_obj.id)[:8]})" # Fallback label

                nodes.append({
                    "id": str(person_obj.id),
                    "type": "personNode", # For frontend differentiation
                    "position": {"x": 0, "y": 0}, # Frontend should calculate layout
                    "data": { # Core person data for the node
                        "id": str(person_obj.id), # Redundant but often useful
                        "label": label,
                        "full_name": f"{person_obj.first_name or ''} {person_obj.last_name or ''}".strip(),
                        "gender": person_obj.gender,
                        "dob": person_obj.birth_date.isoformat() if person_obj.birth_date else None,
                        "dod": person_obj.death_date.isoformat() if person_obj.death_date else None,
                        "birth_place": person_obj.birth_place,
                        "death_place": person_obj.death_place,
                        "is_living": person_obj.is_living,
                        # Add other fields as needed by the frontend visualization
                    },
                    "person_id": str(person_obj.id) # Explicit person_id if useful for frontend
                })

            links = []
            for rel_obj in relationships_list:
                links.append({
                    "id": str(rel_obj.id),
                    "source": str(rel_obj.person1_id),
                    "target": str(rel_obj.person2_id),
                    "type": "customEdge", # Or use rel_obj.relationship_type.value for type
                    "animated": False, # Default, can be customized
                    "label": rel_obj.relationship_type.value.replace("_", " ").title(), # User-friendly label
                    "data": rel_obj.to_dict() # Full relationship data if needed by frontend on edge click
                })
            
            logger.info("Full tree data fetched and formatted successfully", tree_id=tree_id, num_nodes=len(nodes), num_links=len(links))
            return {"nodes": nodes, "links": links}
        except SQLAlchemyError as e:
            logger.error("Database error fetching tree data for visualization.", exc_info=True, tree_id=tree_id)
            _handle_sqlalchemy_error(e, f"fetching tree data for tree {tree_id}", db)
        except Exception as e:
            logger.error("Unexpected error fetching tree data for visualization.", exc_info=True, tree_id=tree_id)
            abort(500, description="An unexpected error occurred while fetching tree data for visualization.")


# --- Database Setup ---
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    logger.critical("DATABASE_URL environment variable is not set. Application cannot start.")
    # For a real app, you might want to exit(1) or raise a more specific startup error.
    # For now, this will cause issues later when engine is used.
    # Let's make it exit to prevent running in a broken state.
    raise RuntimeError("DATABASE_URL is not set. Database connection cannot be established.")

logger.info(f"Database URL: {'<set>' if DATABASE_URL else '<not set>'}") # Will always be set due to check above

try:
    # Consider connection pool settings for production (pool_recycle, pool_timeout, etc.)
    engine = create_engine(
        DATABASE_URL,
        pool_size=int(os.getenv("DB_POOL_SIZE", 20)), # Default to 20, configurable
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", 10)), # Default to 10
        pool_recycle=int(os.getenv("DB_POOL_RECYCLE", 1800)), # Recycle connections e.g., every 30 mins
        echo=os.getenv("SQLALCHEMY_ECHO", "False").lower() == "true" # Enable SQL echo via env var
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    SQLAlchemyInstrumentor().instrument(engine=engine) # Instrument for OpenTelemetry
    logger.info("SQLAlchemy engine and session factory created successfully.")
except Exception as e:
    logger.critical(f"Failed to create SQLAlchemy engine or session factory: {e}", exc_info=True)
    # This is a critical startup failure.
    raise RuntimeError(f"Database engine initialization failed: {e}")


# --- Database Initialization Functions ---
def create_tables(engine_to_use):
    logger.info("Attempting to create database tables if they don't exist...")
    try:
        # Base.metadata.create_all(bind=engine_to_use, checkfirst=True) is simpler
        # The inspector logic is fine too.
        inspector = inspect(engine_to_use)
        existing_tables = inspector.get_table_names()
        
        # Check if all tables defined in Base.metadata exist
        all_defined_tables_present = True
        for table_name in Base.metadata.tables.keys():
            if table_name not in existing_tables:
                all_defined_tables_present = False
                logger.info(f"Table '{table_name}' is missing.")
                break
        
        if not all_defined_tables_present:
             logger.info("Not all defined tables exist. Creating/updating schema...")
             Base.metadata.create_all(bind=engine_to_use) # This creates tables that don't exist
             logger.info("Database schema creation/update attempt complete.")
        else:
             logger.info(f"All defined tables ({len(Base.metadata.tables)}) seem to exist. Skipping schema creation.")
    except Exception as e:
        logger.error(f"Error during database schema check/creation: {e}", exc_info=True)
        raise # Re-raise to indicate critical failure

def populate_initial_data(session_factory):
    logger.info("Checking if initial data population is needed...")
    db_session_init = session_factory()
    try:
        user_count = db_session_init.query(func.count(User.id)).scalar()
        if user_count == 0:
            logger.info("No users found. Populating initial admin data...")
            admin_username = os.getenv("INITIAL_ADMIN_USERNAME", "admin")
            admin_email = os.getenv("INITIAL_ADMIN_EMAIL", "admin@example.com")
            admin_password = os.getenv("INITIAL_ADMIN_PASSWORD")

            if not admin_password:
                 logger.critical("INITIAL_ADMIN_PASSWORD environment variable is not set. Cannot create initial admin user.")
                 return # Skip admin creation if password not set

            try:
                _validate_password_complexity(admin_password)
            except ValueError as e:
                 logger.critical(f"Initial admin password does not meet complexity requirements: {e}. Cannot create initial admin user.")
                 return

            hashed_password = _hash_password(admin_password)
            admin_user = User(
                username=admin_username,
                email=admin_email.lower(),
                password_hash=hashed_password,
                role=UserRole.ADMIN,
                is_active=True,
                email_verified=True # Assume admin's email is verified initially
            )
            db_session_init.add(admin_user)
            db_session_init.commit()
            logger.info(f"Initial admin user '{admin_user.username}' created successfully.")
        else:
            logger.info(f"Database already contains {user_count} users. Skipping initial admin data population.")
    except SQLAlchemyError as e: # Catch DB errors during population
        logger.error(f"Database error during initial data population: {e}", exc_info=True)
        db_session_init.rollback()
    except Exception as e: # Catch other errors
        logger.error(f"Unexpected error during initial data population: {e}", exc_info=True)
        db_session_init.rollback()
    finally:
        db_session_init.close()

def initialize_database(engine_to_use, session_factory):
    logger.info("Initializing database...")
    try:
        # Test connection first
        with engine_to_use.connect() as connection:
            logger.info("Database connection successful.")
        create_tables(engine_to_use)
        populate_initial_data(session_factory)
        logger.info("Database initialization process complete.")
    except Exception as e: # Catch errors from create_tables or populate_initial_data
        logger.critical(f"Database initialization failed: {e}", exc_info=True)
        # This is a critical startup failure.
        raise RuntimeError(f"Database initialization failed: {e}")

# Initialize DB when app module is loaded.
# Ensure this is safe for your deployment (e.g., not run multiple times by Gunicorn workers if not intended)
# Typically, migrations (like Alembic) handle schema, and seeding is a separate script or conditional logic.
# For this single-file app, this is a common pattern.
if os.getenv("SKIP_DB_INIT", "false").lower() != "true":
    initialize_database(engine, SessionLocal)
else:
    logger.info("Skipping database initialization as per SKIP_DB_INIT environment variable.")


@app.errorhandler(Exception)
def handle_global_exception(e):
    # Log the full exception trace for unexpected errors
    if not isinstance(e, HTTPException): # Log non-HTTP exceptions with more detail
        logger.error(
            "Unhandled exception caught by global error handler",
            exc_info=e, # This will include the full traceback
            path=request.path,
            method=request.method,
            error_type=type(e).__name__
        )
    
    if isinstance(e, HTTPException):
        # For HTTPExceptions (like abort()), the description is usually user-friendly.
        # The logger.warning in the specific abort calls might be sufficient.
        # Here, we ensure the response is JSON.
        response_data = {
            "error": getattr(e, 'name', "Error"), # e.g. "Not Found", "Bad Request"
            "message": getattr(e, 'description', "An error occurred."),
        }
        # If description itself is a dict (as used in some abort calls), merge it
        if isinstance(e.description, dict):
            response_data["message"] = e.description.get("message", "An error occurred.")
            if "details" in e.description: response_data["details"] = e.description["details"]
            if "code" in e.description: response_data["error_code"] = e.description["code"]

        response = jsonify(response_data)
        response.status_code = e.code or 500 # Default to 500 if code is not set
        return response

    # For non-HTTP exceptions, return a generic 500 error.
    return jsonify({
        "error": "Internal Server Error",
        "message": "An unexpected error occurred on the server. Please try again later."
    }), 500

# --- Flask Request Lifecycle Hooks ---
@app.before_request
def before_request_hook():
    # Create a new DB session for each request and store it in Flask's 'g' object
    g.db = SessionLocal()

@app.teardown_appcontext
def teardown_db_hook(exception=None):
    # Close the DB session when the app context ends (after request is handled)
    db = g.pop('db', None)
    if db is not None:
        try:
            if exception: # If an exception occurred during the request, rollback
                db.rollback()
                logger.debug("Rolling back DB session due to exception in request.", exc_info=exception)
            else: # Otherwise, commit (though most commits happen in service layers)
                # db.commit() # This might be too broad. Better to commit explicitly in services.
                pass
        except Exception as e:
            logger.error(f"Error during DB session teardown (rollback/commit): {e}", exc_info=True)
        finally:
            try:
                db.close()
            except Exception as e:
                logger.error(f"Error closing database session: {e}", exc_info=True)

# --- API Helper for Pagination Params ---
def get_pagination_params() -> Tuple[int, int, Optional[str], Optional[str]]:
    page = request.args.get('page', default=PAGINATION_DEFAULTS["page"], type=int)
    per_page = request.args.get('per_page', default=PAGINATION_DEFAULTS["per_page"], type=int)
    sort_by = request.args.get('sort_by', default=None, type=str)
    sort_order = request.args.get('sort_order', default="asc", type=str)

    page = max(1, page) # Ensure page is at least 1
    per_page = max(1, min(per_page, PAGINATION_DEFAULTS["max_per_page"])) # Clamp per_page
    if sort_order not in ["asc", "desc"]:
        sort_order = "asc" # Default to asc if invalid
    return page, per_page, sort_by, sort_order

# --- API Endpoints ---
@limiter.limit("10 per minute") # Stricter limit for login attempts
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        abort(400, description="Username and password are required.")
    
    username_or_email = data['username']
    password = data['password']
    db = g.db # Get DB session from g

    user = authenticate_user_db(db, username_or_email, password) # This now handles aborts for inactive, etc.
    
    if not user: # If authenticate_user_db returns None (and didn't abort for other reasons like inactive)
        # auth_failure_counter is incremented within authenticate_user_db
        abort(401, description="Incorrect username or password.") # Generic message

    # Create session
    session['user_id'] = str(user['id'])
    session['username'] = user['username']
    session['role'] = user['role']
    # session.permanent = True # If PERMANENT_SESSION_LIFETIME is used

    logger.info("User logged in successfully", user_id=user['id'], username=user['username'])
    return jsonify({"message": "Login successful!", "user": user, "active_tree_id": session.get('active_tree_id')}), 200


@limiter.limit("5 per minute") # Stricter limit for registration
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password') or not data.get('email'):
        abort(400, description="Username, email, and password are required.")
    
    db = g.db
    try:
        # Ensure role validation is handled within register_user_db or here
        user_data = {
            'username': data['username'],
            'email': data['email'],
            'password': data['password'],
            'full_name': data.get('full_name'),
            'role': data.get('role') # Pass role if provided, register_user_db will validate
        }
        # register_user_db handles aborts for validation errors (password, role) and integrity errors
        user = register_user_db(db, user_data)
        
        # Optionally log in user immediately after registration
        # session['user_id'] = str(user['id'])
        # session['username'] = user['username']
        # session['role'] = user['role']
        
        logger.info("User registered successfully", user_id=user['id'], username=user['username'])
        return jsonify({"message": "Registration successful! Please log in.", "user": user}), 201 # Don't return sensitive parts of user
    except HTTPException: # Re-raise aborts from service layer
        # user_registration_counter is handled in service layer for success/failure
        raise
    except Exception as e: # Catch any other unexpected error
        user_registration_counter.add(1, {"status": "failure", "reason": "endpoint_unknown_error"})
        logger.error("Unexpected error in /api/register endpoint", exc_info=True)
        abort(500, description="An unexpected error occurred during registration.")


@app.route('/api/logout', methods=['POST'])
@require_auth # Ensure user is logged in to log out
def logout():
    user_id = session.get('user_id')
    username = session.get('username')
    
    session.clear() # Clear all session data
    
    logger.info("User logged out successfully", user_id=user_id, username=username)
    # Make sure frontend handles cookie clearing if necessary (though server-side session clear is key)
    response = jsonify({"message": "Logout successful"})
    # Explicitly tell browser to clear session cookie if it's persistent and not httpOnly (though it should be httpOnly)
    # response.set_cookie(app.session_cookie_name, '', expires=0, path=app.config.get('SESSION_COOKIE_PATH', '/'))
    return response, 200


@app.route('/api/session', methods=['GET'])
def session_status():
    if 'user_id' in session and 'username' in session and 'role' in session:
        # Optionally, verify user still exists and is active in DB for enhanced security
        # db = g.db
        # current_user = db.query(User).filter(User.id == session['user_id'], User.is_active == True).one_or_none()
        # if not current_user:
        #     session.clear()
        #     return jsonify({"isAuthenticated": False, "user": None, "active_tree_id": None}), 200

        user_info = {
            "id": session['user_id'],
            "username": session['username'],
            "role": session['role']
            # Add other non-sensitive info if needed: full_name, preferences etc.
            # These would need to be added to session on login or fetched here.
        }
        active_tree_id = session.get('active_tree_id')
        logger.debug("Session status retrieved: authenticated", user_id=user_info['id'], active_tree_id=active_tree_id)
        return jsonify({
            "isAuthenticated": True,
            "user": user_info,
            "active_tree_id": active_tree_id
        }), 200
    else:
        logger.debug("Session status retrieved: not authenticated")
        return jsonify({"isAuthenticated": False, "user": None, "active_tree_id": None}), 200


@limiter.limit("5 per 15minute") # Stricter limit for password reset requests
@app.route('/api/request-password-reset', methods=['POST'])
def request_password_reset_endpoint(): # Renamed to avoid conflict
    data = request.get_json()
    if not data or not data.get('email_or_username'): # Changed field name for clarity
        abort(400, description="Email or username is required.")
    
    email_or_username_input = data['email_or_username']
    db = g.db
    
    # request_password_reset_db handles aborts and always returns True (or aborts)
    # to prevent user enumeration.
    request_password_reset_db(db, email_or_username_input) 
    
    return jsonify({"message": "If an account exists for this identifier and is active, a password reset link has been sent to the associated email address."}), 200


@limiter.limit("5 per 15minute") # Stricter limit for reset attempts
@app.route('/api/reset-password/<string:token>', methods=['POST']) # Ensure token is string
def reset_password_endpoint(token: str): # Renamed
    data = request.get_json()
    if not data or not data.get('new_password'):
        abort(400, description="New password is required.")
    
    new_password = data['new_password']
    db = g.db
    
    # reset_password_db handles aborts for invalid token, password complexity etc.
    reset_password_db(db, token, new_password)
    
    return jsonify({"message": "Your password has been reset successfully. You can now log in with your new password."}), 200


@app.route('/api/trees', methods=['POST'])
@require_auth
def create_tree_endpoint(): # Renamed
    data = request.get_json()
    if not data: abort(400, description="Request body cannot be empty.")
    # name validation is handled in create_tree_db

    user_id = uuid.UUID(session['user_id']) # require_auth ensures user_id is in session
    db = g.db
    
    try:
        # create_tree_db handles aborts for validation (name, privacy level)
        new_tree = create_tree_db(db, user_id, data)
        
        # Set the newly created tree as active for the user
        session['active_tree_id'] = str(new_tree['id']) # Store as string
        logger.info(f"New tree {new_tree['id']} set as active for user {user_id}")
        
        return jsonify(new_tree), 201
    except HTTPException: # Re-raise aborts from service
        raise
    except Exception as e: # Catch unexpected errors
        logger.error("Unexpected error in create_tree endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while creating the tree.")


@app.route('/api/trees', methods=['GET'])
@require_auth
def get_user_trees_endpoint(): # Renamed
    user_id = uuid.UUID(session['user_id'])
    db = g.db
    page, per_page, sort_by, sort_order = get_pagination_params()
    # Default sort for trees if not provided by client
    sort_by = sort_by or "name" 
    sort_order = sort_order or "asc"

    try:
        # get_user_trees_db now returns a paginated structure and handles aborts
        trees_page = get_user_trees_db(db, user_id, page, per_page, sort_by, sort_order)
        return jsonify(trees_page), 200
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error in get_user_trees endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while fetching your trees.")


@app.route('/api/session/active_tree', methods=['PUT'])
@require_auth
def set_active_tree_endpoint(): # Renamed
    data = request.get_json()
    if not data or not data.get('tree_id'):
        abort(400, description="tree_id is required in the request body.")
    
    tree_id_str = data['tree_id']
    user_id = uuid.UUID(session['user_id'])
    db = g.db

    try:
        tree_id_uuid = uuid.UUID(tree_id_str)
    except ValueError:
        abort(400, description="Invalid UUID format for tree_id.")

    # Verify user has at least view access to this tree before setting it as active
    # This logic is similar to require_tree_access but without aborting if no access,
    # instead, we check explicitly.
    tree = db.query(Tree).filter(Tree.id == tree_id_uuid).one_or_none()
    if not tree:
        abort(404, description=f"Tree with ID {tree_id_str} not found.")

    can_set_active = False
    if tree.created_by == user_id or tree.is_public: # Owner or public tree
        can_set_active = True
    else: # Check TreeAccess table
        tree_access_obj = db.query(TreeAccess).filter(
            TreeAccess.tree_id == tree_id_uuid,
            TreeAccess.user_id == user_id
        ).first() # .first() is fine, we just need to know if any access exists
        if tree_access_obj:
            can_set_active = True
            
    if not can_set_active:
        abort(403, description=f"You do not have permission to access tree {tree_id_str}.")

    session['active_tree_id'] = tree_id_str # Store as string
    logger.info("Active tree set in session.", user_id=user_id, tree_id=tree_id_str)
    return jsonify({"message": "Active tree set successfully.", "active_tree_id": tree_id_str}), 200


# --- People Endpoints ---
# The require_tree_access decorator will use active_tree_id from session if tree_id_param not in path
@app.route('/api/people', methods=['GET'])
@require_tree_access('view') # Ensures active tree is set and user has view access
def get_all_people_endpoint(): # Renamed
    db = g.db
    tree_id = g.active_tree_id # Set by require_tree_access
    page, per_page, sort_by, sort_order = get_pagination_params()
    sort_by = sort_by or "last_name" # Default sort for people

    # Example: Allow filtering by 'is_living' from query params
    filters = {}
    is_living_filter = request.args.get('is_living', type=str) # Get as string to handle "true"/"false"
    if is_living_filter is not None:
        if is_living_filter.lower() == 'true':
            filters['is_living'] = True
        elif is_living_filter.lower() == 'false':
            filters['is_living'] = False
        # else: ignore invalid filter value or abort(400)

    try:
        people_page = get_all_people_db(db, tree_id, page, per_page, sort_by, sort_order, filters=filters)
        return jsonify(people_page), 200
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error in get_all_people endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while fetching people for the active tree.")


@app.route('/api/people/<uuid:person_id_param>', methods=['GET']) # Use a distinct param name
@require_tree_access('view') # Ensures active tree context
def get_person_endpoint(person_id_param: uuid.UUID): # Renamed
    db = g.db
    tree_id = g.active_tree_id # From decorator
    
    try:
        # get_person_db uses _get_or_404 which includes tree_id check
        person_details = get_person_db(db, person_id_param, tree_id)
        return jsonify(person_details), 200
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error in get_person endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while fetching the person's details.")


@app.route('/api/people', methods=['POST'])
@require_tree_access('edit') # Requires edit access to the active tree
def create_person_endpoint(): # Renamed
    data = request.get_json()
    if not data: abort(400, description="Request body is required and cannot be empty.")
    
    user_id = uuid.UUID(session['user_id'])
    tree_id = g.active_tree_id # From decorator
    db = g.db
    
    try:
        # create_person_db handles validation and aborts
        new_person_obj = create_person_db(db, user_id, tree_id, data)
        return jsonify(new_person_obj), 201
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error in create_person endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while creating the person.")


@app.route('/api/people/<uuid:person_id_param>', methods=['PUT'])
@require_tree_access('edit')
def update_person_endpoint(person_id_param: uuid.UUID): # Renamed
    data = request.get_json()
    if not data: abort(400, description="Request body is required and cannot be empty.")
    
    tree_id = g.active_tree_id # From decorator
    db = g.db
    
    try:
        # update_person_db handles _get_or_404, validation, and aborts
        updated_person_obj = update_person_db(db, person_id_param, tree_id, data)
        return jsonify(updated_person_obj), 200
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error in update_person endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while updating the person.")


@app.route('/api/people/<uuid:person_id_param>', methods=['DELETE'])
@require_tree_access('edit') # Or 'admin' level on tree if deletion is more restricted
def delete_person_endpoint(person_id_param: uuid.UUID): # Renamed
    tree_id = g.active_tree_id # From decorator
    db = g.db
    
    try:
        # delete_person_db handles _get_or_404 and aborts on integrity errors
        delete_person_db(db, person_id_param, tree_id)
        return '', 204 # No content response for successful deletion
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error in delete_person endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while deleting the person.")


# --- Relationships Endpoints ---
@app.route('/api/relationships', methods=['GET'])
@require_tree_access('view')
def get_all_relationships_endpoint(): # Renamed
    db = g.db
    tree_id = g.active_tree_id
    page, per_page, sort_by, sort_order = get_pagination_params()
    sort_by = sort_by or "created_at" # Default sort for relationships
    sort_order = sort_order or "desc"

    filters = {}
    # Example: filter by a specific person involved in the relationship
    person_id_filter = request.args.get('person_id', type=str)
    if person_id_filter:
        try:
            uuid.UUID(person_id_filter) # Validate format
            filters['person_id'] = person_id_filter
        except ValueError:
            abort(400, description="Invalid person_id format for filtering relationships.")
    
    # Example: filter by relationship_type
    rel_type_filter = request.args.get('relationship_type', type=str)
    if rel_type_filter:
        filters['relationship_type'] = rel_type_filter


    try:
        relationships_page = get_all_relationships_db(db, tree_id, page, per_page, sort_by, sort_order, filters=filters)
        return jsonify(relationships_page), 200
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error in get_all_relationships endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while fetching relationships.")


@app.route('/api/relationships/<uuid:relationship_id_param>', methods=['GET'])
@require_tree_access('view')
def get_relationship_endpoint(relationship_id_param: uuid.UUID): # Renamed
    with tracer.start_as_current_span("endpoint.get_relationship") as span: # Keep span if custom logic here
        span.set_attribute("relationship.id", str(relationship_id_param))
        db = g.db
        tree_id = g.active_tree_id # From decorator
        span.set_attribute("tree.id", str(tree_id))
        try:
            # _get_or_404 ensures relationship belongs to the active tree
            relationship_obj = _get_or_404(db, Relationship, relationship_id_param, tree_id=tree_id)
            return jsonify(relationship_obj.to_dict()), 200
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Unexpected error in get_relationship endpoint.", exc_info=True)
            abort(500, description="An unexpected error occurred while fetching the relationship.")


@app.route('/api/relationships', methods=['POST'])
@require_tree_access('edit')
def create_relationship_endpoint(): # Renamed
    data = request.get_json()
    if not data: abort(400, description="Request body is required and cannot be empty.")
    
    user_id = uuid.UUID(session['user_id'])
    tree_id = g.active_tree_id # From decorator
    db = g.db
    
    try:
        # Ensure field names in payload match what create_relationship_db expects (e.g., person1_id, person2_id)
        # create_relationship_db handles validation, _get_or_404 for persons, and aborts
        new_relationship_obj = create_relationship_db(db, user_id, tree_id, data)
        return jsonify(new_relationship_obj), 201
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error in create_relationship endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while creating the relationship.")


@app.route('/api/relationships/<uuid:relationship_id_param>', methods=['PUT'])
@require_tree_access('edit')
def update_relationship_endpoint(relationship_id_param: uuid.UUID): # Renamed
    data = request.get_json()
    if not data: abort(400, description="Request body is required and cannot be empty.")
    
    tree_id = g.active_tree_id # From decorator
    db = g.db
    
    try:
        # update_relationship_db handles _get_or_404 for relationship and persons, validation, aborts
        updated_relationship_obj = update_relationship_db(db, relationship_id_param, tree_id, data)
        return jsonify(updated_relationship_obj), 200
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error in update_relationship endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while updating the relationship.")


@app.route('/api/relationships/<uuid:relationship_id_param>', methods=['DELETE'])
@require_tree_access('edit')
def delete_relationship_endpoint(relationship_id_param: uuid.UUID): # Renamed
    tree_id = g.active_tree_id # From decorator
    db = g.db
    
    try:
        # delete_relationship_db handles _get_or_404 and aborts
        delete_relationship_db(db, relationship_id_param, tree_id)
        return '', 204
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error in delete_relationship endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while deleting the relationship.")


# This endpoint can be very resource-intensive for large trees.
# Apply a stricter rate limit.
@limiter.limit("10 per minute") # Example: 10 requests per minute for this specific heavy endpoint
@app.route('/api/tree_data', methods=['GET'])
@require_tree_access('view') # Ensures user has access to the active tree
def get_tree_data_endpoint(): # Renamed
    db = g.db
    tree_id = g.active_tree_id # From decorator
    
    try:
        # get_tree_data_db fetches all nodes and links; consider alternatives for huge trees.
        tree_data_result = get_tree_data_db(db, tree_id)
        return jsonify(tree_data_result), 200
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error in get_tree_data endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while fetching tree data for visualization.")


# --- Admin Endpoints ---
@app.route('/api/users', methods=['GET'])
@require_admin # Only admins can list all users
def get_all_users_endpoint(): # Renamed
    db = g.db
    page, per_page, sort_by, sort_order = get_pagination_params()
    sort_by = sort_by or "username" # Default sort for users
    
    try:
        users_page = get_all_users_db(db, page, per_page, sort_by, sort_order)
        return jsonify(users_page), 200
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error in get_all_users admin endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while fetching all users.")


@app.route('/api/users/<uuid:user_id_param>', methods=['DELETE'])
@require_admin
def delete_user_endpoint(user_id_param: uuid.UUID): # Renamed
    current_admin_user_id_str = session.get('user_id') # From @require_auth in @require_admin
    
    if current_admin_user_id_str and uuid.UUID(current_admin_user_id_str) == user_id_param:
        logger.warning("Admin attempted to delete their own account.", admin_user_id=current_admin_user_id_str)
        abort(403, description="Administrators cannot delete their own account using this endpoint.")
    
    db = g.db
    try:
        # delete_user_db handles _get_or_404 and aborts on integrity errors (e.g., user owns trees)
        delete_user_db(db, user_id_param)
        return '', 204
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error in delete_user admin endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while deleting the user.")


@app.route('/api/users/<uuid:user_id_param>/role', methods=['PUT'])
@require_admin
def set_user_role_endpoint(user_id_param: uuid.UUID): # Renamed
    data = request.get_json()
    if not data or not data.get('role'):
        abort(400, description="The 'role' field (e.g., 'user', 'admin') is required in the request body.")
    
    new_role_str = data['role']
    current_admin_user_id_str = session.get('user_id')

    if current_admin_user_id_str and uuid.UUID(current_admin_user_id_str) == user_id_param:
        logger.warning("Admin attempted to change their own role.", admin_user_id=current_admin_user_id_str)
        abort(403, description="Administrators cannot change their own role using this endpoint. Use direct database modification or another admin account if necessary.")
    
    db = g.db
    try:
        # update_user_role_db handles _get_or_404, role validation, and aborts
        updated_user_obj = update_user_role_db(db, user_id_param, new_role_str)
        # role_change_counter is incremented in service layer
        return jsonify(updated_user_obj), 200
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error in set_user_role admin endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while setting the user role.")


# --- Health & Metrics ---
@limiter.limit("60 per minute") # Standard rate limit for health/metrics
@app.route('/health', methods=['GET'])
def health_check_endpoint(): # Renamed
    service_status = "healthy"
    db_status = "unknown" # Renamed variable
    db_latency_ms = None # Renamed variable
    dependencies = {} # Renamed variable
    
    start_time_db_check = time.monotonic()
    try:
        # Use a new session for health check, separate from request context
        with SessionLocal() as health_db_session:
            health_db_session.execute(text("SELECT 1")) # Simple query to check DB connectivity
            db_status = "healthy"
    except SQLAlchemyError as e: # Catch only SQLAlchemy errors for DB status
        db_status = "unhealthy"
        service_status = "unhealthy" # If DB is unhealthy, service is unhealthy
        logger.error(f"Database health check failed: {e}", exc_info=False) # Don't need full trace for common health fail
    except Exception as e: # Catch other unexpected errors during DB check
        db_status = "error"
        service_status = "unhealthy"
        logger.error(f"Unexpected error during DB health check: {e}", exc_info=True)
    finally:
        end_time_db_check = time.monotonic()
        db_latency_ms = (end_time_db_check - start_time_db_check) * 1000

    dependencies["database"] = {
        "status": db_status,
        "latency_ms": round(db_latency_ms, 2) if db_latency_ms is not None else None
    }
    
    # Add other dependency checks here (e.g., Redis, external services)

    response_data = {
        "status": service_status,
        "timestamp": datetime.utcnow().isoformat() + "Z", # ISO 8601 format
        "dependencies": dependencies
    }
    
    http_status_code = 200 if service_status == "healthy" else 503 # 503 Service Unavailable if not healthy
    
    if service_status != "healthy":
        logger.warning(
            "Health check failed.",
            service_status=service_status,
            db_status=db_status,
            db_latency_ms=db_latency_ms,
            # dependencies_log=dependencies # Avoid too much noise in logs for simple health check
        )
    else:
        logger.debug(
            "Health check successful.",
            db_status=db_status,
            db_latency_ms=db_latency_ms
        )
        
    return jsonify(response_data), http_status_code


@limiter.limit("60 per minute")
@app.route('/metrics', methods=['GET'])
def metrics_endpoint():
    # Ensure prometheus_client is installed: pip install prometheus-client
    try:
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry
        
        # Use a specific registry if you have custom metrics registered elsewhere,
        # otherwise, the default registry is used by generate_latest().
        # registry = CollectorRegistry() 
        # For OTel metrics, they are exported via OTLPMetricExporter, not typically scraped here
        # unless you also bridge OTel metrics to Prometheus.
        # This endpoint is more for Flask/app-specific Prometheus metrics if you add them.

        prometheus_response_body = generate_latest() # Uses default Prometheus registry
        response = make_response(prometheus_response_body)
        response.headers['Content-Type'] = CONTENT_TYPE_LATEST
        return response
    except ImportError:
        logger.error("prometheus_client library is not installed. /metrics endpoint unavailable.")
        abort(501, "Metrics endpoint is not implemented or prometheus_client is missing.")
    except Exception as e:
        logger.error(f"Error generating Prometheus metrics: {e}", exc_info=True)
        abort(500, "Error generating Prometheus metrics.")


if __name__ == '__main__':
    host = os.environ.get('FLASK_RUN_HOST', '0.0.0.0') # Default to 0.0.0.0 to be accessible externally
    port = int(os.environ.get('FLASK_RUN_PORT', 8090)) # Consistent with original
    # FLASK_DEBUG is a string 'true' or 'false'. Python's bool('false') is True.
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() in ['true', '1', 't']
    
    logger.info(f"Starting Flask server on http://{host}:{port}")
    logger.info(f"Flask Environment: {os.getenv('FLASK_ENV', 'N/A')}, Debug Mode: {debug_mode}")
    
    # For production, use a proper WSGI server like Gunicorn or uWSGI
    # e.g., gunicorn -w 4 -b 0.0.0.0:8090 main:app
    app.run(host=host, port=port, debug=debug_mode)
