# Dzinza Family Tree Application - Full SQLAlchemy Models
# This file contains the SQLAlchemy ORM models for the Dzinza Family Tree application.
# The models are designed to represent the database schema and include relationships, constraints, and data types.

from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Date, ForeignKey, Text, Enum, JSON, LargeBinary, Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM, TSVECTOR
from sqlalchemy.ext.declarative import declarative_base
import enum
import uuid

Base = declarative_base()

# Enums
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

# Models
class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(Enum(RoleEnum), default=RoleEnum.user, nullable=False)
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    preferences = Column(JSONB, default=dict)
    profile_image_path = Column(String(255))

class Tree(Base):
    __tablename__ = "trees"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    is_public = Column(Boolean, default=False)
    default_privacy_level = Column(Enum(PrivacyLevelEnum), default=PrivacyLevelEnum.private)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class TreeAccess(Base):
    __tablename__ = "tree_access"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_id = Column(UUID(as_uuid=True), ForeignKey("trees.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    access_level = Column(String(50), nullable=False, default="view")
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
    gender = Column(String(20))
    birth_date = Column(Date)
    birth_date_approx = Column(Boolean, default=False)
    birth_place = Column(String(255))
    death_date = Column(Date)
    death_date_approx = Column(Boolean, default=False)
    death_place = Column(String(255))
    burial_place = Column(String(255))
    privacy_level = Column(Enum(PrivacyLevelEnum), default=PrivacyLevelEnum.inherit)
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
    relationship_type = Column(Enum(RelationshipTypeEnum), nullable=False)
    start_date = Column(Date)
    end_date = Column(Date)
    certainty_level = Column(Integer)
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
    event_type = Column(String(100), nullable=False)
    date = Column(Date)
    date_approx = Column(Boolean, default=False)
    date_range_start = Column(Date)
    date_range_end = Column(Date)
    place = Column(String(255))
    description = Column(Text)
    custom_attributes = Column(JSONB, default=dict)
    privacy_level = Column(Enum(PrivacyLevelEnum), default=PrivacyLevelEnum.inherit)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Media(Base):
    __tablename__ = "media"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_id = Column(UUID(as_uuid=True), ForeignKey("trees.id", ondelete="CASCADE"), nullable=False)
    file_path = Column(String(512), nullable=False)
    storage_bucket = Column(String(255), nullable=False)
    media_type = Column(Enum(MediaTypeEnum), nullable=False)
    original_filename = Column(String(255))
    file_size = Column(Integer)
    mime_type = Column(String(100))
    title = Column(String(255))
    description = Column(Text)
    date_taken = Column(Date)
    location = Column(String(255))
    media_metadata = Column(JSONB, default=dict)  # Renamed from 'metadata' to 'media_metadata'
    privacy_level = Column(Enum(PrivacyLevelEnum), default=PrivacyLevelEnum.inherit)
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
    tree_id = Column(UUID(as_uuid=True), ForeignKey("trees.id"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    action_type = Column(String(50), nullable=False)
    previous_state = Column(JSONB)
    new_state = Column(JSONB)
    ip_address = Column(String(50))
    user_agent = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
