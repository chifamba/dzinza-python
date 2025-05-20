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
import structlog

# Base for SQLAlchemy models
Base = declarative_base()
logger = structlog.get_logger(__name__)

# Custom EncryptedString Type
class EncryptedString(TypeDecorator):
    impl = Text 
    cache_ok = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _get_fernet_instance(self):
        try:
            from extensions import get_fernet 
            fernet_instance = get_fernet()
            if fernet_instance is None:
                logger.warning("EncryptedString: Fernet suite not available. Encryption/Decryption disabled.")
            return fernet_instance
        except ImportError:
            logger.error("EncryptedString: Could not import 'get_fernet' from 'extensions'. Fernet unavailable.")
            return None
        except Exception as e:
            logger.error(f"EncryptedString: Error getting Fernet instance: {e}", exc_info=True)
            return None


    def process_bind_param(self, value, dialect):
        fernet = self._get_fernet_instance()
        if value is not None and fernet:
            try:
                encoded_value = str(value).encode('utf-8')
                return fernet.encrypt(encoded_value).decode('utf-8')
            except Exception as e:
                logger.error("Encryption failed for value.", error=str(e), exc_info=False)
                logger.critical("Storing plaintext due to encryption failure. Review key setup.")
                return str(value) 
        return value

    def process_result_value(self, value, dialect):
        fernet = self._get_fernet_instance()
        if value is not None and fernet:
            try:
                encrypted_bytes = str(value).encode('utf-8')
                return fernet.decrypt(encrypted_bytes).decode('utf-8')
            except InvalidToken:
                logger.error("Decryption failed: Invalid token.", field_value_start=str(value)[:20], exc_info=False)
                return None 
            except Exception as e:
                 logger.error("Unexpected error during decryption.", error=str(e), field_value_start=str(value)[:20], exc_info=False)
                 return None
        return value


# --- Consolidated UserRole Enum ---
class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"
    researcher = "researcher"
    guest = "guest"


# Other Enums (kept separate as they serve different purposes)
class RelationshipTypeEnum(str, enum.Enum):
    biological_parent = "biological_parent"; adoptive_parent = "adoptive_parent"; step_parent = "step_parent"
    foster_parent = "foster_parent"; guardian = "guardian"; spouse_current = "spouse_current"
    spouse_former = "spouse_former"; partner = "partner"; biological_child = "biological_child"
    adoptive_child = "adoptive_child"; step_child = "step_child"; foster_child = "foster_child"
    sibling_full = "sibling_full"; sibling_half = "sibling_half"; sibling_step = "sibling_step"
    sibling_adoptive = "sibling_adoptive"; other = "other"

class PrivacyLevelEnum(str, enum.Enum):
    inherit = "inherit"; private = "private"; public = "public"
    connections = "connections"; researchers = "researchers"

class MediaTypeEnum(str, enum.Enum):
    photo = "photo"; document = "document"; audio = "audio"; video = "video"; other = "other"

# Models
class User(Base):
    __tablename__ = "users"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255)) 
    # Uses the consolidated UserRole enum
    role = Column(SQLAlchemyEnum(UserRole, name="userrole", create_type=False), default='user', nullable=False)
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
    cover_image_url = Column(String(512))
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    is_public = Column(Boolean, default=False)
    default_privacy_level = Column(SQLAlchemyEnum(PrivacyLevelEnum, name="privacylevelenum", create_type=False), default=PrivacyLevelEnum.private)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {"id": str(self.id), "name": self.name, "description": self.description,
            "cover_image_url": self.cover_image_url,
            "created_by": str(self.created_by), "is_public": self.is_public,
            "default_privacy_level": self.default_privacy_level.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None}

class TreeAccess(Base):
    __tablename__ = "tree_access"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_id = Column(PG_UUID(as_uuid=True), ForeignKey("trees.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    access_level = Column(String(50), nullable=False, default="view") # Could also be an Enum if desired
    granted_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    granted_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("tree_id", "user_id", name="tree_user_unique"),)

    def to_dict(self):
        return {"id": str(self.id), "tree_id": str(self.tree_id), "user_id": str(self.user_id),
            "access_level": self.access_level,
            "granted_by": str(self.granted_by) if self.granted_by else None,
            "granted_at": self.granted_at.isoformat() if self.granted_at else None}

class Person(Base):
    __tablename__ = "people"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_id = Column(PG_UUID(as_uuid=True), ForeignKey("trees.id", ondelete="CASCADE"), nullable=False, index=True)
    first_name = Column(EncryptedString, index=True) 
    middle_names = Column(EncryptedString)
    last_name = Column(EncryptedString, index=True)
    maiden_name = Column(EncryptedString)
    nickname = Column(String(100))
    gender = Column(String(20))
    birth_date = Column(Date, index=True) 
    birth_date_approx = Column(Boolean, default=False)
    birth_place = Column(EncryptedString)
    place_of_birth = Column(EncryptedString)
    death_date = Column(Date, index=True)
    death_date_approx = Column(Boolean, default=False)
    death_place = Column(EncryptedString)
    place_of_death = Column(EncryptedString)
    burial_place = Column(EncryptedString)
    privacy_level = Column(SQLAlchemyEnum(PrivacyLevelEnum, name="privacylevelenum", create_type=False), default=PrivacyLevelEnum.inherit)
    is_living = Column(Boolean, index=True)
    notes = Column(EncryptedString) 
    biography = Column(EncryptedString)
    profile_picture_url = Column(String(512))
    custom_attributes = Column(JSONB, default=dict)
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    profile_picture_url = Column(String(512))  # Added profile_picture_url field
    custom_fields = Column(JSONB, nullable=True, default=dict)  # Added custom_fields

    def to_dict(self):
        return {"id": str(self.id), "tree_id": str(self.tree_id), "first_name": self.first_name,
            "middle_names": self.middle_names, "last_name": self.last_name, "maiden_name": self.maiden_name,
            "nickname": self.nickname, "gender": self.gender,
            "birth_date": self.birth_date.isoformat() if self.birth_date else None,
            "birth_date_approx": self.birth_date_approx, "birth_place": self.birth_place,
            "place_of_birth": self.place_of_birth,
            "death_date": self.death_date.isoformat() if self.death_date else None,
            "death_date_approx": self.death_date_approx, "death_place": self.death_place,
            "place_of_death": self.place_of_death,
            "burial_place": self.burial_place, "privacy_level": self.privacy_level.value,
            "is_living": self.is_living, "notes": self.notes, "biography": self.biography, 
            "profile_picture_url": self.profile_picture_url, "custom_attributes": self.custom_attributes,
            "created_by": str(self.created_by),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None}

class Relationship(Base):
    __tablename__ = "relationships"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_id = Column(PG_UUID(as_uuid=True), ForeignKey("trees.id", ondelete="CASCADE"), nullable=False, index=True)
    person1_id = Column(PG_UUID(as_uuid=True), ForeignKey("people.id", ondelete="CASCADE"), nullable=False, index=True)
    person2_id = Column(PG_UUID(as_uuid=True), ForeignKey("people.id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_type = Column(SQLAlchemyEnum(RelationshipTypeEnum, name="relationshiptypeenum", create_type=False), nullable=False)
    location = Column(EncryptedString)
    start_date = Column(Date); end_date = Column(Date)
    certainty_level = Column(Integer)
    custom_attributes = Column(JSONB, default=dict)
    notes = Column(Text) 
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (UniqueConstraint("tree_id", "person1_id", "person2_id", "relationship_type", name="uq_relationship_key_fields"),)

    def to_dict(self):
        return {"id": str(self.id), "tree_id": str(self.tree_id),
            "person1_id": str(self.person1_id), "person2_id": str(self.person2_id),
            "relationship_type": self.relationship_type.value,
            "location": self.location,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "certainty_level": self.certainty_level, "custom_attributes": self.custom_attributes,
            "notes": self.notes, "created_by": str(self.created_by),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None}

class Event(Base):
    __tablename__ = "events"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_id = Column(PG_UUID(as_uuid=True), ForeignKey("trees.id", ondelete="CASCADE"), nullable=False, index=True)
    person_id = Column(PG_UUID(as_uuid=True), ForeignKey("people.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    date = Column(Date, index=True); date_approx = Column(Boolean, default=False)
    date_range_start = Column(Date); date_range_end = Column(Date)
    place = Column(EncryptedString) 
    description = Column(EncryptedString) 
    custom_attributes = Column(JSONB, default=dict)
    privacy_level = Column(SQLAlchemyEnum(PrivacyLevelEnum, name="privacylevelenum", create_type=False), default=PrivacyLevelEnum.inherit)
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Media(Base):
    __tablename__ = "media"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_id = Column(PG_UUID(as_uuid=True), ForeignKey("trees.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(String(512), nullable=False); storage_bucket = Column(String(255), nullable=False)
    media_type = Column(SQLAlchemyEnum(MediaTypeEnum, name="mediatypeenum", create_type=False), nullable=False)
    original_filename = Column(String(255)); file_size = Column(Integer); mime_type = Column(String(100))
    title = Column(String(255), index=True); description = Column(Text)
    date_taken = Column(Date); location = Column(EncryptedString) 
    media_metadata = Column(JSONB, default=dict)
    privacy_level = Column(SQLAlchemyEnum(PrivacyLevelEnum, name="privacylevelenum", create_type=False), default=PrivacyLevelEnum.inherit)
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Citation(Base):
    __tablename__ = "citations"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_id = Column(PG_UUID(as_uuid=True), ForeignKey("trees.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = Column(PG_UUID(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"), nullable=False, index=True)
    citation_text = Column(Text, nullable=False); page_number = Column(String(50))
    confidence_level = Column(Integer); notes = Column(Text)
    custom_attributes = Column(JSONB, default=dict)
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ActivityLog(Base):
    __tablename__ = "activity_log"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_id = Column(PG_UUID(as_uuid=True), ForeignKey("trees.id", ondelete="SET NULL"), index=True)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    action_type = Column(String(50), nullable=False, index=True)
    previous_state = Column(JSONB); new_state = Column(JSONB)
    ip_address = Column(String(50)); user_agent = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {"id": str(self.id),
            "tree_id": str(self.tree_id) if self.tree_id else None,
            "user_id": str(self.user_id) if self.user_id else None,
            "entity_type": self.entity_type, "entity_id": str(self.entity_id),
            "action_type": self.action_type, "previous_state": self.previous_state,
            "new_state": self.new_state, "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "created_at": self.created_at.isoformat() if self.created_at else None}
