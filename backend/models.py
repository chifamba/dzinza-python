# backend/models.py
import enum
import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, Boolean, DateTime, Date, ForeignKey, String, Text,
    Enum as SQLAlchemyEnum, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import TypeDecorator
from cryptography.fernet import Fernet, InvalidToken
import os # For fernet_suite initialization (though it should be in utils or config)
import json # For fernet_suite initialization
# Note: Fernet initialization is better handled outside models.py.
# It's temporarily here to match original structure for EncryptedString.
# Ideally, fernet_suite would be passed to EncryptedString or accessed via a global app context.

# --- Encryption Setup (Simplified for model definition context) ---
# This is a temporary workaround. Proper Fernet suite should be managed by the app.
# For models.py to be self-contained for definition, we might need to pass fernet_suite
# or make EncryptedString more flexible.
_fernet_suite_for_models = None
try:
    # This is a simplified key loading for model definition time.
    # In a real app, the app's configured Fernet instance should be used.
    key_env = os.getenv("ENCRYPTION_KEY")
    if key_env:
        _fernet_suite_for_models = Fernet(key_env.encode('utf-8'))
except Exception:
    # logger.critical("Failed to init Fernet for models.py context. Encryption might not work as expected.")
    pass # Avoid crashing if key not present during model definition/import time

# --- Base for SQLAlchemy models ---
Base = declarative_base()

# --- Custom EncryptedString Type ---
class EncryptedString(TypeDecorator):
    impl = Text
    cache_ok = True

    def __init__(self, *args, **kwargs):
        # Allow passing fernet_instance at runtime if needed, or use a global one.
        self.fernet = kwargs.pop('fernet_instance', _fernet_suite_for_models) # Fallback to module-level
        super().__init__(*args, **kwargs)

    def process_bind_param(self, value, dialect):
        current_fernet = self.fernet # Use instance-specific or module-level Fernet
        if value is not None and current_fernet:
            try:
                encoded_value = str(value).encode('utf-8')
                return current_fernet.encrypt(encoded_value).decode('utf-8')
            except Exception: # Simplified error handling for model context
                return str(value) # Fallback, log externally
        return value

    def process_result_value(self, value, dialect):
        current_fernet = self.fernet
        if value is not None and current_fernet:
            try:
                encrypted_bytes = str(value).encode('utf-8')
                return current_fernet.decrypt(encrypted_bytes).decode('utf-8')
            except InvalidToken:
                return None # Decryption failed
            except Exception:
                 return None # Unexpected error
        return value


# --- Enums ---
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

# --- Models ---
class User(Base):
    __tablename__ = "users"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(SQLAlchemyEnum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    preferences = Column(JSONB, default=dict)
    profile_image_path = Column(String(255))
    password_reset_token = Column(String(255), unique=True, index=True)
    password_reset_expires = Column(DateTime)

    def to_dict(self, include_sensitive=False):
        data = {
            "id": str(self.id), "username": self.username, "email": self.email,
            "full_name": self.full_name, "role": self.role.value, "is_active": self.is_active,
            "email_verified": self.email_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
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
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
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
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_id = Column(PG_UUID(as_uuid=True), ForeignKey("trees.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    access_level = Column(String(50), nullable=False, default="view")
    granted_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
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
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_id = Column(PG_UUID(as_uuid=True), ForeignKey("trees.id", ondelete="CASCADE"), nullable=False, index=True)
    first_name = Column(String(100), index=True)
    middle_names = Column(String(255))
    last_name = Column(String(100), index=True)
    maiden_name = Column(String(100))
    nickname = Column(String(100))
    gender = Column(String(20))
    birth_date = Column(Date, index=True)
    birth_date_approx = Column(Boolean, default=False)
    birth_place = Column(String(255))
    death_date = Column(Date, index=True)
    death_date_approx = Column(Boolean, default=False)
    death_place = Column(String(255))
    burial_place = Column(String(255))
    privacy_level = Column(SQLAlchemyEnum(PrivacyLevelEnum), default=PrivacyLevelEnum.inherit)
    is_living = Column(Boolean, index=True)
    notes = Column(Text) # Consider EncryptedString(fernet_instance=configured_fernet) if notes are sensitive
    custom_attributes = Column(JSONB, default=dict)
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
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
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_id = Column(PG_UUID(as_uuid=True), ForeignKey("trees.id", ondelete="CASCADE"), nullable=False, index=True)
    person1_id = Column(PG_UUID(as_uuid=True), ForeignKey("people.id", ondelete="CASCADE"), nullable=False, index=True)
    person2_id = Column(PG_UUID(as_uuid=True), ForeignKey("people.id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_type = Column(SQLAlchemyEnum(RelationshipTypeEnum), nullable=False)
    start_date = Column(Date)
    end_date = Column(Date)
    certainty_level = Column(Integer)
    custom_attributes = Column(JSONB, default=dict)
    notes = Column(Text)
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (
        UniqueConstraint("tree_id", "person1_id", "person2_id", "relationship_type", name="uq_relationship_key_fields"),
    )

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
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_id = Column(PG_UUID(as_uuid=True), ForeignKey("trees.id", ondelete="CASCADE"), nullable=False, index=True)
    person_id = Column(PG_UUID(as_uuid=True), ForeignKey("people.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    date = Column(Date, index=True)
    date_approx = Column(Boolean, default=False)
    date_range_start = Column(Date)
    date_range_end = Column(Date)
    place = Column(String(255))
    description = Column(Text)
    custom_attributes = Column(JSONB, default=dict)
    privacy_level = Column(SQLAlchemyEnum(PrivacyLevelEnum), default=PrivacyLevelEnum.inherit)
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Add to_dict if needed

class Media(Base):
    __tablename__ = "media"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_id = Column(PG_UUID(as_uuid=True), ForeignKey("trees.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(String(512), nullable=False)
    storage_bucket = Column(String(255), nullable=False)
    media_type = Column(SQLAlchemyEnum(MediaTypeEnum), nullable=False)
    original_filename = Column(String(255))
    file_size = Column(Integer)
    mime_type = Column(String(100))
    title = Column(String(255), index=True)
    description = Column(Text)
    date_taken = Column(Date)
    location = Column(String(255))
    media_metadata = Column(JSONB, default=dict)
    privacy_level = Column(SQLAlchemyEnum(PrivacyLevelEnum), default=PrivacyLevelEnum.inherit)
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Add to_dict if needed

class Citation(Base):
    __tablename__ = "citations"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_id = Column(PG_UUID(as_uuid=True), ForeignKey("trees.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = Column(PG_UUID(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"), nullable=False, index=True)
    citation_text = Column(Text, nullable=False)
    page_number = Column(String(50))
    confidence_level = Column(Integer)
    notes = Column(Text)
    custom_attributes = Column(JSONB, default=dict)
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Add to_dict if needed

class ActivityLog(Base):
    __tablename__ = "activity_log"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_id = Column(PG_UUID(as_uuid=True), ForeignKey("trees.id", ondelete="SET NULL"), index=True)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True) # Ensure this is UUID if it refers to UUID PKs
    action_type = Column(String(50), nullable=False, index=True)
    previous_state = Column(JSONB)
    new_state = Column(JSONB)
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
