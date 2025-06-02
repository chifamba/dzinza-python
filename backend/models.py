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

class TreePrivacySettingEnum(str, enum.Enum):
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"

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
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    is_public = Column(Boolean, default=False)
    default_privacy_level = Column(SQLAlchemyEnum(PrivacyLevelEnum, name="privacylevelenum", create_type=False), default=PrivacyLevelEnum.private)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    cover_image_url = Column(String(512), nullable=True) # Added cover_image_url
    privacy_setting = Column(SQLAlchemyEnum(TreePrivacySettingEnum, name="treeprivacysettingenum", create_type=False), 
                             nullable=False, default=TreePrivacySettingEnum.PRIVATE, 
                             server_default=TreePrivacySettingEnum.PRIVATE.value) # New field

    def to_dict(self):
        return {"id": str(self.id), "name": self.name, "description": self.description,
            "created_by": str(self.created_by), 
            # "is_public": self.is_public, # Removed is_public
            "privacy_setting": self.privacy_setting.value, # Added privacy_setting
            "default_privacy_level": self.default_privacy_level.value,
            "cover_image_url": self.cover_image_url, 
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

class PersonTreeAssociation(Base):
    __tablename__ = "person_tree_association"
    person_id = Column(PG_UUID(as_uuid=True), ForeignKey("people.id", ondelete="CASCADE"), primary_key=True)
    tree_id = Column(PG_UUID(as_uuid=True), ForeignKey("trees.id", ondelete="CASCADE"), primary_key=True)
    # Add any other relevant fields if needed, like 'date_added_to_tree', 'role_in_tree' (if a person can have different roles in different trees)
    # For now, keeping it simple as per the plan.
    # Consider adding a __table_args__ for a UniqueConstraint on (person_id, tree_id) if not already covered by composite primary key.
    # SQLAlchemy usually handles composite primary keys as implicitly unique.

    # Optional: Add a to_dict method if this model will be directly serialized.
    # def to_dict(self):
    #     return {
    #         "person_id": str(self.person_id),
    #         "tree_id": str(self.tree_id),
    #     }

class Person(Base):
    __tablename__ = "people"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
    custom_attributes = Column(JSONB, default=dict)
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    profile_picture_url = Column(String(512))  # Added profile_picture_url field
    custom_fields = Column(JSONB, nullable=True, default=dict)  # Added custom_fields
    display_order = Column(Integer, nullable=True, index=True) # New field for ordering

    def to_dict(self):
        return {"id": str(self.id), "first_name": self.first_name,
            "middle_names": self.middle_names, "last_name": self.last_name, "maiden_name": self.maiden_name,
            "nickname": self.nickname, "gender": self.gender,
            "birth_date": self.birth_date.isoformat() if self.birth_date else None,
            "birth_date_approx": self.birth_date_approx, "birth_place": self.birth_place,
            "place_of_birth": self.place_of_birth,
            "death_date": self.death_date.isoformat() if self.death_date else None,
            "death_date_approx": self.death_date_approx, "death_place": self.death_place,
            "place_of_death": self.place_of_death,
            "burial_place": self.burial_place, "privacy_level": self.privacy_level.value,
            "is_living": self.is_living, "notes": self.notes, "biography": self.biography, "custom_attributes": self.custom_attributes,
            "profile_picture_url": self.profile_picture_url,  # Added to to_dict
            "custom_fields": self.custom_fields,  # Added custom_fields to to_dict
            "display_order": self.display_order, # Added to to_dict
            "created_by": str(self.created_by),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None}

class Relationship(Base):
    __tablename__ = "relationships"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    person1_id = Column(PG_UUID(as_uuid=True), ForeignKey("people.id", ondelete="CASCADE"), nullable=False, index=True)
    person2_id = Column(PG_UUID(as_uuid=True), ForeignKey("people.id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_type = Column(SQLAlchemyEnum(RelationshipTypeEnum, name="relationshiptypeenum", create_type=False), nullable=False)
    start_date = Column(Date); end_date = Column(Date)
    certainty_level = Column(Integer)
    custom_attributes = Column(JSONB, default=dict)
    notes = Column(Text) 
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    location = Column(String(255), nullable=True) # Added location field
    __table_args__ = (UniqueConstraint("person1_id", "person2_id", "relationship_type", name="uq_relationship_key_fields"),)

    def to_dict(self):
        return {"id": str(self.id),
            "person1_id": str(self.person1_id), "person2_id": str(self.person2_id),
            "relationship_type": self.relationship_type.value,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "location": self.location, # Added location to to_dict
            "certainty_level": self.certainty_level, "custom_attributes": self.custom_attributes,
            "notes": self.notes, "created_by": str(self.created_by),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None}

class Event(Base):
    __tablename__ = "events"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    person_id = Column(PG_UUID(as_uuid=True), ForeignKey("people.id", ondelete="CASCADE"), nullable=True, index=True) # Changed to nullable=True
    event_type = Column(String(100), nullable=False, index=True)
    date = Column(Date, index=True); date_approx = Column(Boolean, default=False)
    date_range_start = Column(Date); date_range_end = Column(Date)
    place = Column(EncryptedString) 
    description = Column(EncryptedString) 
    custom_attributes = Column(JSONB, default=dict)
    related_person_ids = Column(JSONB, nullable=True, default=list) # New field, stores list of UUIDs as strings or actual UUIDs
    privacy_level = Column(SQLAlchemyEnum(PrivacyLevelEnum, name="privacylevelenum", create_type=False), default=PrivacyLevelEnum.inherit)
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": str(self.id),
            "person_id": str(self.person_id) if self.person_id else None, # Handle nullable person_id
            "event_type": self.event_type,
            "date": self.date.isoformat() if self.date else None,
            "date_approx": self.date_approx,
            "date_range_start": self.date_range_start.isoformat() if self.date_range_start else None,
            "date_range_end": self.date_range_end.isoformat() if self.date_range_end else None,
            "place": self.place,
            "description": self.description,
            "custom_attributes": self.custom_attributes,
            "related_person_ids": [str(pid) for pid in self.related_person_ids] if self.related_person_ids else [], # Ensure UUIDs are strings
            "privacy_level": self.privacy_level.value if self.privacy_level else None,
            "created_by": str(self.created_by),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class MediaItem(Base): # Renamed Media to MediaItem
    __tablename__ = "media" # Table name remains "media"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    uploader_user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True) # Renamed created_by
    tree_id = Column(PG_UUID(as_uuid=True), ForeignKey("trees.id", ondelete="CASCADE"), nullable=True, index=True)
    
    file_name = Column(String(255), nullable=False) # Renamed original_filename, made non-nullable
    file_type = Column(SQLAlchemyEnum(MediaTypeEnum, name="mediatypeenum", create_type=False), nullable=False) # Was media_type
    mime_type = Column(String(100)) # Existed
    file_size = Column(Integer) # Existed

    storage_path = Column(String(512), nullable=False) # Renamed file_path, removed storage_bucket
    
    linked_entity_type = Column(String(50), nullable=False, index=True) # New field
    linked_entity_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True) # New field
    
    caption = Column(Text) # Renamed description
    thumbnail_url = Column(String(512)) # New field
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True) # Renamed uploaded_at
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) # Existed

    def to_dict(self):
        return {
            "id": str(self.id),
            "uploader_user_id": str(self.uploader_user_id),
            "tree_id": str(self.tree_id) if self.tree_id else None,
            "file_name": self.file_name,
            "file_type": self.file_type.value if self.file_type else None,
            "mime_type": self.mime_type,
            "file_size": self.file_size,
            "storage_path": self.storage_path,
            "linked_entity_type": self.linked_entity_type,
            "linked_entity_id": str(self.linked_entity_id),
            "caption": self.caption,
            "thumbnail_url": self.thumbnail_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class Citation(Base):
    __tablename__ = "citations"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_id = Column(PG_UUID(as_uuid=True), ForeignKey("trees.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = Column(PG_UUID(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"), nullable=False, index=True) # This foreign key should point to 'media.id'
    citation_text = Column(Text, nullable=False); page_number = Column(String(50))
    confidence_level = Column(Integer); notes = Column(Text)
    custom_attributes = Column(JSONB, default=dict)
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TreeLayout(Base):
    __tablename__ = "tree_layouts"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    tree_id = Column(PG_UUID(as_uuid=True), ForeignKey("trees.id", ondelete="CASCADE"), nullable=False, index=True)
    layout_data = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (UniqueConstraint("user_id", "tree_id", name="uq_user_tree_layout"),)

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "tree_id": str(self.tree_id),
            "layout_data": self.layout_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

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
