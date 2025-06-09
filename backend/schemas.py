# backend/schemas.py
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime

class UserProfileUpdateSchema(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None

    @validator('full_name')
    def full_name_must_not_be_empty(cls, value):
        if value is not None and not value.strip():
            raise ValueError("Full name must not be empty.")
        return value

class NotificationPreferencesSchema(BaseModel):
    new_relative_suggestion: Optional[bool] = True
    upcoming_event_reminder: Optional[bool] = True
    new_message: Optional[bool] = True
    # Add more specific notification preferences as needed

class PrivacySettingsSchema(BaseModel):
    profile_visibility: Optional[str] = "private"  # e.g., "public", "connections_only", "private"
    tree_visibility_default: Optional[str] = "private" # e.g., "public", "connections_only", "private"
    show_activity_status: Optional[bool] = True
    # Add more specific privacy settings as needed

    @validator('profile_visibility')
    def profile_visibility_valid(cls, value):
        if value not in ["public", "connections_only", "private"]:
            raise ValueError("Invalid profile visibility setting.")
        return value

    @validator('tree_visibility_default')
    def tree_visibility_default_valid(cls, value):
        if value not in ["public", "connections_only", "private"]:
            raise ValueError("Invalid tree visibility default setting.")
        return value

class UserSettingsSchema(BaseModel):
    notification_preferences: Optional[NotificationPreferencesSchema] = NotificationPreferencesSchema()
    privacy_settings: Optional[PrivacySettingsSchema] = PrivacySettingsSchema()
    # Can add other general user settings/preferences here, e.g., language, theme

class UserResponseSchema(BaseModel):
    id: UUID
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    role: str # Consider using an Enum here if roles are fixed
    is_active: bool
    email_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    preferences: Optional[UserSettingsSchema] = None # This will hold combined settings
    profile_image_path: Optional[str] = None

    class Config:
        orm_mode = True # Enables compatibility with SQLAlchemy models

# Schema for updating only preferences (part of UserSettingsSchema)
class PreferencesUpdateSchema(BaseModel):
    notification_preferences: Optional[NotificationPreferencesSchema] = None
    privacy_settings: Optional[PrivacySettingsSchema] = None

    # Ensure at least one setting is being updated
    @validator('*', pre=True, always=True)
    def check_at_least_one_field(cls, v, values, field):
        if not values: # on first pass, values is empty
             return v
        if all(val is None for val in values.values()):
            raise ValueError("At least one preference field must be provided for an update.")
        return v

# Example of how UserSettingsSchema might be stored in User.preferences JSONB field
# {
#   "notification_preferences": {
#     "new_relative_suggestion": True,
#     "upcoming_event_reminder": False
#   },
#   "privacy_settings": {
#     "profile_visibility": "connections_only",
#     "show_activity_status": True
#   }
# }
